# Test Cases

Every automated test is tagged with an ID (e.g. `TC-R05`) in its docstring, so a
failure in the test output can be traced straight back to this table.

**Legend:** *Type* = Functional, Edge case, Negative (bad input must be rejected),
or End-to-end.

## Record processing (`tests/test_records.py`)

| ID | Type | Scenario | Input | Expected result |
|---|---|---|---|---|
| TC-R01 | Functional | Codes and IDs are cleaned | `region="  northeast "`, `status="shipped "` | `NORTHEAST`, `SHIPPED`, IDs trimmed |
| TC-R02 | Functional | Input is not modified | Any record | Original dict unchanged after normalizing |
| TC-R03 | Functional | String numbers converted | `quantity="4"`, `unit_price="10.5"` | `4`, `Decimal("10.50")`, date parsed |
| TC-R04 | Negative | Invalid / missing dates | `2026-02-30`, `04/01/2026`, `""`, `None` | `ValueError` raised |
| TC-R05 | Functional | Basic line total | 3 x 19.99 | `59.97` |
| TC-R06 | Functional | Discount applied | 3 x 19.99, 10% off | `53.97` |
| TC-R07 | Edge case | Half-cent rounding | 1 x 0.25, 50% off (= 0.125) | `0.13` (half-up, not banker's rounding) |
| TC-R08 | Edge case | Floating-point drift | 3 x 0.10 | Exactly `0.30` |
| TC-R09 | Functional | Cancelled orders | `status="cancelled"` | `0.00` revenue |
| TC-R10 | Edge case | Discount boundaries | 0% and 100% | `59.97` and `0.00` |
| TC-R11 | Negative | Out-of-range values | qty -1, price -5, discount 101 / -1 | `ValueError` raised |
| TC-R12 | Functional | Region summary | 2 WEST orders + 1 cancelled MIDWEST | WEST: 2 orders / $20.00; MIDWEST: 1 order / $0.00 |
| TC-R13 | Edge case | Empty input | `[]` | `{}` (no error) |
| TC-R14 | Functional | Reconciliation finds discrepancies | Source A,B,C vs. target A,B(changed),D | Missing `C`, unexpected `D`, mismatch `B`, totals differ |
| TC-R14b | Functional | Reconciliation of identical sets | Same records both sides | No discrepancies, totals match |

## Data-quality validators (`tests/test_validators.py`)

| ID | Rule | Scenario | Expected result |
|---|---|---|---|
| TC-V01 | All | Valid record | 0 issues, report `passed = True` |
| TC-V02 | Completeness | Field is `""`, `None`, or whitespace | 1 issue per missing field |
| TC-V03 | Completeness | `order_id` itself missing | Issue reported against `<unknown>` |
| TC-V04 | Uniqueness | Same ID 3 times (one with extra spaces) | 2 duplicate issues |
| TC-V05 | Range | qty 0, qty -3, price -1, discount 150, qty `"three"` | All 5 records flagged |
| TC-V06 | Valid code | Region `atlantis`, status `LOST`, region `west` | First two flagged; lower-case `west` accepted |
| TC-V07 | Date | Month 13, future date, date equal to as-of | First two flagged; as-of date allowed |
| TC-V08 | Referential | Customer not in master list | Orphan flagged |
| TC-V09 | Report | Mixed problems | Counts grouped correctly by rule |

## Simulator and end-to-end detection (`tests/test_simulator.py`)

| ID | Type | Scenario | Expected result |
|---|---|---|---|
| TC-S01 | Functional | Same seed twice / different seeds | Identical data / different data |
| TC-S02 | Functional | 500 generated records | Pass every data-quality check |
| TC-S03 | Functional | Inject defects | Original clean data set unchanged |
| TC-S04 | Negative | Unknown defect type, or more defects than records | `ValueError` raised |
| TC-S05 | End-to-end | Plant 4 of each defect type, one type at a time | Exactly 4 issues, from the correct rule |
| TC-S06 | End-to-end | Plant 3 of every defect type at once | Issue count = defects planted; every planted record flagged |

## Known edge cases and decisions

- **Rounding:** money is rounded half-up to the cent with `Decimal`, matching
  accounting practice. Floats are never used for totals.
- **Case and whitespace:** `" west "` and `"WEST"` are treated as the same code.
  Validators normalize before comparing, so they don't report false positives.
- **Cancelled orders** count toward order volume but add no revenue.
- **The as-of date** is passed in rather than read from the clock, so the
  future-date check gives the same result whenever the tests run.
- **Blank fields** are reported once, by the completeness rule. Other rules skip
  them so the same problem isn't counted twice.
