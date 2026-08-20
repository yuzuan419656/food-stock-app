"""allow custom shopping items

Revision ID: 70a69ae5e1e8
Revises: fbfa4d594cba
Create Date: 2026-08-19 12:43:31.045843

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70a69ae5e1e8'
down_revision: Union[str, Sequence[str], None] = 'fbfa4d594cba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table(
        "shopping_items"
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "custom_name",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.alter_column(
            "ingredient_id",
            existing_type=sa.Integer(),
            nullable=True,
        )

        batch_op.create_check_constraint(
            "ck_shopping_items_source",
            """
            (
                ingredient_id IS NOT NULL
                AND custom_name IS NULL
            )
            OR
            (
                ingredient_id IS NULL
                AND custom_name IS NOT NULL
            )
            """,
        )

    # ### end Alembic commands ###


def downgrade() -> None:
    # 旧スキーマでは手入力項目を表現できないため、
    # downgrade時は手入力項目を削除する。
    op.execute(
        """
        DELETE FROM shopping_items
        WHERE ingredient_id IS NULL
        """
    )

    with op.batch_alter_table(
        "shopping_items"
    ) as batch_op:
        batch_op.drop_constraint(
            "ck_shopping_items_source",
            type_="check",
        )

        batch_op.alter_column(
            "ingredient_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

        batch_op.drop_column(
            "custom_name"
        )
    # ### end Alembic commands ###
