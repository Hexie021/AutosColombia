"""Cuentas y sesiones del operador."""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cuenta_operador",
        sa.Column("operador_id", sa.BigInteger(), sa.ForeignKey("operador.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("usuario", sa.String(80), nullable=False, unique=True),
        sa.Column("clave", sa.String(97), nullable=False),
    )
    op.create_table(
        "sesion_operador",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("operador_id", sa.BigInteger(), sa.ForeignKey("cuenta_operador.operador_id", ondelete="CASCADE"), nullable=False),
        sa.Column("vence", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sesion_operador_operador_id", "sesion_operador", ["operador_id"])


def downgrade() -> None:
    op.drop_table("sesion_operador")
    op.drop_table("cuenta_operador")
