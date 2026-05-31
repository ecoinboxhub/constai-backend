from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier


def pseudo_lstm_prob(x: pd.DataFrame) -> np.ndarray:
    score = (
        0.35 * (x["rainfall_mm"] > 35).astype(float)
        + 0.25 * (x["resource_availability"] < 0.75).astype(float)
        + 0.2 * (x["workforce_attendance"] < 0.8).astype(float)
        + 0.2 * (x["supply_delay_days"] > 3).astype(float)
    )
    return score.clip(0, 1).to_numpy()


def main() -> None:
    df = pd.read_csv("data/raw/project_delay.csv")
    X = df.drop(columns=["delay_label"])
    y = df["delay_label"]

    x_train, x_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    dt = DecisionTreeClassifier(max_depth=5, random_state=42)
    rf = RandomForestClassifier(n_estimators=250, max_depth=8, random_state=42)

    dt.fit(x_train, y_train)
    rf.fit(x_train, y_train)

    p_lstm = pseudo_lstm_prob(x_test)
    p_dt = dt.predict_proba(x_test)[:, 1]
    p_rf = rf.predict_proba(x_test)[:, 1]

    p_ens = (0.34 * p_lstm) + (0.26 * p_dt) + (0.40 * p_rf)
    y_pred = (p_ens >= 0.5).astype(int)

    f1 = f1_score(y_test, y_pred)

    mlflow.set_experiment("project_tracker")
    with mlflow.start_run(run_name="ensemble_baseline"):
        mlflow.log_metric("f1", float(f1))
        mlflow.log_param("models", "pseudo_lstm+dt+rf")

    model_dir = Path("artifacts/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(dt, model_dir / "project_tracker_dt.pkl")
    joblib.dump(rf, model_dir / "project_tracker_rf.pkl")

    print(f"Project Tracker F1: {f1:.4f}")


if __name__ == "__main__":
    main()
