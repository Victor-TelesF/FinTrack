"""adiciona constraint unique em user_name

Revision ID: 6e2885353bbb
Revises: e3fdcf5bccc8
Create Date: 2026-08-09 14:30:52.331258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e2885353bbb'
down_revision: Union[str, None] = 'e3fdcf5bccc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_user_user_name', 'user', ['user_name'])

def downgrade() -> None:
    op.drop_constraint('uq_user_user_name', 'user', type_='unique')