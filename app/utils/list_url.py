from urllib.parse import urlencode


def build_list_redirect_url(
    keyword: str | None = None,
    category_filters: list[str] | None = None,
    sort: str = "category",
    out_of_stock_first: bool = False,
) -> str:
    """一覧画面の表示条件を維持したURLを作成する。"""
    query_params: list[tuple[str, str]] = []

    if keyword:
        query_params.append(
            ("keyword", keyword)
        )

    if category_filters:
        for category in category_filters:
            query_params.append(
                ("category_filters", category)
            )

    allowed_sorts = [
        "id",
        "name",
        "category",
        "expiration_asc",
        "expiration_desc",
    ]   

    if sort in allowed_sorts:
        query_params.append(
            ("sort", sort)
        )

    if out_of_stock_first:
        query_params.append(
            ("out_of_stock_first", "true")
        )

    if not query_params:
        return "/"

    return f"/?{urlencode(query_params)}"