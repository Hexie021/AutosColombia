from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse

from app.routers.vehiculos import router as vehiculos_router
from app.services.vehiculo import VehiculoError
from app.routers.celdas import router as celdas_router
from app.services.celda import CeldaError
from app.routers.operadores import router as operadores_router
from app.services.operador import OperadorError
from app.services.estancia import EstanciaError

from app.routers.operacion import router as operacion_router

from app.routers.acceso import operador_actual, router as acceso_router

app = FastAPI(title="Autos Colombia API")
app.include_router(acceso_router)
app.include_router(vehiculos_router, dependencies=[Depends(operador_actual)])
app.include_router(celdas_router, dependencies=[Depends(operador_actual)])
app.include_router(operadores_router, dependencies=[Depends(operador_actual)])
app.include_router(operacion_router, dependencies=[Depends(operador_actual)])
# Los CRUD originales quedan como apoyo; las rutas antiguas de estancia no se publican,
# pues permitían omitir la mensualidad y la validación del comprobante.


@app.exception_handler(VehiculoError)
@app.exception_handler(CeldaError)
@app.exception_handler(OperadorError)
@app.exception_handler(EstanciaError)
async def entity_error_handler(request, error: VehiculoError | CeldaError | OperadorError | EstanciaError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    if request.url.path.startswith("/acceso/"):
        return JSONResponse(status_code=422, content={"detail": "Revisa los campos de acceso."})
    return await request_validation_exception_handler(request, error)
