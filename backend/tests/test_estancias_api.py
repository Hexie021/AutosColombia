from fastapi.testclient import TestClient
import pytest

from app.main import app


def test_openapi_y_salud():
    with TestClient(app) as client:
        schema = client.get('/openapi.json').json()
        for path, method in [('/operacion/entrada', 'post'), ('/operacion/salida', 'post'),
                             ('/operacion/vehiculo/{placa}', 'get'), ('/operacion/correccion', 'post'), ('/operacion/catalogos', 'get')]:
            assert method in schema['paths'][path]
        assert client.get('/health').json() == {'status': 'ok'}


@pytest.mark.parametrize('payload', [
    {}, {'placa': ' ', 'celda_id': 1, 'operador_id': 1},
    {'placa': None, 'celda_id': 1, 'operador_id': 1},
    {'placa': 'TEST', 'celda_id': 0, 'operador_id': 1},
    {'placa': 'TEST', 'celda_id': True, 'operador_id': 1},
    {'placa': 'TEST', 'celda_id': '1', 'operador_id': 1},
    {'placa': 'TEST', 'celda_id': 1, 'operador_id': None},
    {'placa': 'TEST', 'celda_id': 1, 'operador_id': 9223372036854775808},
    {'placa': 'TEST', 'celda_id': 1, 'operador_id': 1, 'entrada': '2026-01-01'},
])
def test_entrada_invalida(payload):
    with TestClient(app) as client:
        assert client.post('/operacion/entrada', json=payload).status_code == 422


def test_salida_no_admite_celda_ni_fecha():
    with TestClient(app) as client:
        for extra in ({'celda_id': 1}, {'salida': '2026-01-01'}, {'id': 1}):
            assert client.post('/operacion/salida', json={'placa': 'TEST', 'operador_id': 1, **extra}).status_code == 422
        assert client.get('/operacion/vehiculo/%20%20').status_code == 422

def test_contrato_entrada_http_y_errores_publicos(monkeypatch):
    from app.database import get_session
    from app.services.operacion import ServicioOperacion
    def session_ficticia():
        yield object()
    app.dependency_overrides[get_session] = session_ficticia
    try:
        monkeypatch.setattr(ServicioOperacion, 'registrar_entrada', lambda self, data: {'id': 31, 'placa': data.placa, 'celda': 'A01'})
        with TestClient(app) as client:
            response = client.post('/operacion/entrada', json={'placa': ' abc123 ', 'operador_id': 1})
            assert response.status_code == 201
            assert response.json() == {'id': 31, 'placa': 'ABC123', 'celda': 'A01'}
            from app.services.estancia import EstanciaError
            def conflicto(self, data):
                raise EstanciaError(409, 'El vehículo ya está dentro.')
            monkeypatch.setattr(ServicioOperacion, 'registrar_entrada', conflicto)
            result = client.post('/operacion/entrada', json={'placa': 'ABC123', 'operador_id': 1})
            assert result.status_code == 409
            assert result.json() == {'detail': 'El vehículo ya está dentro.'}
    finally:
        app.dependency_overrides.clear()
