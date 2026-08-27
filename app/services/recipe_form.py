from dataclasses import dataclass
from math import isfinite
from typing import Mapping
import re
import unicodedata

from app.constants.ingredient_options import (
    CATEGORY_OPTIONS,
)
from app.constants.recipe_options import (
    RECIPE_CUISINE_OPTIONS,
    RECIPE_DISH_CATEGORY_OPTIONS,
)
from app.services.ingredient_form import (
    resolve_selected_option,
)
from app.utils.ingredient_name import (
    normalize_ingredient_name,
)
from app.utils.quantity import (
    is_valid_quantity_step,
)


@dataclass(frozen=True)
class RecipeFormIngredient:
    """フォームから解析したレシピ材料。"""

    ingredient_id: int | None
    name: str
    category: str | None
    quantity: float | None
    quantity_text: str | None
    unit: str
    notes: str | None
    display_order: int


@dataclass(frozen=True)
class RecipeFormStep:
    """フォームから解析した調理手順。"""

    step_number: int
    description: str


@dataclass(frozen=True)
class ParsedRecipeForm:
    """解析・検証済みのレシピ登録内容。"""

    name: str
    cooking_time_minutes: int
    cuisine_type: str
    dish_category: str
    yield_type: str
    base_servings: int | None
    fixed_yield_text: str | None
    is_favorite: bool
    ingredients: tuple[
        RecipeFormIngredient,
        ...,
    ]
    steps: tuple[
        RecipeFormStep,
        ...,
    ]


class RecipeFormValidationError(ValueError):
    """レシピフォームの入力エラー。"""


def _get_string(
    form: Mapping[str, object],
    key: str,
) -> str:
    value = form.get(key, "")

    if value is None:
        return ""

    return str(value).strip()


def _collect_indices(
    form: Mapping[str, object],
    pattern: re.Pattern[str],
) -> list[int]:
    indices: set[int] = set()

    for key in form:
        matched = pattern.fullmatch(
            str(key)
        )

        if matched:
            indices.add(
                int(matched.group(1))
            )

    return sorted(indices)


def _parse_positive_integer(
    value: str,
    field_label: str,
) -> int:
    if not value:
        raise RecipeFormValidationError(
            f"{field_label}を入力してください。"
        )

    try:
        parsed_value = int(value)

    except ValueError as error:
        raise RecipeFormValidationError(
            f"{field_label}は整数で入力してください。"
        ) from error

    if parsed_value < 1:
        raise RecipeFormValidationError(
            f"{field_label}は1以上で入力してください。"
        )

    return parsed_value


def _parse_quantity(
    value: str,
    row_number: int,
) -> tuple[float | None, str | None]:
    normalized_value = unicodedata.normalize(
        "NFKC",
        value.strip(),
    )

    if not normalized_value:
        raise RecipeFormValidationError(
            f"材料{row_number}の数量を"
            "入力してください。"
        )

    try:
        quantity = float(normalized_value)

    except ValueError:
        if len(normalized_value) > 50:
            raise RecipeFormValidationError(
                f"材料{row_number}の数量表記は"
                "50文字以内で入力してください。"
            )

        return None, normalized_value

    if not isfinite(quantity):
        raise RecipeFormValidationError(
            f"材料{row_number}の数量が"
            "正しくありません。"
        )

    if quantity <= 0:
        raise RecipeFormValidationError(
            f"材料{row_number}の数量は"
            "0より大きい値を入力してください。"
        )

    if not is_valid_quantity_step(quantity):
        raise RecipeFormValidationError(
            f"材料{row_number}の数値数量は"
            "0.5刻みで入力してください。"
        )

    return quantity, None


def _parse_ingredient_id(
    value: str,
    row_number: int,
) -> int | None:
    if not value:
        return None

    try:
        ingredient_id = int(value)

    except ValueError as error:
        raise RecipeFormValidationError(
            f"材料{row_number}の食材情報が"
            "正しくありません。"
        ) from error

    if ingredient_id < 1:
        raise RecipeFormValidationError(
            f"材料{row_number}の食材情報が"
            "正しくありません。"
        )

    return ingredient_id


