from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    category: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    default_unit: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        nullable=False,
    )

    inventories = relationship(
        "Inventory",
        back_populates="ingredient",
        cascade="all, delete-orphan",
    )

    shopping_item = relationship(
        "ShoppingItem",
        back_populates="ingredient",
        uselist=False,
        cascade="all, delete-orphan",
    )