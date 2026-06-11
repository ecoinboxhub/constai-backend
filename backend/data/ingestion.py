import os
import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "budget_allocated",
    "budget_spent",
    "workforce_count",
    "equipment_count",
    "material_cost",
    "completion_percentage",
    "weather_delay_days",
    "safety_incidents",
    "inspection_score",
    "task_completion_rate",
    "daily_progress_rate",
    "resource_availability",
    "workforce_attendance",
    "supply_delay_days",
    "rainfall_mm",
    "project_type",
    "state",
    "delayed",
    "budget_overrun_pct",
    "risk_level",
]

NUMERIC_FEATURES = [
    "budget_allocated",
    "budget_spent",
    "workforce_count",
    "equipment_count",
    "material_cost",
    "completion_percentage",
    "weather_delay_days",
    "safety_incidents",
    "inspection_score",
    "task_completion_rate",
    "daily_progress_rate",
    "resource_availability",
    "workforce_attendance",
    "supply_delay_days",
    "rainfall_mm",
]

CATEGORICAL_FEATURES = ["project_type", "state"]

VALID_PROJECT_TYPES = ["Road", "Building", "Bridge", "Dam", "Pipeline", "Railway", "PowerPlant"]

VALID_STATES = [
    "Lagos", "FCT", "Rivers", "Kano", "Oyo", "Kaduna", "Enugu", "Edo",
    "Delta", "Abia", "Taraba", "Niger", "Anambra", "Kogi", "Katsina",
    "Akwa_Ibom", "Sokoto", "Osun", "Ondo", "Benue",
]

VALID_RISK_LEVELS = ["low", "medium", "high"]

NUMERIC_BOUNDS = {
    "budget_allocated": (1e5, 1e10),
    "budget_spent": (0, 1e10),
    "workforce_count": (1, 10000),
    "equipment_count": (0, 500),
    "material_cost": (0, 1e10),
    "completion_percentage": (0, 100),
    "weather_delay_days": (0, 365),
    "safety_incidents": (0, 100),
    "inspection_score": (0, 100),
    "task_completion_rate": (0, 1),
    "daily_progress_rate": (0, 100),
    "resource_availability": (0, 1),
    "workforce_attendance": (0, 1),
    "supply_delay_days": (0, 365),
    "rainfall_mm": (0, 500),
}

NUMERIC_DEFAULTS = {
    "budget_allocated": 50_000_000,
    "budget_spent": 0,
    "workforce_count": 10,
    "equipment_count": 0,
    "material_cost": 0,
    "completion_percentage": 0,
    "weather_delay_days": 0,
    "safety_incidents": 0,
    "inspection_score": 50,
    "task_completion_rate": 0.5,
    "daily_progress_rate": 0.0,
    "resource_availability": 0.7,
    "workforce_attendance": 0.8,
    "supply_delay_days": 0,
    "rainfall_mm": 0,
}


def validate_schema(df: pd.DataFrame) -> dict:
    missing_cols = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in EXPECTED_COLUMNS and c not in (
        "duration_days", "actual_completion_days",
    )]
    errors = []

    if "project_type" in df.columns:
        invalid_types = df["project_type"].dropna().loc[
            ~df["project_type"].dropna().isin(VALID_PROJECT_TYPES)
        ]
        if len(invalid_types) > 0:
            bad = invalid_types.unique().tolist()
            errors.append(f"Invalid project_type values: {bad}")

    if "state" in df.columns:
        invalid_states = df["state"].dropna().loc[
            ~df["state"].dropna().isin(VALID_STATES)
        ]
        if len(invalid_states) > 0:
            bad = invalid_states.unique().tolist()
            errors.append(f"Invalid state values: {bad}")

    if "risk_level" in df.columns:
        invalid_risk = df["risk_level"].dropna().loc[
            ~df["risk_level"].dropna().isin(VALID_RISK_LEVELS)
        ]
        if len(invalid_risk) > 0:
            bad = invalid_risk.unique().tolist()
            errors.append(f"Invalid risk_level values: {bad}")

    if "delayed" in df.columns:
        non_binary = df["delayed"].dropna().loc[
            ~df["delayed"].dropna().isin([0, 1])
        ]
        if len(non_binary) > 0:
            errors.append(f"delayed column contains non-binary values: {non_binary.unique().tolist()}")

    valid = len(missing_cols) == 0 and len(errors) == 0

    return {
        "valid": valid,
        "missing_cols": missing_cols,
        "extra_cols": extra_cols,
        "errors": errors,
    }


