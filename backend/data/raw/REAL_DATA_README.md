# Real Data Ingestion Pipeline

This pipeline ingests external Nigerian construction project data (CSV/JSON), validates it against the expected schema, normalises it, and merges it with the existing synthetic dataset for ML training.

## Quick Start

```python
from data.ingestion import load_external_data, merge_with_synthetic, save_training_data

external = load_external_data("data/external/sample_projects.csv")

merged = merge_with_synthetic(external, "data/raw/construction_projects.csv")

save_training_data(merged, "data/processed/training_data.csv")
```

## Input File Format

Drop your CSV or JSON files into `data/external/`. Each record must contain these columns (all optional except the pipeline will fill missing values with sensible defaults):

### Numeric Features
| Column | Description | Expected Range |
|---|---|---|
| `budget_allocated` | Approved project budget (NGN) | 100,000 - 10,000,000,000 |
| `budget_spent` | Amount spent to date (NGN) | 0 - 10,000,000,000 |
| `workforce_count` | Number of workers on site | 1 - 10,000 |
| `equipment_count` | Number of equipment units | 0 - 500 |
| `material_cost` | Cost of materials procured (NGN) | 0 - 10,000,000,000 |
| `completion_percentage` | Percentage complete | 0 - 100 |
| `weather_delay_days` | Days lost to weather | 0 - 365 |
| `safety_incidents` | Number of safety incidents | 0 - 100 |
| `inspection_score` | Quality inspection score | 0 - 100 |
| `task_completion_rate` | Fraction of tasks completed | 0 - 1 |
| `daily_progress_rate` | Daily progress (%) | 0 - 100 |
| `resource_availability` | Resource availability fraction | 0 - 1 |
| `workforce_attendance` | Workforce attendance fraction | 0 - 1 |
| `supply_delay_days` | Days of supply chain delay | 0 - 365 |
| `rainfall_mm` | Monthly rainfall at site (mm) | 0 - 500 |

### Categorical Features
| Column | Valid Values |
|---|---|
| `project_type` | Road, Building, Bridge, Dam, Pipeline, Railway, PowerPlant |
| `state` | Any Nigerian state (Lagos, FCT, Rivers, Kano, Oyo, Kaduna, Enugu, Edo, Delta, Abia, Taraba, Niger, Anambra, etc.) |

### Labels
| Column | Description |
|---|---|
| `delayed` | Binary: 0 = on time, 1 = delayed |
| `budget_overrun_pct` | Overrun percentage (0 = on budget) |
| `risk_level` | low, medium, or high |

### Metadata (optional)
| Column | Description |
|---|---|
| `duration_days` | Planned project duration in days |
| `actual_completion_days` | Actual project duration in days |

## API Reference

### `validate_schema(df) -> dict`
Checks column presence, categorical value validity, and binary constraints. Returns `{valid, missing_cols, extra_cols, errors}`.

### `normalize_data(df) -> pd.DataFrame`
Converts types, fills missing values with defaults, clips outliers within expected ranges, ensures categorical columns are strings.

### `load_external_data(path) -> pd.DataFrame`
Loads CSV or JSON, validates schema (logs warnings on issues), normalises, reports data quality. Returns a clean DataFrame.

### `merge_with_synthetic(external_df, synthetic_path) -> pd.DataFrame`
Concatenates external and synthetic data, aligns columns, adds a `source` column (`external` / `synthetic`), handles dtype mismatches.

### `save_training_data(df, output_path)`
Saves to CSV/JSON/Parquet (inferred from extension) and prints a training data report covering record counts, delay rate, overrun stats, risk distribution, and data quality metrics. Writes a `.stats.json` sidecar file.

## Data Quality Checks

On load, the pipeline logs:
- Missing columns and how many values were filled per column
- Outlier values clipped to expected ranges
- Invalid categorical values (project_type, state, risk_level)
- Non-binary delayed flags
- Duplicate rows
- Remaining null values after normalisation

## Sample Data

`data/external/sample_projects.csv` contains 20 hand-crafted records representing real Nigerian construction projects (with realistic but non-confidential figures). Use this to test the pipeline end-to-end.

## Workflow

```
data/external/your_data.csv
       |
       v
load_external_data()
       |
       v
validate_schema() + normalize_data()
       |
       v
merge_with_synthetic(external, data/raw/construction_projects.csv)
       |
       v
save_training_data(merged, data/processed/training_data.csv)
       |
       v
data/processed/training_data.csv   +   training_data.stats.json
```
