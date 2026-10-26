"""Carga datos ficticios una sola vez, sin borrar datos ni renovar vigencias existentes."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_engine
from app.config import load_database_settings
from app.models import Cliente, Vehiculo, Celda, Operador, VigenciaMensualidad, siguiente_mes


def main() -> int:
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
            if s.scalar(select(Operador.id).where(Operador.nombre == 'Ana López')) is None:
                s.add(Operador(nombre='Ana López', telefono='0000000000'))
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
        print('Datos de demostración preparados sin borrar registros existentes.')
        print('Vigentes: ABC123, DEF456, JKL45F. Vencida: GHI78F.')
        print('Documentos ficticios para verificar pérdida: DEMO-001 a DEMO-004, respectivamente.')
        return 0
    except Exception:
        print('No se pudo cargar la demostración. Revisa conexión y migración 0003. No se muestran datos privados.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
