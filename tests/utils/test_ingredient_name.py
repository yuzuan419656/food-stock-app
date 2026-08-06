from app.utils.ingredient_name import create_search_keywords


def test_create_search_keywords_from_hiragana():
    keywords = create_search_keywords("ねぎ")

    assert "ねぎ" in keywords
    assert "ネギ" in keywords


def test_create_search_keywords_from_katakana():
    keywords = create_search_keywords("ネギ")

    assert "ねぎ" in keywords
    assert "ネギ" in keywords


def test_create_search_keywords_from_half_width_katakana():
    keywords = create_search_keywords("ﾈｷﾞ")

    assert "ねぎ" in keywords
    assert "ネギ" in keywords


def test_create_search_keywords_with_mixed_characters():
    keywords = create_search_keywords("長ねぎ")

    assert "長ねぎ" in keywords
    assert "長ネギ" in keywords


def test_create_search_keywords_removes_surrounding_spaces():
    keywords = create_search_keywords(" ねぎ ")

    assert "ねぎ" in keywords
    assert "ネギ" in keywords


def test_create_search_keywords_returns_empty_for_blank_keyword():
    assert create_search_keywords("   ") == []