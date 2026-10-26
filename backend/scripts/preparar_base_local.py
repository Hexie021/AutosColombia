from __future__ import annotations

import argparse
import getpass
from pathlib import Path
import secrets
import sys

import psycopg
from psycopg import sql
from dotenv import dotenv_values

HOST = "127.0.0.1"
PORT = 5432
DATABASE = "autos_colombia"
APP_USER = "autos_colombia_app"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
MARKER = "# Configuración local de Autos Colombia generada por preparar_base_local.py"


def connect(user: str, password: str, database: str):
    return psycopg.connect(host=HOST, port=PORT, dbname=database, user=user,
                           password=password, connect_timeout=5, autocommit=True)


def prepare() -> None:
    existing = ENV_FILE.exists()
    password = secrets.token_urlsafe(32)
    if existing:
        content = ENV_FILE.read_text(encoding="utf-8-sig")
        if not content.startswith(MARKER):
            raise RuntimeError("Ya existe backend/.env. Se conserva sin cambios; revisa su configuración antes de continuar.")
        values = dotenv_values(ENV_FILE, interpolate=False)
        expected = {"DB_HOST": HOST, "DB_PORT": str(PORT), "DB_NAME": DATABASE, "DB_USER": APP_USER}
        if any(values.get(key) != value for key, value in expected.items()) or not values.get("DB_PASSWORD"):
            raise RuntimeError("La configuración existente no corresponde a esta preparación. No se modificó.")
        password = values["DB_PASSWORD"]

    admin_password = getpass.getpass("Contraseña de postgres (no se muestra al escribir): ")
    if not admin_password:
        raise RuntimeError("Debes ingresar la contraseña que definiste al instalar PostgreSQL.")

    with connect("postgres", admin_password, "postgres") as admin:
        admin_password = ""
        role_exists = admin.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_USER,)).fetchone() is not None
        database_owner = admin.execute(
            "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = %s", (DATABASE,)
        ).fetchone()
        if role_exists and not existing:
            raise RuntimeError("El usuario de aplicación ya existe y no hay una configuración local reconocida. No se cambiará su contraseña.")
        if database_owner and database_owner[0] != APP_USER:
            raise RuntimeError("La base autos_colombia ya existe con otro propietario. Se conserva sin cambios y debe revisarse.")
        if role_exists:
            # Confirma la identidad de la credencial conservada antes de reutilizarla.
            with connect(APP_USER, password, "postgres") as app:
                app.execute("SELECT 1").fetchone()
        if not existing:
            body = (MARKER + "\n"
                    f"DB_HOST={HOST}\nDB_PORT={PORT}\nDB_NAME={DATABASE}\nDB_USER={APP_USER}\n"
                    f"DB_PASSWORD='{password}'\nDB_CONNECT_TIMEOUT=5\n")
            # No sobrescribe ninguna configuración creada mientras se ejecutaba.
            with ENV_FILE.open("x", encoding="utf-8") as env:
                env.write(body)
        if not role_exists:
            admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}")
                          .format(sql.Identifier(APP_USER), sql.Literal(password)))
            print("Usuario de aplicación creado.")
        if not database_owner:
            admin.execute(sql.SQL("CREATE DATABASE {} OWNER {}")
                          .format(sql.Identifier(DATABASE), sql.Identifier(APP_USER)))
            print("Base autos_colombia creada.")
    with connect(APP_USER, password, DATABASE) as app:
        if app.execute("SELECT 1").fetchone() != (1,):
            raise RuntimeError("No se pudo confirmar la respuesta de PostgreSQL.")
    print("Conexión de aplicación verificada: SELECT 1 correcto.")
    print("Configuración guardada en backend/.env. No compartas ni publiques ese archivo.")
    print("Preparación completa. No se crearon tablas ni se aplicaron migraciones.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", action="store_true", help="Muestra las acciones sin conectar ni escribir archivos.")
    args = parser.parse_args()
    if args.plan:
        print("Destino local: PostgreSQL en 127.0.0.1:5432.")
        print("Crear usuario autos_colombia_app y base autos_colombia si corresponde.")
        print("Generar credencial local de aplicación y guardar backend/.env sin sobrescribirlo.")
        print("Comprobar SELECT 1. No crear tablas, borrar datos ni aplicar migraciones.")
        return 0
    try:
        prepare()
        return 0
    except KeyboardInterrupt:
        print("Preparación cancelada.", file=sys.stderr)
        return 130
    except psycopg.Error:
        print("No se pudo completar la preparación. Revisa que PostgreSQL esté iniciado, el puerto sea 5432 y la contraseña de postgres sea correcta. Si se creó algún recurso, se conserva para revisión; no se borran datos ni se muestran credenciales.", file=sys.stderr)
        return 1
    except (OSError, RuntimeError) as error:
        if isinstance(error, RuntimeError):
            print(str(error), file=sys.stderr)
        else:
            print("No se pudo leer o guardar la configuración local. Comprueba los permisos de la carpeta.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
