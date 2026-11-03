"""Store data layer: loads the raw CSVs once and answers the questions the agent's tools need.

Pure pandas, no LLM — every business rule that can be deterministic lives here, so it can be
unit-tested and the model never has to do arithmetic or remember data quirks.
"""

import json
import math
import re
import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd

from .config import RAW_DATA_DIR

_FILE_PREFIX = "desafio_tecnico_ai_eng - "

# Availability is derived in ONE place. Status wins over stock: a discontinued product with
# units left (#136) is not for sale, and a "coming_soon" one (#130) can't be bought yet.
AVAILABLE, OUT_OF_STOCK, DISCONTINUED, COMING_SOON = "available", "out_of_stock", "discontinued", "coming_soon"

PIX_DISCOUNT = 0.05
# Policy 3.1 is ambiguous for 1-3x ("no minimum, except below R$ 50"); we read it as a R$ 50 minimum.
INSTALLMENT_MINIMUMS = [(3, 50.0), (6, 80.0), (12, 100.0)]  # (max installments in tier, minimum installment)
SPLIT_PAYMENT_THRESHOLD = 2000.0

ORDER_STATUS_PT = {
    "pending": "aguardando confirmação do pagamento",
    "confirmed": "pagamento confirmado, em separação",
    "shipped": "enviado",
    "delivered": "entregue",
    "cancelled": "cancelado",
}


