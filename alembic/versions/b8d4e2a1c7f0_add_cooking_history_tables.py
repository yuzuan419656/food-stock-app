"""add cooking history tables

Revision ID: b8d4e2a1c7f0
Revises: 85a0d7397576
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d4e2a1c7f0"
down_revision: Union[str, Sequence[str], None] = "85a0d7397576"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cooking_histories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("recipe_id", sa.Integer(), nullable=False),
        sa.Column("recipe_name", sa.String(length=100), nullable=False),
        sa.Column("cooked_at", sa.DateTime(), nullable=False),
        sa.Column("yield_type", sa.String(length=20), nullable=False),
        sa.Column("servings", sa.Integer(), nullable=True),
        sa.Column("fixed_yield_text", sa.String(length=100), nullable=True),
        sa.CheckConstraint(
            "length(trim(recipe_name)) > 0",
            name="check_cooking_history_recipe_name",
        ),
        sa.CheckConstraint(
            "yield_type IN ('servings', 'fixed')",
            name="check_cooking_history_yield_type",
        ),
        sa.CheckConstraint(
            """
            (
                yield_type = 'servings'
                AND servings IS NOT NULL
                AND servings >= 1
                AND fixed_yield_text IS NULL
            )
            OR
            (
                yield_type = 'fixed'
                AND servings IS NULL
                AND fixed_yield_text IS NOT NULL
                AND length(trim(fixed_yield_text)) > 0
            )
            """,
            name="check_cooking_history_yield_values",
        ),
        sa.ForeignKeyConstraint(
            ["recipe_id"], ["recipes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cooking_histories_recipe_id",
        "cooking_histories",
        ["recipe_id"],
    )
    op.create_index(
        "ix_cooking_histories_cooked_at",
        "cooking_histories",
        ["cooked_at"],
    )

    op.create_table(
        "cooking_history_ingredients",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cooking_history_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_id", sa.Integer(), nullable=False),
        sa.Column("ingredient_name", sa.String(length=100), nullable=False),
        sa.Column("required_quantity", sa.Float(), nullable=True),
        sa.Column("required_quantity_text", sa.String(length=50), nullable=True),
        sa.Column("consumed_quantity", sa.Float(), nullable=False),
        sa.Column("shortage_quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("inventory_consumed", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.CheckConstraint(
            "length(trim(ingredient_name)) > 0",
            name="check_history_ingredient_name",
        ),
        sa.CheckConstraint(
            """
            (
                required_quantity IS NOT NULL
                AND required_quantity > 0
                AND required_quantity_text IS NULL
            )
            OR
            (
                required_quantity IS NULL
                AND required_quantity_text IS NOT NULL
                AND length(trim(required_quantity_text)) > 0
            )
            """,
            name="check_history_required_quantity",
        ),
        sa.CheckConstraint(
            "consumed_quantity >= 0",
            name="check_history_consumed_quantity",
        ),
        sa.CheckConstraint(
            "shortage_quantity IS NULL OR shortage_quantity >= 0",
            name="check_history_shortage_quantity",
        ),
        sa.CheckConstraint(
            "status IN ('sufficient', 'shortage', 'unit_mismatch', 'not_applicable')",
            name="check_history_ingredient_status",
        ),
        sa.ForeignKeyConstraint(
            ["cooking_history_id"],
            ["cooking_histories.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["ingredient_id"], ["ingredients.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cooking_history_ingredients_cooking_history_id",
        "cooking_history_ingredients",
        ["cooking_history_id"],
    )
    op.create_index(
        "ix_cooking_history_ingredients_ingredient_id",
        "cooking_history_ingredients",
        ["ingredient_id"],
    )

    op.create_table(
        "cooking_history_inventory_consumptions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cooking_history_ingredient_id", sa.Integer(), nullable=False),
        sa.Column("inventory_id", sa.Integer(), nullable=False),
        sa.Column("consumed_quantity", sa.Float(), nullable=False),
        sa.CheckConstraint(
            "consumed_quantity > 0",
            name="check_history_lot_consumed_quantity",
        ),
        sa.ForeignKeyConstraint(
            ["cooking_history_ingredient_id"],
            ["cooking_history_ingredients.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_id"], ["inventories.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_cooking_history_inventory_consumptions_cooking_history_ingredient_id",
        "cooking_history_inventory_consumptions",
        ["cooking_history_ingredient_id"],
    )
    op.create_index(
        "ix_cooking_history_inventory_consumptions_inventory_id",
        "cooking_history_inventory_consumptions",
        ["inventory_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cooking_history_inventory_consumptions_inventory_id",
        table_name="cooking_history_inventory_consumptions",
    )
    op.drop_index(
        "ix_cooking_history_inventory_consumptions_cooking_history_ingredient_id",
        table_name="cooking_history_inventory_consumptions",
    )
    op.drop_table("cooking_history_inventory_consumptions")

    op.drop_index(
        "ix_cooking_history_ingredients_ingredient_id",
        table_name="cooking_history_ingredients",
    )
    op.drop_index(
        "ix_cooking_history_ingredients_cooking_history_id",
        table_name="cooking_history_ingredients",
    )
    op.drop_table("cooking_history_ingredients")

    op.drop_index(
        "ix_cooking_histories_cooked_at",
        table_name="cooking_histories",
    )
    op.drop_index(
        "ix_cooking_histories_recipe_id",
        table_name="cooking_histories",
    )
    op.drop_table("cooking_histories")
