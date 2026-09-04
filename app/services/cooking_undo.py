"""直前の調理取り消しと在庫ロット復元。"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.crud.cooking_history import (
    get_cooking_history_by_id,
    get_latest_cooking_history,
    mark_latest_cooking_history_undone,
)
from app.crud.inventory import (
    restore_inventory_lot_quantity_without_commit,
)
from app.models.inventory import Inventory


class CookingUndoError(RuntimeError):
    """安全に調理を取り消せない場合の例外。"""


class CookingUndoNotAllowedError(CookingUndoError):
    """対象履歴が直前の未取り消し履歴ではない。"""


class CookingUndoInventoryUnavailableError(CookingUndoError):
    """復元先ロットが存在しないか利用できない。"""


@dataclass(frozen=True)
class CookingUndoPlanItem:
    ingredient_name: str
    unit: str | None
    restore_quantity: float


def _ensure_history_is_undoable(db: Session, history) -> None:
    latest = get_latest_cooking_history(db=db)

    if (
        latest is None
        or latest.id != history.id
        or history.undone_at is not None
    ):
        raise CookingUndoNotAllowedError(
            "この調理履歴は取り消せません。"
        )


def _get_allocations(history):
    return [
        allocation
        for ingredient in history.ingredients
        for allocation in ingredient.inventory_consumptions
    ]


def _ensure_inventories_are_restorable(
    db: Session,
    history,
) -> None:
    allocations = _get_allocations(history)
    inventory_ids = {
        allocation.inventory_id
        for allocation in allocations
    }

    if not inventory_ids:
        return

    restorable_ids = {
        inventory_id
        for (inventory_id,) in (
            db.query(Inventory.id)
            .join(Inventory.ingredient)
            .filter(
                Inventory.id.in_(inventory_ids),
                Inventory.deleted_at.is_(None),
                Inventory.ingredient.has(is_active=True),
            )
            .all()
        )
    }

    if restorable_ids != inventory_ids:
        raise CookingUndoInventoryUnavailableError(
            "復元先の在庫ロットが削除されているため、"
            "この調理は取り消せません。"
        )


def build_cooking_undo_plan(
    db: Session,
    cooking_history_id: int,
):
    """取り消し可否を確認し、材料別の復元予定を返す。"""
    history = get_cooking_history_by_id(
        db=db,
        cooking_history_id=cooking_history_id,
    )

    if history is None:
        return None

    _ensure_history_is_undoable(db=db, history=history)
    _ensure_inventories_are_restorable(db=db, history=history)

    plan = [
        CookingUndoPlanItem(
            ingredient_name=ingredient.ingredient_name,
            unit=ingredient.unit,
            restore_quantity=sum(
                allocation.consumed_quantity
                for allocation in ingredient.inventory_consumptions
            ),
        )
        for ingredient in history.ingredients
        if ingredient.inventory_consumptions
    ]

    return history, plan


def undo_latest_cooking(
    db: Session,
    cooking_history_id: int,
    undone_at: datetime | None = None,
):
    """直前の調理で消費した数量を元ロットへ戻す。"""
    history = get_cooking_history_by_id(
        db=db,
        cooking_history_id=cooking_history_id,
    )

    if history is None:
        return None

    undo_time = undone_at or datetime.now()

    try:
        _ensure_history_is_undoable(db=db, history=history)
        _ensure_inventories_are_restorable(
            db=db,
            history=history,
        )

        marked = mark_latest_cooking_history_undone(
            db=db,
            cooking_history_id=history.id,
            undone_at=undo_time,
        )

        if not marked:
            raise CookingUndoNotAllowedError(
                "この調理履歴はすでに取り消されたか、"
                "直前の調理ではありません。"
            )

        for allocation in _get_allocations(history):
            inventory = (
                restore_inventory_lot_quantity_without_commit(
                    db=db,
                    inventory_id=allocation.inventory_id,
                    amount=allocation.consumed_quantity,
                )
            )

            if inventory is None:
                raise CookingUndoInventoryUnavailableError(
                    "復元先の在庫ロットを利用できません。"
                )

        history.undone_at = undo_time
        db.commit()

    except Exception:
        db.rollback()
        raise

    return history
