from datetime import date

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
    normalized_value = (
        current_value or ""
    ).strip()

    if not normalized_value:
        return "", ""

    if normalized_value in allowed_options:
        return normalized_value, ""

    return OTHER_OPTION, normalized_value


def parse_optional_date(
    value: str | None,
    field_label: str = "消費期限",
) -> tuple[date | None, str | None]:
    """
    フォームから送信された任意の日付文字列を
    dateへ変換する。

    未入力の場合はNoneを返す。
    """
    normalized_value = (value or "").strip()

    if not normalized_value:
        return None, None

    try:
        parsed_date = date.fromisoformat(
            normalized_value
        )

    except ValueError:
        return (
            None,
            f"{field_label}の日付形式が正しくありません。",
        )

    return parsed_date, None


def parse_required_date(
    value: str | None,
    field_label: str,
) -> tuple[date | None, str | None]:
    """
    フォームから送信された必須の日付文字列を
    dateへ変換する。
    """
    normalized_value = (value or "").strip()

    if not normalized_value:
        return (
            None,
            f"{field_label}を入力してください。",
        )

    try:
        parsed_date = date.fromisoformat(
            normalized_value
        )

    except ValueError:
        return (
            None,
            f"{field_label}の日付形式が正しくありません。",
        )

    return parsed_date, None


def date_to_form_value(
    value: date | None,
) -> str:
    """
    dateをHTMLの日付入力欄で使用できる
    YYYY-MM-DD形式へ変換する。
    """
    if value is None:
        return ""

    return value.isoformat()


def build_new_form_data(
    name: str,
    category_select: str,
    category_other: str | None,
    default_unit_select: str,
    default_unit_other: str | None,
    quantity: float,
    purchase_date: str | None = None,
    expiration_date: str | None = None,
) -> dict:
    """新規登録・編集画面へ渡すフォームデータを作成する。"""
    return {
        "name": name,
        "category_select": category_select,
        "category_other": category_other or "",
        "default_unit_select": default_unit_select,
        "default_unit_other": default_unit_other or "",
        "quantity": quantity,
        "purchase_date": purchase_date or "",
        "expiration_date": expiration_date or "",
    }


def build_duplicate_form_data(
    name: str,
    category: str,
    quantity: float,
    default_unit: str,
    purchase_date: date,
    expiration_date: date | None,
) -> dict:
    """重複確認画面へ渡すフォームデータを作成する。"""
    return {
        "name": name,
        "category": category,
        "quantity": quantity,
        "default_unit": default_unit,
        "purchase_date": date_to_form_value(
            purchase_date
        ),
        "expiration_date": date_to_form_value(
            expiration_date
        ),
    }


def build_duplicate_context(
    existing_ingredient,
    existing_quantity: float,
    existing_purchase_date: date,
    existing_expiration_date: date | None,
    name: str,
    category: str,
    quantity: float,
    default_unit: str,
    purchase_date: date,
    expiration_date: date | None,
    error_message: str | None = None,
) -> dict:
    """重複確認画面へ渡すcontextを作成する。"""
    return {
        "existing_ingredient": existing_ingredient,
        "existing_quantity": existing_quantity,
        "existing_purchase_date": (
            existing_purchase_date
        ),
        "existing_expiration_date": (
            existing_expiration_date
        ),
        "form_data": build_duplicate_form_data(
            name=name,
            category=category,
            quantity=quantity,
            default_unit=default_unit,
            purchase_date=purchase_date,
            expiration_date=expiration_date,
        ),
        "can_add_quantity": (
            existing_ingredient.default_unit
            == default_unit
        ),
        "error_message": error_message,
    }