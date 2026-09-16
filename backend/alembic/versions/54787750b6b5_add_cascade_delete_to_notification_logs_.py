"""add cascade delete to notification_logs price_snapshot_id fk

Revision ID: 54787750b6b5
Revises: 2b5da118aea6
Create Date: 2026-09-16 14:05:25.244468

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54787750b6b5'
down_revision: Union[str, None] = '2b5da118aea6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(op.f('notification_logs_price_snapshot_id_fkey'), 'notification_logs', type_='foreignkey')
    op.create_foreign_key(
        'notification_logs_price_snapshot_id_fkey',
        'notification_logs', 'price_snapshots', ['price_snapshot_id'], ['id'], ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint(op.f('notification_logs_price_snapshot_id_fkey'), 'notification_logs', type_='foreignkey')
    op.create_foreign_key(
        op.f('notification_logs_price_snapshot_id_fkey'),
        'notification_logs', 'price_snapshots', ['price_snapshot_id'], ['id'],
    )
