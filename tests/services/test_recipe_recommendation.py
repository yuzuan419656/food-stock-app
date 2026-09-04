from datetime import date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.cooking_history import CookingHistory
from app.models.ingredient import Ingredient
from app.models.inventory import Inventory
from app.models.recipe import Recipe
from app.models.recipe_ingredient import RecipeIngredient
from app.services.recipe_recommendation import (
    MODE_WEIGHTS,
    RecommendationWeights,
    calculate_cooking_time_score,
    calculate_expiration_score,
    calculate_history_score,
    get_recipe_history_summaries,
    recommend_recipes,
)


NOW = datetime(2026, 9, 4, 12, 0, 0)


def _create_recipe(
    db: Session,
    *,
    name: str,
    quantities: list[tuple[float | None, float, int | None]] | None = None,
    cooking_time: int = 20,
    favorite: bool = False,
    yield_type: str = "servings",
    active: bool = True,
    recipe_unit: str = "個",
    inventory_unit: str = "個",
    is_inventory_consumed: bool = True,
    is_seasoning: bool = False,
) -> Recipe:
    ingredients = []
    for index, (required, stock, days_to_expiry) in enumerate(
        quantities or [(2, 2, None)], start=1
    ):
        ingredient = Ingredient(
            name=f"{name}食材{index}",
            category="野菜",
            default_unit=inventory_unit,
        )
        if stock > 0:
            ingredient.inventories = [
                Inventory(
                    quantity=stock,
                    purchase_date=date(2026, 9, 1),
                    expiration_date=(
                        NOW.date() + timedelta(days=days_to_expiry)
                        if days_to_expiry is not None
                        else None
                    ),
                )
            ]
        ingredients.append(
            RecipeIngredient(
                ingredient=ingredient,
                quantity=required,
                quantity_text=None if required is not None else "適量",
                unit=recipe_unit if required is not None else None,
                is_inventory_consumed=is_inventory_consumed,
                is_seasoning=is_seasoning,
                display_order=index,
            )
        )

    recipe = Recipe(
        name=name,
        cooking_time_minutes=cooking_time,
        cuisine_type="和食",
        dish_category="主菜",
        yield_type=yield_type,
        base_servings=2 if yield_type == "servings" else None,
        fixed_yield_text=None if yield_type == "servings" else "1皿",
        is_favorite=favorite,
        is_active=active,
        deleted_at=None if active else NOW,
        ingredients=ingredients,
    )
    db.add(recipe)
    db.commit()
    return recipe


def _add_history(
    db: Session,
    recipe: Recipe,
    cooked_at: datetime,
    undone: bool = False,
) -> CookingHistory:
    history = CookingHistory(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        cooked_at=cooked_at,
        undone_at=cooked_at + timedelta(hours=1) if undone else None,
        yield_type=recipe.yield_type,
        servings=2 if recipe.yield_type == "servings" else None,
        fixed_yield_text=(
            recipe.fixed_yield_text if recipe.yield_type == "fixed" else None
        ),
    )
    db.add(history)
    db.commit()
    return history


def test_recommend_recipes_filters_by_cuisine_and_category(
    db_session: Session,
):
    japanese = _create_recipe(db_session, name="和食候補")
    western = _create_recipe(db_session, name="洋食候補")
    western.cuisine_type = "洋食"
    western.dish_category = "副菜"
    db_session.commit()

    results = recommend_recipes(
        db_session,
        cuisine_type="洋食",
        dish_category="副菜",
    )

    assert [item.recipe.id for item in results] == [western.id]
    assert all(item.recipe.id != japanese.id for item in results)


@pytest.mark.parametrize(
    ("days", "expected", "reason_fragment"),
    [
        (-1, 8, "期限を過ぎた"),
        (1, 6, "1日以内"),
        (3, 4, "3日以内"),
        (7, 2, "7日以内"),
    ],
)
def test_expiration_bands(
    db_session: Session,
    days: int,
    expected: float,
    reason_fragment: str,
):
    recipe = _create_recipe(
        db_session,
        name=f"期限{days}",
        quantities=[(1, 1, days)],
    )
    result = recommend_recipes(db_session, now=NOW)[0]

    assert result.expiration_score == expected
    assert any(reason_fragment in reason for reason in result.recommendation_reasons)


def test_expiration_without_date_adds_no_score(db_session: Session):
    _create_recipe(db_session, name="期限なし", quantities=[(1, 1, None)])
    result = recommend_recipes(db_session, now=NOW)[0]
    assert result.expiration_score == 0
    assert result.urgent_ingredient_count == 0


def test_expiration_counts_ingredient_types(db_session: Session):
    recipe = _create_recipe(
        db_session,
        name="期限種類数",
        quantities=[(1, 10, 1), (1, 1, 1), (1, 1, 3)],
    )
    statuses = list(recommend_recipes(db_session, now=NOW)[0].inventory_statuses)
    expiration = calculate_expiration_score(statuses, NOW.date())

    assert expiration.within_one_day_count == 2
    assert expiration.within_three_days_count == 1
    assert expiration.urgent_ingredient_count == 3
    assert recipe.id is not None


