"""add provider column to generation_jobs and creations

Revision ID: 16f2cfad36ea
Revises: 21c01919fd36
Create Date: 2026-05-30 19:18:19.563183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16f2cfad36ea'
down_revision: Union[str, None] = '21c01919fd36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('creations', sa.Column('provider', sa.String(length=20), nullable=False, server_default='gemini'))
    op.add_column('generation_jobs', sa.Column('provider', sa.String(length=20), nullable=False, server_default='gemini'))


def downgrade() -> None:
    op.drop_column('generation_jobs', 'provider')
    op.drop_column('creations', 'provider')
