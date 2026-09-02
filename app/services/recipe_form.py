from dataclasses import dataclass
from math import isfinite
from typing import Mapping
import re
import unicodedata

from app.models.recipe import Recipe
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


def build_recipe_form_data(
    form: Mapping[str, object] | None = None,
) -> dict:
    """
    登録画面へ渡すフォームデータを作成する。

    入力エラー時も、利用者が入力した文字列を
    可能な限りそのまま保持する。
    """
    source = form or {}

    ingredient_indices = _collect_indices(
        form=source,
        pattern=re.compile(
            r"ingredient_(\d+)_name"
        ),
    )

    if not ingredient_indices:
        ingredient_indices = [0]

    ingredients = [
        {
            "index": new_index,
            "name": _get_string(
                source,
                f"ingredient_{old_index}_name",
            ),
            "ingredient_id": _get_string(
                source,
                f"ingredient_{old_index}_id",
            ),
            "quantity_input": _get_string(
                source,
                (
                    f"ingredient_{old_index}"
                    "_quantity_input"
                ),
            ),
            "unit": _get_string(
                source,
                f"ingredient_{old_index}_unit",
            ),
            "notes": _get_string(
                source,
                f"ingredient_{old_index}_notes",
            ),
            "category_select": _get_string(
                source,
                (
                    f"ingredient_{old_index}"
                    "_category_select"
                ),
            ),
            "category_other": _get_string(
                source,
                (
                    f"ingredient_{old_index}"
                    "_category_other"
                ),
            ),
        }
        for new_index, old_index in enumerate(
            ingredient_indices
        )
    ]

    step_indices = _collect_indices(
        form=source,
        pattern=re.compile(
            r"step_(\d+)_description"
        ),
    )

    if not step_indices:
        step_indices = [0]

    steps = [
        {
            "index": new_index,
            "description": _get_string(
                source,
                (
                    f"step_{old_index}"
                    "_description"
                ),
            ),
        }
        for new_index, old_index in enumerate(
            step_indices
        )
    ]

    yield_type = _get_string(
        source,
        "yield_type",
    )

    if yield_type not in {
        "servings",
        "fixed",
    }:
        yield_type = "servings"

    base_servings = _get_string(
        source,
        "base_servings",
    )

    if not form:
        base_servings = "2"

    return {
        "name": _get_string(
            source,
            "name",
        ),
        "cooking_time_minutes": (
            _get_string(
                source,
                "cooking_time_minutes",
            )
        ),
        "cuisine_type": _get_string(
            source,
            "cuisine_type",
        ),
        "dish_category": _get_string(
            source,
            "dish_category",
        ),
        "yield_type": yield_type,
        "base_servings": base_servings,
        "fixed_yield_text": _get_string(
            source,
            "fixed_yield_text",
        ),
        "is_favorite": (
            _get_string(
                source,
                "is_favorite",
            )
            in {
                "true",
                "on",
                "1",
            }
        ),
        "ingredients": ingredients,
        "steps": steps,
    }


def _quantity_to_form_value(
    quantity: float | None,
    quantity_text: str | None,
) -> str:
    """
    登録済みの数量をフォーム表示用文字列へ変換する。

    数値数量は不要な末尾の.0を表示せず、
    文字数量はそのまま表示する。
    """
    if quantity_text is not None:
        return quantity_text

    if quantity is None:
        return ""

    return format(quantity, "g")


def build_recipe_edit_form_data(
    recipe: Recipe,
) -> dict:
    """
    登録済みレシピを編集フォーム用データへ変換する。
    """
    return {
        "name": recipe.name,
        "cooking_time_minutes": str(
            recipe.cooking_time_minutes
        ),
        "cuisine_type": recipe.cuisine_type,
        "dish_category": (
            recipe.dish_category
        ),
        "yield_type": recipe.yield_type,
        "base_servings": (
            str(recipe.base_servings)
            if recipe.base_servings is not None
            else ""
        ),
        "fixed_yield_text": (
            recipe.fixed_yield_text or ""
        ),
        "is_favorite": recipe.is_favorite,
        "ingredients": [
            {
                "index": index,
                "name": (
                    recipe_ingredient
                    .ingredient.name
                ),
                "ingredient_id": str(
                    recipe_ingredient
                    .ingredient_id
                ),
                "quantity_input": (
                    _quantity_to_form_value(
                        quantity=(
                            recipe_ingredient
                            .quantity
                        ),
                        quantity_text=(
                            recipe_ingredient
                            .quantity_text
                        ),
                    )
                ),
                "unit": (
                    recipe_ingredient.unit
                    or ""
                ),
                "notes": (
                    recipe_ingredient.notes
                    or ""
                ),
                # 既存食材なので新規食材用の
                # カテゴリ入力欄は使用しない。
                "category_select": "",
                "category_other": "",
            }
            for index, recipe_ingredient
            in enumerate(recipe.ingredients)
        ],
        "steps": [
            {
                "index": index,
                "description": step.description,
            }
            for index, step
            in enumerate(recipe.steps)
        ],
    }