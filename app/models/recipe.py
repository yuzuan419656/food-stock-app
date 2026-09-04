from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    cooking_time_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    cuisine_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    dish_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    yield_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    base_servings: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    fixed_yield_text: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        nullable=False,
    )

    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.display_order",
    )

    steps = relationship(
        "RecipeStep",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeStep.step_number",
    )

    cooking_histories = relationship(
        "CookingHistory",
        back_populates="recipe",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="check_recipe_name_not_blank",
        ),
        CheckConstraint(
            "cooking_time_minutes >= 1",
            name="check_cooking_time_positive",
        ),
        CheckConstraint(
            "yield_type IN ('servings', 'fixed')",
            name="check_recipe_yield_type",
        ),
        CheckConstraint(
            """
            (
                yield_type = 'servings'
                AND base_servings IS NOT NULL
                AND base_servings >= 1
                AND fixed_yield_text IS NULL
            )
            OR
            (
                yield_type = 'fixed'
                AND base_servings IS NULL
                AND fixed_yield_text IS NOT NULL
                AND length(trim(fixed_yield_text)) > 0
            )
            """,
            name="check_recipe_yield_values",
        ),
    )
