import base64
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_MODELS: dict[str, Any] = {}
_META_CACHE: dict[str, dict] = {}
_LOAD_TIMES: dict[str, float] = {}
_ACTIVE_MODELS: dict[str, str] = {}

_ACTIVE_MODELS_PATH: Optional[Path] = None

CAT_FEATURES = ["project_type", "state"]

_DELAY_FEATURES = [
    "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "workforce_attendance",
    "supply_delay_days", "rainfall_mm",
]

_BUDGET_FEATURES = [
    "budget_allocated", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "supply_delay_days",
]

_RISK_FEATURES = [
    "budget_allocated", "budget_spent", "workforce_count", "equipment_count",
    "material_cost", "completion_percentage", "weather_delay_days",
    "safety_incidents", "inspection_score", "task_completion_rate",
    "daily_progress_rate", "resource_availability", "workforce_attendance",
    "supply_delay_days", "rainfall_mm",
]


def _models_dir() -> Path:
    from app.core.config import settings
    return Path(settings.model_registry_path)


def _meta_path(name: str) -> Path:
    return _models_dir() / f"{name}_meta.json"


def _label_encoder_path(name: str) -> Path:
    return _models_dir() / f"{name}_labels.pkl"


def _active_models_config_path() -> Path:
    global _ACTIVE_MODELS_PATH
    if _ACTIVE_MODELS_PATH is None:
        _ACTIVE_MODELS_PATH = _models_dir() / "active_models.json"
    return _ACTIVE_MODELS_PATH


def _load_active_models_config():
    path = _active_models_config_path()
    if path.exists():
        try:
            with open(path) as f:
                _ACTIVE_MODELS.update(json.load(f))
        except Exception as exc:
            logger.warning(f"Failed to load active models config: {exc}")


def _save_active_models_config():
    path = _active_models_config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(_ACTIVE_MODELS, f, indent=2)
    except Exception as exc:
        logger.warning(f"Failed to save active models config: {exc}")


def get_active_model_version(name: str) -> Optional[str]:
    _load_active_models_config()
    return _ACTIVE_MODELS.get(name)


def set_active_model_version(name: str, version: Optional[str]):
    if version is None:
        _ACTIVE_MODELS.pop(name, None)
    else:
        _ACTIVE_MODELS[name] = version
    _save_active_models_config()
    _MODELS.pop(name, None)
    _LOAD_TIMES.pop(name, None)


def get_active_models_config() -> dict:
    _load_active_models_config()
    return dict(_ACTIVE_MODELS)


def _model_path(name: str) -> Path:
    base = _models_dir() / f"{name}.pkl"
    version = get_active_model_version(name)
    if version:
        versioned = _models_dir() / f"{name}_{version}.pkl"
        if versioned.exists():
            return versioned
        logger.info(f"Versioned model {versioned} not found, falling back to {base}")
    return base


def _restore_model_from_db(name: str) -> bool:
    """Restore model files from the ModelArtifact DB table if they don't exist on disk."""
    try:
        from app.db.session import SessionLocal
        from app.db.models.core import ModelArtifact
        db = SessionLocal()
        try:
            artifact = db.query(ModelArtifact).filter(ModelArtifact.name == name).first()
            if artifact is None:
                return False
            model_dir = _models_dir()
            model_dir.mkdir(parents=True, exist_ok=True)
            pkl_path = model_dir / f"{name}.pkl"
            with open(pkl_path, "wb") as f:
                f.write(base64.b64decode(artifact.data))
            if artifact.meta:
                meta_path = model_dir / f"{name}_meta.json"
                with open(meta_path, "w") as f:
                    f.write(artifact.meta)
            logger.info(f"Restored model '{name}' from database to {pkl_path}")
            return True
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Failed to restore model '{name}' from DB: {exc}")
        return False


def _save_model_to_db(name: str, data: bytes, meta_json: Optional[str] = None) -> None:
    """Persist model binary to the ModelArtifact DB table so it survives redeploys."""
    try:
        from app.db.session import SessionLocal
        from app.db.models.core import ModelArtifact
        db = SessionLocal()
        try:
            artifact = db.query(ModelArtifact).filter(ModelArtifact.name == name).first()
            b64_data = base64.b64encode(data).decode("ascii")
            if artifact:
                artifact.data = b64_data
                if meta_json:
                    artifact.meta = meta_json
            else:
                artifact = ModelArtifact(name=name, data=b64_data, meta=meta_json)
                db.add(artifact)
            db.commit()
            logger.info(f"Saved model '{name}' to database ({len(data)} bytes)")
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Failed to save model '{name}' to DB: {exc}")


