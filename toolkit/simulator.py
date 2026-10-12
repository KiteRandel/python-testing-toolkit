"""Test-data simulator.

Generates realistic, repeatable order records so tests never depend on a live
source system. Pass the same seed and you get the same data every time.

`inject_defects` takes a clean data set and plants known problems
(missing fields, duplicates, bad ranges, bad codes, future dates, orphaned
customers) so the validators can be tested against defects whose count and
type are known in advance.
"""

from __future__ import annotations

import copy
import random
from datetime import date, timedelta

from toolkit.records import VALID_REGIONS, VALID_STATUSES

DEFECT_TYPES = (
    "missing_field",
    "duplicate_id",
    "negative_quantity",
    "bad_discount",
    "unknown_region",
    "future_date",
    "orphan_customer",
)


def make_customers(count: int = 25) -> list[str]:
    return [f"CUST-{i:04d}" for i in range(1, count + 1)]


def generate_orders(
    count: int = 100,
    seed: int = 42,
    customers: list[str] | None = None,
    start: date = date(2026, 1, 1),
    end: date = date(2026, 6, 30),
) -> list[dict]:
    """Generate `count` clean, valid order records."""
    rng = random.Random(seed)
    customers = customers or make_customers()
    regions = sorted(VALID_REGIONS)
    statuses = sorted(VALID_STATUSES)
    span = (end - start).days

    orders = []
    for i in range(1, count + 1):
        orders.append(
            {
                "order_id": f"ORD-{i:05d}",
                "customer_id": rng.choice(customers),
                "order_date": (start + timedelta(days=rng.randint(0, span))).isoformat(),
                "region": rng.choice(regions),
                "quantity": rng.randint(1, 20),
                "unit_price": round(rng.uniform(2.0, 250.0), 2),
                "discount_pct": rng.choice([0, 0, 0, 5, 10, 15, 20]),
                "status": rng.choice(statuses),
            }
        )
    return orders


def inject_defects(
    records: list[dict],
    defects: dict[str, int],
    seed: int = 7,
    as_of: date = date(2026, 7, 1),
) -> tuple[list[dict], list[dict]]:
    """Return (defective_records, manifest).

    `defects` maps a defect type (see DEFECT_TYPES) to how many to plant.
    Each defect is applied to a different record so expected counts are exact.
    The manifest lists every planted defect for comparison against what the
    validators report.
    """
    unknown = set(defects) - set(DEFECT_TYPES)
    if unknown:
        raise ValueError(f"unknown defect types: {sorted(unknown)}")
    total = sum(defects.values())
    if total > len(records):
        raise ValueError("more defects requested than records available")

    rng = random.Random(seed)
    data = copy.deepcopy(records)
    targets = rng.sample(range(len(data)), total)
    manifest = []
    duplicates = []

    cursor = 0
    for defect, n in defects.items():
        for _ in range(n):
            idx = targets[cursor]
            cursor += 1
            rec = data[idx]
            if defect == "missing_field":
                rec["customer_id"] = ""
            elif defect == "duplicate_id":
                dup = dict(rec)
                dup["quantity"] = rec["quantity"] + 1
                duplicates.append(dup)
            elif defect == "negative_quantity":
                rec["quantity"] = -abs(rec["quantity"])
            elif defect == "bad_discount":
                rec["discount_pct"] = 150
            elif defect == "unknown_region":
                rec["region"] = "ATLANTIS"
            elif defect == "future_date":
                rec["order_date"] = (as_of + timedelta(days=30)).isoformat()
            elif defect == "orphan_customer":
                rec["customer_id"] = "CUST-9999"
            manifest.append({"defect": defect, "order_id": rec["order_id"]})

    data.extend(duplicates)
    return data, manifest
