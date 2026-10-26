# Backend de Autos Colombia

FastAPI, SQLAlchemy y PostgreSQL. Consultar el **README.md de la raíz** para instalar, preparar la base local, ejecutar la API y probar la EA1.

- API de la entrega: `/operacion/*`.
- `/health` no depende de PostgreSQL.
- Configuración privada: `.env` local; no versionar.
- Migración vigente: `0003`.
- Demostración: `scripts/cargar_demo.py`.
- Verificación de integración: `scripts/verificar_ea1.py`, que revierte sus datos temporales.

Las pruebas PostgreSQL heredadas con `RUN_POSTGRES_TESTS=1` fueron escritas para los esquemas 0001 y 0002. No ejecutarlas sobre 0003; usar el verificador EA1 para esta revisión.
