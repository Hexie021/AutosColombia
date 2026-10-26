"""Operación transaccional EA1 sobre los modelos del profesor."""
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from app.models import Celda, CorreccionCelda, Estancia, IncidenciaSalida, Operador, Vehiculo, VigenciaMensualidad, required_text
from app.schemas.operacion import EntradaOperacion, SalidaOperacion, CorreccionOperacion
from app.services.estancia import ServicioEstancia, EstanciaError, transaccion

BOGOTA = ZoneInfo("America/Bogota")

def tipo_celda(tipo: str) -> str:
    return "MOTO" if tipo == "MOTO" else "AUTOMOVIL_CAMIONETA"

class ServicioOperacion(ServicioEstancia):
    def _vigencia(self, vehiculo_id: int, ahora: datetime):
        return self.session.scalar(select(VigenciaMensualidad).where(
            VigenciaMensualidad.vehiculo_id == vehiculo_id,
            VigenciaMensualidad.inicio <= ahora, VigenciaMensualidad.vencimiento > ahora,
        ).order_by(VigenciaMensualidad.vencimiento.desc()).limit(1))

    def _abierta(self, vehiculo_id: int, bloquear: bool = False):
        query = select(Estancia).where(Estancia.vehiculo_id == vehiculo_id, Estancia.salida.is_(None))
        return self.session.scalar(query.with_for_update() if bloquear else query)

    def _detalle(self, estancia: Estancia) -> dict:
        vehiculo = self.session.get(Vehiculo, estancia.vehiculo_id)
        celda = self.session.get(Celda, estancia.celda_id)
        return {"id": estancia.id, "placa": vehiculo.placa, "tipo": vehiculo.tipo,
                "cliente": vehiculo.cliente.nombre, "celda": celda.codigo,
                "celda_id": celda.id, "entrada": estancia.entrada, "salida": estancia.salida,
                "operador_entrada": estancia.operador_entrada.nombre,
                "operador_salida": estancia.operador_salida.nombre if estancia.operador_salida else None}

    @transaccion
    def consultar_operacion(self, placa: str) -> dict:
        vehiculo = self._vehiculo(required_text(placa, "placa").upper())
        vigencia = self._vigencia(vehiculo.id, datetime.now(timezone.utc))
        estancia = self._abierta(vehiculo.id)
        return {"placa": vehiculo.placa, "marca": vehiculo.marca, "modelo": vehiculo.modelo,
                "color": vehiculo.color, "tipo": vehiculo.tipo, "cliente": vehiculo.cliente.nombre,
                "vigencia": {"inicio": vigencia.inicio, "vencimiento": vigencia.vencimiento} if vigencia else None,
                "estancia": self._detalle(estancia) if estancia else None}

    @transaccion
    def registrar_entrada(self, data: EntradaOperacion) -> dict:
        # Bloquea la placa para serializar ingresos duplicados.
        vehiculo = self.session.scalar(select(Vehiculo).where(Vehiculo.placa == data.placa).with_for_update())
        if vehiculo is None:
            raise EstanciaError(404, "Vehículo no registrado.")
        operador = self._operador(data.operador_id)
        if self._abierta(vehiculo.id):
            raise EstanciaError(409, "El vehículo ya está dentro.")
        ahora = datetime.now(timezone.utc)
        if self._vigencia(vehiculo.id, ahora) is None:
            raise EstanciaError(409, "El vehículo no tiene una mensualidad vigente. No se permite el ingreso.")
        # Si otra entrada reserva una celda, intenta otra libre y compatible.
        ocupada = select(Estancia.id).where(Estancia.celda_id == Celda.id, Estancia.salida.is_(None)).exists()
        intentadas: list[int] = []
        while True:
            celda = self.session.scalar(select(Celda).where(
                Celda.tipo == tipo_celda(vehiculo.tipo), ~ocupada,
                Celda.id.not_in(intentadas),
            ).order_by(Celda.codigo).with_for_update(skip_locked=True).limit(1))
            if celda is None:
                raise EstanciaError(409, "No hay una celda compatible disponible. Reintenta si hay otra operación en curso.")
            celda_id = celda.id
            try:
                # El índice único resuelve incluso carreras entre instantáneas SQL.
                with self.session.begin_nested():
                    estancia = Estancia(vehiculo_id=vehiculo.id, celda_id=celda_id,
                                        operador_entrada_id=operador.id, entrada=ahora)
                    self.session.add(estancia)
                    self.session.flush()
                return self._detalle(estancia)
            except IntegrityError as error:
                nombre = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
                if nombre != "uq_estancia_celda_abierta":
                    raise
                intentadas.append(celda_id)

    @transaccion
    def registrar_salida(self, data: SalidaOperacion) -> dict:
        vehiculo = self._vehiculo(data.placa)
        operador = self._operador(data.operador_id)
        estancia = self._abierta(vehiculo.id, bloquear=True)
        if estancia is None:
            raise EstanciaError(409, "El vehículo no tiene una estancia abierta.")
        if data.perdido:
            if data.documento.strip() != vehiculo.cliente.documento:
                raise EstanciaError(409, "El documento no coincide con el cliente asociado. No se autoriza la salida.")
            self.session.add(IncidenciaSalida(estancia_id=estancia.id, operador_id=operador.id,
                fecha=datetime.now(timezone.utc), motivo=data.motivo.strip(), identidad_verificada=True))
        elif data.comprobante_id != estancia.id:
            raise EstanciaError(409, "El comprobante no corresponde a la estancia abierta de esta placa.")
        # Una mensualidad vencida durante la estancia no bloquea la salida.
        estancia.cerrar(datetime.now(timezone.utc), operador)
        self.session.flush()
        return self._detalle(estancia)

    @transaccion
    def corregir(self, data: CorreccionOperacion) -> dict:
        operador = self._operador(data.operador_id)
        estancia = self.session.scalar(select(Estancia).where(Estancia.id == data.estancia_id).with_for_update())
        if estancia is None or estancia.salida is not None:
            raise EstanciaError(409, "La corrección requiere una estancia abierta.")
        if estancia.celda_id == data.celda_id:
            raise EstanciaError(409, "Selecciona una celda diferente a la actual.")
        celda = self.session.scalar(select(Celda).where(Celda.id == data.celda_id).with_for_update())
        if celda is None:
            raise EstanciaError(404, "Celda no encontrada.")
        if not celda.es_compatible(estancia.vehiculo.tipo):
            raise EstanciaError(409, "La celda no es compatible con el vehículo.")
        if self.session.scalar(select(Estancia.id).where(Estancia.celda_id == celda.id, Estancia.salida.is_(None))):
            raise EstanciaError(409, "La celda está ocupada.")
        self.session.add(CorreccionCelda(estancia_id=estancia.id, celda_anterior_id=estancia.celda_id,
            celda_nueva_id=celda.id, operador_id=operador.id, motivo=data.motivo))
        estancia.celda_id = celda.id
        self.session.flush()
        return self._detalle(estancia)

    @transaccion
    def comprobante(self, estancia_id: int) -> dict:
        estancia = self.session.get(Estancia, estancia_id)
        if estancia is None:
            raise EstanciaError(404, "Estancia no encontrada.")
        return self._detalle(estancia)

    @transaccion
    def catalogos(self) -> dict:
        # Una misma instantánea para celdas y ocupación; evita contadores parciales.
        rows = self.session.execute(select(Celda, Estancia.id).outerjoin(Estancia,
            (Estancia.celda_id == Celda.id) & Estancia.salida.is_(None)).order_by(Celda.codigo)).all()
        celdas = [{"id": c.id, "codigo": c.codigo, "tipo": c.tipo, "ocupada": e is not None} for c, e in rows]
        presentes = sum(c["ocupada"] for c in celdas)
        return {"operadores": [{"id": o.id, "nombre": o.nombre} for o in self.session.scalars(select(Operador).order_by(Operador.id))],
                "celdas": celdas, "resumen": {"presentes": presentes, "libres": len(celdas) - presentes,
                    "inscritos": self.session.scalar(select(func.count()).select_from(Vehiculo)),
                    "motos_libres": sum(c["tipo"] == "MOTO" and not c["ocupada"] for c in celdas),
                    "autos_libres": sum(c["tipo"] == "AUTOMOVIL_CAMIONETA" and not c["ocupada"] for c in celdas)}}

    @transaccion
    def listado(self, presentes: bool, placa: str, desde: date | None, hasta: date | None, offset: int, limit: int) -> dict:
        if desde and hasta and desde > hasta:
            raise EstanciaError(422, "La fecha inicial no puede ser posterior a la final.")
        query = select(Estancia).join(Vehiculo)
        if presentes:
            query = query.where(Estancia.salida.is_(None))
        if placa.strip():
            query = query.where(Vehiculo.placa == placa.strip().upper())
        if desde:
            query = query.where(Estancia.entrada >= datetime.combine(desde, time.min, BOGOTA))
        if hasta:
            query = query.where(Estancia.entrada < datetime.combine(hasta + timedelta(days=1), time.min, BOGOTA))
        total = self.session.scalar(select(func.count()).select_from(query.subquery()))
        items = self.session.scalars(query.order_by(Estancia.entrada.desc(), Estancia.id.desc()).offset(offset).limit(limit))
        return {"items": [self._detalle(e) for e in items], "total": total, "offset": offset, "limit": limit}