def _load_model(name: str) -> Any:
    path = _model_path(name)
    meta = _meta_path(name)
    now = datetime.now(UTC).timestamp()

    if name in _MODELS:
        last = _LOAD_TIMES.get(name, 0)
        if path.stat().st_mtime <= last:
            return _MODELS[name]

    if not path.exists():
        logger.warning(f"Model file not found: {path}, trying DB restore...")
        if _restore_model_from_db(name):
            # retry after restore
            if path.exists():
                logger.info(f"Model '{name}' restored from DB, loading...")
            else:
                _MODELS[name] = None
                _META_CACHE[name] = {}
                return None
        else:
            _MODELS[name] = None
            _META_CACHE[name] = {}
            return None

    try:
        model = joblib.load(path)
        _MODELS[name] = model
        _LOAD_TIMES[name] = now

        if meta.exists():
            with open(meta) as f:
                _META_CACHE[name] = json.load(f)
        else:
            _META_CACHE[name] = {}

        logger.info(f"Loaded model {name} from {path}")
        return model
    except Exception as exc:
        logger.warning(f"Unable to load model {name}: {exc}")
        _MODELS[name] = None
        return None


def _build_feature_df(data: dict, numeric_features: list[str]) -> pd.DataFrame:
    row = {}
    for feat in numeric_features:
        row[feat] = float(data.get(feat, 0.0) or 0.0)
    for cat in CAT_FEATURES:
        val = data.get(cat, "Unknown")
        dummies = pd.get_dummies(pd.Series([val]), prefix=cat)
        for col in dummies.columns:
            row[col] = int(dummies.iloc[0][col])
    return pd.DataFrame([row])


def _reindex_to_model(df: pd.DataFrame, model: Any) -> pd.DataFrame:
    expected = getattr(model, "feature_names_in_", None)
    if expected is not None:
        for col in expected:
            if col not in df.columns:
                df[col] = 0
        df = df[list(expected)]
    return df


def _heuristic_delay(project_data: dict) -> float:
    score = 0.05
    score += min(0.35, float(project_data.get("weather_delay_days", 0)) * 0.05)
    score += min(0.25, (1.0 - float(project_data.get("resource_availability", 0.5))) * 0.35)
    score += min(0.25, (1.0 - float(project_data.get("workforce_attendance", 0.8))) * 0.35)
    score += min(0.20, float(project_data.get("supply_delay_days", 0)) * 0.05)
    if float(project_data.get("completion_percentage", 100)) < 30 and \
       float(project_data.get("daily_progress_rate", 1)) < 0.5:
        score += 0.15
    if float(project_data.get("safety_incidents", 0)) > 3:
        score += 0.10
    return min(1.0, score)


def _heuristic_budget_overrun(project_data: dict) -> float:
    spent = float(project_data.get("budget_spent", 0))
    allocated = float(project_data.get("budget_allocated", 1))
    if allocated <= 0:
        allocated = 1
    trend = min(1.0, spent / allocated)
    score = 0.2 + 0.4 * trend
    score += 0.15 if float(project_data.get("weather_delay_days", 0)) > 5 else 0.0
    score += 0.15 if float(project_data.get("safety_incidents", 0)) > 2 else 0.0
    return min(1.0, score)


def _heuristic_risk(project_data: dict, delay_prob: float = 0.0) -> str:
    budget_prob = _heuristic_budget_overrun(project_data)
    score = delay_prob + budget_prob
    if score > 1.2:
        return "high"
    if score > 0.7:
        return "medium"
    return "low"


def predict_delay(data: dict) -> dict:
    model = _load_model("delay_model")
    if model is None:
        prob = _heuristic_delay(data)
        return {"delay_risk": round(prob, 4), "model_version": "heuristic", "will_delay": prob > 0.5}

    raw = _build_feature_df(data, _DELAY_FEATURES)
    X = _reindex_to_model(raw, model)

    try:
        prob = float(model.predict_proba(X)[0][1])
    except Exception as exc:
        logger.warning(f"Delay model prediction failed: {exc}")
        prob = _heuristic_delay(data)
        return {"delay_risk": round(prob, 4), "model_version": "heuristic", "will_delay": prob > 0.5}

    meta = _META_CACHE.get("delay_model", {})
    return {
        "delay_risk": round(prob, 4),
        "model_version": meta.get("version", "v1.0"),
        "will_delay": prob > 0.5,
    }


