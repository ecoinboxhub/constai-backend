from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_external_deps():
    with patch("app.modules.project_tracker.service._get_redis") as mock_redis:
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        with patch("app.modules.project_tracker.service.model_predict_delay") as mock_delay:
            mock_delay.return_value = {"delay_risk": 0.3, "will_delay": False, "model_version": "v0"}

            with patch("app.modules.project_tracker.service.model_predict_budget") as mock_budget:
                mock_budget.return_value = {"overrun_probability": 0.2, "model_version": "v0"}

                with patch("app.modules.project_tracker.service.model_predict_risk") as mock_risk:
                    mock_risk.return_value = {"risk_level": "low", "model_version": "v0"}

                    with patch("app.modules.project_tracker.service.get_live_weather") as mock_weather:
                        mock_weather.return_value = {
                            "temperature_c": 28.0,
                            "condition": "Clear",
                            "humidity_pct": 65,
                            "rainfall_mm": 0.0,
                            "wind_speed_kmh": 10.0,
                            "pressure_hpa": 1013,
                        }

                        with patch("app.modules.project_tracker.service.log_prediction"):
                            yield


PROJECT_PAYLOAD = {
    "name": "Test Highway Project",
    "contractor_name": "Test Contractor Ltd",
    "location": "Lagos",
    "state": "Lagos",
    "lga": "Ikeja",
    "project_type": "Road Construction",
    "start_date": "2024-01-15",
    "expected_end_date": "2024-12-20",
    "budget_allocated": 50000000.0,
    "budget_spent": 10000000.0,
    "workforce_count": 80,
    "equipment_count": 15,
    "material_cost": 20000000.0,
    "completion_percentage": 25.0,
    "weather_delay_days": 3,
    "safety_incidents": 1,
    "inspection_score": 78.0,
    "task_completion_rate": 0.65,
    "daily_progress_rate": 0.8,
    "delay_status": "on_time",
    "risk_level": "medium",
    "project_status": "active"
}


def test_create_project(auth_headers, client):
    resp = client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == PROJECT_PAYLOAD["name"]
    assert "id" in data


def test_list_projects(auth_headers, client):
    client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    resp = client.get("/api/v1/project-tracker/projects", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == PROJECT_PAYLOAD["name"]


def test_get_project(auth_headers, client):
    create_resp = client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/project-tracker/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == project_id


def test_get_project_not_found(auth_headers, client):
    resp = client.get("/api/v1/project-tracker/projects/99999", headers=auth_headers)
    assert resp.status_code == 404


def test_update_project(auth_headers, client):
    create_resp = client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]
    resp = client.put(
        f"/api/v1/project-tracker/projects/{project_id}",
        json={"name": "Updated Project Name"},
        headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated Project Name"


def test_delete_project(auth_headers, client):
    create_resp = client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]
    resp = client.delete(f"/api/v1/project-tracker/projects/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Project deleted"
    get_resp = client.get(f"/api/v1/project-tracker/projects/{project_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_dashboard_metrics(auth_headers, client):
    client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    resp = client.get("/api/v1/project-tracker/analytics", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_projects"] >= 1
    assert "average_completion" in data


def test_predictions(auth_headers, client):
    create_resp = client.post("/api/v1/project-tracker/projects", json=PROJECT_PAYLOAD, headers=auth_headers)
    project_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/project-tracker/predictions/{project_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["project_id"] == project_id
    assert "delay_probability" in data
