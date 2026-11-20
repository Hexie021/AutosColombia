"""Validación del contrato y pruebas del flujo completo en PostgreSQL aislado."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import load_database_settings
from app.database import get_engine, get_session
from app.main import app
from app.models import (
    Celda, Cliente, CuentaOperador, Estancia, Operador, PagoMensualidad,
    SesionOperador, Vehiculo, VigenciaMensualidad,
)
from app.routers.acceso import COOKIE, hash_token
from app.services.pago import ServicioPago

require_db = pytest.mark.skipif(
    os.getenv("RUN_EA3_POSTGRES_TESTS") != "1", reason="Requiere la base aislada autos_colombia_ea3_test."
)
AHORA = datetime.fromisoformat("2027-01-31T10:00:00-05:00")


def test_pagos_requiere_sesion_en_las_cuatro_rutas(monkeypatch):
    with Session() as sesion:
        monkeypatch.setitem(app.dependency_overrides, get_session, lambda: sesion)
        with TestClient(app) as cliente:
            for ruta in ("/pagos/vehiculo/ABC123", "/pagos/historial", "/pagos/comprobante/1"):
                assert cliente.get(ruta).status_code == 401
            assert cliente.post("/pagos/mensualidad", json={}).status_code == 401


@pytest.fixture
def preparar(monkeypatch):
    settings = load_database_settings()
    assert settings.name == "autos_colombia_ea3_test"
    assert settings.host in {"localhost", "127.0.0.1"}
    monkeypatch.setattr("app.services.pago.ahora_pago", lambda: AHORA)

    def crear(tipo="AUTOMOVIL", vencimiento=None, con_mora=False):
        identificador = uuid4().hex
        placa = identificador[:8].upper()
        token = uuid4().hex
        with Session(get_engine()) as session, session.begin():
            operador = Operador(nombre="Operador EA3", telefono="3000000000")
            titular = Cliente(nombre="Titular EA3", documento=identificador)
            vehiculo = Vehiculo(tipo=tipo, placa=placa, color="Gris", modelo=2026, marca="Demo", cliente=titular)
            session.add_all([vehiculo, operador])
            session.flush()
            session.add(CuentaOperador(operador_id=operador.id, usuario=identificador, clave="no-usada-en-la-prueba"))
            session.flush()
            session.add(SesionOperador(token=hash_token(token), operador_id=operador.id,
                                       vence=datetime.now(timezone.utc) + timedelta(minutes=15)))
            if vencimiento:
                session.add(VigenciaMensualidad(vehiculo_id=vehiculo.id, inicio=vencimiento - timedelta(days=31),
                                                vencimiento=vencimiento))
            if con_mora:
                celda = Celda(codigo=placa, tipo="AUTOMOVIL_CAMIONETA")
                session.add(celda)
                session.flush()
                session.add(Estancia(
                    vehiculo_id=vehiculo.id, celda_id=celda.id, entrada=AHORA - timedelta(days=5),
                    salida=AHORA - timedelta(days=1), operador_entrada_id=operador.id,
                    operador_salida_id=operador.id, mora_pendiente=True,
                ))
            return placa, token

    return crear


def cliente_api(token):
    return TestClient(app, cookies={COOKIE: token})


def solicitud(cliente, placa):
    respuesta = cliente.get(f"/pagos/vehiculo/{placa.lower()}")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    return datos, {
        "placa": placa, "solicitud_id": str(uuid4()), "importe": datos["tarifa"],
        "ultima_vigencia_id": (datos["ultima_vigencia"] or {}).get("id"),
        "mora_pendiente_id": datos["mora_pendiente"][0]["estancia_id"] if datos["mora_pendiente"] else None,
    }


@require_db
def test_primera_mensualidad_importe_reintentos_historial_y_comprobante(preparar):
    placa, token = preparar("MOTO")
    with cliente_api(token) as cliente:
        assert cliente.get("/pagos/vehiculo/INEXISTENTE-EA3").status_code == 404
        datos, carga = solicitud(cliente, placa)
        assert datos["tarifa"] == 100_000
        assert datos["ultima_vigencia"] is None
        assert cliente.post("/pagos/mensualidad", json={**carga, "importe": 150000}).status_code == 422
        assert not cliente.get("/pagos/historial", params={"placa": placa}).json()["items"]

        creado = cliente.post("/pagos/mensualidad", json=carga)
        assert creado.status_code == 201
        pago = creado.json()
        assert pago["concepto"] == "PRIMERA_MENSUALIDAD"
        assert pago["importe"] == 100_000
        assert datetime.fromisoformat(pago["vigencia"]["inicio"]) == AHORA
        assert datetime.fromisoformat(pago["vigencia"]["vencimiento"]) == AHORA.replace(month=2, day=28)
        assert pago["operador"] == "Operador EA3"

        repetido = cliente.post("/pagos/mensualidad", json=carga)
        assert repetido.status_code == 200 and repetido.json() == pago
        assert cliente.post("/pagos/mensualidad", json={**carga, "importe": 1}).status_code == 409
        assert cliente.post("/pagos/mensualidad", json={**carga, "operador_id": 42}).status_code == 422
        assert cliente.get("/pagos/historial?desde=2027-02-01&hasta=2027-01-01").status_code == 422
        filtrado = cliente.get("/pagos/historial", params={"placa": placa, "desde": "2027-01-31", "hasta": "2027-01-31"})
        assert filtrado.status_code == 200 and filtrado.json()["total"] == 1
        assert cliente.get("/pagos/historial", params={"placa": placa, "desde": "2027-02-01"}).json()["total"] == 0
        ruta = "/pagos/comprobante/" + str(filtrado.json()["items"][0]["id"])
        assert cliente.get(ruta).json() == cliente.get(ruta).json() == pago
        assert cliente.get("/pagos/comprobante/9999999999").status_code == 404


@require_db
@pytest.mark.parametrize(("dias", "inicio"), [(15, AHORA + timedelta(days=15)), (-7, AHORA)])
def test_renueva_vigente_o_vencida_con_tarifa_de_camioneta(preparar, dias, inicio):
    placa, token = preparar("CAMIONETA", AHORA + timedelta(days=dias))
    with cliente_api(token) as cliente:
        datos, carga = solicitud(cliente, placa)
        assert datos["tarifa"] == 150_000
        assert bool(datos["vigencia_actual"]) is (dias > 0)
        resultado = cliente.post("/pagos/mensualidad", json=carga)
        assert resultado.status_code == 201
        assert resultado.json()["concepto"] == "RENOVACION"
        assert datetime.fromisoformat(resultado.json()["vigencia"]["inicio"]) == inicio


@require_db
def test_mora_con_rollback_y_salida_conservada(preparar, monkeypatch):
    placa, token = preparar(vencimiento=AHORA - timedelta(days=2), con_mora=True)
    with cliente_api(token) as cliente:
        datos, carga = solicitud(cliente, placa)
        pendiente = datos["mora_pendiente"][0]
        assert not datos["vigencia_actual"]

        def fallo(self, pago):
            self.session.flush()
            raise SQLAlchemyError("fallo simulado después de persistir")

        with monkeypatch.context() as mock:
            mock.setattr(ServicioPago, "_detalle", fallo)
            assert cliente.post("/pagos/mensualidad", json=carga).status_code == 503

        despues, _ = solicitud(cliente, placa)
        assert despues["mora_pendiente"] == [pendiente]
        assert despues["ultima_vigencia"] == datos["ultima_vigencia"]
        assert cliente.get("/pagos/historial", params={"placa": placa}).json()["total"] == 0
        confirmado = cliente.post("/pagos/mensualidad", json=carga)
        assert confirmado.status_code == 201
        assert confirmado.json()["importe"] == 150_000
        assert confirmado.json()["concepto"] == "RENOVACION_CON_MORA"
        assert confirmado.json()["estancias_regularizadas"] == [pendiente["estancia_id"]]
        assert solicitud(cliente, placa)[0]["mora_pendiente"] == []
        estancia = cliente.get(f"/operacion/comprobante/{pendiente['estancia_id']}").json()
        assert estancia["mora_regularizada"] and not estancia["mora_pendiente"]
        assert estancia["salida"] == pendiente["salida"] and estancia["operador_salida"] == pendiente["operador"]

        with Session(get_engine()) as session:
            assert session.scalar(select(func.count()).select_from(PagoMensualidad).where(PagoMensualidad.placa == placa)) == 1


@require_db
def test_dos_confirmaciones_para_el_mismo_periodo(preparar):
    placa, token = preparar(vencimiento=AHORA + timedelta(days=10))
    with cliente_api(token) as cliente:
        _, primera = solicitud(cliente, placa)
    barrera = Barrier(2)

    def enviar(carga):
        with cliente_api(token) as cliente:
            barrera.wait(timeout=5)
            return cliente.post("/pagos/mensualidad", json=carga).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(enviar, (primera, {**primera, "solicitud_id": str(uuid4())})))
    assert sorted(resultados) == [201, 409]


@require_db
def test_ingreso_de_plan_vencido_renovacion_y_salida(preparar, monkeypatch):
    ahora = datetime.now(timezone.utc)
    monkeypatch.setattr("app.services.pago.ahora_pago", lambda: ahora)
    placa, token = preparar("AUTOMOVIL", ahora - timedelta(days=1))
    with Session(get_engine()) as session, session.begin():
        session.add(Celda(codigo=placa, tipo="AUTOMOVIL_CAMIONETA"))
        vehiculo = session.scalar(select(Vehiculo).where(Vehiculo.placa == placa))
        operador_id = session.scalar(select(SesionOperador.operador_id).where(SesionOperador.token == hash_token(token)))
        assert vehiculo is not None and operador_id is not None

    with cliente_api(token) as cliente:
        entrada = {"placa": placa, "operador_id": operador_id}
        assert cliente.post("/operacion/entrada", json=entrada).status_code == 409
        _, carga = solicitud(cliente, placa)
        assert cliente.post("/pagos/mensualidad", json=carga).status_code == 201
        ingreso = cliente.post("/operacion/entrada", json=entrada)
        assert ingreso.status_code == 201
        salida = cliente.post("/operacion/salida", json={**entrada, "comprobante_id": ingreso.json()["id"]})
        assert salida.status_code == 200
        assert not salida.json()["mora_pendiente"]
