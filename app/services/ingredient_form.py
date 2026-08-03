from app.constants.ingredient_options import OTHER_OPTION


def resolve_selected_option(
    selected_value: str,
    other_value: str | None,
    allowed_options: list[str],
    field_label: str,
) -> tuple[str | None, str | None]:
    """
    プルダウンと「その他」の入力値から、
    データベースへ保存する値を決定する。
    """
    selected_value = selected_value.strip()
    other_value = (other_value or "").strip()

    if not selected_value:
        return None, f"{field_label}を選択してください。"

    if selected_value == OTHER_OPTION:
        if not other_value:
            return None, f"{field_label}を入力してください。"

        return other_value, None

    if selected_value not in allowed_options:
        return None, (
            f"{field_label}の選択内容が正しくありません。"
        )

    return selected_value, None


def get_option_form_values(
    current_value: str | None,
    allowed_options: list[str],
) -> tuple[str, str]:
    """
    登録済みの値から、
    プルダウンと「その他」入力欄の値を決定する。
    """
    normalized_value = (current_value or "").strip()

    if not normalized_value:
        return "", ""

    if normalized_value in allowed_options:
        return normalized_value, ""

    return OTHER_OPTION, normalized_value


def build_new_form_data(
    name: str,
    category_select: str,
    category_other: str | None,
    default_unit_select: str,
    default_unit_other: str | None,
    quantity: float,
) -> dict:
    """新規登録・編集画面へ渡すフォームデータを作成する。"""
    return {
        "name": name,
        "category_select": category_select,
        "category_other": category_other or "",
        "default_unit_select": default_unit_select,
        "default_unit_other": default_unit_other or "",
        "quantity": quantity,
    }


def build_duplicate_form_data(
    name: str,
    category: str,
    quantity: float,
    default_unit: str,
) -> dict:
    """重複確認画面へ渡すフォームデータを作成する。"""
    return {
        "name": name,
        "category": category,
        "quantity": quantity,
        "default_unit": default_unit,
    }