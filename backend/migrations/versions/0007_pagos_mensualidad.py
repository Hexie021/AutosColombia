"""Persiste pagos y conserva la salida que originó una mora."""
import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    op.create_table(
        "pago_mensualidad",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("solicitud_id", sa.Uuid(), nullable=False),
        sa.Column("vehiculo_id", sa.BigInteger(), nullable=False),
        sa.Column("vigencia_id", sa.BigInteger(), nullable=False),
        sa.Column("vigencia_anterior_id", sa.BigInteger(), nullable=True),
        sa.Column("mora_pendiente_id", sa.BigInteger(), nullable=True),
        sa.Column("operador_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("concepto", sa.String(24), nullable=False),
        sa.Column("importe", sa.Integer(), nullable=False),
        sa.Column("placa", sa.Text(), nullable=False),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("cliente", sa.Text(), nullable=False),
        sa.Column("operador", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["vehiculo_id"], ["vehiculo.id"], name="fk_pago_vehiculo", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vigencia_id"], ["vigencia_mensualidad.id"], name="fk_pago_vigencia", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vigencia_anterior_id"], ["vigencia_mensualidad.id"], name="fk_pago_vigencia_anterior", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["mora_pendiente_id"], ["estancia.id"], name="fk_pago_mora", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["operador_id"], ["operador.id"], name="fk_pago_operador", ondelete="RESTRICT"),
        sa.UniqueConstraint("solicitud_id", name="uq_pago_solicitud"),
        sa.UniqueConstraint("vigencia_id", name="uq_pago_vigencia"),
        sa.CheckConstraint("importe > 0", name="ck_pago_importe_positivo"),
        sa.CheckConstraint(
            "concepto IN ('PRIMERA_MENSUALIDAD', 'RENOVACION', 'RENOVACION_CON_MORA')",
            name="ck_pago_concepto",
        ),
    )
    op.create_index("ix_pago_fecha", "pago_mensualidad", ["fecha", "id"])
    op.create_index("ix_pago_placa_fecha", "pago_mensualidad", ["placa", "fecha", "id"])
    op.add_column("estancia", sa.Column("mora_regularizada_pago_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_estancia_pago_mora", "estancia", "pago_mensualidad", ["mora_regularizada_pago_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_estancia_mora_regularizada", "estancia",
        "mora_regularizada_pago_id IS NULL OR (salida IS NOT NULL AND NOT mora_pendiente)",
    )
    op.create_index("ix_estancia_pago_mora", "estancia", ["mora_regularizada_pago_id"])


def downgrade() -> None:
    op.drop_index("ix_estancia_pago_mora", table_name="estancia")
    op.drop_constraint("ck_estancia_mora_regularizada", "estancia", type_="check")
    op.execute("UPDATE estancia SET mora_pendiente = true WHERE mora_regularizada_pago_id IS NOT NULL")
    op.drop_constraint("fk_estancia_pago_mora", "estancia", type_="foreignkey")
    op.drop_column("estancia", "mora_regularizada_pago_id")
    op.drop_index("ix_pago_placa_fecha", table_name="pago_mensualidad")
    op.drop_index("ix_pago_fecha", table_name="pago_mensualidad")
    op.drop_table("pago_mensualidad")
