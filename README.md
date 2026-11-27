# Meridian Data Profiling Pipeline

## Objective
Build a data profiling pipeline that ingests structured data sources, asseses the quality, and generates a report.


## Dataset Details

**Overview**: The datasets of interest (csv & json) contain synthetic capital-markets trade data for a fictional company (Meridian Capital Markets).
They are intentionally blemished with realistic data quality defects. Each dataset contains the exact same data & errors but with different schemas.


**Shapes:** Each dataset has a shape of $1000 \times 9$. For json, that's after flattening its nested fields.

**Data Constraints:**
The following uses CSV field names; equivalent JSON fields have the same requirements. All constraints below are implemented. 
1. `trade_id` must be a non-null string, not empty or whitespace-only, matching `TRD-` followed by exactly 10 hexadecimal characters. (Validity)
2. `instrument_id` must be a non-null string containing exactly four uppercase letters. (Validity)
3. `instrument_type` must be non-null and one of `Equity`, `Bond`, or `ETF`. (Validity)
4. `trade_date` must be non-null, represent an actual calendar date, use `YYYY-MM-DD` to pass the format check, and fall within January 1, 2025–June 30, 2026, inclusive, under the assumed historical reporting window. (Timeliness)
5. `buyer` must be a non-null string that is neither empty nor whitespace-only. (Completeness)
6. `seller` must be a non-null string that is neither empty nor whitespace-only. (Completeness)
7. `quantity` must be present and have an integer value greater than zero. (Validity)
8. `price` must be present and have a finite real numeric value greater than zero. (Validity)
9. `trade_status` must be non-null and one of `EXECUTED`, `SETTLED`, `CANCELLED`, `PENDING`, or `REJECTED`. (Validity)
10. Each trade record must contain all nine fields defined in the schema. (Completeness)
11. Each populated `instrument_id` must exist in the instrument master. (Validity)
12. Each trade's `instrument_type` must equal the master type for its `instrument_id`. (Accuracy)
13. `buyer` and `seller` must differ within a trade under the rule for this synthetic dataset. (Consistency)
14. Each `trade_id` must occur in no more than one trade row. (Consistency)
15. No two trade rows may have identical values across all nine fields. (Consistency)
16. Each instrument-master `instrument_id` must be populated and occur in exactly one master row. (Consistency)
17. The CSV and JSON exports must contain the same number of trade records. (Consistency)
18. Corresponding CSV and JSON records must agree on all nine values after schema mapping and equivalent missing-value and numeric representations are accounted for; correspondence uses the documented matching row order. (Consistency)

## Quality Assesment

- **Completeness:** Required data is present.
- **Validity:** Data conforms to specified formats, types, ranges, and rules.
- **Consistency:** Related values agree within and across datasets.
- **Accuracy:** Data correctly represents the real-world facts it describes.
- **Timeliness:** Data is available and sufficiently current when needed.

`profile()` calculates descriptive statistics;

`score()` evaluates constraints;

`assess()` combines both.

Each dimension scores passed checks divided by evaluated checks. The overall score is their weighted average on a 0–100 scale, with equal weights by default. Missing evidence reduces coverage and marks a score as partial.

```text
Dimension score = passed checks / evaluated checks
Overall score = 100 × Σ(weight × dimension score) / Σ(weights of assessed dimensions)
```

## System Design

```text
meridian-data-platform/
├── main.py                 # Configure constraints and run assessments
├── src/
│   ├── schemas.py          # Define sources, rules, profiles, and scores
│   ├── loaders.py          # Load CSV/JSON, flatten JSON, and join data
│   ├── profilers.py        # Calculate statistics and score quality dimensions
│   ├── pipeline.py         # Connect loading to profiling and assessment
│   └── reporting.py        # Format results 
├── data/                   # Supplied trade exports and instrument master
├── pyproject.toml          # Python version and dependencies
└── uv.lock                 # Locked dependency versions
```

## Usage

Requires Python 3.14+ and `uv`. From the project directory:

1. Place the supplied files at these paths:

   ```text
   data/meridian_trades_small.csv
   data/meridian_trades_small.json
   data/data_info/meridian_reference_data.csv
   ```

2. Install dependencies and run the pipeline:

   ```sh
   uv sync
   uv run main.py
   ```

3. Save the printed report to a text file:

   ```sh
   uv run main.py > report.txt
   ```

The report includes column statistics, quality scores, coverage, and failed or unassessed checks. Missing or unreadable files stop the run with an error message.

## Results

Both exports contain the same 1,000 trades and produce the same results:

| Dimension | Score |
| --- | --- |
| Completeness | 98.66% |
| Consistency | 95.21% |
| Accuracy | 100.00% of assessable instrument-type comparisons |
| Timeliness | 100.00% within the assumed historical window |
| Validity | 97.68% |

**Overall: 98.31/100 (partial), with 98.08% coverage.**

- 88 records lack an instrument ID; 11 lack a buyer and 22 lack a seller.
- 94 records share trade IDs, leaving 952 distinct IDs; there are no identical duplicate rows.
- 96 dates use non-ISO formats, and 23 prices are negative.
- All 912 populated instrument IDs match the master's instrument types. Missing IDs leave 88 accuracy checks unassessed; missing counterparties prevent 33 buyer/seller comparisons.
- Master-key quality and CSV/JSON agreement each score 100/100 under their configured checks.

Findings can overlap within a record. The two exports represent the same trades, so their issue counts should not be added together.

## Business Summary

The exports agree, but they share defects that can disrupt reconciliation: missing instrument and counterparty details, repeated trade IDs, inconsistent date formats, and negative prices.

Prioritize recovering missing identifiers and counterparties, investigating repeated trade IDs and negative prices, and standardizing date representations. Repeated IDs do not prove that trades are duplicates; verify the underlying records before removing anything.

The high overall score does not establish readiness for operational use. Resolve the identified issues and rerun the pipeline before relying on the records for downstream processing.
