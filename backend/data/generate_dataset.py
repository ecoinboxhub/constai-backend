import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)
N_SAMPLES = 10000

project_types = ["Road", "Building", "Bridge", "Dam", "Pipeline", "Railway", "PowerPlant"]
states = ["Lagos", "FCT", "Rivers", "Kano", "Oyo", "Kaduna", "Enugu", "Edo", "Delta", "Abia"]
project_size_mult = {
    "Road": 1.0, "Building": 0.8, "Bridge": 1.2, "Dam": 1.5,
    "Pipeline": 1.1, "Railway": 1.3, "PowerPlant": 1.4,
}
state_delay_mod = {
    "Lagos": 0.85, "FCT": 0.90, "Rivers": 1.15, "Kano": 1.00, "Oyo": 0.95,
    "Kaduna": 0.95, "Enugu": 1.00, "Edo": 1.00, "Delta": 1.10, "Abia": 1.00,
}
state_rainfall_base = {
    "Lagos": 80, "FCT": 40, "Rivers": 120, "Kano": 15, "Oyo": 50,
    "Kaduna": 25, "Enugu": 60, "Edo": 70, "Delta": 100, "Abia": 55,
}

raw = Path(__file__).resolve().parent / "raw"
raw.mkdir(parents=True, exist_ok=True)

records = []
for i in range(N_SAMPLES):
    ptype = np.random.choice(project_types)
    state = np.random.choice(states)
    size_mult = project_size_mult[ptype]
    base_budget = np.random.uniform(20_000_000, 800_000_000) * size_mult

    budget_allocated = base_budget * np.random.uniform(0.8, 1.2)
    workforce_count = int(np.random.uniform(15, 400) * size_mult)
    equipment_count = int(np.random.uniform(2, 40) * size_mult)
    material_cost = budget_allocated * np.random.uniform(0.25, 0.55)
    inspection_score = np.clip(np.random.normal(72, 12), 0, 100)
    daily_progress_rate = np.clip(np.random.normal(1.4, 0.8), 0, 10)

    rain_base = state_rainfall_base[state]
    rainfall_mm = np.clip(np.random.exponential(rain_base), 0, 300)
    weather_delay_days = int(np.round(rainfall_mm / 40 + np.random.exponential(1)))
    weather_delay_days = max(0, weather_delay_days)

    supply_delay_days = int(np.round(
        np.random.poisson(3) + (weather_delay_days / 5) + (1.0 - inspection_score / 100) * 3
    ))
    supply_delay_days = max(0, supply_delay_days)

    resource_availability = np.clip(np.random.normal(0.72, 0.14), 0, 1)
    workforce_attendance = np.clip(np.random.normal(0.78, 0.10), 0, 1)
    safety_incidents = int(np.round(
        np.random.poisson(0.5) + max(0, (1.0 - inspection_score / 100) * 2 - 0.5)
    ))
    task_completion_rate = np.clip(np.random.normal(0.62, 0.18), 0, 1)

    completion_pct = np.clip(np.random.normal(50, 28), 0, 100)

    # -- Delay label (stronger signal) --
    z_delay = 0.0
    z_delay += 0.35 * max(0, (1.0 - resource_availability) * 2 - 0.3)
    z_delay += 0.25 * max(0, (1.0 - workforce_attendance) * 2 - 0.3)
    z_delay += 0.25 * min(1.0, weather_delay_days / 12)
    z_delay += 0.20 * min(1.0, supply_delay_days / 15)
    z_delay += 0.15 * max(0, (1.0 - task_completion_rate) * 1.5 - 0.2)
    z_delay += 0.10 * (1.0 - inspection_score / 100)
    z_delay *= state_delay_mod[state]
    z_delay += np.random.normal(0, 0.10)

    delay_prob = 1.0 / (1.0 + np.exp(-(z_delay - 0.45) * 3.5))
    delayed = int(delay_prob > 0.5)

    # -- Budget overrun label (stronger signal) --
    overrun_drivers = 0.0
    overrun_drivers += 0.30 * (weather_delay_days / 20)
    overrun_drivers += 0.25 * (supply_delay_days / 25)
    overrun_drivers += 0.20 * (1.0 - resource_availability)
    overrun_drivers += 0.15 * max(0, (1.0 - inspection_score / 100) * 1.5 - 0.2)
    overrun_drivers += 0.10 * (safety_incidents / 5)

    base_overrun = overrun_drivers * np.random.uniform(20, 45)
    if delayed:
        base_overrun += np.random.uniform(8, 20)

    budget_overrun_pct = max(0, base_overrun + np.random.normal(0, 4))
    budget_overrun_pct = min(budget_overrun_pct, 60)

    budget_spent_with_overrun = budget_allocated * (1.0 + budget_overrun_pct / 100)

    elapsed_frac = completion_pct / 100.0
    budget_spent = budget_spent_with_overrun * elapsed_frac * np.random.uniform(0.85, 1.15)
    budget_spent = min(budget_spent, budget_spent_with_overrun)
    budget_spent = max(budget_spent, 0)

    # -- Risk label (derived from delay + overrun) --
    raw_risk = delay_prob + min(1.0, budget_overrun_pct / 20)
    raw_risk += (1.0 - inspection_score / 100) * 0.25
    raw_risk += max(0, (1.0 - resource_availability) * 0.35)
    raw_risk += safety_incidents * 0.05
    if raw_risk > 1.1:
        risk_level = "high"
    elif raw_risk > 0.6:
        risk_level = "medium"
    else:
        risk_level = "low"

    duration_days = int(np.random.uniform(90, 1095))
    actual_duration = duration_days + (30 * delayed) + int(np.random.uniform(-15, 45))

    records.append({
        "budget_allocated": round(budget_allocated, 2),
        "budget_spent": round(budget_spent, 2),
        "workforce_count": workforce_count,
        "equipment_count": equipment_count,
        "material_cost": round(material_cost, 2),
        "completion_percentage": round(completion_pct, 2),
        "weather_delay_days": weather_delay_days,
        "safety_incidents": safety_incidents,
        "inspection_score": round(inspection_score, 2),
        "task_completion_rate": round(task_completion_rate, 4),
        "daily_progress_rate": round(daily_progress_rate, 4),
        "resource_availability": round(resource_availability, 4),
        "workforce_attendance": round(workforce_attendance, 4),
        "supply_delay_days": supply_delay_days,
        "rainfall_mm": round(rainfall_mm, 2),
        "project_type": ptype,
        "state": state,
        "duration_days": duration_days,
        "delayed": delayed,
        "budget_overrun_pct": round(budget_overrun_pct, 2),
        "risk_level": risk_level,
        "actual_completion_days": actual_duration,
    })

df = pd.DataFrame(records)

csv_path = raw / "construction_projects.csv"
df.to_csv(csv_path, index=False)
print(f"Generated {len(df)} records -> {csv_path}")
print(f"  delayed: {df['delayed'].mean():.1%}")
print(f"  risk_level distribution:\n{df['risk_level'].value_counts(normalize=True)}")
print(f"  budget_overrun_pct mean: {df['budget_overrun_pct'].mean():.2f}%")
print(f"  budget_overrun_pct median: {df['budget_overrun_pct'].median():.2f}%")
