"""Data-layer tests. IDs in the test names refer to docs/test-scenarios.md."""

from datetime import date

import pytest

from emporio_agent.store import AVAILABLE, COMING_SOON, DISCONTINUED, OUT_OF_STOCK, Store, normalize

TODAY = date(2026, 11, 2)


@pytest.fixture(scope="module")
def store():
    return Store()


def test_normalize():
    assert normalize("Violão GD-20 Elétrico") == "violao gd 20 eletrico"


# ---------------------------------------------------------------- catalog


def test_c1_empty_categories_return_nothing(store):
    for category in ["Instrumentos de Sopro (Madeiras)", "Instrumentos de Sopro (Metais)", "Cordas Orquestrais"]:
        assert store.search_products(category=category, only_available=False)["total"] == 0


def test_c2_active_without_stock_is_out_of_stock(store):
    assert store.product_card(96)["availability"] == OUT_OF_STOCK


def test_c3_c4_discontinued_wins_over_stock(store):
    assert store.product_card(136)["availability"] == DISCONTINUED  # has 13 units
    assert store.product_card(113)["availability"] == DISCONTINUED


def test_c5_coming_soon(store):
    assert store.product_card(130)["availability"] == COMING_SOON


def test_c2_c5_unavailable_hidden_from_default_search(store):
    ids = {p["product_id"] for p in store.search_products(limit=100)["products"]}
    assert not ids & {96, 113, 130, 136}
    assert all(p["availability"] == AVAILABLE for p in store.search_products(limit=100)["products"])


@pytest.mark.parametrize("query", ["Takamine GD20", "takamine gd-20", "GD 20", "gd20"])
def test_c6_fuzzy_name_lookup(store, query):
    matches = store.find_products(query)
    assert matches[0]["product_id"] == 95
    assert len(matches) == 1  # exact hit doesn't come with noise


def test_c6_category_plural_and_accents(store):
    a = store.search_products(category="violões", only_available=False)["total"]
    b = store.search_products(category="Violao", only_available=False)["total"]
    assert a == b == 35


def test_c6_guitar_budget_question(store):
    """'Quais opções de violões disponíveis custando até R$1000?'"""
    result = store.search_products(category="Violões", max_price=1000, limit=50)
    assert result["total"] > 0
    assert all(p["availability"] == AVAILABLE for p in result["products"])
    assert all(p.get("promo_price_brl", p["price_brl"]) <= 1000 for p in result["products"])
    assert 96 not in {p["product_id"] for p in result["products"]}  # R$ 799,90 but out of stock


def test_unknown_category_lists_valid_ones(store):
    result = store.search_products(category="sintetizadores modulares")
    assert result["total"] == 0 and "Violões" in result["note"]


# ---------------------------------------------------------------- prices and promotions


def test_p1_active_promotions(store):
    promos = {pid: store.product_card(pid).get("promo_percent") for pid in (90, 94, 121, 127)}
    assert promos == {90: 18, 94: 8, 121: 20, 127: 10}
    assert store.product_card(90)["promo_price_brl"] == round(2399 * 0.82, 2)


def test_p2_p3_inactive_promotions_ignored(store):
    for pid in (93, 96, 99, 102, 113):  # only inactive rows (Black Friday, Semana do Músico...)
        assert "promo_percent" not in store.product_card(pid)


def test_p4_pix_not_cumulative_with_promotion(store):
    promo = store.payment_options([127])  # 10% off
    assert promo["pix_total_brl"] == promo["total_brl"] == 323.1
    regular = store.payment_options([95])  # Takamine GD20, no promo
    assert regular["pix_total_brl"] == round(2199 * 0.95, 2)


def test_p4_mixed_cart(store):
    result = store.payment_options([127, 95])
    assert result["total_brl"] == round(323.1 + 2199, 2)
    assert result["pix_total_brl"] == round(323.1 + 2199 * 0.95, 2)
    assert result["split_payment_allowed"] is True


@pytest.mark.parametrize(
    "product_id, price, expected_max",
    [
        (119, 159.9, 3),  # 3x 53.30 ok; 4x would be < R$ 80
        (83, 429.9, 5),  # 5x 85.98 ok; 6x 71.65 < 80; 7x < 100
        (95, 2199, 12),  # 12x 183.25
        (82, 849, 8),  # 8x 106.12 ok; 9x 94.33 < 100
    ],
)
def test_p5_installment_minimums(store, product_id, price, expected_max):
    result = store.payment_options([product_id])
    assert result["total_brl"] == price
    assert result["credit_card_max_installments"] == expected_max


def test_payment_warns_about_unavailable_items(store):
    assert "warning" in store.payment_options([136])


def test_payment_unknown_product(store):
    assert "error" in store.payment_options([9999])


# ---------------------------------------------------------------- orders


@pytest.mark.parametrize("contact", ["pedro.oliveira@jmail.com", "PEDRO.OLIVEIRA@JMAIL.COM", "(67) 98432-1098", "98432-1098", "67984321098"])
def test_o1_order_with_valid_contact(store, contact):
    order = store.get_order(1, contact, TODAY)
    assert order["status"] == "delivered" and order["customer_first_name"] == "Pedro"


def test_o1_o2_wrong_contact_and_unknown_order_look_the_same(store):
    wrong_contact = store.get_order(1, "lucas.mendes@jmail.com", TODAY)  # a real customer, not the owner
    unknown_order = store.get_order(999, "pedro.oliveira@jmail.com", TODAY)
    assert wrong_contact == unknown_order and "error" in wrong_contact


def test_o1_short_phone_fragment_rejected(store):
    assert "error" in store.get_order(1, "1098", TODAY)


def test_o3_cancelled_order_shows_reason(store):
    order = store.get_order(18, "gustavo.nunes@inlook.com", TODAY)
    assert order["status"] == "cancelled" and "estoque" in order["notes"]


def test_o3_pending_order_has_no_tracking(store):
    order = store.get_order(13, "fernanda.ribeiro@coldmail.com", TODAY)
    assert order["status"] == "pending" and "tracking_code" not in order


def test_o4_overdue_shipment(store):
    order = store.get_order(8, "anacarol.ferreira@coldmail.com", TODAY)
    assert order["status"] == "shipped" and order["tracking_code"] == "BRJL5544332BR"
    assert order["delay_days"] == (TODAY - date(2026, 2, 28)).days


def test_o5_o6_delivered_order_receipt_assumption(store):
    order = store.get_order(7, "leticia.rocha@jmail.com", TODAY)
    assert order["assumed_receipt_date"] == "2026-02-17"
    assert order["days_since_receipt"] > 7  # withdrawal window (7 days) has passed


def test_o7_total_reported_as_recorded(store):
    order = store.get_order(3, "isabela.moreira@jmail.com", TODAY)
    assert order["total_brl"] == 3450  # 2 x 1749 = 3498 in the catalog; we keep the recorded total
    assert order["items"] == [{"name": "Kala KA-ABP-CTG Barítono Cedar", "quantity": 2}]


def test_multi_item_order(store):
    order = store.get_order(15, "aline.monteiro@jmail.com", TODAY)
    assert {i["name"] for i in order["items"]} == {"Yamaha C70 Nylon Natural", "Taylor 214ce Elétrico Aço Natural"}
