from sqlalchemy import CheckConstraint, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CookingHistoryInventoryConsumption(Base):
    __tablename__ = "cooking_history_inventory_consumptions"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    cooking_history_ingredient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cooking_history_ingredients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("inventories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    consumed_quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    cooking_history_ingredient = relationship(
        "CookingHistoryIngredient",
        back_populates="inventory_consumptions",
    )
    inventory = relationship(
        "Inventory",
        back_populates="cooking_history_consumptions",
    )

    __table_args__ = (
        CheckConstraint(
            "consumed_quantity > 0",
            name="check_history_lot_consumed_quantity",
        ),
    )