def normalize_data(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    for col in NUMERIC_FEATURES:
        if col not in result.columns:
            result[col] = np.nan

        result[col] = pd.to_numeric(result[col], errors="coerce")

        null_mask = result[col].isna()
        if null_mask.any():
            logger.info(f"{col}: filled {null_mask.sum()} missing values with default")
            result.loc[null_mask, col] = NUMERIC_DEFAULTS.get(col, 0)

        if col in NUMERIC_BOUNDS:
            lo, hi = NUMERIC_BOUNDS[col]
            clipped = result[col].clip(lo, hi)
            n_clipped = (result[col] != clipped).sum()
            if n_clipped > 0:
                logger.info(f"{col}: clipped {n_clipped} out-of-range values to [{lo}, {hi}]")
            result[col] = clipped

    for col in CATEGORICAL_FEATURES:
        if col not in result.columns:
            result[col] = "Unknown"
        result[col] = result[col].fillna("Unknown").astype(str)

    if "delayed" in result.columns:
        result["delayed"] = pd.to_numeric(result["delayed"], errors="coerce").fillna(0).astype(int)
        result["delayed"] = result["delayed"].clip(0, 1)

    if "budget_overrun_pct" in result.columns:
        result["budget_overrun_pct"] = pd.to_numeric(result["budget_overrun_pct"], errors="coerce").fillna(0)
        result["budget_overrun_pct"] = result["budget_overrun_pct"].clip(0)

    if "risk_level" in result.columns:
        result["risk_level"] = result["risk_level"].fillna("unknown").astype(str)

    if "duration_days" in result.columns:
        result["duration_days"] = pd.to_numeric(result["duration_days"], errors="coerce")
    if "actual_completion_days" in result.columns:
        result["actual_completion_days"] = pd.to_numeric(result["actual_completion_days"], errors="coerce")

    return result


def load_external_data(path: str) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"External data file not found: {path}")

    suffix = path.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix == ".json":
        df = pd.read_json(path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use .csv or .json")

    logger.info(f"Loaded {len(df)} records from {path}")
    logger.info(f"Columns found: {list(df.columns)}")

    validation = validate_schema(df)
    if not validation["valid"]:
        logger.warning(f"Schema validation issues: {validation['errors']}")
        if validation["missing_cols"]:
            logger.warning(f"Missing columns: {validation['missing_cols']}")
        if validation["extra_cols"]:
            logger.info(f"Extra columns (will be preserved): {validation['extra_cols']}")
    else:
        logger.info("Schema validation passed")

    df = normalize_data(df)
    logger.info(f"Normalized: {len(df)} records, {len(df.columns)} columns")
    _report_quality(df)

    return df


def merge_with_synthetic(external_df: pd.DataFrame, synthetic_path: str) -> pd.DataFrame:
    synth_path = Path(synthetic_path)
    if not synth_path.exists():
        raise FileNotFoundError(f"Synthetic data not found: {synth_path}")

    synth_df = pd.read_csv(synth_path)
    logger.info(f"Loaded {len(synth_df)} synthetic records from {synth_path}")

    ext_cols = set(external_df.columns)
    synth_cols = set(synth_df.columns)
    common = ext_cols & synth_cols
    only_ext = ext_cols - synth_cols
    only_synth = synth_cols - ext_cols

    logger.info(f"Common columns: {len(common)}")
    if only_ext:
        logger.info(f"External-only columns: {only_ext}")
    if only_synth:
        logger.info(f"Synthetic-only columns: {only_synth}")

    if "source" not in external_df.columns:
        external_df = external_df.copy()
        external_df["source"] = "external"
    if "source" not in synth_df.columns:
        synth_df = synth_df.copy()
        synth_df["source"] = "synthetic"

    all_columns = list(dict.fromkeys(list(external_df.columns) + list(synth_df.columns)))
    for col in all_columns:
        if col not in external_df.columns:
            external_df[col] = np.nan
        if col not in synth_df.columns:
            synth_df[col] = np.nan

    for col in all_columns:
        if external_df[col].dtype != synth_df[col].dtype:
            try:
                if pd.api.types.is_numeric_dtype(synth_df[col]):
                    external_df[col] = pd.to_numeric(external_df[col], errors="coerce")
                elif pd.api.types.is_numeric_dtype(external_df[col]):
                    synth_df[col] = pd.to_numeric(synth_df[col], errors="coerce")
            except Exception:
                pass

    merged = pd.concat([external_df, synth_df], ignore_index=True)
    logger.info(f"Merged dataset: {len(merged)} total records ({len(external_df)} external + {len(synth_df)} synthetic)")

    return merged


def save_training_data(df: pd.DataFrame, output_path: str) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ext_count = int((df.get("source", pd.Series("synthetic")) == "external").sum())
    synth_count = int((df.get("source", pd.Series("synthetic")) == "synthetic").sum())
    if ext_count + synth_count == 0:
        total = len(df)
    else:
        total = len(df)

    delayed_count = int(df["delayed"].sum()) if "delayed" in df.columns else 0
    on_time_count = total - delayed_count if "delayed" in df.columns else 0

    risk_dist = df["risk_level"].value_counts().to_dict() if "risk_level" in df.columns else {}

    budget_col = "budget_overrun_pct" if "budget_overrun_pct" in df.columns else None
    if budget_col:
        budget_avg = float(df[budget_col].mean())
        budget_std = float(df[budget_col].std())
    else:
        budget_avg = budget_std = 0.0

    unique_types = list(df["project_type"].unique()) if "project_type" in df.columns else []
    unique_states = list(df["state"].unique()) if "state" in df.columns else []

    stats = {
        "total_records": total,
        "external_records": ext_count,
        "synthetic_records": synth_count,
        "delayed_projects": int(delayed_count),
        "on_time_projects": int(on_time_count),
        "delay_rate_pct": round(float(delayed_count / total * 100), 2) if total > 0 else 0,
        "avg_budget_overrun_pct": round(budget_avg, 2),
        "std_budget_overrun_pct": round(budget_std, 2),
        "risk_distribution": {k: int(v) for k, v in risk_dist.items()},
        "project_types": unique_types,
        "states": unique_states,
        "columns": list(df.columns),
        "output_file": str(output_path),
    }

    suffix = output_path.suffix.lower()
    if suffix == ".csv":
        df.to_csv(output_path, index=False)
    elif suffix == ".json":
        df.to_json(output_path, orient="records", indent=2)
    elif suffix == ".parquet":
        df.to_parquet(output_path, index=False)
    else:
        df.to_csv(output_path, index=False)

    logger.info(f"Saved training data ({len(df)} records) to {output_path}")

    print("\n" + "=" * 60)
    print("TRAINING DATA REPORT")
    print("=" * 60)
    print(f"  Total records:         {stats['total_records']}")
    print(f"  External records:      {stats['external_records']}")
    print(f"  Synthetic records:     {stats['synthetic_records']}")
    print(f"  Delayed projects:      {stats['delayed_projects']} ({stats['delay_rate_pct']}%)")
    print(f"  On-time projects:      {stats['on_time_projects']}")
    print(f"  Avg budget overrun:    {stats['avg_budget_overrun_pct']}%")
    print(f"  Std budget overrun:    {stats['std_budget_overrun_pct']}%")
    print(f"  Risk distribution:     {stats['risk_distribution']}")
    print(f"  Project types:         {len(stats['project_types'])}")
    print(f"  States represented:    {len(stats['states'])}")
    print(f"  Output:                {stats['output_file']}")
    print("=" * 60 + "\n")

    _report_quality(df)

    stats_path = output_path.with_suffix(".stats.json")
    with open(stats_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    logger.info(f"Statistics written to {stats_path}")


def _report_quality(df: pd.DataFrame) -> None:
    total = len(df)
    print("  DATA QUALITY REPORT")
    print("  " + "-" * 50)
    print(f"  Rows: {total}")
    print(f"  Columns: {len(df.columns)}")
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if len(null_cols) > 0:
        print(f"  Columns with nulls:")
        for col, cnt in null_cols.items():
            print(f"    - {col}: {cnt} ({cnt/total*100:.1f}%)")
    else:
        print(f"  Null values: None")
    duplicates = df.duplicated().sum()
    if duplicates > 0:
        print(f"  Duplicate rows: {duplicates}")
    else:
        print(f"  Duplicate rows: None")
    print()
