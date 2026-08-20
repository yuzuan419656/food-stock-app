"""add soft delete fields to ingredients

Revision ID: c61ce24ab294
Revises: 70a69ae5e1e8
Create Date: 2026-08-20 09:46:11.904917

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c61ce24ab294'
down_revision: Union[str, Sequence[str], None] = '70a69ae5e1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ingredients",
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
    )

    op.add_column(
        "ingredients",
        sa.Column(
            "deleted_at",
            sa.DateTime(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column(
        "ingredients",
        "deleted_at",
    )

    op.drop_column(
        "ingredients",
        "is_active",
    )
