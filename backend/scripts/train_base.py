import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def engineer_features(df, features, cat_features):
    X = df[features].copy()
    for col in cat_features:
        dummies = pd.get_dummies(df[col], prefix=col)
        X = pd.concat([X, dummies], axis=1)
    return X


def save_model(model, name, model_name, model_dir, meta_extra=None):
    model_dir = Path(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    path = model_dir / f"{model_name}.pkl"
    joblib.dump(model, path)
    logger.info(f"Saved {name} -> {path}")

    meta = {
        "model_name": model_name,
        "version": "v1.0",
        "algorithm": name,
        "training_date": pd.Timestamp.now().isoformat(),
    }
    if meta_extra:
        meta.update(meta_extra)

    with open(model_dir / f"{model_name}_meta.json", "w") as f:
        json.dump(meta, f, indent=2)
    logger.info(f"Saved metadata -> {model_dir / f'{model_name}_meta.json'}")


def evaluate_classifier(y_test, y_pred, y_proba=None):
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report

    n_unique = len(set(y_test))
    average = "binary" if n_unique == 2 else "weighted"

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, average=average, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, average=average, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, average=average, zero_division=0)),
    }

    if y_proba is not None and n_unique == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))

    metrics["confusion_matrix"] = confusion_matrix(y_test, y_pred).tolist()
    metrics["classification_report"] = classification_report(y_test, y_pred, output_dict=True)

    return metrics


def evaluate_regressor(y_test, y_pred):
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    return {
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
    }


def log_to_mlflow(experiment_name, model, run_name, params, metrics, extra_dicts=None):
    import mlflow
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if extra_dicts:
            for key, value in extra_dicts.items():
                mlflow.log_dict(value, key)
        mlflow.sklearn.log_model(model, artifact_path="model")


def try_optuna_classifier(X_train, y_train, X_test, y_test, model_type, n_trials=20):
    try:
        import optuna
    except ImportError:
        logger.warning("optuna not installed, skipping Optuna tuning for classifier")
        return None, None
    from sklearn.metrics import f1_score

    n_unique = len(set(y_train))

    def objective(trial):
        if model_type == "RandomForest":
            from sklearn.ensemble import RandomForestClassifier
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                "max_depth": trial.suggest_int("max_depth", 5, 25),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
                "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"]),
                "random_state": 42,
                "n_jobs": -1,
            }
            if n_unique == 2:
                params["class_weight"] = "balanced"
            model = RandomForestClassifier(**params)
        elif model_type == "GradientBoosting":
            from sklearn.ensemble import GradientBoostingClassifier
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                "random_state": 42,
            }
            model = GradientBoostingClassifier(**params)
        elif model_type == "XGBoost":
            from xgboost import XGBClassifier
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "random_state": 42,
                "n_jobs": -1,
                "eval_metric": "logloss",
            }
            model = XGBClassifier(**params)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        if n_unique == 2:
            return f1_score(y_test, y_pred, zero_division=0)
        else:
            return f1_score(y_test, y_pred, average="weighted", zero_division=0)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    if "random_state" not in best_params:
        best_params["random_state"] = 42

    if model_type == "RandomForest":
        from sklearn.ensemble import RandomForestClassifier
        if n_unique == 2:
            best_params["class_weight"] = "balanced"
        best_params.setdefault("n_jobs", -1)
        model = RandomForestClassifier(**best_params)
    elif model_type == "GradientBoosting":
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(**best_params)
    elif model_type == "XGBoost":
        from xgboost import XGBClassifier
        best_params["eval_metric"] = "logloss"
        best_params.setdefault("n_jobs", -1)
        model = XGBClassifier(**best_params)

    model.fit(X_train, y_train)
    return model, best_params


def try_optuna_regressor(X_train, y_train, X_test, y_test, model_type, n_trials=20):
    try:
        import optuna
    except ImportError:
        logger.warning("optuna not installed, skipping Optuna tuning for regressor")
        return None, None
    from sklearn.metrics import r2_score

    def objective(trial):
        if model_type == "RandomForest":
            from sklearn.ensemble import RandomForestRegressor
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 500),
                "max_depth": trial.suggest_int("max_depth", 5, 25),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
                "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2"]),
                "random_state": 42,
                "n_jobs": -1,
            }
            model = RandomForestRegressor(**params)
        elif model_type == "GradientBoosting":
            from sklearn.ensemble import GradientBoostingRegressor
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 10),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 2, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3),
                "random_state": 42,
            }
            model = GradientBoostingRegressor(**params)
        elif model_type == "XGBoost":
            from xgboost import XGBRegressor
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 50, 300),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "random_state": 42,
                "n_jobs": -1,
            }
            model = XGBRegressor(**params)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        return float(r2_score(y_test, y_pred))

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials)

    best_params = study.best_params
    if "random_state" not in best_params:
        best_params["random_state"] = 42

    if model_type == "RandomForest":
        from sklearn.ensemble import RandomForestRegressor
        best_params.setdefault("n_jobs", -1)
        model = RandomForestRegressor(**best_params)
    elif model_type == "GradientBoosting":
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(**best_params)
    elif model_type == "XGBoost":
        from xgboost import XGBRegressor
        best_params.setdefault("n_jobs", -1)
        model = XGBRegressor(**best_params)

    model.fit(X_train, y_train)
    return model, best_params


def try_xgboost_classifier(X_train, y_train, X_test, y_test):
    try:
        from xgboost import XGBClassifier
    except ImportError:
        logger.warning("xgboost not installed, skipping XGBoost classifier")
        return None, None

    model = XGBClassifier(random_state=42, n_jobs=-1, eval_metric="logloss")
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    n_unique = len(set(y_train))
    y_proba = model.predict_proba(X_test)
    proba_for_metric = y_proba[:, 1] if n_unique == 2 else y_proba
    metrics = evaluate_classifier(y_test, y_pred, proba_for_metric if n_unique == 2 else None)
    return model, metrics


def try_xgboost_regressor(X_train, y_train, X_test, y_test):
    try:
        from xgboost import XGBRegressor
    except ImportError:
        logger.warning("xgboost not installed, skipping XGBoost regressor")
        return None, None

    model = XGBRegressor(random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    metrics = evaluate_regressor(y_test, y_pred)
    return model, metrics
