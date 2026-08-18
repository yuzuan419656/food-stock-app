from app.utils.list_url import (
    build_list_redirect_url,
)


def test_build_list_redirect_url_keeps_expiration_asc():
    result = build_list_redirect_url(
        sort="expiration_asc",
    )

    assert result == "/?sort=expiration_asc"


def test_build_list_redirect_url_keeps_expiration_desc():
    result = build_list_redirect_url(
        sort="expiration_desc",
    )

    assert result == "/?sort=expiration_desc"


def test_build_list_redirect_url_keeps_all_conditions():
    result = build_list_redirect_url(
        keyword="たまご",
        category_filters=[
            "卵",
            "乳製品",
        ],
        sort="expiration_asc",
        out_of_stock_first=True,
    )

    assert "keyword=" in result
    assert "category_filters=" in result
    assert "sort=expiration_asc" in result
    assert "out_of_stock_first=true" in result