# Python Software Testing Toolkit

An automated testing and data-validation toolkit written in plain Python (no
third-party packages). It does three things:

1. **Unit tests** check that record-processing functions return accurate,
   consistent data: totals, discounts, rounding, regional summaries, and
   source-vs-target reconciliation.
2. **A test-data simulator** generates repeatable sample records, so testing
   never depends on a live source system. It can also plant known defects.
3. **Data-quality validators** check completeness, uniqueness, valid ranges,
   valid codes, dates, and referential integrity (orphaned records).
   They run in the test suite or from the command line.

Every test has an ID that maps to a documented test case with an expected
result. See [`docs/test_cases.md`](docs/test_cases.md).

## Project layout

```
toolkit/
  records.py      functions under test: normalize, line totals, summaries, reconciliation
  validators.py   data-quality rules and a combined validation report
  simulator.py    seeded test-data generator + defect injector
tests/
  test_records.py     TC-R01 to TC-R14b
  test_validators.py  TC-V01 to TC-V09
  test_simulator.py   TC-S01 to TC-S06 (incl. end-to-end defect detection)
docs/
  test_cases.md   test case catalogue, expected results, edge-case decisions
validate.py       command-line validation runner
```

## Run it

Requires Python 3.10+.

```bash
python -m unittest discover -s tests -t . -v   # run all 30 tests

python validate.py                    # validate 200 clean simulated records -> PASS
python validate.py --with-defects     # plant 2 of each defect type -> FAIL, every one reported
python validate.py --csv orders.csv   # validate your own CSV export
```

Sample output with defects planted:

```
Validated: 200 simulated records + 14 planted defects
Records checked: 202
Result: FAIL (14 issues)
  completeness  2
  date          2
  range         4
  referential   2
  uniqueness    2
  valid_code    2
  - [completeness] ORD-00039: missing customer_id
  - [uniqueness] ORD-00102: duplicate order_id
  ...
```

## How the defect testing works

`inject_defects()` takes a clean data set and plants an exact number of known
problems, for example 4 duplicate IDs or 4 orphaned customer references. It
returns the defective data plus a manifest of everything it planted. The
end-to-end tests then check that the validators report **exactly** what was
planted: no defect missed and no false positives.

The tests also run automatically on every push through GitHub Actions
(`.github/workflows/tests.yml`).
