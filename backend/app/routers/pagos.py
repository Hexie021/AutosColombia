from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.database import get_session
from app.routers.acceso import OperadorActual
from app.schemas.pago import PagoCrear
from app.schemas.vehiculo import Placa
from app.services.pago import ServicioPago

router = APIRouter(prefix="/pagos", tags=["Pagos EA3"])
Db = Annotated[Session, Depends(get_session)]


@router.get("/vehiculo/{placa}")
def consultar(placa: Placa, session: Db, operador: OperadorActual) -> dict:
    return ServicioPago(session).consultar(placa)


@router.post("/mensualidad", status_code=201, responses={200: {"description": "Pago ya registrado"}})
def registrar(data: PagoCrear, session: Db, operador: OperadorActual, response: Response) -> dict:
    pago, creado = ServicioPago(session).registrar(data, operador)
    if not creado:
        response.status_code = 200
    return pago


@router.get("/historial")
def historial(
    session: Db, operador: OperadorActual, placa: str = "",
    desde: date | None = None, hasta: date | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    return ServicioPago(session).historial(placa, desde, hasta, offset, limit)


@router.get("/comprobante/{pago_id}")
def comprobante(pago_id: Annotated[int, Path(ge=1)], session: Db, operador: OperadorActual) -> dict:
    return ServicioPago(session).comprobante(pago_id)
