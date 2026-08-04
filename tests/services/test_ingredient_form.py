from app.constants.ingredient_options import OTHER_OPTION
from app.services.ingredient_form import (
    build_duplicate_form_data,
    build_new_form_data,
    get_option_form_values,
    resolve_selected_option,
)


def test_resolve_selected_option_returns_selected_value():
    """通常の選択肢がそのまま返されることを確認する。"""
    value, error = resolve_selected_option(
        selected_value="野菜",
        other_value=None,
        allowed_options=["野菜", "肉類"],
        field_label="カテゴリ",
    )

    assert value == "野菜"
    assert error is None


def test_resolve_selected_option_returns_other_value():
    """「その他」を選んだ場合に自由入力値が返されることを確認する。"""
    value, error = resolve_selected_option(
        selected_value=OTHER_OPTION,
        other_value="果物",
        allowed_options=["野菜", "肉類"],
        field_label="カテゴリ",
    )

    assert value == "果物"
    assert error is None


def test_resolve_selected_option_returns_error_when_not_selected():
    """選択されていない場合にエラーになることを確認する。"""
    value, error = resolve_selected_option(
        selected_value="",
        other_value=None,
        allowed_options=["野菜", "肉類"],
        field_label="カテゴリ",
    )

    assert value is None
    assert error == "カテゴリを選択してください。"


def test_resolve_selected_option_returns_error_when_other_is_empty():
    """「その他」の自由入力が空の場合にエラーになることを確認する。"""
    value, error = resolve_selected_option(
        selected_value=OTHER_OPTION,
        other_value="",
        allowed_options=["野菜", "肉類"],
        field_label="カテゴリ",
    )

    assert value is None
    assert error == "カテゴリを入力してください。"


def test_resolve_selected_option_rejects_unknown_option():
    """許可されていない選択肢が拒否されることを確認する。"""
    value, error = resolve_selected_option(
        selected_value="不正な値",
        other_value=None,
        allowed_options=["野菜", "肉類"],
        field_label="カテゴリ",
    )

    assert value is None
    assert error == "カテゴリの選択内容が正しくありません。"


def test_get_option_form_values_returns_registered_option():
    """登録済みの選択肢がプルダウン値として返されることを確認する。"""
    selected_value, other_value = get_option_form_values(
        current_value="野菜",
        allowed_options=["野菜", "肉類"],
    )

    assert selected_value == "野菜"
    assert other_value == ""


def test_get_option_form_values_returns_other_option():
    """一覧にない値が「その他」の入力値として返されることを確認する。"""
    selected_value, other_value = get_option_form_values(
        current_value="果物",
        allowed_options=["野菜", "肉類"],
    )

    assert selected_value == OTHER_OPTION
    assert other_value == "果物"


def test_build_new_form_data():
    """新規登録画面用のフォームデータが作成されることを確認する。"""
    result = build_new_form_data(
        name="トマト",
        category_select="野菜",
        category_other=None,
        default_unit_select="個",
        default_unit_other=None,
        quantity=3,
    )

    assert result == {
        "name": "トマト",
        "category_select": "野菜",
        "category_other": "",
        "default_unit_select": "個",
        "default_unit_other": "",
        "quantity": 3,
    }


def test_build_duplicate_form_data():
    """重複確認画面用のフォームデータが作成されることを確認する。"""
    result = build_duplicate_form_data(
        name="トマト",
        category="野菜",
        quantity=3,
        default_unit="個",
    )

    assert result == {
        "name": "トマト",
        "category": "野菜",
        "quantity": 3,
        "default_unit": "個",
    }