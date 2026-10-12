"""Run the data-quality checks from the command line.

    python validate.py                     # validate a clean simulated data set
    python validate.py --with-defects      # plant known defects and show they are caught
    python validate.py --csv orders.csv    # validate your own CSV file
"""

import argparse
import csv
import sys
from datetime import date

from toolkit.simulator import DEFECT_TYPES, generate_orders, inject_defects, make_customers
from toolkit.validators import run_all_checks


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate order records.")
    parser.add_argument("--csv", help="path to a CSV file of order records")
    parser.add_argument("--count", type=int, default=200, help="records to simulate (default 200)")
    parser.add_argument("--with-defects", action="store_true", help="plant 2 of each defect type")
    parser.add_argument("--as-of", default="2026-07-01", help="date used for the future-date check")
    args = parser.parse_args(argv)
    as_of = date.fromisoformat(args.as_of)

    customers = None
    if args.csv:
        records = load_csv(args.csv)
        source = args.csv
    else:
        customers = make_customers()
        records = generate_orders(args.count, customers=customers)
        source = f"{args.count} simulated records"
        if args.with_defects:
            records, manifest = inject_defects(records, {d: 2 for d in DEFECT_TYPES}, as_of=as_of)
            source += f" + {len(manifest)} planted defects"

    report = run_all_checks(records, known_customers=set(customers) if customers else None, as_of=as_of)

    print(f"Validated: {source}")
    print(f"Records checked: {report['records_checked']}")
    print(f"Result: {'PASS' if report['passed'] else 'FAIL'} ({report['issue_count']} issues)")
    for check, n in sorted(report["by_check"].items()):
        print(f"  {check:<13} {n}")
    for issue in report["issues"][:25]:
        print(f"  - {issue}")
    if report["issue_count"] > 25:
        print(f"  ... and {report['issue_count'] - 25} more")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
