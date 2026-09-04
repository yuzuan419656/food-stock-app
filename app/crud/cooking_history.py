from datetime import datetime

from sqlalchemy import func
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


def get_latest_cooking_history(
    db: Session,
) -> CookingHistory | None:
    """取り消し状態を問わず最後に確定した履歴を返す。"""
    return (
        db.query(CookingHistory)
        .order_by(CookingHistory.id.desc())
        .first()
    )


def get_latest_undoable_cooking_history(
    db: Session,
) -> CookingHistory | None:
    """最後の履歴が未取り消しの場合だけ返す。"""
    history = get_latest_cooking_history(db=db)

    if history is None or history.undone_at is not None:
        return None

    return history


def mark_latest_cooking_history_undone(
    db: Session,
    cooking_history_id: int,
    undone_at: datetime,
) -> bool:
    """
    対象が全履歴の最新かつ未取り消しの場合だけ更新する。

    commitは呼び出し側が行う。
    """
    latest_id = db.query(
        func.max(CookingHistory.id)
    ).scalar_subquery()

    updated_count = (
        db.query(CookingHistory)
        .filter(
            CookingHistory.id == cooking_history_id,
            CookingHistory.id == latest_id,
            CookingHistory.undone_at.is_(None),
        )
        .update(
            {CookingHistory.undone_at: undone_at},
            synchronize_session=False,
        )
    )

    return updated_count == 1
