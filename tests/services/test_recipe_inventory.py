from datetime import date

from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import (
    RecipeIngredient,
)
from app.services.recipe_inventory import (
    build_recipe_inventory_statuses,
)


def _build_recipe(
    *,
    quantity: float | None = 2,
    quantity_text: str | None = None,
    recipe_unit: str | None = "個",
    inventory_unit: str | None = "個",
    inventories: list[Inventory] | None = None,
    yield_type: str = "servings",
    base_servings: int | None = 2,
    is_inventory_consumed: bool = True,
    is_seasoning: bool = False,
) -> Recipe:
    ingredient = Ingredient(
        name="じゃがいも",
        category="野菜",
        default_unit=inventory_unit,
        inventories=inventories or [],
    )
    recipe_ingredient = RecipeIngredient(
        ingredient=ingredient,
        quantity=quantity,
        quantity_text=quantity_text,
        unit=recipe_unit,
        is_inventory_consumed=(
            is_inventory_consumed
        ),
        is_seasoning=is_seasoning,
        display_order=1,
    )
    return Recipe(
        name="テストレシピ",
        cooking_time_minutes=20,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=(
            "4個"
            if yield_type == "fixed"
            else None
        ),
        ingredients=[recipe_ingredient],
    )


def _lot(
    quantity: float,
    expiration_date: date | None = date(
        2026, 9, 10
    ),
) -> Inventory:
    return Inventory(
        quantity=quantity,
        purchase_date=date(2026, 9, 1),
        expiration_date=expiration_date,
    )


def _status(recipe, target_servings=None):
    return build_recipe_inventory_statuses(
        recipe,
        target_servings=target_servings,
    )[0]


def test_inventory_is_sufficient():
    result = _status(
        _build_recipe(inventories=[_lot(3)])
    )

    assert result.status == "sufficient"
    assert result.required_quantity == 2
    assert result.inventory_quantity == 3
    assert result.shortage_quantity == 0
    assert result.is_automatically_checkable
    assert result.is_unit_matched


def test_inventory_is_insufficient():
    result = _status(
        _build_recipe(inventories=[_lot(1)])
    )

    assert result.status == "shortage"
    assert result.shortage_quantity == 1


def test_zero_inventory_is_insufficient():
    result = _status(_build_recipe())

    assert result.inventory_quantity == 0
    assert result.shortage_quantity == 2
    assert result.status == "shortage"


def test_multiple_inventory_lots_are_summed():
    result = _status(
        _build_recipe(
            quantity=3,
            inventories=[_lot(1), _lot(2)],
        )
    )

    assert result.inventory_quantity == 3
    assert result.status == "sufficient"


def test_required_quantity_is_scaled_by_servings():
    result = _status(
        _build_recipe(inventories=[_lot(2)]),
        target_servings=4,
    )

    assert result.required_quantity == 4
    assert result.shortage_quantity == 2


def test_fixed_yield_uses_registered_quantity():
    result = _status(
        _build_recipe(
            quantity=2,
            inventories=[_lot(2)],
            yield_type="fixed",
            base_servings=None,
        ),
        target_servings=None,
    )

    assert result.required_quantity == 2
    assert result.status == "sufficient"


def test_unit_mismatch_is_not_treated_as_shortage():
    result = _status(
        _build_recipe(
            recipe_unit="g",
            inventory_unit="個",
            inventories=[_lot(1)],
        )
    )

    assert result.status == "unit_mismatch"
    assert result.shortage_quantity is None
    assert not result.is_automatically_checkable
    assert result.is_unit_matched is False


def test_non_consumed_ingredient_is_not_applicable():
    result = _status(
        _build_recipe(is_inventory_consumed=False)
    )

    assert result.status == "not_applicable"
    assert not result.is_automatically_checkable


def test_seasoning_is_not_applicable():
    result = _status(
        _build_recipe(
            is_seasoning=True,
            is_inventory_consumed=False,
        )
    )

    assert result.status == "not_applicable"


def test_text_quantity_is_not_applicable():
    result = _status(
        _build_recipe(
            quantity=None,
            quantity_text="適量",
            recipe_unit=None,
            is_inventory_consumed=False,
        )
    )

    assert result.status == "not_applicable"
    assert result.display_required_quantity == "適量"


def test_inventory_without_expiration_is_included():
    result = _status(
        _build_recipe(
            quantity=2,
            inventories=[
                _lot(0.5),
                _lot(1.5, expiration_date=None),
            ],
        )
    )

    assert result.inventory_quantity == 2
    assert result.status == "sufficient"


def test_soft_deleted_and_empty_lots_are_excluded():
    deleted = _lot(10)
    deleted.deleted_at = date(2026, 9, 2)

    result = _status(
        _build_recipe(
            inventories=[deleted, _lot(0)],
        )
    )

    assert result.inventory_quantity == 0
    assert result.status == "shortage"
