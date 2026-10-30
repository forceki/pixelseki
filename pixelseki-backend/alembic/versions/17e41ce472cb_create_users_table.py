"""create users table

Revision ID: 17e41ce472cb
Revises: 
Create Date: 2026-05-23 02:00:56.918115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '17e41ce472cb'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('avatar_url', sa.String(length=512), nullable=True),
    sa.Column('google_id', sa.String(length=255), nullable=True),
    sa.Column('generation_credits', sa.Integer(), nullable=False, server_default='50'),
    sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('google_id')
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_google_id', 'users', ['google_id'])


def downgrade() -> None:
    op.drop_index('idx_users_google_id', table_name='users')
    op.drop_index('idx_users_email', table_name='users')
    op.drop_table('users')
