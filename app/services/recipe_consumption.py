"""レシピ調理による在庫消費処理。"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.crud.inventory import (
    InventoryConsumptionResult,
    consume_inventory_quantity_without_commit,
)
from app.services.recipe_inventory import (
    RecipeInventoryStatus,
    build_recipe_inventory_statuses,
)
from app.services.recipe_serving import (
    format_recipe_quantity,
)


class RecipeConsumptionError(RuntimeError):
    """レシピの在庫消費を完了できない場合の例外。"""


@dataclass(frozen=True)
class RecipeConsumptionPlanItem:
    """確認画面に表示する材料ごとの消費予定。"""

    inventory_status: RecipeInventoryStatus
    planned_consumption_quantity: float | None
    display_planned_consumption_quantity: str | None


@dataclass(frozen=True)
class RecipeConsumptionResult:
    """レシピ1回分の在庫消費結果。"""

    inventory_results: tuple[
        InventoryConsumptionResult, ...
    ]
    has_shortage: bool


def build_recipe_consumption_plan(
    recipe,
    target_servings: int | None = None,
) -> list[RecipeConsumptionPlanItem]:
    """Step 2の在庫判定結果から消費予定を作る。"""
    statuses = build_recipe_inventory_statuses(
        recipe=recipe,
        target_servings=target_servings,
    )
    plan: list[RecipeConsumptionPlanItem] = []

    for status in statuses:
        planned_quantity = None

        if status.is_automatically_checkable:
            planned_quantity = min(
                status.required_quantity or 0.0,
                status.inventory_quantity or 0.0,
            )

        plan.append(
            RecipeConsumptionPlanItem(
                inventory_status=status,
                planned_consumption_quantity=(
                    planned_quantity
                ),
                display_planned_consumption_quantity=(
                    format_recipe_quantity(
                        planned_quantity
                    )
                    if planned_quantity is not None
                    else None
                ),
            )
        )

    return plan


def consume_recipe_inventory(
    db: Session,
    recipe,
    target_servings: int | None = None,
) -> RecipeConsumptionResult:
    """
    自動減算可能な全材料を1トランザクションで消費する。

    在庫不足時は存在する数量だけを消費する。
    """
    plan = build_recipe_consumption_plan(
        recipe=recipe,
        target_servings=target_servings,
    )
    inventory_results: list[
        InventoryConsumptionResult
    ] = []

    try:
        for item in plan:
            status = item.inventory_status

            if not status.is_automatically_checkable:
                continue

            required_quantity = (
                status.required_quantity
            )

            if required_quantity is None:
                continue

            result = (
                consume_inventory_quantity_without_commit(
                    db=db,
                    ingredient_id=(
                        status.recipe_ingredient
                        .ingredient_id
                    ),
                    amount=required_quantity,
                )
            )

            if result is None:
                raise RecipeConsumptionError(
                    "減算対象の食材が見つかりません。"
                )

            inventory_results.append(result)

        db.commit()

    except Exception:
        db.rollback()
        raise

    return RecipeConsumptionResult(
        inventory_results=tuple(inventory_results),
        has_shortage=any(
            result.shortage_quantity > 0
            for result in inventory_results
        ),
    )