def normalize(text: str) -> str:
    """Lowercase, strip accents and punctuation: 'Violão GD-20' -> 'violao gd 20'."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _stem(token: str) -> str:
    """Crude Portuguese singular so 'violoes' matches 'violao' and 'guitarras' matches 'guitarra'."""
    if token.endswith("oes") or token.endswith("aes"):
        return token[:-3] + "ao"
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _tokens(text: str) -> list[str]:
    return [_stem(t) for t in normalize(text).split()]


def _digits(text: str) -> str:
    return re.sub(r"\D", "", str(text))


class Store:
    def __init__(self, data_dir: Path = RAW_DATA_DIR):
        read = lambda name: pd.read_csv(data_dir / f"{_FILE_PREFIX}{name}.csv")
        self.categories = read("categories")
        self.customers = read("customers")
        self.orders = read("orders")
        self.order_items = read("order_items")
        self.promotions = read("promotions")
        self.products = self._build_products(read("products"))

    # ---------------------------------------------------------------- products

    def _build_products(self, products: pd.DataFrame) -> pd.DataFrame:
        df = products.merge(
            self.categories[["category_id", "name"]].rename(columns={"name": "category"}), on="category_id", how="left"
        )
        df["specs"] = df["specs"].apply(lambda s: json.loads(s) if isinstance(s, str) and s.strip() else {})

        # Only active promotions count (#93/#96/#99 have several inactive rows). If a product ever had
        # two active ones, the bigger discount wins — policy says promotions are not cumulative.
        active = (
            self.promotions[self.promotions["is_active"] == 1]
            .sort_values("discount_percent", ascending=False)
            .drop_duplicates("product_id")[["product_id", "discount_percent", "description"]]
            .rename(columns={"discount_percent": "promo_percent", "description": "promo_name"})
        )
        df = df.merge(active, on="product_id", how="left")
        df["promo_percent"] = df["promo_percent"].fillna(0).astype(int)
        df["final_price"] = (df["price_brl"] * (1 - df["promo_percent"] / 100)).round(2)

        def availability(row) -> str:
            if row["status"] == "discontinued":
                return DISCONTINUED
            if row["status"] == "coming_soon":
                return COMING_SOON
            return AVAILABLE if row["stock_quantity"] > 0 else OUT_OF_STOCK

        df["availability"] = df.apply(availability, axis=1)
        df["_search"] = (df["name"] + " " + df["category"] + " " + df["description"]).apply(
            lambda t: " ".join(_tokens(t))
        )
        df["_name_compact"] = df["name"].apply(lambda t: normalize(t).replace(" ", ""))
        return df.set_index("product_id", drop=False)

    def category_names(self) -> list[str]:
        return self.categories["name"].tolist()

    def categories_for_sale(self) -> list[str]:
        """Categories with at least one available product — what the store can actually sell right now."""
        on_sale = self.products[self.products["availability"] == AVAILABLE]["category"]
        return [c for c in self.category_names() if c in set(on_sale)]

    def product_card(self, product_id: int, with_details: bool = False) -> dict:
        p = self.products.loc[product_id]
        card = {
            "product_id": int(p["product_id"]),
            "name": p["name"],
            "category": p["category"],
            "availability": p["availability"],
            "price_brl": float(p["price_brl"]),
        }
        if p["promo_percent"]:
            card.update(
                promo_name=p["promo_name"], promo_percent=int(p["promo_percent"]), promo_price_brl=float(p["final_price"])
            )
        if with_details:
            card.update(description=p["description"], specs=p["specs"], units_in_stock=int(p["stock_quantity"]))
        return card

    def search_products(
        self,
        query: str | None = None,
        category: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        only_available: bool = True,
        limit: int = 10,
    ) -> dict:
        """Filter the catalog. Prices are compared against the final (promotional) price the customer pays."""
        df = self.products
        if category:
            wanted = set(_tokens(category))
            matches = [c for c in self.category_names() if wanted & set(_tokens(c))]
            if not matches:
                return {"total": 0, "products": [], "note": f"Categoria desconhecida. Categorias: {self.category_names()}"}
            df = df[df["category"].isin(matches)]
        if query:
            for token in _tokens(query):
                df = df[df["_search"].str.contains(rf"\b{re.escape(token)}", regex=True)]
        if min_price is not None:
            df = df[df["final_price"] >= min_price]
        if max_price is not None:
            df = df[df["final_price"] <= max_price]
        if only_available:
            df = df[df["availability"] == AVAILABLE]
        df = df.sort_values("final_price")
        return {"total": len(df), "products": [self.product_card(pid) for pid in df.index[:limit]]}

    def find_products(self, name: str, limit: int = 3) -> list[dict]:
        """Fuzzy lookup by name ('takamine gd20', 'GD-20', 'yamaha c 40'). Best matches first, any availability."""
        q_tokens = _tokens(name)
        q_compact = normalize(name).replace(" ", "")
        if not q_tokens:
            return []
        scored = []
        for pid, row in self.products.iterrows():
            name_tokens = set(_tokens(row["name"]))
            hits = sum(1 for t in q_tokens if t in name_tokens or t in row["_name_compact"])
            score = hits / len(q_tokens)
            if q_compact and q_compact in row["_name_compact"]:
                score += 1  # whole query appears contiguously in the name ("gd20" vs "gd 20")
            if score >= 0.5:
                scored.append((score, pid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        best = scored[0][0] if scored else 0
        # Keep only matches close to the best one, so an exact hit doesn't come with noise.
        return [self.product_card(pid, with_details=True) for s, pid in scored[:limit] if s >= best - 0.34]

    # ---------------------------------------------------------------- payments

    def payment_options(self, product_ids: list[int]) -> dict:
        """Cart total and payment conditions per policy 3 / 6.2. Repeat an id for quantity > 1."""
        unknown = [pid for pid in product_ids if pid not in self.products.index]
        if unknown or not product_ids:
            return {"error": f"Produto(s) não encontrado(s): {unknown or 'nenhum informado'}"}

        items = [self.products.loc[pid] for pid in product_ids]
        total = round(sum(float(p["final_price"]) for p in items), 2)
        # PIX 5% applies only to items NOT already on promotion (policy 6.2: not cumulative).
        pix_total = round(
            sum(float(p["final_price"]) * (1 if p["promo_percent"] else 1 - PIX_DISCOUNT) for p in items), 2
        )

        max_installments = 1
        for n in range(1, 13):
            minimum = next(m for limit, m in INSTALLMENT_MINIMUMS if n <= limit)
            if total / n >= minimum:
                max_installments = n
        installment_value = math.floor(total / max_installments * 100) / 100

        unavailable = [p["name"] for p in items if p["availability"] != AVAILABLE]
        result = {
            "items": [
                {"name": p["name"], "price_brl": float(p["final_price"]), "on_promotion": bool(p["promo_percent"])}
                for p in items
            ],
            "total_brl": total,
            "pix_total_brl": pix_total,
            "pix_note": "PIX dá 5% de desconto só nos itens que não estão em promoção (descontos não acumulam).",
            "debit_or_boleto_total_brl": total,
            "credit_card_max_installments": max_installments,
            "credit_card_installment_brl": installment_value,
            "credit_card_note": "Sem juros. Parcela mínima: R$ 50 (até 3x), R$ 80 (4x a 6x), R$ 100 (7x a 12x).",
            "split_payment_allowed": total > SPLIT_PAYMENT_THRESHOLD,
        }
        if unavailable:
            result["warning"] = f"Itens que não podem ser vendidos agora: {unavailable}"
        return result

    # ---------------------------------------------------------------- orders

    def get_order(self, order_id: int, contact: str, today: date) -> dict:
        """Order details, only if `contact` (e-mail or phone) matches the order's customer (LGPD).

        Unknown order and wrong contact return the SAME error, so the tool can't be used to
        discover which order numbers exist.
        """
        denied = {"error": "Não encontrei um pedido com esse número para esse e-mail/telefone."}
        order = self.orders[self.orders["order_id"] == order_id]
        if order.empty:
            return denied
        order = order.iloc[0]
        customer = self.customers[self.customers["customer_id"] == order["customer_id"]].iloc[0]

        contact = str(contact).strip()
        by_email = "@" in contact and contact.lower() == customer["email"].lower()
        digits = _digits(contact)
        by_phone = len(digits) >= 8 and _digits(customer["phone"]).endswith(digits[-9:] if len(digits) >= 9 else digits)
        if not (by_email or by_phone):
            return denied

        items = self.order_items[self.order_items["order_id"] == order_id]
        result = {
            "order_id": int(order_id),
            "customer_first_name": customer["name"].split()[0],
            "order_date": order["order_date"],
            "status": order["status"],
            "status_description": ORDER_STATUS_PT.get(order["status"], order["status"]),
            # Reported as recorded: some totals don't match item prices (#3, #20) — we don't recompute.
            "total_brl": float(order["total_brl"]),
            "payment_method": order["payment_method"],
            "items": [
                {"name": self.products.loc[int(i["product_id"])]["name"], "quantity": int(i["quantity"])}
                for _, i in items.iterrows()
                if int(i["product_id"]) in self.products.index
            ],
        }
        for field in ("tracking_code", "estimated_delivery", "notes"):
            if pd.notna(order[field]) and str(order[field]).strip():
                result[field] = str(order[field])

        if "estimated_delivery" in result:
            eta = date.fromisoformat(result["estimated_delivery"])
            if order["status"] == "shipped" and eta < today:
                result["delay_days"] = (today - eta).days
            if order["status"] == "delivered":
                # No real receipt date in the data: we assume it equals the estimated delivery.
                result["assumed_receipt_date"] = result["estimated_delivery"]
                result["days_since_receipt"] = (today - eta).days
        return result
