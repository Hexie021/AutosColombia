from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.main import app
from app.models import CuentaOperador, Operador
from app.routers.acceso import Identidad, identidad_actual


def test_administrador_crea_lista_y_desactiva_cuentas(monkeypatch):
    db = MagicMock()
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: db)
    monkeypatch.setitem(app.dependency_overrides, identidad_actual, lambda: Identidad(1, "ADMINISTRADOR"))
    modelos = {}

    def guardar(modelo):
        if isinstance(modelo, Operador):
            modelo.id = 2
        modelos[type(modelo)] = modelo

    db.add.side_effect = guardar
    db.get.side_effect = lambda modelo, id, **kw: modelos.get(modelo)
    perfil = {"nombre": "Turno tarde", "telefono": "000", "usuario": " Nuevo "}
    clave = "una clave de prueba"
    with TestClient(app) as client:
        assert client.get("/pagos/historial").status_code == 403
        assert client.get("/operacion/catalogos").status_code == 403
        assert client.post("/acceso/cuentas", json={**perfil, "contrasena": clave, "rol": "ADMINISTRADOR"}).status_code == 422
        respuesta = client.post("/acceso/cuentas", json={**perfil, "contrasena": clave})
        assert respuesta.status_code == 201
        assert respuesta.json() == {"id": 2, **perfil, "usuario": "nuevo", "activa": True}
        assert modelos[CuentaOperador].rol == "OPERADOR"
        assert clave not in respuesta.text and modelos[CuentaOperador].clave != clave

        db.scalar.return_value = 1
        db.execute.return_value = [(modelos[CuentaOperador], modelos[Operador])]
        lista = client.get("/acceso/cuentas")
        assert lista.status_code == 200
        assert lista.json() == {"items": [respuesta.json()], "total": 1}

        cambio = client.put("/acceso/cuentas/2", json={**perfil, "activa": False})
        assert cambio.status_code == 200 and not cambio.json()["activa"]
        assert "DELETE FROM sesion_operador" in str(db.execute.call_args.args[0])

        modelos[CuentaOperador].rol = "ADMINISTRADOR"
        bloqueado = client.put("/acceso/cuentas/2", json={**perfil, "activa": False})
        assert bloqueado.status_code == 404


def test_usuario_duplicado_rollback_y_validacion_privada(monkeypatch):
    db = MagicMock()
    monkeypatch.setitem(app.dependency_overrides, get_session, lambda: db)
    monkeypatch.setitem(app.dependency_overrides, identidad_actual, lambda: Identidad(1, "ADMINISTRADOR"))
    db.flush.side_effect = [None, IntegrityError("INSERT", {}, SimpleNamespace(sqlstate="23505"))]
    with TestClient(app) as client:
        payload = {"nombre": "Turno tarde", "telefono": "000", "usuario": "ocupado"}
        invalida = client.post("/acceso/cuentas", json={**payload, "contrasena": "corta"})
        assert invalida.status_code == 422 and "corta" not in invalida.text
        duplicada = client.post("/acceso/cuentas", json={**payload, "contrasena": "una clave de prueba"})
        assert duplicada.status_code == 409
        db.rollback.assert_called_once()
