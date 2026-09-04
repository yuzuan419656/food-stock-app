"""add undone at to cooking histories

Revision ID: e4a7c9d2f6b1
Revises: b8d4e2a1c7f0
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4a7c9d2f6b1"
down_revision: Union[str, Sequence[str], None] = "b8d4e2a1c7f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cooking_histories") as batch_op:
        batch_op.add_column(
            sa.Column("undone_at", sa.DateTime(), nullable=True)
        )
        batch_op.create_index(
            "ix_cooking_histories_undone_at",
            ["undone_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("cooking_histories") as batch_op:
        batch_op.drop_index("ix_cooking_histories_undone_at")
        batch_op.drop_column("undone_at")
