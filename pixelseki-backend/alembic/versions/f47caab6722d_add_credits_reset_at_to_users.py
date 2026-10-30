"""add credits_reset_at to users

Revision ID: f47caab6722d
Revises: b289e6340847
Create Date: 2026-05-31 00:27:27.081963

"""
from datetime import datetime, timedelta, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f47caab6722d'
down_revision: Union[str, None] = 'b289e6340847'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _next_monday_str() -> str:
    now = datetime.now(timezone.utc)
    days_ahead = (7 - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return (now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)).isoformat()


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('credits_reset_at', sa.DateTime(timezone=True), nullable=False, server_default=_next_monday_str()),
    )


def downgrade() -> None:
    op.drop_column('users', 'credits_reset_at')
