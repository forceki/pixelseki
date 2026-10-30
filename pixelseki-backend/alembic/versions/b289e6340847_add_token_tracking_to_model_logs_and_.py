"""add token tracking to model_logs and users

Revision ID: b289e6340847
Revises: 16f2cfad36ea
Create Date: 2026-05-30 19:37:48.144017

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b289e6340847'
down_revision: Union[str, None] = '16f2cfad36ea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # model_logs: add user_id FK + token columns
    op.add_column('model_logs', sa.Column('user_id', sa.Integer(), nullable=True))
    op.add_column('model_logs', sa.Column('input_tokens', sa.Integer(), nullable=True))
    op.add_column('model_logs', sa.Column('output_tokens', sa.Integer(), nullable=True))
    op.add_column('model_logs', sa.Column('total_tokens', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_model_logs_user_id'), 'model_logs', ['user_id'], unique=False)
    op.create_foreign_key('fk_model_logs_user_id', 'model_logs', 'users', ['user_id'], ['id'], ondelete='SET NULL')

    # users: add cumulative token counters
    op.add_column('users', sa.Column('total_input_tokens', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('total_output_tokens', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'total_output_tokens')
    op.drop_column('users', 'total_input_tokens')
    op.drop_constraint('fk_model_logs_user_id', 'model_logs', type_='foreignkey')
    op.drop_index(op.f('ix_model_logs_user_id'), table_name='model_logs')
    op.drop_column('model_logs', 'total_tokens')
    op.drop_column('model_logs', 'output_tokens')
    op.drop_column('model_logs', 'input_tokens')
    op.drop_column('model_logs', 'user_id')
