# Backend de Autos Colombia

FastAPI, SQLAlchemy y PostgreSQL. Consulta el **README.md de la raíz** para instalar, preparar la base local, ejecutar la API y probar ambas iteraciones.

- API de la entrega: `/operacion/*`.
- `/health` no depende de PostgreSQL.
- Configuración privada: `.env` local; no versionar.
- Migración vigente: `0006`.
- Demostración: `scripts/cargar_demo.py`.
- Verificación de integración: `scripts/verificar_ea1.py`, que revierte sus datos temporales.

Para verificar la gestión de celdas en PostgreSQL, aplica primero la migración `0005`. Desde la carpeta del backend, ejecuta:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_celdas_postgres.py
Remove-Item Env:RUN_POSTGRES_TESTS
```

Estas pruebas revierten los datos que crean. Las otras pruebas PostgreSQL heredadas corresponden a las revisiones iniciales del esquema.
