from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    recipe_id: Mapped[int] = mapped_column(
        ForeignKey(
            "recipes.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ingredients.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    quantity_text: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    is_seasoning: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_inventory_consumed: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )

    recipe = relationship(
        "Recipe",
        back_populates="ingredients",
    )

    ingredient = relationship(
        "Ingredient",
        back_populates="recipe_ingredients",
    )

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "ingredient_id",
            name="uq_recipe_ingredient",
        ),
        CheckConstraint(
            """
            (
                quantity IS NOT NULL
                AND quantity > 0
                AND quantity_text IS NULL
            )
            OR
            (
                quantity IS NULL
                AND quantity_text IS NOT NULL
                AND length(trim(quantity_text)) > 0
            )
            """,
            name="check_recipe_ingredient_quantity",
        ),
        CheckConstraint(
            """
            quantity IS NULL
            OR
            (
                unit IS NOT NULL
                AND length(trim(unit)) > 0
            )
            """,
            name="check_numeric_quantity_has_unit",
        ),
        CheckConstraint(
            """
            is_inventory_consumed = false
            OR
            (
                is_seasoning = false
                AND quantity IS NOT NULL
                AND quantity_text IS NULL
            )
            """,
            name="check_inventory_consumption",
        ),
        CheckConstraint(
            "display_order >= 1",
            name="check_ingredient_display_order",
        ),
    )