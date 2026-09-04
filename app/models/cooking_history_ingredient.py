from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CookingHistoryIngredient(Base):
    __tablename__ = "cooking_history_ingredients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    cooking_history_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cooking_histories.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey("ingredients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ingredient_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    required_quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    required_quantity_text: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    consumed_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )
    shortage_quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    unit: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )
    inventory_consumed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    cooking_history = relationship(
        "CookingHistory",
        back_populates="ingredients",
    )
    ingredient = relationship(
        "Ingredient",
        back_populates="cooking_history_ingredients",
    )
    inventory_consumptions = relationship(
        "CookingHistoryInventoryConsumption",
        back_populates="cooking_history_ingredient",
        cascade="all, delete-orphan",
        order_by="CookingHistoryInventoryConsumption.id",
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(ingredient_name)) > 0",
            name="check_history_ingredient_name",
        ),
        CheckConstraint(
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
        CheckConstraint(
            "consumed_quantity >= 0",
            name="check_history_consumed_quantity",
        ),
        CheckConstraint(
            "shortage_quantity IS NULL OR shortage_quantity >= 0",
            name="check_history_shortage_quantity",
        ),
        CheckConstraint(
            "status IN ('sufficient', 'shortage', 'unit_mismatch', 'not_applicable')",
            name="check_history_ingredient_status",
        ),
    )
