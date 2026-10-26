"""Aplica el esquema EA1 al destino local reconocido y comprueba el resultado.

No contiene contraseñas. Usa backend/.env. Nunca borra ni recrea tablas.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from app.config import ConfigurationError, load_database_settings
from app.database import create_database_engine

EXPECTED = {"cliente", "vehiculo", "celda", "operador", "estancia",
            "vigencia_mensualidad", "correccion_celda", "incidencia_salida"}


def main() -> int:
    engine = None
    try:
        settings = load_database_settings()
        if settings.host not in {"127.0.0.1", "localhost"} or settings.name != "autos_colombia" or settings.user != "autos_colombia_app":
            raise ValueError("El destino no es la base local preparada para esta EA1. No se aplicará la migración.")
        engine = create_database_engine(settings)
        with engine.connect() as c:
            if c.scalar(text("SELECT current_database()")) != "autos_colombia":
                raise ValueError("No se confirmó el destino de la migración.")
            tables = set(inspect(c).get_table_names(schema="public"))
            if tables - EXPECTED - {"alembic_version"}:
                raise ValueError("Hay tablas ajenas al modelo esperado. Se requiere revisar la base antes de migrar.")
            if tables and "alembic_version" not in tables:
                raise ValueError("Existen tablas sin historial de migraciones. No se intentará recrearlas.")
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        print("Aplicando migraciones al destino local autos_colombia...")
        command.upgrade(config, "head")
        with engine.connect() as c:
            actual = set(inspect(c).get_table_names(schema="public"))
            revision = c.scalar(text("SELECT version_num FROM alembic_version"))
            if actual != EXPECTED | {"alembic_version"} or revision != "0003":
                raise ValueError("La estructura resultante requiere revisión; no se declara completada.")
        print("Modelo físico aplicado: 8 tablas del proyecto y revisión 0003.")
        print("Las tablas están listas para la carga de datos y la integración de los servicios de acceso.")
        return 0
    except ConfigurationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:
        # Alembic y los controladores pueden incluir parámetros o datos privados.
        print("No se pudo completar la migración. Se requiere revisar conexión, permisos e historial. No se borraron ni recrearon tablas deliberadamente y no se muestran datos privados.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
