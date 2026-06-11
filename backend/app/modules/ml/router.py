import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import APIRouter, Query, Depends, HTTPException, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.core import DelayPrediction
from app.core.config import settings

logger = logging.getLogger(__name__)

bearer = HTTPBearer(auto_error=False)
router = APIRouter()


def _verify_ml_access(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> dict:
    if x_api_key and x_api_key == settings.api_key:
        return {"role": "admin", "source": "api_key"}
    if credentials is not None:
        from app.core.security import decode_access_token
        try:
            payload = decode_access_token(credentials.credentials)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return payload
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
    raise HTTPException(status_code=401, detail="Authentication required. Provide a valid JWT Bearer token or X-API-Key header.")

BACKEND_DIR = Path(__file__).resolve().parents[3]

_MODEL_EVAL_CONFIGS = [
    {
        "name": "delay_model",
        "features": [
            "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
            "material_cost", "completion_percentage", "weather_delay_days",
            "safety_incidents", "inspection_score", "task_completion_rate",
            "daily_progress_rate", "resource_availability", "workforce_attendance",
            "supply_delay_days", "rainfall_mm",
        ],
        "cat_features": ["project_type", "state"],
        "target": "delayed",
        "type": "classifier",
    },
    {
        "name": "budget_model",
        "features": [
            "budget_allocated", "workforce_count", "equipment_count",
            "material_cost", "completion_percentage", "weather_delay_days",
            "safety_incidents", "inspection_score", "task_completion_rate",
            "daily_progress_rate", "resource_availability", "supply_delay_days",
        ],
        "cat_features": ["project_type", "state"],
        "target": "budget_overrun_pct",
        "type": "regressor",
    },
    {
        "name": "risk_classifier",
        "features": [
            "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
            "material_cost", "completion_percentage", "weather_delay_days",
            "safety_incidents", "inspection_score", "task_completion_rate",
            "daily_progress_rate", "resource_availability", "workforce_attendance",
            "supply_delay_days", "rainfall_mm",
        ],
        "cat_features": ["project_type", "state"],
        "target": "risk_level",
        "type": "classifier",
    },
]


def _reindex_to_model(df, model):
    expected = getattr(model, "feature_names_in_", None)
    if expected is not None:
        for col in expected:
            if col not in df.columns:
                df[col] = 0
        df = df[list(expected)]
    return df


def _engineer_features(df, features, cat_features):
    X = df[features].copy()
    for col in cat_features:
        dummies = pd.get_dummies(df[col], prefix=col)
        X = pd.concat([X, dummies], axis=1)
    return X


def _evaluate_classifier(y_test, y_pred, y_proba=None):
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


def _evaluate_regressor(y_test, y_pred):
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    import numpy as np

    return {
        "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
        "mae": float(mean_absolute_error(y_test, y_pred)),
        "r2": float(r2_score(y_test, y_pred)),
    }


@router.get("/model-health")
async def model_health(auth: dict = Depends(_verify_ml_access)):
    from app.services.model_service import get_model_health
    return get_model_health()


@router.post("/train")
async def train_models(auth: dict = Depends(_verify_ml_access)):
    scripts = [
        ("Generate Dataset", "data/generate_dataset.py"),
        ("Delay Model", "scripts/train_delay_model.py"),
        ("Budget Model", "scripts/train_budget_model.py"),
        ("Risk Model", "scripts/train_risk_model.py"),
    ]

    results = []
    dataset_info = ""
    errors = []

    for label, script in scripts:
        try:
            proc = subprocess.run(
                [sys.executable, str(BACKEND_DIR / script)],
                capture_output=True, text=True, timeout=600,
                cwd=str(BACKEND_DIR),
            )
            lines = proc.stdout.strip().split("\n")
            info_lines = [l for l in lines if l.strip()]
            summary = info_lines[-1] if info_lines else ""

            if proc.returncode != 0:
                err = proc.stderr.strip() or "Unknown error"
                results.append({
                    "model_name": label,
                    "status": "failed",
                    "message": err,
                })
                errors.append(f"{label}: {err}")
            else:
                results.append({
                    "model_name": label,
                    "status": "success",
                    "message": summary,
                })

            if label == "Generate Dataset":
                dataset_info = summary

        except subprocess.TimeoutExpired:
            results.append({
                "model_name": label,
                "status": "failed",
                "message": "Training timed out after 600s",
            })
            errors.append(f"{label}: timed out")
        except Exception as exc:
            results.append({
                "model_name": label,
                "status": "failed",
                "message": str(exc),
            })
            errors.append(f"{label}: {exc}")

    from app.services.model_service import _MODELS, _META_CACHE, _LOAD_TIMES
    _MODELS.clear()
    _META_CACHE.clear()
    _LOAD_TIMES.clear()

    overall = "success" if not errors else "partial_success" if len(errors) < len(scripts) else "failed"
    message = f"Training completed: {len([r for r in results if r['status'] == 'success'])}/{len(scripts)} scripts succeeded"
    if errors:
        message += f". Errors: {'; '.join(errors)}"

    return {
        "status": overall,
        "dataset": dataset_info,
        "results": results,
        "message": message,
    }


@router.get("/predictions")
async def get_predictions(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    project_id: int = Query(None),
    company_id: int = Query(None),
    db: Session = Depends(get_db),
    auth: dict = Depends(_verify_ml_access),
):
    query = db.query(DelayPrediction)

    if project_id is not None:
        query = query.filter(DelayPrediction.project_id == project_id)
    if company_id is not None:
        query = query.filter(DelayPrediction.company_id == company_id)

    total = query.count()
    query = query.order_by(desc(DelayPrediction.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    records = query.all()

    return {
        "predictions": [
            {
                "id": r.id,
                "project_id": r.project_id,
                "company_id": r.company_id,
                "features_json": r.features_json,
                "delay_risk": r.delay_risk,
                "will_delay": r.will_delay,
                "model_version": r.model_version,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/model-config")
async def get_model_config(auth: dict = Depends(_verify_ml_access)):
    from app.services.model_service import get_active_models_config
    return {"model_config": get_active_models_config()}


@router.put("/model-config")
async def update_model_config(config: dict, auth: dict = Depends(_verify_ml_access)):
    from app.services.model_service import set_active_model_version
    errors = []
    for name, version in config.items():
        try:
            set_active_model_version(name, version if version else None)
        except Exception as exc:
            errors.append({name: str(exc)})
    from app.services.model_service import get_active_models_config
    return {"status": "updated", "model_config": get_active_models_config(), "errors": errors}


@router.get("/stats")
async def prediction_stats(
    db: Session = Depends(get_db),
    auth: dict = Depends(_verify_ml_access),
):
    total = db.query(DelayPrediction).count()
    if total == 0:
        return {
            "total_predictions": 0,
            "avg_delay_risk": 0.0,
            "will_delay_count": 0,
            "will_delay_pct": 0.0,
            "model_version_counts": {},
            "recent_daily_counts": [],
        }

    from sqlalchemy import func

    avg_risk = db.query(func.avg(DelayPrediction.delay_risk)).scalar() or 0.0
    will_delay_count = db.query(DelayPrediction).filter(DelayPrediction.will_delay == True).count()

    version_rows = (
        db.query(DelayPrediction.model_version, func.count(DelayPrediction.id))
        .group_by(DelayPrediction.model_version)
        .all()
    )
    model_version_counts = {v: c for v, c in version_rows}

    daily_rows = (
        db.query(
            func.date(DelayPrediction.created_at).label("day"),
            func.count(DelayPrediction.id).label("cnt"),
            func.avg(DelayPrediction.delay_risk).label("avg_risk"),
        )
        .group_by(func.date(DelayPrediction.created_at))
        .order_by(func.date(DelayPrediction.created_at).desc())
        .limit(30)
        .all()
    )
    recent_daily_counts = [
        {"date": str(r.day), "count": r.cnt, "avg_delay_risk": round(float(r.avg_risk), 4)}
        for r in daily_rows
    ]

    return {
        "total_predictions": total,
        "avg_delay_risk": round(float(avg_risk), 4),
        "will_delay_count": will_delay_count,
        "will_delay_pct": round(will_delay_count / total, 4),
        "model_version_counts": model_version_counts,
        "recent_daily_counts": recent_daily_counts,
    }


@router.get("/evaluate")
async def evaluate_models(auth: dict = Depends(_verify_ml_access)):
    from app.services.model_service import _load_model

    DATA_PATH = BACKEND_DIR / "data" / "raw" / "construction_projects.csv"
    df = pd.read_csv(DATA_PATH)
    results = {}

    for cfg in _MODEL_EVAL_CONFIGS:
        name = cfg["name"]
        model = _load_model(name)
        if model is None:
            results[name] = {"error": "Model not loaded or not found"}
            continue

        X = _engineer_features(df, cfg["features"], cfg["cat_features"])
        y = df[cfg["target"]].copy()

        le = None
        if name == "risk_classifier":
            le = LabelEncoder()
            y = le.fit_transform(y)

        stratify = y if cfg["type"] == "classifier" else None
        _, X_test, _, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=stratify
        )

        X_test = _reindex_to_model(X_test, model)
        y_pred = model.predict(X_test)

        if cfg["type"] == "classifier":
            n_unique = len(set(y))
            y_proba = None
            if n_unique == 2:
                y_proba = model.predict_proba(X_test)[:, 1]
            metrics = _evaluate_classifier(y_test, y_pred, y_proba)
            if hasattr(model, "feature_importances_"):
                metrics["feature_importance"] = dict(
                    zip(X_test.columns, [float(v) for v in model.feature_importances_])
                )
            if name == "risk_classifier" and le is not None:
                metrics["label_encoder_mapping"] = dict(enumerate(le.classes_))
        else:
            metrics = _evaluate_regressor(y_test, y_pred)
            if hasattr(model, "feature_importances_"):
                metrics["feature_importance"] = dict(
                    zip(X_test.columns, [float(v) for v in model.feature_importances_])
                )

        results[name] = metrics

    return results
