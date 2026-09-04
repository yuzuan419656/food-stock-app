from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CookingHistory(Base):
    __tablename__ = "cooking_histories"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    recipe_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    cooked_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
        index=True,
    )
    yield_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    servings: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    fixed_yield_text: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    recipe = relationship(
        "Recipe",
        back_populates="cooking_histories",
    )
    ingredients = relationship(
        "CookingHistoryIngredient",
        back_populates="cooking_history",
        cascade="all, delete-orphan",
        order_by="CookingHistoryIngredient.id",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(recipe_name)) > 0",
            name="check_cooking_history_recipe_name",
        ),
        CheckConstraint(
            "yield_type IN ('servings', 'fixed')",
            name="check_cooking_history_yield_type",
        ),
        CheckConstraint(
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
    )
