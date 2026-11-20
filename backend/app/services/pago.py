"""Mensualidades y comprobantes de pagos recibidos por el operador."""
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select

from app.models import Estancia, Operador, PagoMensualidad, Vehiculo, VigenciaMensualidad, siguiente_mes
from app.schemas.pago import PagoCrear
from app.services.estancia import EstanciaError, ServicioEstancia, transaccion
from app.services.operacion import BOGOTA, vigencia_en_fecha

TARIFAS = {"MOTO": 100_000, "AUTOMOVIL": 150_000, "CAMIONETA": 150_000}


def ahora_pago() -> datetime:
    return datetime.now(timezone.utc)


def periodo(vigencia: VigenciaMensualidad | None) -> dict | None:
    if vigencia is None:
        return None
    return {"id": vigencia.id, "inicio": vigencia.inicio, "vencimiento": vigencia.vencimiento}


class ServicioPago(ServicioEstancia):
    def _ultima_vigencia(self, vehiculo_id: int) -> VigenciaMensualidad | None:
        return self.session.scalar(
            select(VigenciaMensualidad)
            .where(VigenciaMensualidad.vehiculo_id == vehiculo_id)
            .order_by(VigenciaMensualidad.vencimiento.desc(), VigenciaMensualidad.id.desc())
            .limit(1)
        )

    def _mora(self, vehiculo_id: int) -> list[Estancia]:
        return list(self.session.scalars(
            select(Estancia)
            .where(Estancia.vehiculo_id == vehiculo_id, Estancia.mora_pendiente.is_(True))
            .order_by(Estancia.id.desc())
        ))

    def _detalle(self, pago: PagoMensualidad) -> dict:
        regularizadas = self.session.scalars(
            select(Estancia.id)
            .where(Estancia.mora_regularizada_pago_id == pago.id)
            .order_by(Estancia.id)
        )
        return {
            "referencia": pago.referencia,
            "placa": pago.placa,
            "tipo": pago.tipo,
            "cliente": pago.cliente,
            "operador": pago.operador,
            "fecha": pago.fecha,
            "concepto": pago.concepto,
            "importe": pago.importe,
            "vigencia": periodo(pago.vigencia),
            "estancias_regularizadas": list(regularizadas),
        }

    @transaccion
    def consultar(self, placa: str) -> dict:
        vehiculo = self._vehiculo(placa)
        ahora = ahora_pago()
        ultima = self._ultima_vigencia(vehiculo.id)
        activa = vigencia_en_fecha(self.session, vehiculo.id, ahora)
        pendientes = self._mora(vehiculo.id)
        inicio = max(ahora, ultima.vencimiento) if ultima else ahora
        return {
            "placa": vehiculo.placa,
            "tipo": vehiculo.tipo,
            "marca": vehiculo.marca,
            "cliente": vehiculo.cliente.nombre,
            "tarifa": TARIFAS[vehiculo.tipo],
            "vigencia_actual": periodo(activa),
            "ultima_vigencia": periodo(ultima),
            "mora_pendiente": [
                {"estancia_id": e.id, "salida": e.salida, "operador": e.operador_salida.nombre}
                for e in pendientes
            ],
            "periodo_estimado": {"inicio": inicio, "vencimiento": siguiente_mes(inicio)},
        }

    @transaccion
    def registrar(self, data: PagoCrear, operador_id: int) -> tuple[dict, bool]:
        # Entrada y salida toman el mismo bloqueo antes de leer la vigencia.
        vehiculo = self._vehiculo(data.placa, bloquear=True)
        anterior = self.session.scalar(
            select(PagoMensualidad).where(PagoMensualidad.solicitud_id == data.solicitud_id)
        )
        if anterior is not None:
            if (anterior.vehiculo_id, anterior.importe, anterior.vigencia_anterior_id,
                    anterior.mora_pendiente_id) != (
                    vehiculo.id, data.importe, data.ultima_vigencia_id, data.mora_pendiente_id):
                raise EstanciaError(409, "La solicitud ya corresponde a otro pago.")
            return self._detalle(anterior), False

        ultima = self._ultima_vigencia(vehiculo.id)
        pendientes = self._mora(vehiculo.id)
        if (ultima.id if ultima else None, pendientes[0].id if pendientes else None) != (
                data.ultima_vigencia_id, data.mora_pendiente_id):
            raise EstanciaError(409, "La vigencia o la mora cambió. Vuelve a consultar la placa.")
        if data.importe != TARIFAS[vehiculo.tipo]:
            raise EstanciaError(422, "El importe no corresponde a la tarifa del vehículo.")

        operador = self.session.get(Operador, operador_id)
        if operador is None:
            raise EstanciaError(401, "Inicia sesión para continuar.")
        ahora = ahora_pago()
        inicio = max(ahora, ultima.vencimiento) if ultima else ahora
        vigencia = VigenciaMensualidad(vehiculo_id=vehiculo.id, inicio=inicio, vencimiento=siguiente_mes(inicio))
        concepto = "RENOVACION_CON_MORA" if pendientes else "RENOVACION" if ultima else "PRIMERA_MENSUALIDAD"
        pago = PagoMensualidad(
            solicitud_id=data.solicitud_id, vehiculo_id=vehiculo.id, vigencia=vigencia,
            vigencia_anterior_id=data.ultima_vigencia_id, mora_pendiente_id=data.mora_pendiente_id,
            operador_id=operador.id, fecha=ahora, concepto=concepto,
            importe=data.importe, placa=vehiculo.placa, tipo=vehiculo.tipo,
            cliente=vehiculo.cliente.nombre, operador=operador.nombre,
        )
        self.session.add(pago)
        self.session.flush()
        for estancia in pendientes:
            estancia.mora_pendiente = False
            estancia.mora_regularizada_pago_id = pago.id
        return self._detalle(pago), True

    @transaccion
    def comprobante(self, pago_id: int) -> dict:
        pago = self.session.get(PagoMensualidad, pago_id)
        if pago is None:
            raise EstanciaError(404, "Comprobante de pago no encontrado.")
        return self._detalle(pago)

    @transaccion
    def historial(self, placa: str, desde: date | None, hasta: date | None, offset: int, limit: int) -> dict:
        if desde and hasta and desde > hasta:
            raise EstanciaError(422, "La fecha inicial no puede ser posterior a la final.")
        query = select(PagoMensualidad)
        if placa.strip():
            query = query.where(PagoMensualidad.placa == placa.strip().upper())
        if desde:
            query = query.where(PagoMensualidad.fecha >= datetime.combine(desde, time.min, BOGOTA))
        if hasta and hasta < date.max:
            query = query.where(PagoMensualidad.fecha < datetime.combine(hasta + timedelta(days=1), time.min, BOGOTA))
        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        pagos = self.session.scalars(
            query.order_by(PagoMensualidad.fecha.desc(), PagoMensualidad.id.desc()).offset(offset).limit(limit)
        )
        return {
            "items": [
                {"id": p.id, "referencia": p.referencia, "placa": p.placa, "fecha": p.fecha,
                 "concepto": p.concepto, "importe": p.importe, "operador": p.operador}
                for p in pagos
            ],
            "total": total,
        }
