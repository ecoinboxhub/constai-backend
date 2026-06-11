import logging
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, KFold

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from scripts.train_base import (
    engineer_features, save_model, evaluate_regressor, log_to_mlflow,
    try_optuna_regressor, try_xgboost_regressor,
)

FEATURES = [
    "budget_allocated", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "supply_delay_days",
]

CAT_FEATURES = ["project_type", "state"]
TARGET = "budget_overrun_pct"

MODEL_NAME = "budget_model"
MODEL_VERSION = "v1.0"
MODEL_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "models"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "construction_projects.csv"
MLFLOW_EXPERIMENT = "nigeria_construction_budget"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Loaded {len(df)} records from {DATA_PATH}")
    return df


def train(X: pd.DataFrame, y: pd.Series):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    models = {}

    rf_model, rf_params = try_optuna_regressor(X_train, y_train, X_test, y_test, "RandomForest")
    rf_pred = rf_model.predict(X_test)
    rf_metrics = evaluate_regressor(y_test, rf_pred)
    log_to_mlflow(MLFLOW_EXPERIMENT, rf_model, f"{MODEL_NAME}_RF_tuned", rf_params,
                  {k: v for k, v in rf_metrics.items() if isinstance(v, (int, float))},
                  {"evaluation_results.json": rf_metrics,
                   "feature_importances.json": dict(zip(X.columns, [float(v) for v in rf_model.feature_importances_]))})
    models["RandomForest_tuned"] = (rf_model, rf_metrics)

    gb_model, gb_params = try_optuna_regressor(X_train, y_train, X_test, y_test, "GradientBoosting")
    gb_pred = gb_model.predict(X_test)
    gb_metrics = evaluate_regressor(y_test, gb_pred)
    log_to_mlflow(MLFLOW_EXPERIMENT, gb_model, f"{MODEL_NAME}_GB_tuned", gb_params,
                  {k: v for k, v in gb_metrics.items() if isinstance(v, (int, float))},
                  {"evaluation_results.json": gb_metrics,
                   "feature_importances.json": dict(zip(X.columns, [float(v) for v in gb_model.feature_importances_]))})
    models["GradientBoosting_tuned"] = (gb_model, gb_metrics)

    xgb_model, xgb_metrics = try_xgboost_regressor(X_train, y_train, X_test, y_test)
    if xgb_model is not None:
        log_to_mlflow(MLFLOW_EXPERIMENT, xgb_model, f"{MODEL_NAME}_XGBoost",
                      {"model_type": "XGBoost", "version": MODEL_VERSION},
                      {k: v for k, v in xgb_metrics.items() if isinstance(v, (int, float))},
                      {"evaluation_results.json": xgb_metrics,
                       "feature_importances.json": dict(zip(X.columns, [float(v) for v in xgb_model.feature_importances_]))})
        models["XGBoost"] = (xgb_model, xgb_metrics)

        xgb_tuned_model, xgb_tuned_params = try_optuna_regressor(X_train, y_train, X_test, y_test, "XGBoost")
        xgb_tuned_pred = xgb_tuned_model.predict(X_test)
        xgb_tuned_metrics = evaluate_regressor(y_test, xgb_tuned_pred)
        log_to_mlflow(MLFLOW_EXPERIMENT, xgb_tuned_model, f"{MODEL_NAME}_XGBoost_tuned", xgb_tuned_params,
                      {k: v for k, v in xgb_tuned_metrics.items() if isinstance(v, (int, float))},
                      {"evaluation_results.json": xgb_tuned_metrics,
                       "feature_importances.json": dict(zip(X.columns, [float(v) for v in xgb_tuned_model.feature_importances_]))})
        models["XGBoost_tuned"] = (xgb_tuned_model, xgb_tuned_metrics)

    best_metric = -float("inf")
    best_name = None
    best_model = None
    for name, (model, _) in models.items():
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring="r2")
        cv_mean = cv_scores.mean()
        logger.info(f"{name}: cv_r2={cv_mean:.4f}")
        if cv_mean > best_metric:
            best_metric = cv_mean
            best_model = model
            best_name = name

    logger.info(f"Best model: {best_name} (CV R2={best_metric:.4f})")

    save_model(best_model, best_name, MODEL_NAME, MODEL_DIR, {
        "features": FEATURES,
        "categorical_features": CAT_FEATURES,
        "version": MODEL_VERSION,
        "best_r2": best_metric,
    })

    return best_model, best_name


def main():
    df = load_data()
    y = df[TARGET]
    X = engineer_features(df, FEATURES, CAT_FEATURES)
    train(X, y)


if __name__ == "__main__":
    main()
