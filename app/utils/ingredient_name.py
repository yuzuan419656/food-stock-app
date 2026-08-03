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