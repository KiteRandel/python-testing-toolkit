"""Tests for the test-data simulator, plus end-to-end checks that the validators
catch every planted defect (TC-S01 to TC-S06, see docs/test_cases.md)."""

import unittest
from datetime import date

from toolkit.simulator import DEFECT_TYPES, generate_orders, inject_defects, make_customers
from toolkit.validators import run_all_checks

AS_OF = date(2026, 7, 1)


class TestSimulator(unittest.TestCase):
    def test_same_seed_same_data(self):
        """TC-S01: generation is repeatable: the same seed always gives the same records."""
        self.assertEqual(generate_orders(50, seed=1), generate_orders(50, seed=1))
        self.assertNotEqual(generate_orders(50, seed=1), generate_orders(50, seed=2))

    def test_generated_data_is_clean(self):
        """TC-S02: freshly generated data passes every data-quality check."""
        customers = make_customers()
        orders = generate_orders(500, customers=customers)
        report = run_all_checks(orders, known_customers=set(customers), as_of=AS_OF)
        self.assertTrue(report["passed"], [str(i) for i in report["issues"][:5]])

    def test_inject_does_not_touch_original(self):
        """TC-S03: injecting defects works on a copy and leaves the clean set intact."""
        clean = generate_orders(20)
        snapshot = [dict(r) for r in clean]
        inject_defects(clean, {"negative_quantity": 5})
        self.assertEqual(clean, snapshot)

    def test_unknown_defect_rejected(self):
        """TC-S04: asking for an unsupported defect type, or too many defects, raises an error."""
        with self.assertRaises(ValueError):
            inject_defects(generate_orders(5), {"gremlins": 1})
        with self.assertRaises(ValueError):
            inject_defects(generate_orders(5), {"negative_quantity": 6})


class TestValidatorsCatchPlantedDefects(unittest.TestCase):
    """End-to-end: plant a known number of each defect, confirm the validators find exactly that many."""

    EXPECTED_CHECK = {
        "missing_field": "completeness",
        "duplicate_id": "uniqueness",
        "negative_quantity": "range",
        "bad_discount": "range",
        "unknown_region": "valid_code",
        "future_date": "date",
        "orphan_customer": "referential",
    }

    def test_each_defect_type_is_detected(self):
        """TC-S05: each defect type, planted alone, is caught by the right rule with the exact count."""
        customers = make_customers()
        clean = generate_orders(200, customers=customers)
        for defect in DEFECT_TYPES:
            with self.subTest(defect=defect):
                data, manifest = inject_defects(clean, {defect: 4}, as_of=AS_OF)
                report = run_all_checks(data, known_customers=set(customers), as_of=AS_OF)
                self.assertEqual(report["by_check"], {self.EXPECTED_CHECK[defect]: 4})
                self.assertEqual(len(manifest), 4)

    def test_mixed_defects_all_detected(self):
        """TC-S06: with every defect type mixed together, no planted defect is missed."""
        customers = make_customers()
        clean = generate_orders(300, customers=customers)
        plan = {d: 3 for d in DEFECT_TYPES}
        data, manifest = inject_defects(clean, plan, as_of=AS_OF)
        report = run_all_checks(data, known_customers=set(customers), as_of=AS_OF)
        self.assertEqual(report["issue_count"], len(manifest))
        flagged_ids = {i.order_id for i in report["issues"]}
        self.assertTrue({m["order_id"] for m in manifest} <= flagged_ids)


if __name__ == "__main__":
    unittest.main()
