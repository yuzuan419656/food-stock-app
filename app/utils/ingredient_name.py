import unicodedata


def normalize_ingredient_name(name: str) -> str:
    """
    食材名を保存・比較しやすい形式へ正規化する。

    処理内容:
    - 全角英数字などを半角へ統一する
    - 前後の空白を除去する
    """
    normalized_name = unicodedata.normalize("NFKC", name)

    return normalized_name.strip()


def normalize_ingredient_name(name: str) -> str:
    """食材名の前後空白や全角・半角表記を正規化する。"""
    return unicodedata.normalize("NFKC", name).strip()


def hiragana_to_katakana(text: str) -> str:
    """文字列内のひらがなをカタカナへ変換する。"""
    converted_chars = []

    for char in text:
        code_point = ord(char)

        # 「ぁ」から「ゖ」までをカタカナへ変換
        if ord("ぁ") <= code_point <= ord("ゖ"):
            converted_chars.append(chr(code_point + 0x60))
        else:
            converted_chars.append(char)

    return "".join(converted_chars)


def katakana_to_hiragana(text: str) -> str:
    """文字列内のカタカナをひらがなへ変換する。"""
    converted_chars = []

    for char in text:
        code_point = ord(char)

        # 「ァ」から「ヶ」までをひらがなへ変換
        if ord("ァ") <= code_point <= ord("ヶ"):
            converted_chars.append(chr(code_point - 0x60))
        else:
            converted_chars.append(char)

    return "".join(converted_chars)


def create_search_keywords(keyword: str) -> list[str]:
    """検索用に元の表記・ひらがな・カタカナの候補を作る。"""
    normalized_keyword = normalize_ingredient_name(keyword)

    if not normalized_keyword:
        return []

    keywords = {
        normalized_keyword,
        hiragana_to_katakana(normalized_keyword),
        katakana_to_hiragana(normalized_keyword),
    }

    return list(keywords)