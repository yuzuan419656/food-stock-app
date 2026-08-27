import pytest

from app.services.recipe_form import (
    RecipeFormValidationError,
    parse_recipe_form,
)


def _build_valid_form() -> dict[str, str]:
    return {
        "name": "肉じゃが",
        "cooking_time_minutes": "30",
        "cuisine_type": "和食",
        "dish_category": "主菜",
        "yield_type": "servings",
        "base_servings": "2",
        "fixed_yield_text": "",
        "is_favorite": "true",
        "ingredient_0_name": "玉ねぎ",
        "ingredient_0_id": "10",
        "ingredient_0_quantity_input": "1.5",
        "ingredient_0_unit": "個",
        "ingredient_0_notes": "薄切り",
        "ingredient_1_name": "塩",
        "ingredient_1_id": "",
        "ingredient_1_category_select": (
            "調味料"
        ),
        "ingredient_1_category_other": "",
        "ingredient_1_quantity_input": "少々",
        "ingredient_1_unit": "g",
        "ingredient_1_notes": "",
        "step_0_description": (
            "材料を切る。"
        ),
        "step_1_description": (
            "鍋で煮込む。"
        ),
    }


def test_parse_recipe_form(
):
    parsed = parse_recipe_form(
        _build_valid_form()
    )

    assert parsed.name == "肉じゃが"
    assert parsed.cooking_time_minutes == 30
    assert parsed.base_servings == 2
    assert parsed.fixed_yield_text is None
    assert parsed.is_favorite is True

    assert len(parsed.ingredients) == 2

    first_ingredient = parsed.ingredients[0]

    assert first_ingredient.ingredient_id == 10
    assert first_ingredient.quantity == 1.5
    assert first_ingredient.quantity_text is None
    assert first_ingredient.unit == "個"
    assert first_ingredient.display_order == 1

    second_ingredient = parsed.ingredients[1]

    assert second_ingredient.ingredient_id is None
    assert second_ingredient.category == "調味料"
    assert second_ingredient.quantity is None
    assert (
        second_ingredient.quantity_text
        == "少々"
    )
    assert second_ingredient.display_order == 2

    assert [
        step.step_number
        for step in parsed.steps
    ] == [1, 2]


def test_parse_recipe_form_accepts_fixed_yield(
):
    form = _build_valid_form()
    form["yield_type"] = "fixed"
    form["base_servings"] = ""
    form["fixed_yield_text"] = "12枚"
    form["ingredient_0_quantity_input"] = (
        "０．５"
    )

    parsed = parse_recipe_form(form)

    assert parsed.base_servings is None
    assert parsed.fixed_yield_text == "12枚"
    assert parsed.ingredients[0].quantity == 0.5


@pytest.mark.parametrize(
    (
        "field_name",
        "field_value",
        "expected_message",
    ),
    [
        (
            "name",
            "",
            "レシピ名",
        ),
        (
            "cooking_time_minutes",
            "0",
            "所要時間",
        ),
        (
            "yield_type",
            "fixed",
            "固定出来高",
        ),
        (
            "ingredient_0_quantity_input",
            "0.3",
            "0.5刻み",
        ),
        (
            "step_0_description",
            "",
            "手順1",
        ),
    ],
)
def test_parse_recipe_form_rejects_invalid_values(
    field_name,
    field_value,
    expected_message,
):
    form = _build_valid_form()
    form[field_name] = field_value

    if field_name == "yield_type":
        form["fixed_yield_text"] = ""

    with pytest.raises(
        RecipeFormValidationError,
        match=expected_message,
    ):
        parse_recipe_form(form)


def test_parse_recipe_form_rejects_duplicate_ingredients(
):
    form = _build_valid_form()

    form["ingredient_1_name"] = "玉ねぎ"
    form["ingredient_1_id"] = "10"

    with pytest.raises(
        RecipeFormValidationError,
        match="重複",
    ):
        parse_recipe_form(form)


def test_parse_recipe_form_resolves_other_category(
):
    form = _build_valid_form()

    form["ingredient_1_category_select"] = (
        "その他"
    )
    form["ingredient_1_category_other"] = (
        "香辛料"
    )

    parsed = parse_recipe_form(form)

    assert (
        parsed.ingredients[1].category
        == "香辛料"
    )