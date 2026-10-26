"""Contratos de operación EA1."""
from pydantic import BaseModel, ConfigDict, StrictBool, model_validator
from app.schemas.estancia import Identificador
from app.schemas.vehiculo import Placa, Texto

class EntradaOperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    placa: Placa
    operador_id: Identificador

class SalidaOperacion(EntradaOperacion):
    comprobante_id: Identificador | None = None
    perdido: StrictBool = False
    documento: str = ""
    motivo: str = ""
    identidad_verificada: StrictBool = False

    @model_validator(mode="after")
    def verificar_respaldo(self):
        if self.perdido:
            if not self.documento.strip() or not self.motivo.strip() or not self.identidad_verificada:
                raise ValueError("Verifica la identidad e indica documento y motivo de pérdida.")
        elif self.comprobante_id is None:
            raise ValueError("Indica el número de comprobante.")
        return self

class CorreccionOperacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estancia_id: Identificador
    celda_id: Identificador
    operador_id: Identificador
    motivo: Texto
