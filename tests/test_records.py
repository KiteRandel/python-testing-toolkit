"""Unit tests for toolkit.records (test cases TC-R01 to TC-R14, see docs/test_cases.md)."""

import unittest
from datetime import date
from decimal import Decimal

from toolkit.records import (
    line_total,
    normalize_record,
    parse_date,
    reconcile_totals,
    summarize_by_region,
)


def order(**overrides):
    base = {
        "order_id": "ORD-00001",
        "customer_id": "CUST-0001",
        "order_date": "2026-04-01",
        "region": "NORTHEAST",
        "quantity": 3,
        "unit_price": 19.99,
        "discount_pct": 0,
        "status": "SHIPPED",
    }
    base.update(overrides)
    return base


class TestNormalize(unittest.TestCase):
    def test_trims_and_uppercases_codes(self):
        """TC-R01: whitespace and lower-case codes are cleaned."""
        rec = normalize_record(order(region="  northeast ", status="shipped ", order_id=" ORD-1 "))
        self.assertEqual(rec["region"], "NORTHEAST")
        self.assertEqual(rec["status"], "SHIPPED")
        self.assertEqual(rec["order_id"], "ORD-1")

    def test_does_not_mutate_input(self):
        """TC-R02: the original record is left unchanged."""
        original = order(region="west")
        normalize_record(original)
        self.assertEqual(original["region"], "west")

    def test_string_numbers_are_converted(self):
        """TC-R03: numeric fields given as strings are converted to proper types."""
        rec = normalize_record(order(quantity="4", unit_price="10.5", discount_pct="5"))
        self.assertEqual(rec["quantity"], 4)
        self.assertEqual(rec["unit_price"], Decimal("10.50"))
        self.assertEqual(rec["discount_pct"], Decimal("5"))
        self.assertEqual(rec["order_date"], date(2026, 4, 1))


class TestParseDate(unittest.TestCase):
    def test_bad_dates_raise(self):
        """TC-R04: invalid or missing dates raise ValueError instead of passing silently."""
        for bad in ("2026-02-30", "04/01/2026", "", None, "   "):
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    parse_date(bad)


class TestLineTotal(unittest.TestCase):
    def test_basic_total(self):
        """TC-R05: 3 x 19.99 = 59.97."""
        self.assertEqual(line_total(order()), Decimal("59.97"))

    def test_discount_applied(self):
        """TC-R06: 10% off 3 x 19.99 = 53.97 (53.973 rounded half-up)."""
        self.assertEqual(line_total(order(discount_pct=10)), Decimal("53.97"))

    def test_half_cent_rounds_up(self):
        """TC-R07: edge case: exactly half a cent rounds up, not to even."""
        # 1 x 0.25 with 50% off = 0.125 -> 0.13
        self.assertEqual(line_total(order(quantity=1, unit_price=0.25, discount_pct=50)), Decimal("0.13"))

    def test_float_precision(self):
        """TC-R08: edge case: no floating-point drift (0.1 x 3 must be exactly 0.30)."""
        self.assertEqual(line_total(order(quantity=3, unit_price=0.1)), Decimal("0.30"))

    def test_cancelled_is_zero(self):
        """TC-R09: cancelled orders contribute no revenue."""
        self.assertEqual(line_total(order(status="cancelled")), Decimal("0.00"))

    def test_boundary_discounts(self):
        """TC-R10: edge case: 0% and 100% discounts are valid boundaries."""
        self.assertEqual(line_total(order(discount_pct=0)), Decimal("59.97"))
        self.assertEqual(line_total(order(discount_pct=100)), Decimal("0.00"))

    def test_invalid_values_raise(self):
        """TC-R11: negative quantity/price and out-of-range discounts are rejected."""
        for bad in (dict(quantity=-1), dict(unit_price=-5), dict(discount_pct=101), dict(discount_pct=-1)):
            with self.subTest(**bad):
                with self.assertRaises(ValueError):
                    line_total(order(**bad))


class TestSummaries(unittest.TestCase):
    def test_summarize_by_region(self):
        """TC-R12: region totals equal the sum of their line totals; cancelled orders count but add $0."""
        records = [
            order(order_id="A", region="WEST", quantity=1, unit_price=10),
            order(order_id="B", region="west", quantity=2, unit_price=5),
            order(order_id="C", region="MIDWEST", quantity=1, unit_price=99, status="CANCELLED"),
        ]
        summary = summarize_by_region(records)
        self.assertEqual(list(summary), ["MIDWEST", "WEST"])
        self.assertEqual(summary["WEST"], {"orders": 2, "revenue": Decimal("20.00")})
        self.assertEqual(summary["MIDWEST"], {"orders": 1, "revenue": Decimal("0.00")})

    def test_empty_input(self):
        """TC-R13: edge case: empty input gives an empty summary, not an error."""
        self.assertEqual(summarize_by_region([]), {})


class TestReconcile(unittest.TestCase):
    def test_reconcile_finds_every_discrepancy(self):
        """TC-R14: reconciliation reports missing, unexpected, and mismatched records."""
        source = [order(order_id="A"), order(order_id="B"), order(order_id="C")]
        target = [order(order_id="A"), order(order_id="B", quantity=4), order(order_id="D")]
        result = reconcile_totals(source, target)
        self.assertEqual(result["missing_in_target"], ["C"])
        self.assertEqual(result["unexpected_in_target"], ["D"])
        self.assertEqual([m["order_id"] for m in result["value_mismatches"]], ["B"])
        self.assertFalse(result["totals_match"])

    def test_reconcile_identical_sets(self):
        """TC-R14b: identical data sets reconcile cleanly."""
        data = [order(order_id="A"), order(order_id="B")]
        result = reconcile_totals(data, [dict(r) for r in data])
        self.assertEqual(result["missing_in_target"], [])
        self.assertEqual(result["unexpected_in_target"], [])
        self.assertEqual(result["value_mismatches"], [])
        self.assertTrue(result["totals_match"])


if __name__ == "__main__":
    unittest.main()
