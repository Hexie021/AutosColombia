# Backend de Autos Colombia

FastAPI, SQLAlchemy y PostgreSQL. Consulta el **README.md de la raíz** para instalar, preparar la base local, ejecutar la API y probar las tres iteraciones.

- API de la entrega: `/operacion/*` y `/pagos/*`.
- `/health` no depende de PostgreSQL.
- Configuración privada: `.env` local; no versionar.
- Migración vigente: `0008`.
- Demostración: `scripts/cargar_demo.py`.
- Verificación de integración: `scripts/verificar_ea1.py`, que revierte sus datos temporales.

Para verificar la gestión de celdas en PostgreSQL, aplica primero la migración `0005`. Desde la carpeta del backend, ejecuta:

```powershell
$env:RUN_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_celdas_postgres.py
Remove-Item Env:RUN_POSTGRES_TESTS
```

Estas pruebas revierten los datos que crean. Las otras pruebas PostgreSQL heredadas corresponden a las revisiones iniciales del esquema.

## Pruebas de pagos

La prueba de sesión se ejecuta con la suite ordinaria. Para ejecutar también
la integración, configura una base local aislada llamada `autos_colombia_ea3_test`
en las variables de entorno `DB_*`, aplica la migración y ejecuta desde el backend:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
$env:RUN_EA3_POSTGRES_TESTS = '1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_pagos.py
Remove-Item Env:RUN_EA3_POSTGRES_TESTS
```

La prueba de concurrencia confirma transacciones independientes y deja datos
ficticios en la base aislada. Usa una base exclusiva para estas pruebas.
