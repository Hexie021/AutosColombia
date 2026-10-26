"""Completa el modelo de datos de EA1 sin recrear tablas heredadas.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Los vehículos existentes necesitan una asociación real, nunca un cliente ficticio.
    op.execute("""DO $$ BEGIN
        IF EXISTS (SELECT 1 FROM vehiculo) THEN
            RAISE EXCEPTION 'Antes de migrar, debe planificarse la asociación de los vehículos existentes con sus clientes. No se modificaron sus datos.';
        END IF;
        IF EXISTS (SELECT 1 FROM celda WHERE tipo NOT IN ('MOTO', 'AUTOMOVIL_CAMIONETA')) THEN
            RAISE EXCEPTION 'Hay tipos de celda pendientes de clasificar. No se modificaron sus datos.';
        END IF;
    END $$;""")
    op.create_table(
        "cliente",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("documento", sa.Text(), nullable=False),
        sa.UniqueConstraint("documento", name="uq_cliente_documento"),
        sa.CheckConstraint("nombre ~ '[^[:space:]]'", name="ck_cliente_nombre_no_vacio"),
        sa.CheckConstraint("documento ~ '[^[:space:]]'", name="ck_cliente_documento_no_vacio"),
        sa.CheckConstraint("documento = btrim(documento)", name="ck_cliente_documento_normalizado"),
    )
    op.add_column("vehiculo", sa.Column("cliente_id", sa.BigInteger(), nullable=False))
    op.create_foreign_key("fk_vehiculo_cliente", "vehiculo", "cliente", ["cliente_id"], ["id"], ondelete="RESTRICT")
    op.create_check_constraint("ck_celda_tipo_admitido", "celda", "tipo IN ('MOTO', 'AUTOMOVIL_CAMIONETA')")
    op.create_table(
        "vigencia_mensualidad",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("vehiculo_id", sa.BigInteger(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vencimiento", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["vehiculo.id"], name="fk_vigencia_vehiculo", ondelete="RESTRICT"),
        sa.CheckConstraint("vencimiento > inicio", name="ck_vigencia_orden_fechas"),
    )
    op.create_index("ix_vigencia_vehiculo_fechas", "vigencia_mensualidad", ["vehiculo_id", "inicio", "vencimiento"])
    op.create_table(
        "correccion_celda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("estancia_id", sa.BigInteger(), nullable=False),
        sa.Column("celda_anterior_id", sa.BigInteger(), nullable=False),
        sa.Column("celda_nueva_id", sa.BigInteger(), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["estancia_id"], ["estancia.id"], name="fk_correccion_estancia", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["celda_anterior_id"], ["celda.id"], name="fk_correccion_celda_anterior", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["celda_nueva_id"], ["celda.id"], name="fk_correccion_celda_nueva", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"], name="fk_correccion_operador", ondelete="RESTRICT"),
        sa.CheckConstraint("celda_anterior_id <> celda_nueva_id", name="ck_correccion_celdas_distintas"),
        sa.CheckConstraint("motivo ~ '[^[:space:]]'", name="ck_correccion_motivo_no_vacio"),
    )
    op.create_index("ix_correccion_estancia_fecha", "correccion_celda", ["estancia_id", "fecha"])
    op.create_table(
        "incidencia_salida",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("estancia_id", sa.BigInteger(), nullable=False),
        sa.Column("operador_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("identidad_verificada", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["estancia_id"], ["estancia.id"], name="fk_incidencia_estancia", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"], name="fk_incidencia_operador", ondelete="RESTRICT"),
        sa.UniqueConstraint("estancia_id", name="uq_incidencia_estancia"),
        sa.CheckConstraint("motivo ~ '[^[:space:]]'", name="ck_incidencia_motivo_no_vacio"),
        sa.CheckConstraint("identidad_verificada IS TRUE", name="ck_incidencia_identidad_verificada"),
    )


def downgrade() -> None:
    # Una reversión debe planificarse; nunca se ejecuta como parte de la preparación.
    op.drop_table("incidencia_salida")
    op.drop_index("ix_correccion_estancia_fecha", table_name="correccion_celda")
    op.drop_table("correccion_celda")
    op.drop_index("ix_vigencia_vehiculo_fechas", table_name="vigencia_mensualidad")
    op.drop_table("vigencia_mensualidad")
    op.drop_constraint("ck_celda_tipo_admitido", "celda", type_="check")
    op.drop_constraint("fk_vehiculo_cliente", "vehiculo", type_="foreignkey")
    op.drop_column("vehiculo", "cliente_id")
    op.drop_table("cliente")
