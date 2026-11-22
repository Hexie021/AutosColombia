from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.database import get_session
from app.main import app
from app.models import CuentaOperador, Operador, SesionOperador
from app.routers.acceso import COOKIE, hash_token, huella_clave


def test_acceso_emite_cookie_y_protege_catalogo():
    cuenta = CuentaOperador(
        operador_id=1, usuario="operador", clave=huella_clave("clave de prueba"), rol="OPERADOR", activa=True
    )
    operador = Operador(id=1, nombre="Operador", telefono="000")
    sesiones = {}
    db = MagicMock()
    db.scalar.return_value = cuenta

    def buscar(model, key, **kwargs):
        if model is CuentaOperador:
            return cuenta
        if model is Operador:
            return operador
        return sesiones.get(key)

    def registrar(sesion):
        sesiones[sesion.token] = sesion

    db.get.side_effect = buscar
    db.add.side_effect = registrar

    def override():
        yield db

    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            assert client.get("/celdas").status_code == 401
            rechazo = client.post("/acceso/iniciar", json={"usuario": "operador", "contrasena": "incorrecta"})
            assert rechazo.status_code == 401 and COOKIE not in client.cookies
            acceso = client.post("/acceso/iniciar", json={"usuario": "OPERADOR", "contrasena": "clave de prueba"})
            assert acceso.status_code == 200
            assert "HttpOnly" in acceso.headers["set-cookie"]
            assert acceso.json()["rol"] == "OPERADOR"
            assert client.get("/acceso/sesion").json()["id"] == 1
            assert client.get("/celdas").status_code == 403
            assert client.get("/acceso/cuentas").status_code == 403
            cuenta.activa = False
            assert client.get("/acceso/sesion").status_code == 401
            assert client.post("/acceso/iniciar", json={"usuario": "operador", "contrasena": "clave de prueba"}).status_code == 401
            cuenta.activa = True
            cambio = client.post("/acceso/contrasena", json={"actual": "incorrecta", "nueva": "otra clave de prueba"})
            assert cambio.status_code == 400
            cambio = client.post("/acceso/contrasena", json={"actual": "clave de prueba", "nueva": "otra clave de prueba"})
            assert cambio.status_code == 204 and COOKIE not in client.cookies
            assert client.post("/acceso/iniciar", json={"usuario": "operador", "contrasena": "clave de prueba"}).status_code == 401
            assert client.post("/acceso/iniciar", json={"usuario": "operador", "contrasena": "otra clave de prueba"}).status_code == 200
            sesiones[hash_token(client.cookies[COOKIE])].vence = datetime.now(timezone.utc) - timedelta(seconds=1)
            assert client.get("/acceso/sesion").status_code == 401
            assert client.post("/acceso/cerrar").status_code == 204
            assert COOKIE not in client.cookies
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_validacion_no_devuelve_credenciales():
    with TestClient(app) as client:
        response = client.post("/acceso/iniciar", json={"usuario": "", "contrasena": "dato reservado"})
        assert response.status_code == 422
        assert "dato reservado" not in response.text
