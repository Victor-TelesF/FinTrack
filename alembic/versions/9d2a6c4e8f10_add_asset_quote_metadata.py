"""Add explicit quote identity and currency without guessing legacy mappings.

Revision ID: 9d2a6c4e8f10
Revises: 72768f7801ec
"""
from alembic import op
import sqlalchemy as sa

revision = "9d2a6c4e8f10"
down_revision = "72768f7801ec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("asset", sa.Column("price_provider", sa.String(20), nullable=True))
    op.add_column("asset", sa.Column("external_price_id", sa.String(100), nullable=True))
    op.add_column("asset", sa.Column("quote_currency", sa.String(3), nullable=True))
    # Only these two types have an explicit currency in the existing domain.
    op.execute("UPDATE asset SET quote_currency = 'BRL' WHERE type_column = 'national_stock'")
    op.execute("UPDATE asset SET quote_currency = 'USD' WHERE type_column = 'international_stock'")


def downgrade() -> None:
    op.drop_column("asset", "quote_currency")
    op.drop_column("asset", "external_price_id")
    op.drop_column("asset", "price_provider")
