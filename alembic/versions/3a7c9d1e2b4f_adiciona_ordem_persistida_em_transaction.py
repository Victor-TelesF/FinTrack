"""adiciona ordem persistida às transações

Revision ID: 3a7c9d1e2b4f
Revises: 1f4b6c7d8e9f
Create Date: 2026-08-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a7c9d1e2b4f"
down_revision: Union[str, None] = "1f4b6c7d8e9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE transaction_order_seq")
    op.add_column(
        "transaction",
        sa.Column("transaction_sequence", sa.BigInteger(), nullable=True),
    )
    op.execute(
        sa.text(
            """
            WITH ordered_transactions AS (
                SELECT
                    id_transaction,
                    row_number() OVER (
                        ORDER BY
                            transaction_date,
                            CASE WHEN transaction_type = 'SELL' THEN 1 ELSE 0 END,
                            created_at,
                            id_transaction
                    ) AS sequence_number
                FROM transaction
            )
            UPDATE transaction AS current_transaction
            SET transaction_sequence = ordered_transactions.sequence_number
            FROM ordered_transactions
            WHERE current_transaction.id_transaction = ordered_transactions.id_transaction
            """
        )
    )

    op.execute(
        sa.text(
            """
            SELECT setval(
                'transaction_order_seq',
                COALESCE((SELECT MAX(transaction_sequence) FROM transaction), 0) + 1,
                false
            )
            """
        )
    )
    op.alter_column(
        "transaction",
        "transaction_sequence",
        existing_type=sa.BigInteger(),
        nullable=False,
        server_default=sa.text("nextval('transaction_order_seq')"),
    )
    op.create_unique_constraint(
        "uq_transaction_transaction_sequence",
        "transaction",
        ["transaction_sequence"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_transaction_transaction_sequence",
        "transaction",
        type_="unique",
    )
    op.drop_column("transaction", "transaction_sequence")
    op.execute("DROP SEQUENCE transaction_order_seq")
