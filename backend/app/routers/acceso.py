"""Acceso de operador y sesiones revocables de la EA2."""
from datetime import datetime, timedelta, timezone
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
from secrets import token_hex, token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import CuentaOperador, Operador, SesionOperador

router = APIRouter(prefix="/acceso", tags=["Acceso"])
COOKIE = "autos_sesion"
DURACION = 8 * 3600
CLAVE_ITERACIONES = 600_000
Db = Annotated[Session, Depends(get_session)]
Token = Annotated[str | None, Cookie(alias=COOKIE)]


class Credenciales(BaseModel):
    usuario: str = Field(min_length=1, max_length=80)
    contrasena: str = Field(min_length=1, max_length=128)


class CambioClave(BaseModel):
    actual: str = Field(min_length=1, max_length=128)
    nueva: str = Field(min_length=12, max_length=128)


def huella_clave(clave: str, sal: str | None = None) -> str:
    sal = sal if sal is not None else token_hex(16)
    digest = pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), CLAVE_ITERACIONES)
    return f"{sal}:{digest.hex()}"


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def operador_actual(session: Db, token: Token = None) -> int:
    sesion = session.get(SesionOperador, hash_token(token)) if token else None
    if sesion is None or sesion.vence <= datetime.now(timezone.utc):
        raise HTTPException(401, "Inicia sesión para continuar.")
    operador_id = sesion.operador_id
    session.rollback()
    return operador_id


OperadorActual = Annotated[int, Depends(operador_actual)]


@router.post("/iniciar")
def iniciar(data: Credenciales, request: Request, response: Response, session: Db, token: Token = None) -> dict:
    cuenta = session.scalar(select(CuentaOperador).where(
        CuentaOperador.usuario == data.usuario.strip().lower()).with_for_update())
    esperada = cuenta.clave if cuenta else "0" * 32 + ":" + "0" * 64
    calculada = huella_clave(data.contrasena, esperada.split(":")[0])
    if not compare_digest(calculada, esperada) or cuenta is None:
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    operador = session.get(Operador, cuenta.operador_id)
    resultado = {"id": operador.id, "nombre": operador.nombre, "usuario": cuenta.usuario}
    if token:
        session.execute(delete(SesionOperador).where(SesionOperador.token == hash_token(token)))
    ahora = datetime.now(timezone.utc)
    session.execute(delete(SesionOperador).where(SesionOperador.vence <= ahora))
    nuevo = token_urlsafe(32)
    session.add(SesionOperador(token=hash_token(nuevo), operador_id=operador.id,
                               vence=ahora + timedelta(seconds=DURACION)))
    session.commit()
    response.set_cookie(COOKIE, nuevo, max_age=DURACION, httponly=True,
                        samesite="strict", secure=request.url.scheme == "https")
    return resultado


@router.get("/sesion")
def sesion(operador_id: OperadorActual, session: Db) -> dict:
    cuenta = session.get(CuentaOperador, operador_id)
    operador = session.get(Operador, operador_id)
    return {"id": operador.id, "nombre": operador.nombre, "usuario": cuenta.usuario}


@router.post("/cerrar", status_code=204)
def cerrar(response: Response, session: Db, token: Token = None) -> None:
    if token:
        session.execute(delete(SesionOperador).where(SesionOperador.token == hash_token(token)))
        session.commit()
    response.delete_cookie(COOKIE)


@router.post("/contrasena", status_code=204)
def cambiar(data: CambioClave, response: Response, operador_id: OperadorActual, session: Db) -> None:
    cuenta = session.get(CuentaOperador, operador_id, with_for_update=True)
    if not compare_digest(huella_clave(data.actual, cuenta.clave.split(":")[0]), cuenta.clave):
        raise HTTPException(400, "La contraseña actual es incorrecta.")
    if data.actual == data.nueva:
        raise HTTPException(400, "La contraseña nueva debe ser diferente.")
    cuenta.clave = huella_clave(data.nueva)
    session.execute(delete(SesionOperador).where(SesionOperador.operador_id == operador_id))
    session.commit()
    response.delete_cookie(COOKIE)
