"""Distingue los perfiles y conserva el acceso de las cuentas existentes."""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade() -> None:
    op.add_column("cuenta_operador", sa.Column("rol", sa.String(13), server_default="OPERADOR", nullable=False))
    op.add_column("cuenta_operador", sa.Column("activa", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.create_check_constraint(
        "ck_cuenta_operador_rol", "cuenta_operador", "rol IN ('OPERADOR', 'ADMINISTRADOR')"
    )


def downgrade() -> None:
    # El esquema anterior no puede representar estas cuentas ni sus restricciones.
    op.execute("""
        DO $$ BEGIN
          IF EXISTS (SELECT 1 FROM cuenta_operador WHERE rol = 'ADMINISTRADOR' OR NOT activa) THEN
            RAISE EXCEPTION 'La revisión anterior no admite administradores ni cuentas inactivas.';
          END IF;
        END $$
    """)
    op.drop_constraint("ck_cuenta_operador_rol", "cuenta_operador", type_="check")
    op.drop_column("cuenta_operador", "activa")
    op.drop_column("cuenta_operador", "rol")
