"""Contratos para registrar y consultar mensualidades."""
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.vehiculo import Placa


class PagoCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")

    placa: Placa
    importe: Annotated[int, Field(strict=True, gt=0)]
    solicitud_id: UUID
    ultima_vigencia_id: Annotated[int, Field(strict=True, ge=1)] | None
    mora_pendiente_id: Annotated[int, Field(strict=True, ge=1)] | None
