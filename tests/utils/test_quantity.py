import pytest

from app.utils.quantity import is_valid_quantity_step


@pytest.mark.parametrize(
    "quantity",
    [
        0,
        0.5,
        1,
        1.5,
        10,
        10.5,
    ],
)
def test_is_valid_quantity_step_returns_true(
    quantity: float,
):
    """0.5刻みの数量が有効と判定されることを確認する。"""
    assert is_valid_quantity_step(quantity) is True


@pytest.mark.parametrize(
    "quantity",
    [
        0.1,
        0.25,
        0.6,
        1.2,
        10.1,
    ],
)
def test_is_valid_quantity_step_returns_false(
    quantity: float,
):
    """0.5刻みではない数量が無効と判定されることを確認する。"""
    assert is_valid_quantity_step(quantity) is False