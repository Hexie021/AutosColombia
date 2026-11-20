"""Carga datos ficticios una sola vez, sin borrar datos ni renovar vigencias existentes."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_engine
from app.config import load_database_settings
from app.models import Cliente, Vehiculo, Celda, Estancia, Operador, VigenciaMensualidad, siguiente_mes


def cargar_ea3(session: Session, operador: Operador, ahora: datetime) -> None:
    escenarios = [
        ("ABC12D", "Laura Martínez", "MOTO", None, False),
        ("XYZ789", "Daniela Ríos", "CAMIONETA", 1, False),
        ("KLM456", "Mateo Gómez", "AUTOMOVIL", 45, True),
        ("QRS234", "Valentina Ruiz", "AUTOMOVIL", 45, False),
    ]
    for placa, nombre, tipo, dias, mora in escenarios:
        if session.scalar(select(Vehiculo.id).where(Vehiculo.placa == placa)) is not None:
            continue
        documento = f"DEMO-EA3-{placa}"
        titular = session.scalar(select(Cliente).where(Cliente.documento == documento))
        if titular is None:
            titular = Cliente(nombre=nombre, documento=documento)
        vehiculo = Vehiculo(
            placa=placa, cliente=titular, tipo=tipo, marca="Demostración", color="Gris", modelo=2022,
        )
        session.add(vehiculo)
        session.flush()
        if dias is None:
            continue
        inicio = ahora - timedelta(days=dias)
        vencimiento = siguiente_mes(inicio)
        session.add(VigenciaMensualidad(vehiculo_id=vehiculo.id, inicio=inicio, vencimiento=vencimiento))
        if mora:
            celda = session.scalar(select(Celda).where(Celda.codigo == "A01"))
            session.add(Estancia(
                vehiculo_id=vehiculo.id, celda_id=celda.id,
                entrada=vencimiento - timedelta(hours=1), salida=vencimiento + timedelta(hours=1),
                operador_entrada_id=operador.id, operador_salida_id=operador.id, mora_pendiente=True,
            ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ea3", action="store_true", help="Agrega cuatro casos ficticios para probar pagos.")
    args = parser.parse_args()
    try:
        settings = load_database_settings()
        if settings.host not in {'127.0.0.1', 'localhost'} or settings.name != 'autos_colombia':
            print('Este script solo prepara la base local autos_colombia.')
            return 1
        with Session(get_engine()) as s, s.begin():
            for prefix, cantidad, tipo in [('A', 70, 'AUTOMOVIL_CAMIONETA'), ('M', 10, 'MOTO')]:
                for numero in range(1, cantidad + 1):
                    codigo = f'{prefix}{numero:02}'
                    if s.scalar(select(Celda.id).where(Celda.codigo == codigo)) is None:
                        s.add(Celda(codigo=codigo, tipo=tipo))
            operador = s.scalar(select(Operador).where(Operador.nombre == 'Ana López').order_by(Operador.id).limit(1))
            if operador is None:
                operador = Operador(nombre='Ana López', telefono='0000000000')
                s.add(operador)
            ahora = datetime.now(timezone.utc)
            for placa, nombre, documento, tipo, vigente in [
                ('ABC123', 'Carlos Pérez', 'DEMO-001', 'AUTOMOVIL', True),
                ('DEF456', 'Laura Gómez', 'DEMO-002', 'CAMIONETA', True),
                ('JKL45F', 'María Ruiz', 'DEMO-003', 'MOTO', True),
                ('GHI78F', 'Pedro Díaz', 'DEMO-004', 'MOTO', False),
            ]:
                if s.scalar(select(Vehiculo.id).where(Vehiculo.placa == placa)) is not None:
                    continue
                cliente = s.scalar(select(Cliente).where(Cliente.documento == documento))
                if cliente is None:
                    cliente = Cliente(nombre=nombre, documento=documento)
                    s.add(cliente)
                    s.flush()
                v = Vehiculo(cliente_id=cliente.id, placa=placa, marca='Demostración', color='Gris', modelo=2022, tipo=tipo)
                s.add(v)
                s.flush()
                inicio = ahora - timedelta(days=1 if vigente else 60)
                s.add(VigenciaMensualidad(vehiculo_id=v.id, inicio=inicio, vencimiento=siguiente_mes(inicio)))
            if args.ea3:
                s.flush()
                cargar_ea3(s, operador, ahora)
        print('Datos de demostración preparados sin borrar registros existentes.')
        print('Vigentes: ABC123, DEF456, JKL45F. Vencida: GHI78F.')
        print('Documentos ficticios para verificar pérdida: DEMO-001 a DEMO-004, respectivamente.')
        if args.ea3:
            print('Casos nuevos de EA3: ABC12D (primer pago), XYZ789 (vigente), KLM456 (mora), QRS234 (vencida).')
        return 0
    except Exception:
        print('No se pudo cargar la demostración. Revisa la conexión y las migraciones.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
