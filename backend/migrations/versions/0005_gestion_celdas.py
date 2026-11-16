"""Añade la habilitación administrativa de las celdas."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.add_column("celda", sa.Column("habilitada", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("celda", "habilitada")
