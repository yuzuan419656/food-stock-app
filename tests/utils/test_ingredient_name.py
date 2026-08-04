from app.utils.ingredient_name import normalize_ingredient_name


def test_normalize_ingredient_name_removes_surrounding_spaces():
    """食材名の前後にある空白が削除されることを確認する。"""
    result = normalize_ingredient_name("  トマト  ")

    assert result == "トマト"


def test_normalize_ingredient_name_converts_full_width_alphabet():
    """全角英字が半角英字へ変換されることを確認する。"""
    result = normalize_ingredient_name("Ｔｏｍａｔｏ")

    assert result == "Tomato"


def test_normalize_ingredient_name_converts_full_width_numbers():
    """全角数字が半角数字へ変換されることを確認する。"""
    result = normalize_ingredient_name("牛乳１")

    assert result == "牛乳1"


def test_normalize_ingredient_name_keeps_normal_name():
    """変換不要な食材名がそのまま返されることを確認する。"""
    result = normalize_ingredient_name("じゃがいも")

    assert result == "じゃがいも"