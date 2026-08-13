"""adiciona external_price_id em asset

Revision ID: 9b7d1e6f4a2b
Revises: e3fdcf5bccc8
Create Date: 2026-08-13 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9b7d1e6f4a2b'
down_revision = 'e3fdcf5bccc8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('asset', sa.Column('external_price_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('asset', 'external_price_id')
