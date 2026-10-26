from datetime import date
from typing import Annotated
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from app.database import get_session
from app.schemas.operacion import EntradaOperacion, SalidaOperacion, CorreccionOperacion
from app.schemas.vehiculo import Placa
from app.services.operacion import ServicioOperacion

router = APIRouter(prefix="/operacion", tags=["Operación EA1"])
DatabaseSession = Annotated[Session, Depends(get_session)]

@router.get("/catalogos")
def catalogos(session: DatabaseSession) -> dict:
    return ServicioOperacion(session).catalogos()

@router.get("/vehiculo/{placa}")
def consultar(placa: Placa, session: DatabaseSession) -> dict:
    return ServicioOperacion(session).consultar_operacion(placa)

@router.post("/entrada", status_code=201)
def entrada(data: EntradaOperacion, session: DatabaseSession) -> dict:
    return ServicioOperacion(session).registrar_entrada(data)

@router.post("/salida")
def salida(data: SalidaOperacion, session: DatabaseSession) -> dict:
    return ServicioOperacion(session).registrar_salida(data)

@router.post("/correccion")
def correccion(data: CorreccionOperacion, session: DatabaseSession) -> dict:
    return ServicioOperacion(session).corregir(data)

@router.get("/comprobante/{estancia_id}")
def comprobante(estancia_id: Annotated[int, Path(ge=1)], session: DatabaseSession) -> dict:
    return ServicioOperacion(session).comprobante(estancia_id)

@router.get("/estancias")
def listado(session: DatabaseSession, presentes: bool = False, placa: str = "",
            desde: date | None = None, hasta: date | None = None,
            offset: Annotated[int, Query(ge=0)] = 0,
            limit: Annotated[int, Query(ge=1, le=100)] = 20) -> dict:
    return ServicioOperacion(session).listado(presentes, placa, desde, hasta, offset, limit)
