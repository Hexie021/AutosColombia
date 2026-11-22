"""Gestión administrativa de cuentas de operador."""
from typing import Annotated

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from sqlalchemy import delete, func, select

from app.models import CuentaOperador, Operador, SesionOperador
from app.routers.acceso import Db, huella_clave
from app.services.operador import OperadorError, database_operation

router = APIRouter(prefix="/acceso/cuentas", tags=["Cuentas de operador"])
Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Usuario = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=80)]
Clave = Annotated[str, Field(min_length=12, max_length=128)]
CuentaId = Annotated[int, Path(ge=1, le=9223372036854775807)]


class PerfilCuenta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: Texto
    telefono: Texto
    usuario: Usuario


class CrearCuenta(PerfilCuenta):
    contrasena: Clave


class EditarCuenta(PerfilCuenta):
    activa: Annotated[bool, Field(strict=True)]
    contrasena: Clave | None = None

def resumen(cuenta: CuentaOperador, operador: Operador) -> dict:
    return {
        "id": operador.id, "nombre": operador.nombre, "telefono": operador.telefono,
        "usuario": cuenta.usuario, "activa": cuenta.activa,
    }


@router.get("")
@database_operation
def listar(
    session: Db, offset: Annotated[int, Query(ge=0, le=9223372036854775807)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict:
    consulta = (
        select(CuentaOperador, Operador)
        .join(Operador, Operador.id == CuentaOperador.operador_id)
        .where(CuentaOperador.rol == "OPERADOR")
    )
    total = session.scalar(select(func.count()).select_from(consulta.subquery()))
    filas = session.execute(consulta.order_by(CuentaOperador.usuario).offset(offset).limit(limit))
    return {"items": [resumen(cuenta, operador) for cuenta, operador in filas], "total": total}


@router.post("", status_code=201)
@database_operation
def crear(session: Db, data: CrearCuenta) -> dict:
    with session.begin():
        operador = Operador(nombre=data.nombre, telefono=data.telefono)
        session.add(operador)
        session.flush()
        cuenta = CuentaOperador(
            operador_id=operador.id, usuario=data.usuario, clave=huella_clave(data.contrasena),
            rol="OPERADOR", activa=True,
        )
        session.add(cuenta)
        session.flush()
        return resumen(cuenta, operador)


@router.put("/{cuenta_id}")
@database_operation
def editar(session: Db, cuenta_id: CuentaId, data: EditarCuenta) -> dict:
    with session.begin():
        cuenta = session.get(CuentaOperador, cuenta_id, with_for_update=True)
        if cuenta is None or cuenta.rol != "OPERADOR":
            raise OperadorError(404, "Cuenta de operador no encontrada.")
        operador = session.get(Operador, cuenta_id)
        revocar = cuenta.usuario != data.usuario or not data.activa or data.contrasena is not None
        operador.nombre = data.nombre
        operador.telefono = data.telefono
        cuenta.usuario = data.usuario
        cuenta.activa = data.activa
        if data.contrasena is not None:
            cuenta.clave = huella_clave(data.contrasena)
        if revocar:
            session.execute(delete(SesionOperador).where(SesionOperador.operador_id == cuenta_id))
        session.flush()
        return resumen(cuenta, operador)
