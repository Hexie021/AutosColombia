from functools import wraps

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Celda, CorreccionCelda, Estancia
from app.schemas.celda import CeldaActualizar, CeldaCrear, CeldaRespuesta

ocupada = select(Estancia.id).where(
    Estancia.celda_id == Celda.id, Estancia.salida.is_(None)
).exists()
historial = or_(
    select(Estancia.id).where(Estancia.celda_id == Celda.id).exists(),
    select(CorreccionCelda.id).where(or_(
        CorreccionCelda.celda_anterior_id == Celda.id,
        CorreccionCelda.celda_nueva_id == Celda.id,
    )).exists(),
)


class CeldaError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail


def database_operation(operation):
    """Centraliza rollback y mensajes públicos sin detalles del driver."""
    @wraps(operation)
    def wrapped(session: Session, *args, **kwargs):
        try:
            return operation(session, *args, **kwargs)
        except IntegrityError as error:
            session.rollback()
            code = getattr(error.orig, "sqlstate", None)
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if code == "23505" and constraint == "uq_celda_codigo":
                raise CeldaError(409, "Ya existe una celda con ese código.") from None
            if code == "23503":
                raise CeldaError(409, "La celda tiene registros relacionados y no se puede eliminar.") from None
            if code in {"23502", "23514"}:
                raise CeldaError(422, "Los datos incumplen las restricciones de la celda.") from None
            raise CeldaError(409, "La operación entra en conflicto con los datos existentes.") from None
        except SQLAlchemyError:
            session.rollback()
            raise CeldaError(503, "No se pudo completar la operación con la base de datos.") from None
    return wrapped


def find_cell(session: Session, cell_id: int, *, lock: bool = False) -> Celda:
    cell = session.get(Celda, cell_id, with_for_update=lock)
    if cell is None:
        raise CeldaError(404, "Celda no encontrada.")
    return cell


def cell_response(cell: Celda, occupied: bool, has_history: bool) -> CeldaRespuesta:
    return CeldaRespuesta.model_validate(cell).model_copy(
        update={"ocupada": occupied, "tiene_historial": has_history}
    )


@database_operation
def create_cell(session: Session, data: CeldaCrear) -> Celda:
    cell = Celda(**data.model_dump())
    session.add(cell)
    session.commit()
    session.refresh(cell)
    return cell


@database_operation
def list_cells(
    session: Session, offset: int, limit: int, codigo: str | None = None,
    tipo: str | None = None, habilitada: bool | None = None,
    estado_ocupacion: bool | None = None,
) -> dict:
    filters = []
    if codigo and codigo.strip():
        filters.append(Celda.codigo.contains(codigo.strip().upper(), autoescape=True))
    if tipo is not None:
        filters.append(Celda.tipo == tipo)
    if habilitada is not None:
        filters.append(Celda.habilitada == habilitada)
    if estado_ocupacion is not None:
        filters.append(ocupada if estado_ocupacion else ~ocupada)
    total = session.scalar(select(func.count()).select_from(Celda).where(*filters))
    rows = session.execute(
        select(Celda, ocupada, historial).where(*filters).order_by(Celda.codigo)
        .offset(offset).limit(limit)
    )
    items = [cell_response(*row) for row in rows]
    return {"items": items, "total": total, "offset": offset, "limit": limit}


@database_operation
def get_cell(session: Session, cell_id: int) -> CeldaRespuesta:
    row = session.execute(select(Celda, ocupada, historial).where(Celda.id == cell_id)).one_or_none()
    if row is None:
        raise CeldaError(404, "Celda no encontrada.")
    return cell_response(*row)


@database_operation
def update_cell(session: Session, cell_id: int, data: CeldaActualizar) -> CeldaRespuesta:
    cell = find_cell(session, cell_id, lock=True)
    changes = data.model_dump(exclude_unset=True)
    if any(getattr(cell, key) != value for key, value in changes.items()):
        if session.scalar(select(historial).select_from(Celda).where(Celda.id == cell_id)):
            raise CeldaError(409, "El código y el tipo se conservan porque la celda tiene historial.")
    for key, value in changes.items():
        setattr(cell, key, value)
    session.flush()
    result = get_cell(session, cell_id)
    session.commit()
    return result


@database_operation
def set_cell_enabled(session: Session, cell_id: int, enabled: bool) -> CeldaRespuesta:
    cell = find_cell(session, cell_id, lock=True)
    current = get_cell(session, cell_id)
    if not enabled and current.ocupada:
        raise CeldaError(409, "No se puede deshabilitar una celda ocupada.")
    cell.habilitada = enabled
    session.commit()
    return current.model_copy(update={"habilitada": enabled})


@database_operation
def delete_cell(session: Session, cell_id: int) -> None:
    set_cell_enabled(session, cell_id, False)