def predict_budget_overrun(data: dict) -> dict:
    model = _load_model("budget_model")
    if model is None:
        prob = _heuristic_budget_overrun(data)
        return {"overrun_probability": round(prob, 4), "model_version": "heuristic"}

    raw = _build_feature_df(data, _BUDGET_FEATURES)
    X = _reindex_to_model(raw, model)

    try:
        raw_pred = float(model.predict(X)[0])
        prob = min(1.0, max(0.0, raw_pred / 30.0))
    except Exception as exc:
        logger.warning(f"Budget model prediction failed: {exc}")
        prob = _heuristic_budget_overrun(data)
        return {"overrun_probability": round(prob, 4), "model_version": "heuristic"}

    meta = _META_CACHE.get("budget_model", {})
    return {
        "overrun_probability": round(prob, 4),
        "model_version": meta.get("version", "v1.0"),
    }


def predict_risk(data: dict) -> dict:
    model = _load_model("risk_classifier")
    if model is None:
        delay_prob = data.get("_delay_prob", 0.0)
        label = _heuristic_risk(data, delay_prob)
        return {"risk_level": label, "model_version": "heuristic", "risk_probabilities": {}}

    raw = _build_feature_df(data, _RISK_FEATURES)
    X = _reindex_to_model(raw, model)

    try:
        probs = model.predict_proba(X)[0]
        classes = getattr(model, "classes_", [0, 1, 2])
        le_path = _label_encoder_path("risk_classifier")
        if le_path.exists():
            le = joblib.load(le_path)
            label = le.inverse_transform([int(np.argmax(probs))])[0]
        else:
            label = str(classes[int(np.argmax(probs))])
        prob_dist = {str(c): float(p) for c, p in zip(classes, probs)}
    except Exception as exc:
        logger.warning(f"Risk model prediction failed: {exc}")
        delay_prob = data.get("_delay_prob", 0.0)
        label = _heuristic_risk(data, delay_prob)
        return {"risk_level": label, "model_version": "heuristic", "risk_probabilities": {}}

    meta = _META_CACHE.get("risk_classifier", {})
    return {
        "risk_level": label,
        "model_version": meta.get("version", "v1.0"),
        "risk_probabilities": prob_dist,
    }


def log_prediction(data: dict, result: dict, project_id: Optional[int] = None, company_id: Optional[int] = None):
    try:
        from app.db.session import SessionLocal
        from app.db.models.core import DelayPrediction

        session = SessionLocal()
        try:
            record = DelayPrediction(
                project_id=project_id,
                company_id=company_id,
                features_json={k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))},
                delay_risk=result.get("delay_risk", 0.0),
                will_delay=result.get("will_delay", False),
                model_version=result.get("model_version", "v0"),
            )
            session.add(record)
            session.commit()
        except Exception as exc:
            logger.warning(f"Failed to log prediction: {exc}")
            session.rollback()
        finally:
            session.close()
    except Exception as exc:
        logger.warning(f"Database logging unavailable: {exc}")


def get_model_health() -> dict:
    models_info = {}
    for name in ["delay_model", "budget_model", "risk_classifier"]:
        model = _load_model(name)
        if model is None:
            models_info[name] = {
                "status": "unavailable",
                "error": "Model file not found or failed to load",
            }
            continue

        meta = _META_CACHE.get(name, {})
        info = {
            "status": "loaded",
            "version": meta.get("version", "unknown"),
            "algorithm": meta.get("algorithm", "unknown"),
            "features": meta.get("features", []),
            "model_name": meta.get("model_name", name),
            "training_date": meta.get("training_date", None),
        }

        if "best_f1" in meta:
            info["best_f1"] = meta["best_f1"]
        if "best_r2" in meta:
            info["best_r2"] = meta["best_r2"]
        if "classes" in meta:
            info["classes"] = meta["classes"]

        n_features = getattr(model, "n_features_in_", None)
        if n_features:
            info["n_features"] = n_features

        models_info[name] = info

    return {
        "status": "healthy" if any(
            v.get("status") == "loaded" for v in models_info.values()
        ) else "unhealthy",
        "models": models_info,
    }


def extract_project_data(project) -> dict:
    data = {}
    for feat in _DELAY_FEATURES:
        data[feat] = getattr(project, feat, 0.0)
    data["project_type"] = getattr(project, "project_type", "Unknown")
    data["state"] = getattr(project, "state", "Unknown")
    return data


def extract_quickpredict_data(payload) -> dict:
    data = {}
    for feat in ["budget_allocated", "budget_spent", "workforce_count", "equipment_count",
                 "material_cost", "completion_percentage", "weather_delay_days",
                 "safety_incidents", "inspection_score", "task_completion_rate",
                 "daily_progress_rate"]:
        data[feat] = getattr(payload, feat, 0.0)
    data["resource_availability"] = 0.8
    data["workforce_attendance"] = 0.85
    data["supply_delay_days"] = 0
    data["rainfall_mm"] = 0
    data["project_type"] = "Building"
    data["state"] = "Lagos"
    return data
