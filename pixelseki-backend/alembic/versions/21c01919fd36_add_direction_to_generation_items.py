"""add_direction_to_generation_items

Revision ID: 21c01919fd36
Revises: 09ec0dec54df
Create Date: 2026-05-24 18:54:29.085122

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21c01919fd36'
down_revision: Union[str, None] = '09ec0dec54df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generation_items', sa.Column('direction', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('generation_items', 'direction')
