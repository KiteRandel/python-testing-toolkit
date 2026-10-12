"""Record-processing functions under test.

These are the "production" functions the test suite verifies. They work on
order records shaped like:

    {
        "order_id": "ORD-00001",
        "customer_id": "CUST-0001",
        "order_date": "2026-04-01",
        "region": "NORTHEAST",
        "quantity": 3,
        "unit_price": 19.99,
        "discount_pct": 10.0,
        "status": "SHIPPED",
    }
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

VALID_STATUSES = {"PENDING", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}
VALID_REGIONS = {"NORTHEAST", "SOUTHEAST", "MIDWEST", "SOUTHWEST", "WEST"}

_CENTS = Decimal("0.01")


def _to_money(value) -> Decimal:
    """Convert a number to a Decimal rounded to cents (half-up, like accounting)."""
    return Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def parse_date(value) -> date:
    """Parse an ISO date string (YYYY-MM-DD). Raises ValueError on bad input."""
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"order_date is missing or not a string: {value!r}")
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


def normalize_record(record: dict) -> dict:
    """Return a cleaned copy of a record.

    - trims whitespace and upper-cases code fields (region, status)
    - converts quantity to int and price/discount to Decimal
    - parses order_date into a date
    The input record is never modified.
    """
    clean = dict(record)
    for key in ("order_id", "customer_id"):
        if isinstance(clean.get(key), str):
            clean[key] = clean[key].strip()
    for key in ("region", "status"):
        if isinstance(clean.get(key), str):
            clean[key] = clean[key].strip().upper()
    clean["quantity"] = int(clean["quantity"])
    clean["unit_price"] = _to_money(clean["unit_price"])
    clean["discount_pct"] = Decimal(str(clean.get("discount_pct") or 0))
    clean["order_date"] = parse_date(clean["order_date"])
    return clean


def line_total(record: dict) -> Decimal:
    """Quantity x unit price, less discount, rounded to cents.

    Cancelled orders are worth 0. Raises ValueError for negative quantities,
    negative prices, or discounts outside 0-100.
    """
    rec = normalize_record(record)
    if rec["quantity"] < 0:
        raise ValueError("quantity cannot be negative")
    if rec["unit_price"] < 0:
        raise ValueError("unit_price cannot be negative")
    if not (Decimal(0) <= rec["discount_pct"] <= Decimal(100)):
        raise ValueError("discount_pct must be between 0 and 100")
    if rec["status"] == "CANCELLED":
        return Decimal("0.00")
    gross = rec["unit_price"] * rec["quantity"]
    net = gross * (Decimal(100) - rec["discount_pct"]) / Decimal(100)
    return _to_money(net)


def summarize_by_region(records: list[dict]) -> dict[str, dict]:
    """Aggregate order count and revenue per region.

    Returns {region: {"orders": int, "revenue": Decimal}}, regions sorted A-Z.
    Cancelled orders count toward orders but add no revenue.
    """
    summary: dict[str, dict] = {}
    for record in records:
        rec = normalize_record(record)
        bucket = summary.setdefault(rec["region"], {"orders": 0, "revenue": Decimal("0.00")})
        bucket["orders"] += 1
        bucket["revenue"] += line_total(rec)
    return dict(sorted(summary.items()))


def reconcile_totals(source: list[dict], target: list[dict]) -> dict:
    """Compare two record sets (e.g. a source system vs. a loaded copy).

    Matches on order_id and reports:
      - missing_in_target: ids in source but not target
      - unexpected_in_target: ids in target but not source
      - value_mismatches: ids whose line totals differ
      - source_total / target_total and whether they match
    """
    src = {r["order_id"].strip(): r for r in source}
    tgt = {r["order_id"].strip(): r for r in target}

    mismatches = []
    for oid in sorted(src.keys() & tgt.keys()):
        a, b = line_total(src[oid]), line_total(tgt[oid])
        if a != b:
            mismatches.append({"order_id": oid, "source": a, "target": b})

    source_total = sum((line_total(r) for r in source), Decimal("0.00"))
    target_total = sum((line_total(r) for r in target), Decimal("0.00"))
    return {
        "missing_in_target": sorted(src.keys() - tgt.keys()),
        "unexpected_in_target": sorted(tgt.keys() - src.keys()),
        "value_mismatches": mismatches,
        "source_total": source_total,
        "target_total": target_total,
        "totals_match": source_total == target_total,
    }
