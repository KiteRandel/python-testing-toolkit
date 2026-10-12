"""Data-quality checks.

Each check takes a list of records and returns a list of Issue objects.
`run_all_checks` runs every check and returns a combined report, so the same
rules can be used in unit tests and in a standalone validation run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from toolkit.records import VALID_REGIONS, VALID_STATUSES, parse_date

REQUIRED_FIELDS = (
    "order_id",
    "customer_id",
    "order_date",
    "region",
    "quantity",
    "unit_price",
    "status",
)


@dataclass(frozen=True)
class Issue:
    check: str      # which rule failed, e.g. "completeness"
    order_id: str   # record it applies to ("<unknown>" if the id itself is missing)
    detail: str     # human-readable explanation

    def __str__(self) -> str:
        return f"[{self.check}] {self.order_id}: {self.detail}"


def _oid(record: dict) -> str:
    value = record.get("order_id")
    return value.strip() if isinstance(value, str) and value.strip() else "<unknown>"


def check_completeness(records: list[dict]) -> list[Issue]:
    """Every required field must be present and non-blank."""
    issues = []
    for rec in records:
        for field in REQUIRED_FIELDS:
            value = rec.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                issues.append(Issue("completeness", _oid(rec), f"missing {field}"))
    return issues


def check_uniqueness(records: list[dict]) -> list[Issue]:
    """order_id must be unique across the data set."""
    seen: set[str] = set()
    issues = []
    for rec in records:
        oid = _oid(rec)
        if oid == "<unknown>":
            continue  # reported by completeness
        if oid in seen:
            issues.append(Issue("uniqueness", oid, "duplicate order_id"))
        seen.add(oid)
    return issues


def check_ranges(records: list[dict]) -> list[Issue]:
    """Numeric fields must be within business limits."""
    issues = []
    for rec in records:
        oid = _oid(rec)
        try:
            qty = int(rec.get("quantity"))
            if qty <= 0:
                issues.append(Issue("range", oid, f"quantity must be > 0 (got {qty})"))
        except (TypeError, ValueError):
            issues.append(Issue("range", oid, f"quantity is not a number: {rec.get('quantity')!r}"))
        try:
            price = float(rec.get("unit_price"))
            if price < 0:
                issues.append(Issue("range", oid, f"unit_price cannot be negative (got {price})"))
        except (TypeError, ValueError):
            issues.append(Issue("range", oid, f"unit_price is not a number: {rec.get('unit_price')!r}"))
        disc = rec.get("discount_pct", 0) or 0
        try:
            if not 0 <= float(disc) <= 100:
                issues.append(Issue("range", oid, f"discount_pct out of 0-100 (got {disc})"))
        except (TypeError, ValueError):
            issues.append(Issue("range", oid, f"discount_pct is not a number: {disc!r}"))
    return issues


def check_valid_codes(records: list[dict]) -> list[Issue]:
    """region and status must come from the allowed code lists."""
    issues = []
    for rec in records:
        oid = _oid(rec)
        region = str(rec.get("region") or "").strip().upper()
        status = str(rec.get("status") or "").strip().upper()
        if region and region not in VALID_REGIONS:
            issues.append(Issue("valid_code", oid, f"unknown region {region!r}"))
        if status and status not in VALID_STATUSES:
            issues.append(Issue("valid_code", oid, f"unknown status {status!r}"))
    return issues


def check_dates(records: list[dict], as_of: date | None = None) -> list[Issue]:
    """order_date must parse and must not be in the future."""
    as_of = as_of or date.today()
    issues = []
    for rec in records:
        if rec.get("order_date") in (None, ""):
            continue  # reported by completeness
        try:
            d = parse_date(rec["order_date"])
        except ValueError:
            issues.append(Issue("date", _oid(rec), f"unparseable order_date {rec['order_date']!r}"))
            continue
        if d > as_of:
            issues.append(Issue("date", _oid(rec), f"order_date {d} is in the future"))
    return issues


def check_referential_integrity(records: list[dict], known_customers: set[str]) -> list[Issue]:
    """Every customer_id must exist in the customer master list (no orphans)."""
    issues = []
    for rec in records:
        cid = str(rec.get("customer_id") or "").strip()
        if cid and cid not in known_customers:
            issues.append(Issue("referential", _oid(rec), f"customer_id {cid} not in customer list"))
    return issues


def run_all_checks(
    records: list[dict],
    known_customers: set[str] | None = None,
    as_of: date | None = None,
) -> dict:
    """Run every check and return {"passed": bool, "issue_count": int, "issues": [...], "by_check": {...}}."""
    issues = (
        check_completeness(records)
        + check_uniqueness(records)
        + check_ranges(records)
        + check_valid_codes(records)
        + check_dates(records, as_of=as_of)
    )
    if known_customers is not None:
        issues += check_referential_integrity(records, known_customers)

    by_check: dict[str, int] = {}
    for issue in issues:
        by_check[issue.check] = by_check.get(issue.check, 0) + 1
    return {
        "records_checked": len(records),
        "passed": not issues,
        "issue_count": len(issues),
        "by_check": by_check,
        "issues": issues,
    }
