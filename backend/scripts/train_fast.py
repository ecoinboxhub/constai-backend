import logging, sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

from scripts.train_base import (
    engineer_features, save_model, evaluate_classifier, evaluate_regressor,
    try_optuna_classifier, try_optuna_regressor,
)

n_trials = int(os.environ.get("OPTUNA_TRIALS", "5"))
model_dir = Path(__file__).resolve().parents[1] / "artifacts" / "models"
model_dir.mkdir(parents=True, exist_ok=True)

FEATURES = [
    "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "workforce_attendance",
    "supply_delay_days", "rainfall_mm",
]
CAT_FEATURES = ["project_type", "state"]

BUDGET_FEATURES = [
    "budget_allocated", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "supply_delay_days",
]

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "construction_projects.csv"
df = pd.read_csv(DATA_PATH)
logger.info(f"Loaded {len(df)} records from {DATA_PATH}")


def train_delay():
    logger.info("=== Training Delay Model ===")
    y = df["delayed"]
    X = engineer_features(df, FEATURES, CAT_FEATURES)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model, params = try_optuna_classifier(X_train, y_train, X_test, y_test, "RandomForest", n_trials=n_trials)
    if model is None:
        model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1, class_weight="balanced")
        model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    metrics = evaluate_classifier(y_test, y_pred, y_proba)
    logger.info(f"Delay: F1={metrics['f1']:.4f}, ROC-AUC={metrics.get('roc_auc', 0):.4f}")
    save_model(model, "RandomForest_fast", "delay_model", model_dir, {"version": "v1.0", "f1": metrics["f1"]})


def train_budget():
    logger.info("=== Training Budget Model ===")
    y = df["budget_overrun_pct"]
    X = engineer_features(df, BUDGET_FEATURES, CAT_FEATURES)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    try:
        from xgboost import XGBRegressor
        model = XGBRegressor(n_estimators=200, max_depth=8, learning_rate=0.1, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = evaluate_regressor(y_test, y_pred)
        logger.info(f"Budget: RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}")
        save_model(model, "XGBoost", "budget_model", model_dir, {"version": "v1.0", "r2": metrics["r2"]})
    except ImportError:
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(n_estimators=200, max_depth=6, random_state=42)
        model, params = try_optuna_regressor(X_train, y_train, X_test, y_test, "GradientBoosting", n_trials=n_trials)
        if model is None:
            model = GradientBoostingRegressor(n_estimators=200, random_state=42)
            model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        metrics = evaluate_regressor(y_test, y_pred)
        logger.info(f"Budget (GB): RMSE={metrics['rmse']:.4f}, R2={metrics['r2']:.4f}")
        save_model(model, "GB_fast", "budget_model", model_dir, {"version": "v1.0", "r2": metrics["r2"]})


def train_risk():
    logger.info("=== Training Risk Model ===")
    le = LabelEncoder()
    y = le.fit_transform(df["risk_level"])
    X = engineer_features(df, FEATURES, CAT_FEATURES)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    model, params = try_optuna_classifier(X_train, y_train, X_test, y_test, "RandomForest", n_trials=n_trials)
    if model is None:
        model = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = evaluate_classifier(y_test, y_pred)
    logger.info(f"Risk: F1={metrics['f1']:.4f}")
    save_model(model, "RandomForest_fast", "risk_classifier", model_dir, {"version": "v1.0", "f1": metrics["f1"]})


if __name__ == "__main__":
    train_delay()
    train_budget()
    train_risk()
    logger.info("ALL MODELS TRAINED SUCCESSFULLY")
