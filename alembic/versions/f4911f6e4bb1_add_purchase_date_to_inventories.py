"""add purchase date to inventories

Revision ID: f4911f6e4bb1
Revises: 19e42664b6f4
Create Date: 2026-08-06 15:02:43.105243

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4911f6e4bb1"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "19e42664b6f4"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table(
        "inventories",
        schema=None,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "purchase_date",
                sa.Date(),
                nullable=True,
            )
        )

    op.execute(
        """
        UPDATE inventories
        SET purchase_date = DATE(created_at)
        WHERE purchase_date IS NULL
        """
    )

    with op.batch_alter_table(
        "inventories",
        schema=None,
    ) as batch_op:
        batch_op.alter_column(
            "purchase_date",
            existing_type=sa.Date(),
            nullable=False,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table(
        "inventories",
        schema=None,
    ) as batch_op:
        batch_op.drop_column(
            "purchase_date"
        )