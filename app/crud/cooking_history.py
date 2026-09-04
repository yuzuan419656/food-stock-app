from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.cooking_history import CookingHistory
from app.models.cooking_history_ingredient import (
    CookingHistoryIngredient,
)


def add_cooking_history(
    db: Session,
    cooking_history: CookingHistory,
) -> CookingHistory:
    """調理履歴を現在のトランザクションへ追加する。"""
    db.add(cooking_history)
    db.flush()
    return cooking_history


def get_cooking_histories(
    db: Session,
) -> list[CookingHistory]:
    """調理日時が新しい順に履歴一覧を取得する。"""
    return (
        db.query(CookingHistory)
        .order_by(
            CookingHistory.cooked_at.desc(),
            CookingHistory.id.desc(),
        )
        .all()
    )


def get_cooking_history_by_id(
    db: Session,
    cooking_history_id: int,
) -> CookingHistory | None:
    """材料とロット割当を含む調理履歴を取得する。"""
    return (
        db.query(CookingHistory)
        .options(
            selectinload(
                CookingHistory.ingredients
            ).selectinload(
                CookingHistoryIngredient
                .inventory_consumptions
            ),
            selectinload(
                CookingHistory.ingredients
            ).joinedload(
                CookingHistoryIngredient.ingredient
            ),
        )
        .filter(CookingHistory.id == cooking_history_id)
        .first()
    )
