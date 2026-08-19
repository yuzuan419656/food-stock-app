from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.database import Base


class ShoppingItem(Base):
    __tablename__ = "shopping_items"

    __table_args__ = (
        CheckConstraint(
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
            name="ck_shopping_items_source",
        ),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    ingredient_id: Mapped[int | None] = (
        mapped_column(
            ForeignKey(
                "ingredients.id",
                ondelete="CASCADE",
            ),
            nullable=True,
            unique=True,
            index=True,
        )
    )

    custom_name: Mapped[str | None] = (
        mapped_column(
            String(100),
            nullable=True,
        )
    )

    is_purchased: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
        back_populates="shopping_item",
    )

    @property
    def display_name(self) -> str:
        """
        買うものリストに表示する名称を返す。

        食材マスタ由来の場合は食材名、
        手入力の場合はcustom_nameを使用する。
        """
        if self.ingredient is not None:
            return self.ingredient.name

        return self.custom_name or ""