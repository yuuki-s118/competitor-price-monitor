"""seed initial retailer rakuten

Revision ID: 2b5da118aea6
Revises: d0a9fa6e1424
Create Date: 2026-09-12 22:04:47.211476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b5da118aea6'
down_revision: Union[str, None] = 'd0a9fa6e1424'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


retailers = sa.table(
    "retailers",
    sa.column("name", sa.String),
    sa.column("slug", sa.String),
    sa.column("base_url", sa.String),
)


def upgrade() -> None:
    op.bulk_insert(
        retailers,
        [{"name": "楽天市場", "slug": "rakuten", "base_url": "https://www.rakuten.co.jp"}],
    )


def downgrade() -> None:
    op.execute(retailers.delete().where(retailers.c.slug == "rakuten"))
