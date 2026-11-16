"""Registra la novedad de mora en el cierre de la estancia."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.add_column(
        "estancia",
        sa.Column("mora_pendiente", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_check_constraint(
        "ck_estancia_mora_con_salida", "estancia", "NOT mora_pendiente OR salida IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_constraint("ck_estancia_mora_con_salida", "estancia", type_="check")
    op.drop_column("estancia", "mora_pendiente")