def _parse_ingredients(
    form: Mapping[str, object],
) -> tuple[RecipeFormIngredient, ...]:
    indices = _collect_indices(
        form=form,
        pattern=re.compile(
            r"ingredient_(\d+)_name"
        ),
    )

    if not indices:
        raise RecipeFormValidationError(
            "材料を1件以上入力してください。"
        )

    parsed_ingredients: list[
        RecipeFormIngredient
    ] = []

    normalized_names: set[str] = set()

    for display_order, index in enumerate(
        indices,
        start=1,
    ):
        name = normalize_ingredient_name(
            _get_string(
                form,
                f"ingredient_{index}_name",
            )
        )

        if not name:
            raise RecipeFormValidationError(
                f"材料{display_order}の食材名を"
                "入力してください。"
            )

        if len(name) > 100:
            raise RecipeFormValidationError(
                f"材料{display_order}の食材名は"
                "100文字以内で入力してください。"
            )

        normalized_key = name.lower()

        if normalized_key in normalized_names:
            raise RecipeFormValidationError(
                "同じ食材を重複して"
                "指定できません。"
            )

        normalized_names.add(normalized_key)

        ingredient_id = _parse_ingredient_id(
            value=_get_string(
                form,
                f"ingredient_{index}_id",
            ),
            row_number=display_order,
        )

        category: str | None = None

        if ingredient_id is None:
            category, category_error = (
                resolve_selected_option(
                    selected_value=_get_string(
                        form,
                        (
                            f"ingredient_{index}"
                            "_category_select"
                        ),
                    ),
                    other_value=_get_string(
                        form,
                        (
                            f"ingredient_{index}"
                            "_category_other"
                        ),
                    ),
                    allowed_options=(
                        CATEGORY_OPTIONS
                    ),
                    field_label=(
                        f"材料{display_order}の"
                        "カテゴリ"
                    ),
                )
            )

            if category_error:
                raise RecipeFormValidationError(
                    category_error
                )

        quantity, quantity_text = (
            _parse_quantity(
                value=_get_string(
                    form,
                    (
                        f"ingredient_{index}"
                        "_quantity_input"
                    ),
                ),
                row_number=display_order,
            )
        )

        unit = _get_string(
            form,
            f"ingredient_{index}_unit",
        )

        if not unit:
            raise RecipeFormValidationError(
                f"材料{display_order}の単位を"
                "入力してください。"
            )

        if len(unit) > 30:
            raise RecipeFormValidationError(
                f"材料{display_order}の単位は"
                "30文字以内で入力してください。"
            )

        notes = _get_string(
            form,
            f"ingredient_{index}_notes",
        )

        if len(notes) > 255:
            raise RecipeFormValidationError(
                f"材料{display_order}の備考は"
                "255文字以内で入力してください。"
            )

        parsed_ingredients.append(
            RecipeFormIngredient(
                ingredient_id=ingredient_id,
                name=name,
                category=category,
                quantity=quantity,
                quantity_text=quantity_text,
                unit=unit,
                notes=notes or None,
                display_order=display_order,
            )
        )

    return tuple(parsed_ingredients)


def _parse_steps(
    form: Mapping[str, object],
) -> tuple[RecipeFormStep, ...]:
    indices = _collect_indices(
        form=form,
        pattern=re.compile(
            r"step_(\d+)_description"
        ),
    )

    if not indices:
        raise RecipeFormValidationError(
            "調理手順を1件以上入力してください。"
        )

    parsed_steps: list[RecipeFormStep] = []

    for step_number, index in enumerate(
        indices,
        start=1,
    ):
        description = _get_string(
            form,
            f"step_{index}_description",
        )

        if not description:
            raise RecipeFormValidationError(
                f"手順{step_number}を"
                "入力してください。"
            )

        parsed_steps.append(
            RecipeFormStep(
                step_number=step_number,
                description=description,
            )
        )

    return tuple(parsed_steps)


def parse_recipe_form(
    form: Mapping[str, object],
) -> ParsedRecipeForm:
    """レシピ登録フォームを解析・検証する。"""
    name = _get_string(form, "name")

    if not name:
        raise RecipeFormValidationError(
            "レシピ名を入力してください。"
        )

    if len(name) > 100:
        raise RecipeFormValidationError(
            "レシピ名は100文字以内で"
            "入力してください。"
        )

    cooking_time_minutes = (
        _parse_positive_integer(
            value=_get_string(
                form,
                "cooking_time_minutes",
            ),
            field_label="所要時間",
        )
    )

    cuisine_type = _get_string(
        form,
        "cuisine_type",
    )

    if (
        cuisine_type
        not in RECIPE_CUISINE_OPTIONS
    ):
        raise RecipeFormValidationError(
            "料理系統を選択してください。"
        )

    dish_category = _get_string(
        form,
        "dish_category",
    )

    if (
        dish_category
        not in RECIPE_DISH_CATEGORY_OPTIONS
    ):
        raise RecipeFormValidationError(
            "区分を選択してください。"
        )

    yield_type = _get_string(
        form,
        "yield_type",
    )

    if yield_type not in {
        "servings",
        "fixed",
    }:
        raise RecipeFormValidationError(
            "基準量を選択してください。"
        )

    base_servings: int | None = None
    fixed_yield_text: str | None = None

    if yield_type == "servings":
        base_servings = _parse_positive_integer(
            value=_get_string(
                form,
                "base_servings",
            ),
            field_label="基準人数",
        )

    else:
        fixed_yield_text = _get_string(
            form,
            "fixed_yield_text",
        )

        if not fixed_yield_text:
            raise RecipeFormValidationError(
                "固定出来高を入力してください。"
            )

        if len(fixed_yield_text) > 100:
            raise RecipeFormValidationError(
                "固定出来高は100文字以内で"
                "入力してください。"
            )

    ingredients = _parse_ingredients(form)
    steps = _parse_steps(form)

    return ParsedRecipeForm(
        name=name,
        cooking_time_minutes=(
            cooking_time_minutes
        ),
        cuisine_type=cuisine_type,
        dish_category=dish_category,
        yield_type=yield_type,
        base_servings=base_servings,
        fixed_yield_text=fixed_yield_text,
        is_favorite=(
            _get_string(
                form,
                "is_favorite",
            )
            == "true"
        ),
        ingredients=ingredients,
        steps=steps,
    )