def test_inventory_scores_full_partial_multiple_and_zero(db_session: Session):
    _create_recipe(db_session, name="全部あり", quantities=[(2, 2, None)])
    _create_recipe(db_session, name="一部不足", quantities=[(2, 1, None)])
    _create_recipe(
        db_session,
        name="複数不足",
        quantities=[(2, 1, None), (2, 0, None)],
    )
    results = {
        item.recipe.name: item
        for item in recommend_recipes(
            db_session,
            now=NOW,
        )
    }

    assert results["全部あり"].inventory_score == 10
    assert results["全部あり"].shortage_penalty == 0
    assert results["一部不足"].shortage_ingredient_count == 1
    assert results["複数不足"].shortage_ingredient_count == 2
    assert results["複数不足"].shortage_penalty > results["一部不足"].shortage_penalty


@pytest.mark.parametrize(
    "kwargs",
    [
        {"recipe_unit": "g", "inventory_unit": "個"},
        {"is_inventory_consumed": False},
        {"is_inventory_consumed": False, "is_seasoning": True},
    ],
)
def test_uncheckable_items_are_not_shortages(db_session: Session, kwargs: dict):
    _create_recipe(
        db_session,
        name=f"判定外{len(db_session.new)}{len(kwargs)}",
        quantities=[(2, 0, None)],
        **kwargs,
    )
    result = recommend_recipes(db_session, now=NOW)[0]
    assert result.shortage_ingredient_count == 0
    assert result.shortage_penalty == 0


def test_selected_servings_changes_score(db_session: Session):
    _create_recipe(db_session, name="人数変更", quantities=[(2, 3, None)])
    two = recommend_recipes(db_session, target_servings=2, now=NOW)[0]
    four = recommend_recipes(db_session, target_servings=4, now=NOW)[0]

    assert two.shortage_ingredient_count == 0
    assert four.shortage_ingredient_count == 1
    assert four.total_score < two.total_score


def test_fixed_yield_ignores_target_servings(db_session: Session):
    _create_recipe(
        db_session,
        name="固定出来高",
        quantities=[(2, 1, None)],
        yield_type="fixed",
    )
    result = recommend_recipes(db_session, target_servings=10, now=NOW)[0]

    assert result.selected_servings is None
    assert result.inventory_statuses[0].required_quantity == 2


def test_favorite_is_scored_and_explained(db_session: Session):
    _create_recipe(db_session, name="お気に入り", favorite=True)
    result = recommend_recipes(db_session, now=NOW)[0]
    assert result.favorite_score == 3
    assert "お気に入りのレシピです" in result.recommendation_reasons


def test_history_summary_excludes_undone_history(db_session: Session):
    recipe = _create_recipe(db_session, name="履歴")
    _add_history(db_session, recipe, NOW - timedelta(days=30))
    _add_history(db_session, recipe, NOW - timedelta(days=20))
    _add_history(db_session, recipe, NOW - timedelta(days=1), undone=True)

    summary = get_recipe_history_summaries(db_session)[recipe.id]
    result = recommend_recipes(db_session, now=NOW)[0]

    assert summary.cooking_count == 2
    assert summary.last_cooked_at == NOW - timedelta(days=20)
    assert result.cooking_count == 2
    assert result.history_score == 1
    assert result.recency_score == 2


def test_history_score_is_capped_and_new_recipe_gets_moderate_recency(
    db_session: Session,
):
    _create_recipe(db_session, name="未調理")
    result = recommend_recipes(db_session, now=NOW)[0]

    assert calculate_history_score(100) == 2.5
    assert result.cooking_count == 0
    assert result.last_cooked_at is None
    assert result.recency_score == 2


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [(10, 4), (20, 3), (30, 2), (31, 0)],
)
def test_cooking_time_bands(minutes: int, expected: float):
    score, _ = calculate_cooking_time_score(minutes)
    assert score == expected


@pytest.mark.parametrize("mode", ["balanced", "expiring", "quick", "in_stock"])
def test_all_modes_are_available(db_session: Session, mode: str):
    _create_recipe(db_session, name=f"モード{mode}")
    result = recommend_recipes(db_session, mode=mode, now=NOW)[0]
    assert result.total_score is not None
    assert mode in MODE_WEIGHTS


def test_modes_emphasize_expected_components(db_session: Session):
    _create_recipe(
        db_session,
        name="モード比較",
        quantities=[(2, 1, 1)],
        cooking_time=10,
    )
    balanced = recommend_recipes(db_session, mode="balanced", now=NOW)[0]
    expiring = recommend_recipes(db_session, mode="expiring", now=NOW)[0]
    quick = recommend_recipes(db_session, mode="quick", now=NOW)[0]
    in_stock = recommend_recipes(db_session, mode="in_stock", now=NOW)[0]

    assert expiring.expiration_score > balanced.expiration_score
    assert quick.cooking_time_score > balanced.cooking_time_score
    assert in_stock.shortage_penalty > balanced.shortage_penalty


