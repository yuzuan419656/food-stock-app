from datetime import date
from datetime import timedelta

from urllib.parse import parse_qs, urlparse


from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.ingredient import (
    create_ingredient,
    get_ingredient_by_id,
)
from app.crud.inventory import (
    get_inventory_expiration_date,
    get_inventory_quantity,
)


from app.routers.ingredients import (
    build_expiration_display_by_ingredient_id,
)


def test_update_expiration_date_route(
    client: TestClient,
    db_session: Session,
):
    """一覧画面から消費期限を更新できる。"""
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=2,
        expiration_date=date(2026, 8, 10),
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date"
        ),
        data={
            "expiration_date": "2026-08-15",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert get_inventory_expiration_date(
        saved_ingredient
    ) == date(2026, 8, 15)


def test_clear_expiration_date_route(
    client: TestClient,
    db_session: Session,
):
    """空文字を送ると消費期限を未設定へ戻せる。"""
    ingredient = create_ingredient(
        db=db_session,
        name="ヨーグルト",
        category="乳製品",
        default_unit="個",
        quantity=3,
        expiration_date=date(2026, 8, 12),
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date"
        ),
        data={
            "expiration_date": "",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert (
        get_inventory_expiration_date(
            saved_ingredient
        )
        is None
    )


def test_update_expiration_date_preserves_quantity(
    client: TestClient,
    db_session: Session,
):
    """一覧から期限を変更しても数量は変わらない。"""
    ingredient = create_ingredient(
        db=db_session,
        name="卵",
        category="食品",
        default_unit="個",
        quantity=6,
        expiration_date=date(2026, 8, 8),
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date"
        ),
        data={
            "expiration_date": "2026-08-20",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert get_inventory_quantity(
        saved_ingredient
    ) == 6


def test_invalid_expiration_date_is_not_saved(
    client: TestClient,
    db_session: Session,
):
    """不正な日付では消費期限を更新しない。"""
    original_expiration_date = date(
        2026,
        8,
        10,
    )

    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=original_expiration_date,
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date"
        ),
        data={
            "expiration_date": "invalid-date",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    saved_ingredient = get_ingredient_by_id(
        db=db_session,
        ingredient_id=ingredient.id,
    )

    assert saved_ingredient is not None
    assert get_inventory_expiration_date(
        saved_ingredient
    ) == original_expiration_date

    location = response.headers["location"]

    assert "expiration_error=" in location


def test_missing_ingredient_expiration_route(
    client: TestClient,
):
    """存在しない食材IDでも500エラーにならない。"""
    response = client.post(
        "/ingredients/9999/expiration-date",
        data={
            "expiration_date": "2026-08-15",
            "sort": "category",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"



def test_expiration_update_preserves_list_conditions(
    client: TestClient,
    db_session: Session,
):
    """更新後も検索・カテゴリ・並び順を維持する。"""
    ingredient = create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=2,
        expiration_date=None,
    )

    response = client.post(
        (
            f"/ingredients/{ingredient.id}"
            "/expiration-date"
        ),
        data={
            "expiration_date": "2026-08-15",
            "keyword": "牛",
            "category_filters": "乳製品",
            "sort": "name",
            "out_of_stock_first": "true",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    location = response.headers["location"]
    parsed_url = urlparse(location)
    query_params = parse_qs(parsed_url.query)

    assert query_params["keyword"] == ["牛"]
    assert query_params["category_filters"] == [
        "乳製品"
    ]
    assert query_params["sort"] == ["name"]
    assert query_params[
        "out_of_stock_first"
    ] == ["true"]
    assert parsed_url.fragment == (
        f"ingredient-{ingredient.id}"
    )

def test_expiration_display_unset(
    db_session: Session,
):
    """期限未設定はunsetになる。"""
    ingredient = create_ingredient(
        db=db_session,
        name="塩",
        category="調味料",
        default_unit="袋",
        quantity=1,
        expiration_date=None,
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [ingredient]
        )
    )

    expiration_info = result[ingredient.id]

    assert expiration_info["date"] == "未設定"
    assert expiration_info["status"] == "unset"
    assert expiration_info["label"] == ""


def test_expiration_display_expired(
    db_session: Session,
):
    """昨日の期限は期限切れになる。"""
    yesterday = date.today() - timedelta(days=1)

    ingredient = create_ingredient(
        db=db_session,
        name="豆腐",
        category="大豆製品",
        default_unit="丁",
        quantity=1,
        expiration_date=yesterday,
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [ingredient]
        )
    )

    expiration_info = result[ingredient.id]

    assert expiration_info["status"] == "expired"
    assert expiration_info["label"] == "期限切れ"
    assert expiration_info["date"] == (
        yesterday.isoformat()
    )


def test_expiration_display_today(
    db_session: Session,
):
    """今日の期限は期限間近になる。"""
    today = date.today()

    ingredient = create_ingredient(
        db=db_session,
        name="パン",
        category="食品",
        default_unit="袋",
        quantity=1,
        expiration_date=today,
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [ingredient]
        )
    )

    expiration_info = result[ingredient.id]

    assert (
        expiration_info["status"]
        == "expiring-soon"
    )
    assert expiration_info["label"] == "期限間近"


def test_expiration_display_three_days_later(
    db_session: Session,
):
    """3日後の期限は期限間近になる。"""
    expiration_date = (
        date.today() + timedelta(days=3)
    )

    ingredient = create_ingredient(
        db=db_session,
        name="ハム",
        category="加工食品",
        default_unit="袋",
        quantity=1,
        expiration_date=expiration_date,
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [ingredient]
        )
    )

    expiration_info = result[ingredient.id]

    assert (
        expiration_info["status"]
        == "expiring-soon"
    )
    assert expiration_info["label"] == "期限間近"


def test_expiration_display_four_days_later(
    db_session: Session,
):
    """4日後の期限は通常表示になる。"""
    expiration_date = (
        date.today() + timedelta(days=4)
    )

    ingredient = create_ingredient(
        db=db_session,
        name="チーズ",
        category="乳製品",
        default_unit="個",
        quantity=1,
        expiration_date=expiration_date,
    )

    result = (
        build_expiration_display_by_ingredient_id(
            [ingredient]
        )
    )

    expiration_info = result[ingredient.id]

    assert expiration_info["status"] == "normal"
    assert expiration_info["label"] == ""


def test_ingredient_list_contains_expiration_edit_form(
    client: TestClient,
    db_session: Session,
):
    """一覧画面に期限変更フォームが表示される。"""
    create_ingredient(
        db=db_session,
        name="牛乳",
        category="乳製品",
        default_unit="本",
        quantity=1,
        expiration_date=date(2026, 8, 15),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "消費期限" in response.text
    assert "変更" in response.text
    assert 'name="expiration_date"' in response.text
    assert 'value="2026-08-15"' in response.text
    assert "保存" in response.text
    assert "取消" in response.text


def test_unset_expiration_input_is_empty(
    client: TestClient,
    db_session: Session,
):
    """期限未設定の場合、日付入力欄は空になる。"""
    create_ingredient(
        db=db_session,
        name="塩",
        category="調味料",
        default_unit="袋",
        quantity=1,
        expiration_date=None,
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "未設定" in response.text
    assert (
        'name="expiration_date"\n'
        '                                    value=""'
        in response.text
        or 'value=""' in response.text
    )