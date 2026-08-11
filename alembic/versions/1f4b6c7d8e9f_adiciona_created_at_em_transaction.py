"""adiciona timestamp de criacao em transacoes

Revision ID: 1f4b6c7d8e9f
Revises: 6e2885353bbb
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1f4b6c7d8e9f"
down_revision: Union[str, None] = "6e2885353bbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "transaction",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("transaction", "created_at")