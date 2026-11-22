"""Acceso de operador y sesiones revocables de la EA2."""
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Identidad:
    id: int
    rol: str


def identidad_actual(session: Db, token: Token = None) -> Identidad:
    sesion = session.get(SesionOperador, hash_token(token)) if token else None
    if sesion is None or sesion.vence <= datetime.now(timezone.utc):
        raise HTTPException(401, "Inicia sesión para continuar.")
    cuenta = session.get(CuentaOperador, sesion.operador_id)
    if cuenta is None or not cuenta.activa:
        raise HTTPException(401, "Inicia sesión para continuar.")
    identidad = Identidad(cuenta.operador_id, cuenta.rol)
    session.rollback()
    return identidad


SesionActual = Annotated[Identidad, Depends(identidad_actual)]


def operador_actual(identidad: SesionActual) -> int:
    if identidad.rol != "OPERADOR":
        raise HTTPException(403, "Esta operación requiere el perfil de operador.")
    return identidad.id


def administrador_actual(identidad: SesionActual) -> int:
    if identidad.rol != "ADMINISTRADOR":
        raise HTTPException(403, "Esta operación requiere el perfil de administrador.")
    return identidad.id


OperadorActual = Annotated[int, Depends(operador_actual)]


def datos_sesion(cuenta: CuentaOperador, operador: Operador) -> dict:
    return {"id": operador.id, "nombre": operador.nombre, "usuario": cuenta.usuario, "rol": cuenta.rol}


@router.post("/iniciar")
def iniciar(data: Credenciales, request: Request, response: Response, session: Db, token: Token = None) -> dict:
    cuenta = session.scalar(select(CuentaOperador).where(
        CuentaOperador.usuario == data.usuario.strip().lower()).with_for_update())
    esperada = cuenta.clave if cuenta else "0" * 32 + ":" + "0" * 64
    calculada = huella_clave(data.contrasena, esperada.split(":")[0])
    if not compare_digest(calculada, esperada) or cuenta is None or not cuenta.activa:
        raise HTTPException(401, "Usuario o contraseña incorrectos.")
    operador = session.get(Operador, cuenta.operador_id)
    resultado = datos_sesion(cuenta, operador)
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
def sesion(identidad: SesionActual, session: Db) -> dict:
    cuenta = session.get(CuentaOperador, identidad.id)
    if cuenta is None or not cuenta.activa:
        raise HTTPException(401, "Inicia sesión para continuar.")
    return datos_sesion(cuenta, session.get(Operador, identidad.id))


@router.post("/cerrar", status_code=204)
def cerrar(response: Response, session: Db, token: Token = None) -> None:
    if token:
        session.execute(delete(SesionOperador).where(SesionOperador.token == hash_token(token)))
        session.commit()
    response.delete_cookie(COOKIE)


@router.post("/contrasena", status_code=204)
def cambiar(data: CambioClave, response: Response, identidad: SesionActual, session: Db) -> None:
    cuenta = session.get(CuentaOperador, identidad.id, with_for_update=True)
    if cuenta is None or not cuenta.activa:
        raise HTTPException(401, "Inicia sesión para continuar.")
    if not compare_digest(huella_clave(data.actual, cuenta.clave.split(":")[0]), cuenta.clave):
        raise HTTPException(400, "La contraseña actual es incorrecta.")
    if data.actual == data.nueva:
        raise HTTPException(400, "La contraseña nueva debe ser diferente.")
    cuenta.clave = huella_clave(data.nueva)
    session.execute(delete(SesionOperador).where(SesionOperador.operador_id == identidad.id))
    session.commit()
    response.delete_cookie(COOKIE)
