from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventories"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ingredient_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ingredients.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    quantity: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0,
    )

    purchase_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        default=date.today,
    )

    expiration_date: Mapped[date | None] = mapped_column(
        Date,
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

    ingredient = relationship(
        "Ingredient",
        back_populates="inventories",
    )

    __table_args__ = (
        CheckConstraint(
            "quantity >= 0",
            name="check_quantity_non_negative",
        ),
    )