"""Tools the agent can call. Thin wrappers over Store: docstrings are what the model reads to decide
WHEN to call each one, so they are written as part of the prompt."""

import json
from functools import lru_cache
from typing import Literal

from langchain_core.tools import tool

from .config import store_now
from .store import Store
from .tickets import create_ticket


@lru_cache(maxsize=1)
def get_store() -> Store:
    return Store()


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


@tool
def search_products(
    query: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    include_unavailable: bool = False,
    on_promotion: bool = False,
) -> str:
    """Search the store catalog. Use it for open questions such as "which acoustic guitars under R$ 1000?",
    "do you have electric ukuleles?", "what do you have from Yamaha?" or "what's on sale?".

    Args:
        query: free-text keywords matched against name, category and description (e.g. "yamaha", "nylon", "elétrico").
        category: one of: Guitarras, Baixos, Baterias e Percussão, Teclados e Pianos, Violões,
            Instrumentos de Sopro (Madeiras), Instrumentos de Sopro (Metais), Cordas Orquestrais, Ukuleles.
        min_price: minimum price in BRL (compared with the price the customer pays, promotions included).
        max_price: maximum price in BRL (same rule).
        include_unavailable: also return out-of-stock, discontinued and coming-soon items. Default False.
        on_promotion: only items with an ACTIVE promotion — use it when the customer asks about promotions,
            discounts or a specific campaign (e.g. Black Friday), to show what is really on sale now.

    Returns the cheapest matches first, with price, active promotion and availability.
    """
    return _json(
        get_store().search_products(
            query, category, min_price, max_price, only_available=not include_unavailable, on_promotion=on_promotion
        )
    )


@tool
def get_product_details(name: str) -> str:
    """Look up a specific product by (partial) name, e.g. "Takamine GD20" or "Yamaha C40".
    Use it for price, availability, specs or description of a product the customer named.

    Returns the best matches with price, active promotion, availability, units in stock, description and specs.
    An empty list means the product is not in the catalog.
    """
    return _json(get_store().find_products(name))


@tool
def get_payment_options(product_ids: list[int]) -> str:
    """Compute the final price and payment conditions (PIX, debit, boleto, credit-card installments)
    for one or more products. ALWAYS use it instead of doing the math yourself.

    Args:
        product_ids: catalog ids (from search_products / get_product_details). Repeat an id to buy more than one unit.
    """
    return _json(get_store().payment_options(product_ids))


@tool
def get_order_status(order_id: int, customer_contact: str) -> str:
    """Look up an order's status, items, tracking code and dates.
    Requires BOTH the order number and the e-mail or phone number registered by the customer —
    ask the customer for whatever is missing before calling. Never guess these values.

    Args:
        order_id: the order number.
        customer_contact: the e-mail or phone registered in the order (used for identity verification).
    """
    return _json(get_store().get_order(order_id, customer_contact, store_now().date()))


@tool
def create_support_ticket(
    kind: Literal["complaint", "exchange_or_return", "warranty", "human_handoff", "other"],
    summary: str,
    customer_contact: str,
    order_id: int | None = None,
) -> str:
    """Open a ticket for the human team and get a protocol number. Use it for complaints, delayed orders,
    exchange/return/warranty requests, or when the customer asks to talk to a person.
    This is the ONLY way to "register" or "forward" something — never claim you did it without calling this.

    Args:
        kind: complaint | exchange_or_return | warranty | human_handoff | other.
        summary: one or two sentences, in Portuguese, describing the case for the team.
        customer_contact: e-mail or phone where the team will reply (ask the customer if you don't have it).
        order_id: related order number, if any.
    """
    return _json(create_ticket(kind, summary, customer_contact, order_id))


TOOLS = [search_products, get_product_details, get_payment_options, get_order_status, create_support_ticket]