def test_custom_weights_are_applied(db_session: Session):
    _create_recipe(db_session, name="重み", favorite=True)
    result = recommend_recipes(
        db_session,
        weights=RecommendationWeights(favorite=3),
        now=NOW,
    )[0]
    assert result.favorite_score == 9


def test_results_are_sorted_and_ties_are_stable(db_session: Session):
    first = _create_recipe(db_session, name="同点A")
    second = _create_recipe(db_session, name="同点B")
    favorite = _create_recipe(db_session, name="上位", favorite=True)

    results = recommend_recipes(db_session, now=NOW)

    assert results[0].recipe.id == favorite.id
    tied_ids = [
        item.recipe.id
        for item in results
        if item.recipe.id in {first.id, second.id}
    ]
    assert tied_ids == [first.id, second.id]


def test_inactive_recipe_is_excluded(db_session: Session):
    active = _create_recipe(db_session, name="有効")
    _create_recipe(db_session, name="削除済み", active=False)

    results = recommend_recipes(db_session, now=NOW)
    assert [item.recipe.id for item in results] == [active.id]


def test_invalid_mode_is_rejected(db_session: Session):
    with pytest.raises(ValueError, match="未対応"):
        recommend_recipes(db_session, mode="unknown", now=NOW)


@pytest.mark.parametrize(
    ("limit", "expected_names"),
    [
        (None, {"10分", "20分", "30分", "31分"}),
        (10, {"10分"}),
        (20, {"10分", "20分"}),
        (30, {"10分", "20分", "30分"}),
    ],
)
def test_cooking_time_filter(
    db_session: Session,
    limit: int | None,
    expected_names: set[str],
):
    for minutes in (10, 20, 30, 31):
        _create_recipe(
            db_session,
            name=f"{minutes}分",
            cooking_time=minutes,
        )

    results = recommend_recipes(
        db_session,
        max_cooking_time=limit,
        now=NOW,
    )

    assert {result.recipe.name for result in results} == expected_names


def test_invalid_cooking_time_filter_is_rejected(db_session: Session):
    with pytest.raises(ValueError, match="調理時間"):
        recommend_recipes(
            db_session,
            max_cooking_time=15,
            now=NOW,
        )


@pytest.mark.parametrize(
    ("weight_name", "result_name"),
    [
        ("expiration", "expiration_score"),
        ("inventory", "inventory_score"),
        ("favorite", "favorite_score"),
        ("history", "history_score"),
        ("recency", "recency_score"),
        ("cooking_time", "cooking_time_score"),
        ("shortage", "shortage_penalty"),
    ],
)
def test_zero_custom_weight_disables_component(
    db_session: Session,
    weight_name: str,
    result_name: str,
):
    recipe = _create_recipe(
        db_session,
        name=f"ゼロ重み{weight_name}",
        quantities=[(2, 2, 1), (2, 1, None)],
        cooking_time=10,
        favorite=True,
    )
    _add_history(
        db_session,
        recipe,
        NOW - timedelta(days=30),
    )
    values = {
        "expiration": 1.0,
        "inventory": 1.0,
        "favorite": 1.0,
        "history": 1.0,
        "recency": 1.0,
        "cooking_time": 1.0,
        "shortage": 1.0,
    }
    values[weight_name] = 0.0

    result = recommend_recipes(
        db_session,
        weights=RecommendationWeights(**values),
        now=NOW,
    )[0]

    assert getattr(result, result_name) == 0


def test_upper_weight_value_is_supported(db_session: Session):
    _create_recipe(db_session, name="上限重み", favorite=True)
    result = recommend_recipes(
        db_session,
        weights=RecommendationWeights(
            expiration=3,
            inventory=3,
            favorite=3,
            history=3,
            recency=3,
            cooking_time=3,
            shortage=3,
        ),
        now=NOW,
    )[0]
    assert result.favorite_score == 9


def test_mode_and_custom_weights_are_multiplied(db_session: Session):
    _create_recipe(
        db_session,
        name="モード重み併用",
        cooking_time=10,
    )
    result = recommend_recipes(
        db_session,
        mode="quick",
        weights=RecommendationWeights(cooking_time=2),
        now=NOW,
    )[0]
    assert result.cooking_time_score == 24


@pytest.mark.parametrize(
    "invalid_weight",
    [-0.1, 3.1, float("nan"), float("inf")],
)
def test_invalid_custom_weight_is_rejected(
    db_session: Session,
    invalid_weight: float,
):
    with pytest.raises(ValueError, match="0.0から3.0"):
        recommend_recipes(
            db_session,
            weights=RecommendationWeights(
                expiration=invalid_weight
            ),
            now=NOW,
        )
