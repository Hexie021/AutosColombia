"""Verifica el flujo EA1 contra PostgreSQL; revierte todos sus datos al terminar."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.database import get_engine
from app.models import Cliente, Vehiculo, Celda, Operador, VigenciaMensualidad, IncidenciaSalida, CorreccionCelda, siguiente_mes
from app.schemas.operacion import EntradaOperacion, SalidaOperacion, CorreccionOperacion
from app.services.operacion import ServicioOperacion
from app.services.estancia import EstanciaError
from app.config import load_database_settings


def main() -> int:
    settings = load_database_settings()
    if settings.host not in {'127.0.0.1','localhost'} or settings.name != 'autos_colombia':
        print('La verificación requiere la base local autos_colombia.')
        return 1
    token = 'VERIF-' + uuid4().hex[:12].upper()
    connection = None
    exterior = None
    try:
        connection = get_engine().connect()
        exterior = connection.begin()
        with Session(bind=connection, join_transaction_mode='create_savepoint') as s:
            ahora = datetime.now(timezone.utc)
            with s.begin():
                cliente = Cliente(nombre='Cliente ficticio de prueba', documento=token)
                operador = Operador(nombre=token, telefono='0000000000')
                celda = Celda(codigo=token, tipo='AUTOMOVIL_CAMIONETA')
                s.add_all([cliente, operador, celda]); s.flush()
                activos = []
                for n, tipo in enumerate(['AUTOMOVIL','MOTO','AUTOMOVIL']):
                    v = Vehiculo(cliente_id=cliente.id, placa=f'{token}-{n}', marca='Prueba', color='Gris', modelo=2022, tipo=tipo)
                    s.add(v); s.flush(); activos.append(v)
                    inicio = ahora - timedelta(days=1 if n < 2 else 60)
                    s.add(VigenciaMensualidad(vehiculo_id=v.id, inicio=inicio, vencimiento=siguiente_mes(inicio)))
                otra = Celda(codigo=token+'-B', tipo='AUTOMOVIL_CAMIONETA')
                s.add_all([otra, Celda(codigo=token+'-M', tipo='MOTO')]); s.flush()
                alternativa = otra.id
                placas = [v.placa for v in activos]
                operador_id, nueva_celda = operador.id, celda.id
            servicio = ServicioOperacion(s)
            def rechaza(operacion, fragmento):
                try:
                    operacion()
                except EstanciaError as error:
                    assert fragmento in error.detail, error.detail
                else:
                    raise AssertionError('Se aceptó una operación que debía rechazarse.')
            car = servicio.registrar_entrada(EntradaOperacion(placa=placas[0], operador_id=operador_id))
            rechaza(lambda: servicio.registrar_entrada(EntradaOperacion(placa=placas[0], operador_id=operador_id)), 'ya está dentro')
            rechaza(lambda: servicio.registrar_entrada(EntradaOperacion(placa=placas[2], operador_id=operador_id)), 'mensualidad')
            if car['celda_id'] == nueva_celda:
                nueva_celda = alternativa
            corregida = servicio.corregir(CorreccionOperacion(estancia_id=car['id'], celda_id=nueva_celda, operador_id=operador_id, motivo='Prueba controlada'))
            assert corregida['id'] == car['id'] and corregida['entrada'] == car['entrada']
            reimpresa = servicio.comprobante(car['id'])
            assert reimpresa['celda_id'] == nueva_celda
            rechaza(lambda: servicio.registrar_salida(SalidaOperacion(placa=placas[0], operador_id=operador_id, comprobante_id=car['id']+999999)), 'comprobante')
            with s.begin():
                vigencia = s.scalar(select(VigenciaMensualidad).where(VigenciaMensualidad.vehiculo_id == activos[0].id))
                vigencia.inicio = ahora - timedelta(days=60)
                vigencia.vencimiento = ahora - timedelta(days=1)
            salida = servicio.registrar_salida(SalidaOperacion(placa=placas[0], operador_id=operador_id, comprobante_id=car['id']))
            assert salida['salida'] is not None
            moto = servicio.registrar_entrada(EntradaOperacion(placa=placas[1], operador_id=operador_id))
            rechaza(lambda: servicio.registrar_salida(SalidaOperacion(placa=placas[1], operador_id=operador_id, perdido=True, documento='NO-COINCIDE', motivo='Pérdida', identidad_verificada=True)), 'documento')
            servicio.registrar_salida(SalidaOperacion(placa=placas[1], operador_id=operador_id, perdido=True, documento=token, motivo='Pérdida verificada', identidad_verificada=True))
            assert servicio.listado(True, placas[0], None, None, 0, 20)['total'] == 0
            assert servicio.listado(False, placas[0], None, None, 0, 20)['total'] == 1
            with s.begin():
                assert s.scalar(select(func.count()).select_from(IncidenciaSalida).where(IncidenciaSalida.estancia_id == moto['id'])) == 1
                assert s.scalar(select(func.count()).select_from(CorreccionCelda).where(CorreccionCelda.estancia_id == car['id'])) == 1
        print('CORRECTO: entrada automática, duplicado, mensualidad vencida, corrección y reimpresión.')
        print('CORRECTO: comprobante incorrecto, salida con vigencia vencida, pérdida e identidad incorrecta.')
        print('CORRECTO: presentes, historial y registros de incidencia/corrección.')
        return 0
    except Exception as error:
        if isinstance(error, (AssertionError, EstanciaError)):
            print('La verificación detectó una diferencia en una regla del flujo EA1.')
        else:
            print('No se completó la verificación. Revisa conexión, permisos y migración 0003.')
        return 1
    finally:
        if exterior is not None:
            exterior.rollback()
        if connection is not None:
            connection.close()
        print('Datos temporales revertidos. Las secuencias de identificadores pueden avanzar.')

if __name__ == '__main__':
    raise SystemExit(main())
