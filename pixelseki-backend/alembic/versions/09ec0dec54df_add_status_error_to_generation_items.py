"""add_status_error_to_generation_items

Revision ID: 09ec0dec54df
Revises: 70a5382fa14a
Create Date: 2026-05-24 15:14:56.858001

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '09ec0dec54df'
down_revision: Union[str, None] = '70a5382fa14a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('generation_items', sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'))
    op.add_column('generation_items', sa.Column('error_message', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('generation_items', 'error_message')
    op.drop_column('generation_items', 'status')
