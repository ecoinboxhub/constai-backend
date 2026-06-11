import logging
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from scripts.train_base import (
    engineer_features, save_model, evaluate_classifier, log_to_mlflow,
    try_optuna_classifier, try_xgboost_classifier,
)

FEATURES = [
    "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "workforce_attendance",
    "supply_delay_days", "rainfall_mm",
]

CAT_FEATURES = ["project_type", "state"]
TARGET = "risk_level"

MODEL_NAME = "risk_classifier"
MODEL_VERSION = "v1.0"
MODEL_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "models"
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "raw" / "construction_projects.csv"
MLFLOW_EXPERIMENT = "nigeria_construction_risk"


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Loaded {len(df)} records from {DATA_PATH}")
    return df


def train(X: pd.DataFrame, y: pd.Series, label_encoder: LabelEncoder):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    models = {}

    rf_model, rf_params = try_optuna_classifier(X_train, y_train, X_test, y_test, "RandomForest", n_trials=15)
    rf_pred = rf_model.predict(X_test)
    rf_metrics = evaluate_classifier(y_test, rf_pred)
    log_to_mlflow(MLFLOW_EXPERIMENT, rf_model, f"{MODEL_NAME}_RF_tuned", rf_params,
                  {k: v for k, v in rf_metrics.items() if isinstance(v, (int, float))},
                  {"evaluation_results.json": {"confusion_matrix": rf_metrics["confusion_matrix"],
                                                "classification_report": rf_metrics["classification_report"]},
                   "feature_importances.json": dict(zip(X.columns, [float(v) for v in rf_model.feature_importances_]))})
    models["RandomForest_tuned"] = (rf_model, rf_metrics)
    save_model(rf_model, "RandomForest_tuned", MODEL_NAME, MODEL_DIR, {
        "features": FEATURES, "categorical_features": CAT_FEATURES,
        "version": MODEL_VERSION, "classes": label_encoder.classes_.tolist(),
        "best_f1": rf_metrics.get("f1", 0),
    })
    le_path = MODEL_DIR / f"{MODEL_NAME}_labels.pkl"
    joblib.dump(label_encoder, le_path)

    gb_model, gb_params = try_optuna_classifier(X_train, y_train, X_test, y_test, "GradientBoosting", n_trials=10)
    gb_pred = gb_model.predict(X_test)
    gb_metrics = evaluate_classifier(y_test, gb_pred)
    log_to_mlflow(MLFLOW_EXPERIMENT, gb_model, f"{MODEL_NAME}_GB_tuned", gb_params,
                  {k: v for k, v in gb_metrics.items() if isinstance(v, (int, float))},
                  {"evaluation_results.json": {"confusion_matrix": gb_metrics["confusion_matrix"],
                                                "classification_report": gb_metrics["classification_report"]},
                   "feature_importances.json": dict(zip(X.columns, [float(v) for v in gb_model.feature_importances_]))})
    models["GradientBoosting_tuned"] = (gb_model, gb_metrics)

    xgb_model, xgb_metrics = try_xgboost_classifier(X_train, y_train, X_test, y_test)
    if xgb_model is not None:
        log_to_mlflow(MLFLOW_EXPERIMENT, xgb_model, f"{MODEL_NAME}_XGBoost",
                      {"model_type": "XGBoost", "version": MODEL_VERSION},
                      {k: v for k, v in xgb_metrics.items() if isinstance(v, (int, float))},
                      {"evaluation_results.json": {"confusion_matrix": xgb_metrics["confusion_matrix"],
                                                    "classification_report": xgb_metrics["classification_report"]},
                       "feature_importances.json": dict(zip(X.columns, [float(v) for v in xgb_model.feature_importances_]))})
        models["XGBoost"] = (xgb_model, xgb_metrics)

        xgb_tuned_model, xgb_tuned_params = try_optuna_classifier(X_train, y_train, X_test, y_test, "XGBoost", n_trials=10)
        xgb_tuned_pred = xgb_tuned_model.predict(X_test)
        xgb_tuned_metrics = evaluate_classifier(y_test, xgb_tuned_pred)
        log_to_mlflow(MLFLOW_EXPERIMENT, xgb_tuned_model, f"{MODEL_NAME}_XGBoost_tuned", xgb_tuned_params,
                      {k: v for k, v in xgb_tuned_metrics.items() if isinstance(v, (int, float))},
                      {"evaluation_results.json": {"confusion_matrix": xgb_tuned_metrics["confusion_matrix"],
                                                    "classification_report": xgb_tuned_metrics["classification_report"]},
                       "feature_importances.json": dict(zip(X.columns, [float(v) for v in xgb_tuned_model.feature_importances_]))})
        models["XGBoost_tuned"] = (xgb_tuned_model, xgb_tuned_metrics)

    best_metric = -float("inf")
    best_name = None
    best_model = None
    for name, (model, _) in models.items():
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=cv, scoring="f1_weighted")
        cv_mean = cv_scores.mean()
        logger.info(f"{name}: cv_f1={cv_mean:.4f}")
        if cv_mean > best_metric:
            best_metric = cv_mean
            best_model = model
            best_name = name

    logger.info(f"Best model: {best_name} (CV F1={best_metric:.4f})")

    save_model(best_model, best_name, MODEL_NAME, MODEL_DIR, {
        "features": FEATURES,
        "categorical_features": CAT_FEATURES,
        "version": MODEL_VERSION,
        "classes": label_encoder.classes_.tolist(),
        "best_f1": best_metric,
    })

    le_path = MODEL_DIR / f"{MODEL_NAME}_labels.pkl"
    joblib.dump(label_encoder, le_path)
    logger.info(f"Saved label encoder -> {le_path}")

    return best_model, best_name


def main():
    df = load_data()
    le = LabelEncoder()
    y = le.fit_transform(df[TARGET])
    X = engineer_features(df, FEATURES, CAT_FEATURES)
    train(X, y, le)


if __name__ == "__main__":
    main()
