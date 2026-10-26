"""Reglas de vigencia y equivalencia del esquema completo sin conectar a una base."""
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex

from app.models import (Base, Celda, Cliente, CorreccionCelda, IncidenciaSalida,
                        VigenciaMensualidad, siguiente_mes)

BOGOTA = ZoneInfo("America/Bogota")


@pytest.mark.parametrize("year,month,day,expected", [
    (2026, 10, 21, (2026, 11, 21)),
    (2026, 1, 31, (2026, 2, 28)),
    (2028, 1, 31, (2028, 2, 29)),
    (2026, 12, 31, (2027, 1, 31)),
])
def test_mes_calendario_conserva_hora_y_ajusta_dia(year, month, day, expected):
    result = siguiente_mes(datetime(year, month, day, 10, 25, tzinfo=BOGOTA))
    assert (result.year, result.month, result.day) == expected
    assert (result.hour, result.minute, result.tzinfo) == (10, 25, BOGOTA)


def test_vigencia_inicio_inclusivo_vencimiento_exclusivo():
    start = datetime(2026, 10, 21, 10, tzinfo=BOGOTA)
    v = VigenciaMensualidad(inicio=start, vencimiento=siguiente_mes(start))
    assert v.esta_vigente(start)
    assert v.esta_vigente(datetime(2026, 11, 21, 9, 59, 59, tzinfo=BOGOTA))
    assert not v.esta_vigente(v.vencimiento)
    assert not v.esta_vigente(datetime(2026, 10, 21, 9, 59, tzinfo=BOGOTA))
    assert v.esta_vigente(start.astimezone(timezone.utc))
    with pytest.raises(ValueError):
        v.esta_vigente(datetime(2026, 10, 22))


@pytest.mark.parametrize("cell,vehicle,expected", [
    ("MOTO", "MOTO", True), ("MOTO", "AUTOMOVIL", False),
    ("AUTOMOVIL_CAMIONETA", "CAMIONETA", True),
    ("AUTOMOVIL_CAMIONETA", "AUTOMOVIL", True),
    ("AUTOMOVIL_CAMIONETA", "MOTO", False),
    ("AUTOMOVIL_CAMIONETA", "CAMION", False),
])
def test_compatibilidad_de_celdas(cell, vehicle, expected):
    assert Celda(tipo=cell).es_compatible(vehicle) is expected


@pytest.mark.parametrize("model,field", [
    (Cliente, "nombre"), (Cliente, "documento"),
    (CorreccionCelda, "motivo"), (IncidenciaSalida, "motivo"),
])
def test_datos_obligatorios_no_aceptan_blancos(model, field):
    with pytest.raises(ValueError):
        model(**{field: " \t\n"})


def test_cadena_de_migraciones_coincide_con_las_ocho_tablas(monkeypatch):
    metadata = sa.MetaData()
    root = Path(__file__).resolve().parents[1] / "migrations/versions"
    statements = []
    from alembic import op
    monkeypatch.setattr(op, "create_table", lambda name, *args: sa.Table(name, metadata, *args))
    monkeypatch.setattr(op, "execute", lambda statement: statements.append(str(statement)))
    monkeypatch.setattr(op, "add_column", lambda name, col: metadata.tables[name].append_column(col))

    def fk(name, source, target, local, remote, **kw):
        metadata.tables[source].append_constraint(sa.ForeignKeyConstraint(
            local, [f"{target}.{column}" for column in remote], name=name, **kw))

    monkeypatch.setattr(op, "create_foreign_key", fk)
    monkeypatch.setattr(op, "create_check_constraint", lambda name, table, expression:
                        metadata.tables[table].append_constraint(sa.CheckConstraint(expression, name=name)))
    monkeypatch.setattr(op, "create_index", lambda name, table, cols, **kw:
                        sa.Index(name, *(metadata.tables[table].c[col] for col in cols), **kw))
    for filename in ["0001_modelos_iniciales.py", "0002_estancia.py", "0003_modelo_ea1.py"]:
        spec = importlib.util.spec_from_file_location("migration_" + filename[:-3], root / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.upgrade()
    assert set(metadata.tables) == set(Base.metadata.tables)
    assert len(metadata.tables) == 8
    dialect = postgresql.dialect()
    for name, actual in metadata.tables.items():
        expected = Base.metadata.tables[name]
        assert {c.name: (str(c.type), c.nullable) for c in actual.columns} == {
            c.name: (str(c.type), c.nullable) for c in expected.columns}
        assert actual.c.id.identity.always and expected.c.id.identity.always
        def checks(t):
            return {(c.name, str(c.sqltext)) for c in t.constraints if isinstance(c, sa.CheckConstraint)}
        assert checks(actual) == checks(expected), name
        def fks(t):
            return {(f.parent.name, f.target_fullname, f.ondelete) for f in t.foreign_keys}
        assert fks(actual) == fks(expected), name
        def unique(t):
            return {(c.name, tuple(c.columns.keys())) for c in t.constraints if isinstance(c, sa.UniqueConstraint)}
        assert unique(actual) == unique(expected), name
        assert {str(CreateIndex(i).compile(dialect=dialect)) for i in actual.indexes} == {
            str(CreateIndex(i).compile(dialect=dialect)) for i in expected.indexes}, name
    assert any("EXISTS (SELECT 1 FROM vehiculo)" in statement for statement in statements)
    assert all("DROP TABLE" not in statement for statement in statements)
