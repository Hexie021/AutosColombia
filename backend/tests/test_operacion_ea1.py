"""Reglas del servicio sin conexión; la verificación real está en verificar_ea1.py."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
import pytest
from pydantic import ValidationError
from app.models import Cliente, Vehiculo, Operador, Estancia, Celda
from app.schemas.operacion import EntradaOperacion, SalidaOperacion, CorreccionOperacion
from app.services.estancia import EstanciaError
from app.services.operacion import ServicioOperacion, tipo_celda

@pytest.mark.parametrize('tipo, esperado', [('MOTO','MOTO'),('AUTOMOVIL','AUTOMOVIL_CAMIONETA'),('CAMIONETA','AUTOMOVIL_CAMIONETA')])
def test_compatibilidad(tipo, esperado):
    assert tipo_celda(tipo) == esperado

@pytest.mark.parametrize('extra', [{'celda_id':1}, {'entrada':'2026-01-01'}, {'operador_id':True}])
def test_entrada_no_acepta_celda_fecha_ni_operador_booleano(extra):
    with pytest.raises(ValidationError):
        EntradaOperacion(**{'placa':'ABC123','operador_id':1, **extra})

@pytest.mark.parametrize('datos', [{}, {'perdido':True}, {'perdido':True,'documento':'DEMO','motivo':'Perdido'}, {'perdido':True,'documento':'DEMO','motivo':' ','identidad_verificada':True}])
def test_salida_requiere_respaldo(datos):
    with pytest.raises(ValidationError):
        SalidaOperacion(placa='ABC123', operador_id=1, **datos)

def test_rechaza_mensualidad_sin_crear_estancia():
    session=MagicMock()
    vehicle=Vehiculo(id=1, cliente_id=1, placa='ABC123',color='Gris',modelo=2022,marca='Demo',tipo='AUTOMOVIL')
    session.scalar.return_value=vehicle
    service=ServicioOperacion(session)
    with patch.object(service,'_operador'), patch.object(service,'_abierta',return_value=None), patch.object(service,'_vigencia',return_value=None):
        with pytest.raises(EstanciaError,match='mensualidad'):
            service.registrar_entrada(EntradaOperacion(placa='ABC123',operador_id=1))
    session.add.assert_not_called()

@pytest.mark.parametrize('perdido', [False,True])
def test_documento_o_comprobante_incorrecto_no_cierra(perdido):
    session=MagicMock()
    vehicle=Vehiculo(id=1,cliente_id=1,placa='ABC123',color='Gris',modelo=2022,marca='Demo',tipo='AUTOMOVIL')
    vehicle.cliente=Cliente(id=1,nombre='Demo',documento='DEMO-001')
    estancia=Estancia(id=3,vehiculo_id=1,celda_id=1,entrada=datetime.now(timezone.utc)-timedelta(hours=1),salida=None)
    service=ServicioOperacion(session)
    payload=SalidaOperacion(placa='ABC123',operador_id=1,comprobante_id=999,perdido=perdido,documento='OTRO',motivo='Pérdida',identidad_verificada=True)
    with patch.object(service,'_vehiculo',return_value=vehicle), patch.object(service,'_operador'), patch.object(service,'_abierta',return_value=estancia):
        with pytest.raises(EstanciaError): service.registrar_salida(payload)
    assert estancia.salida is None
    session.add.assert_not_called()

def test_correccion_incompatible_no_modifica_la_estancia():
    session=MagicMock()
    vehicle=Vehiculo(id=1,cliente_id=1,placa='ABC123',color='Gris',modelo=2022,marca='Demo',tipo='AUTOMOVIL')
    estancia=Estancia(id=3,vehiculo_id=1,celda_id=1,salida=None)
    estancia.vehiculo=vehicle
    session.scalar.side_effect=[estancia, Celda(id=2,codigo='M01',tipo='MOTO')]
    service=ServicioOperacion(session)
    with patch.object(service,'_operador'):
        with pytest.raises(EstanciaError,match='compatible'):
            service.corregir(CorreccionOperacion(estancia_id=3,celda_id=2,operador_id=1,motivo='Cambio'))
    assert estancia.celda_id==1
    session.add.assert_not_called()

def test_colision_de_celda_intenta_otra_sin_repetir_la_entrada():
    from types import SimpleNamespace
    from sqlalchemy.exc import IntegrityError
    session = MagicMock()
    vehicle = Vehiculo(id=1, cliente_id=1, placa='ABC123',color='Gris',modelo=2022,marca='Demo',tipo='AUTOMOVIL')
    session.scalar.side_effect = [vehicle, Celda(id=11,codigo='A01',tipo='AUTOMOVIL_CAMIONETA'), Celda(id=12,codigo='A02',tipo='AUTOMOVIL_CAMIONETA')]
    driver = Exception('detalle privado')
    driver.diag = SimpleNamespace(constraint_name='uq_estancia_celda_abierta')
    session.flush.side_effect = [IntegrityError('INSERT',{},driver), None]
    service = ServicioOperacion(session)
    with patch.object(service,'_operador',return_value=Operador(id=1,nombre='Ana',telefono='000')), patch.object(service,'_abierta',return_value=None), patch.object(service,'_vigencia',return_value=object()), patch.object(service,'_detalle',return_value={'id': 9,'celda':'A02'}):
        result = service.registrar_entrada(EntradaOperacion(placa='ABC123',operador_id=1))
    assert result['celda'] == 'A02'
    assert [call.args[0].celda_id for call in session.add.call_args_list] == [11,12]
    assert session.begin_nested.call_count == 2
