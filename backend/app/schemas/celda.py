from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, field_validator

from app.models import required_text

Texto = Annotated[str, BeforeValidator(lambda value: required_text(value, "El campo"))]
Codigo = Annotated[Texto, AfterValidator(str.upper)]
TipoCelda = Literal["MOTO", "AUTOMOVIL_CAMIONETA"]
TipoEntrada = Annotated[TipoCelda, BeforeValidator(lambda value: required_text(value, "Tipo").upper())]


class CeldaCrear(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo
    tipo: TipoEntrada


class CeldaActualizar(BaseModel):
    model_config = ConfigDict(extra="forbid")
    codigo: Codigo | None = None
    tipo: TipoEntrada | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Los campos enviados no pueden ser nulos.")
        return value


class CeldaHabilitacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    habilitada: bool


class CeldaRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    codigo: str
    tipo: str
    habilitada: bool = True
    ocupada: bool = False
    tiene_historial: bool = False


class CeldasPagina(BaseModel):
    items: list[CeldaRespuesta]
    total: int
    offset: int
    limit: int
