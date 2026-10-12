"""Unit tests for toolkit.validators (test cases TC-V01 to TC-V09, see docs/test_cases.md)."""

import unittest
from datetime import date

from toolkit.validators import (
    check_completeness,
    check_dates,
    check_ranges,
    check_referential_integrity,
    check_uniqueness,
    check_valid_codes,
    run_all_checks,
)

AS_OF = date(2026, 7, 1)


def order(**overrides):
    base = {
        "order_id": "ORD-00001",
        "customer_id": "CUST-0001",
        "order_date": "2026-04-01",
        "region": "WEST",
        "quantity": 2,
        "unit_price": 10.0,
        "discount_pct": 0,
        "status": "SHIPPED",
    }
    base.update(overrides)
    return base


class TestValidators(unittest.TestCase):
    def test_clean_record_passes_everything(self):
        """TC-V01: a valid record produces zero issues."""
        report = run_all_checks([order()], known_customers={"CUST-0001"}, as_of=AS_OF)
        self.assertTrue(report["passed"])
        self.assertEqual(report["issue_count"], 0)

    def test_completeness(self):
        """TC-V02: missing, None, and blank-string fields are all flagged."""
        records = [order(customer_id=""), order(order_id="ORD-2", status=None), order(order_id="ORD-3", region="   ")]
        issues = check_completeness(records)
        self.assertEqual(len(issues), 3)
        self.assertTrue(all(i.check == "completeness" for i in issues))

    def test_missing_order_id_is_labelled_unknown(self):
        """TC-V03: edge case: a record with no id is still reported, as <unknown>."""
        issues = check_completeness([order(order_id=None)])
        self.assertEqual(issues[0].order_id, "<unknown>")

    def test_uniqueness(self):
        """TC-V04: duplicate ids are flagged once per extra copy (ids are trimmed first)."""
        records = [order(), order(order_id=" ORD-00001 "), order(order_id="ORD-00001"), order(order_id="ORD-2")]
        issues = check_uniqueness(records)
        self.assertEqual(len(issues), 2)

    def test_ranges(self):
        """TC-V05: zero/negative quantity, negative price, bad discount, and non-numbers are flagged."""
        records = [
            order(order_id="A", quantity=0),
            order(order_id="B", quantity=-3),
            order(order_id="C", unit_price=-1),
            order(order_id="D", discount_pct=150),
            order(order_id="E", quantity="three"),
        ]
        flagged = sorted({i.order_id for i in check_ranges(records)})
        self.assertEqual(flagged, ["A", "B", "C", "D", "E"])

    def test_valid_codes(self):
        """TC-V06: unknown region/status codes are flagged; case differences are not."""
        records = [order(order_id="A", region="atlantis"), order(order_id="B", status="LOST"), order(order_id="C", region="west")]
        flagged = sorted(i.order_id for i in check_valid_codes(records))
        self.assertEqual(flagged, ["A", "B"])

    def test_dates(self):
        """TC-V07: unparseable and future dates are flagged; the as-of date itself is allowed."""
        records = [
            order(order_id="A", order_date="2026-13-01"),
            order(order_id="B", order_date="2026-08-15"),
            order(order_id="C", order_date="2026-07-01"),
        ]
        flagged = sorted(i.order_id for i in check_dates(records, as_of=AS_OF))
        self.assertEqual(flagged, ["A", "B"])

    def test_referential_integrity(self):
        """TC-V08: orders pointing at customers not in the master list are orphans."""
        records = [order(order_id="A"), order(order_id="B", customer_id="CUST-9999")]
        issues = check_referential_integrity(records, {"CUST-0001"})
        self.assertEqual([i.order_id for i in issues], ["B"])

    def test_report_counts_by_check(self):
        """TC-V09: the summary report groups issue counts by rule."""
        records = [order(order_id="A", quantity=-1), order(order_id="A", region="MARS")]
        report = run_all_checks(records, as_of=AS_OF)
        self.assertFalse(report["passed"])
        self.assertEqual(report["by_check"], {"uniqueness": 1, "range": 1, "valid_code": 1})


if __name__ == "__main__":
    unittest.main()
