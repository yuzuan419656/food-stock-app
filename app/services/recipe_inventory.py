"""レシピ材料と現在庫の充足判定。"""

from dataclasses import dataclass

from app.crud.inventory import get_inventory_quantity
from app.services.recipe_serving import (
    calculate_scaled_quantity,
    format_recipe_quantity,
)


@dataclass(frozen=True)
class RecipeInventoryStatus:
    """1材料分の、画面表示に使用する在庫判定結果。"""

    recipe_ingredient: object
    required_quantity: float | None
    inventory_quantity: float | None
    shortage_quantity: float | None
    display_required_quantity: str
    display_inventory_quantity: str | None
    display_shortage_quantity: str | None
    is_unit_matched: bool | None
    is_automatically_checkable: bool
    status: str


def _get_required_quantity(
    recipe,
    recipe_ingredient,
    target_servings: int | None,
) -> float | None:
    if recipe_ingredient.quantity is None:
        return None

    if recipe.yield_type == "fixed":
        return float(recipe_ingredient.quantity)

    selected_servings = (
        target_servings
        if target_servings is not None
        else recipe.base_servings
    )

    if recipe.base_servings is None:
        raise ValueError(
            "基準人数が設定されていません。"
        )

    if selected_servings is None:
        raise ValueError(
            "人数が設定されていません。"
        )

    return calculate_scaled_quantity(
        base_quantity=float(
            recipe_ingredient.quantity
        ),
        base_servings=recipe.base_servings,
        target_servings=selected_servings,
    )


def build_recipe_inventory_statuses(
    recipe,
    target_servings: int | None = None,
) -> list[RecipeInventoryStatus]:
    """
    レシピの各材料について現在庫との充足状況を返す。

    この処理は在庫を参照するだけで、DBを更新しない。
    """
    results: list[RecipeInventoryStatus] = []

    for item in recipe.ingredients:
        required_quantity = _get_required_quantity(
            recipe=recipe,
            recipe_ingredient=item,
            target_servings=target_servings,
        )
        display_required_quantity = (
            format_recipe_quantity(required_quantity)
            if required_quantity is not None
            else (item.quantity_text or "")
        )

        is_target = (
            item.is_inventory_consumed
            and not item.is_seasoning
            and required_quantity is not None
        )

        if not is_target:
            results.append(
                RecipeInventoryStatus(
                    recipe_ingredient=item,
                    required_quantity=required_quantity,
                    inventory_quantity=None,
                    shortage_quantity=None,
                    display_required_quantity=(
                        display_required_quantity
                    ),
                    display_inventory_quantity=None,
                    display_shortage_quantity=None,
                    is_unit_matched=None,
                    is_automatically_checkable=False,
                    status="not_applicable",
                )
            )
            continue

        unit_matched = (
            item.unit == item.ingredient.default_unit
        )

        if not unit_matched:
            results.append(
                RecipeInventoryStatus(
                    recipe_ingredient=item,
                    required_quantity=required_quantity,
                    inventory_quantity=None,
                    shortage_quantity=None,
                    display_required_quantity=(
                        display_required_quantity
                    ),
                    display_inventory_quantity=None,
                    display_shortage_quantity=None,
                    is_unit_matched=False,
                    is_automatically_checkable=False,
                    status="unit_mismatch",
                )
            )
            continue

        inventory_quantity = get_inventory_quantity(
            item.ingredient
        )
        shortage_quantity = max(
            required_quantity - inventory_quantity,
            0.0,
        )
        status = (
            "sufficient"
            if shortage_quantity == 0
            else "shortage"
        )

        results.append(
            RecipeInventoryStatus(
                recipe_ingredient=item,
                required_quantity=required_quantity,
                inventory_quantity=inventory_quantity,
                shortage_quantity=shortage_quantity,
                display_required_quantity=(
                    display_required_quantity
                ),
                display_inventory_quantity=(
                    format_recipe_quantity(
                        inventory_quantity
                    )
                ),
                display_shortage_quantity=(
                    format_recipe_quantity(
                        shortage_quantity
                    )
                ),
                is_unit_matched=True,
                is_automatically_checkable=True,
                status=status,
            )
        )

    return results
