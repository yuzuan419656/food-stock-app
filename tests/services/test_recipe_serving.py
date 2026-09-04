import pytest

from app.services.recipe_serving import (
    calculate_scaled_quantity,
    format_recipe_quantity,
)


def test_calculate_scaled_quantity_same_servings():
    result = calculate_scaled_quantity(
        base_quantity=2,
        base_servings=2,
        target_servings=2,
    )

    assert result == 2


def test_calculate_scaled_quantity_increases():
    result = calculate_scaled_quantity(
        base_quantity=2,
        base_servings=2,
        target_servings=3,
    )

    assert result == 3


def test_calculate_scaled_quantity_decreases():
    result = calculate_scaled_quantity(
        base_quantity=2,
        base_servings=4,
        target_servings=1,
    )

    assert result == 0.5


def test_calculate_scaled_quantity_keeps_fraction():
    result = calculate_scaled_quantity(
        base_quantity=1,
        base_servings=2,
        target_servings=3,
    )

    assert result == 1.5


@pytest.mark.parametrize(
    (
        "base_quantity",
        "base_servings",
        "target_servings",
    ),
    [
        (1, 0, 2),
        (1, 2, 0),
        (1, 2, -1),
        (-1, 2, 2),
    ],
)
def test_calculate_scaled_quantity_rejects_invalid_values(
    base_quantity,
    base_servings,
    target_servings,
):
    with pytest.raises(ValueError):
        calculate_scaled_quantity(
            base_quantity=base_quantity,
            base_servings=base_servings,
            target_servings=target_servings,
        )


@pytest.mark.parametrize(
    ("quantity", "expected"),
    [
        (1.0, "1"),
        (2.0, "2"),
        (1.5, "1.5"),
        (0.75, "0.75"),
    ],
)
def test_format_recipe_quantity(
    quantity,
    expected,
):
    assert (
        format_recipe_quantity(quantity)
        == expected
    )