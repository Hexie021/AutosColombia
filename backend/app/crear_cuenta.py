"""Registra una cuenta para un operador existente, con contraseña interactiva."""
import argparse
from getpass import getpass

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.database import get_engine
from app.models import CuentaOperador, Operador
from app.routers.acceso import huella_clave


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("usuario")
    parser.add_argument("operador_id", type=int, nargs="?")
    args = parser.parse_args()
    usuario = args.usuario.strip().lower()
    if not 1 <= len(usuario) <= 80:
        parser.error("El usuario debe tener entre 1 y 80 caracteres.")
    try:
        with Session(get_engine()) as session:
            if args.operador_id is None:
                ids = session.scalars(select(Operador.id).order_by(Operador.id).limit(2)).all()
                if len(ids) != 1:
                    parser.error("Indica el ID del operador si el catálogo no tiene exactamente uno.")
                args.operador_id = ids[0]
            if session.get(Operador, args.operador_id) is None:
                parser.error("El operador indicado no existe.")
            if session.get(CuentaOperador, args.operador_id):
                parser.error("Ese operador ya tiene una cuenta.")
        clave = getpass("Contraseña nueva: ")
        if not 12 <= len(clave) <= 128 or clave != getpass("Repite la contraseña: "):
            parser.error("Usa entre 12 y 128 caracteres y verifica la confirmación.")
        with Session(get_engine()) as session, session.begin():
            session.add(CuentaOperador(operador_id=args.operador_id, usuario=usuario, clave=huella_clave(clave)))
    except (SQLAlchemyError, ValueError):
        parser.exit(1, "No se pudo crear la cuenta. Revisa el esquema y que el usuario esté disponible.\n")
    print("Cuenta de operador creada.")


if __name__ == "__main__":
    main()
