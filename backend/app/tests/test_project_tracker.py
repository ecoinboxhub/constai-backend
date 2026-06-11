import pytest
from fastapi import status
from datetime import date

BASE = "/api/v1/project-tracker"


class TestListProjects:
    def test_list_projects_empty(self, client, auth_headers):
        response = client.get(f"{BASE}/projects", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_list_projects_with_data(self, client, auth_headers, test_project):
        response = client.get(f"{BASE}/projects", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == test_project.name

    def test_list_projects_unauthorized(self, client):
        response = client.get(f"{BASE}/projects")
        assert response.status_code == 401


class TestCreateProject:
    def test_create_project_success(self, client, auth_headers):
        payload = {
            "name": "New Project",
            "contractor_name": "New Contractor",
            "location": "Abuja",
            "state": "FCT",
            "lga": "Municipal",
            "project_type": "Road",
            "start_date": "2024-06-01",
            "expected_end_date": "2025-06-01",
            "budget_allocated": 50000000.0,
            "budget_spent": 5000000.0,
            "workforce_count": 30,
            "equipment_count": 5,
            "material_cost": 2000000.0,
            "completion_percentage": 10.0,
            "weather_delay_days": 0,
            "safety_incidents": 0,
            "inspection_score": 90.0,
            "task_completion_rate": 0.7,
            "daily_progress_rate": 1.0,
            "delay_status": "on_time",
            "risk_level": "low",
            "project_status": "active",
        }
        response = client.post(f"{BASE}/projects", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Project"
        assert data["project_type"] == "Road"
        assert data["company_id"] is not None

    def test_create_project_missing_required(self, client, auth_headers):
        payload = {"name": "Incomplete Project"}
        response = client.post(f"{BASE}/projects", json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_create_project_unauthorized(self, client):
        payload = {
            "name": "Unauthorized Project",
            "contractor_name": "N/A",
            "location": "N/A",
            "project_type": "N/A",
            "start_date": "2024-01-01",
            "expected_end_date": "2024-12-31",
            "budget_allocated": 1000.0,
            "workforce_count": 1,
            "equipment_count": 0,
            "material_cost": 0.0,
            "completion_percentage": 0.0,
            "weather_delay_days": 0,
            "safety_incidents": 0,
            "inspection_score": 0.0,
            "task_completion_rate": 0.0,
            "daily_progress_rate": 0.0,
            "delay_status": "on_time",
            "risk_level": "low",
            "project_status": "active",
        }
        response = client.post(f"{BASE}/projects", json=payload)
        assert response.status_code == 401


class TestGetProject:
    def test_get_project_success(self, client, auth_headers, test_project):
        response = client.get(f"{BASE}/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == test_project.name

    def test_get_project_not_found(self, client, auth_headers):
        response = client.get(f"{BASE}/projects/99999", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateProject:
    def test_update_project_success(self, client, auth_headers, test_project):
        payload = {"name": "Updated Project Name", "completion_percentage": 50.0}
        response = client.put(f"{BASE}/projects/{test_project.id}", json=payload, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Project Name"
        assert response.json()["completion_percentage"] == 50.0

    def test_update_project_not_found(self, client, auth_headers):
        payload = {"name": "Ghost Project"}
        response = client.put(f"{BASE}/projects/99999", json=payload, headers=auth_headers)
        assert response.status_code == 404

    def test_update_project_invalid_field(self, client, auth_headers, test_project):
        payload = {"completion_percentage": 150}
        response = client.put(f"{BASE}/projects/{test_project.id}", json=payload, headers=auth_headers)
        assert response.status_code == 422


class TestDeleteProject:
    def test_delete_project_success(self, client, auth_headers, test_project):
        response = client.delete(f"{BASE}/projects/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        get_resp = client.get(f"{BASE}/projects/{test_project.id}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_project_not_found(self, client, auth_headers):
        response = client.delete(f"{BASE}/projects/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_project_unauthorized(self, client, test_project):
        response = client.delete(f"{BASE}/projects/{test_project.id}")
        assert response.status_code == 401


class TestDashboardAnalytics:
    def test_analytics_empty(self, client, auth_headers):
        response = client.get(f"{BASE}/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 0
        assert data["active_projects"] == 0

    def test_analytics_with_projects(self, client, auth_headers, test_project):
        response = client.get(f"{BASE}/analytics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_projects"] == 1
        assert data["active_projects"] == 1
        assert data["average_completion"] == 20.0

    def test_analytics_unauthorized(self, client):
        response = client.get(f"{BASE}/analytics")
        assert response.status_code == 401


class TestPredictions:
    def test_predictions_endpoint(self, client, auth_headers, test_project):
        response = client.get(f"{BASE}/predictions/{test_project.id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "delay_probability" in data
        assert "budget_overrun_probability" in data
        assert "risk_classification" in data

    def test_predictions_not_found(self, client, auth_headers):
        response = client.get(f"{BASE}/predictions/99999", headers=auth_headers)
        assert response.status_code == 404


class TestWeather:
    def test_weather_lagos(self, client):
        response = client.get(f"{BASE}/weather/Lagos")
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Lagos"
        assert "temperature_c" in data


class TestDelayPrediction:
    def test_predict_delay_low_risk(self, client):
        payload = {
            "rainfall_mm": 0,
            "resource_availability": 0.9,
            "workforce_attendance": 0.95,
            "supply_delay_days": 0,
            "city": "Lagos",
        }
        response = client.post(f"{BASE}/predict-delay", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["delay_risk"] < 0.4
        assert "low" in data["advisory"].lower()

    def test_predict_delay_high_risk(self, client):
        payload = {
            "rainfall_mm": 50,
            "resource_availability": 0.3,
            "workforce_attendance": 0.4,
            "supply_delay_days": 30,
            "city": "Lagos",
        }
        response = client.post(f"{BASE}/predict-delay", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["delay_risk"] > 0.4
        assert data["estimated_delay_days"] >= 0

    def test_predict_delay_invalid_input(self, client):
        payload = {"rainfall_mm": -1, "resource_availability": 2.0, "workforce_attendance": 0.5, "supply_delay_days": 0}
        response = client.post(f"{BASE}/predict-delay", json=payload)
        assert response.status_code == 422

    def test_predict_delay_no_city(self, client):
        payload = {
            "rainfall_mm": 5,
            "resource_availability": 0.7,
            "workforce_attendance": 0.8,
            "supply_delay_days": 2,
        }
        response = client.post(f"{BASE}/predict-delay", json=payload)
        assert response.status_code == 200


class TestQuickPredict:
    def test_quick_predict_success(self, client, monkeypatch):
        async def mock_ask_ai(prompt):
            return "Your project shows low delay risk. Continue monitoring."
        monkeypatch.setattr("app.modules.project_tracker.service.ask_ai", mock_ask_ai)
        payload = {
            "budget_allocated": 10000000.0,
            "budget_spent": 2000000.0,
            "workforce_count": 50,
            "equipment_count": 10,
            "material_cost": 500000.0,
            "completion_percentage": 20.0,
            "weather_delay_days": 0,
            "safety_incidents": 0,
            "inspection_score": 95.0,
            "task_completion_rate": 0.8,
            "daily_progress_rate": 1.5,
        }
        response = client.post(f"{BASE}/quick-predict", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "delay_probability" in data
        assert "risk_level" in data
        assert "advisory" in data

    def test_quick_predict_invalid(self, client):
        payload = {"budget_allocated": -100}
        response = client.post(f"{BASE}/quick-predict", json=payload)
        assert response.status_code == 422


class TestProjectUnit:
    def test_list_projects_service(self, db_session, test_project, test_user):
        from app.modules.project_tracker.service import list_projects
        projects = list_projects(company_id=test_user.company_id)
        assert len(projects) == 1
        assert projects[0].name == test_project.name

    def test_get_project_service(self, db_session, test_project, test_user):
        from app.modules.project_tracker.service import get_project_by_id
        project = get_project_by_id(test_project.id, company_id=test_user.company_id)
        assert project is not None
        assert project.name == test_project.name

    def test_get_project_not_found_service(self, db_session, test_user):
        from app.modules.project_tracker.service import get_project_by_id
        project = get_project_by_id(99999, company_id=test_user.company_id)
        assert project is None

    def test_dashboard_metrics_empty(self, db_session, test_user):
        from app.modules.project_tracker.service import get_dashboard_metrics
        metrics = get_dashboard_metrics(company_id=test_user.company_id)
        assert metrics.total_projects == 0

    def test_dashboard_metrics_with_project(self, db_session, test_project, test_user):
        from app.modules.project_tracker.service import get_dashboard_metrics
        metrics = get_dashboard_metrics(company_id=test_user.company_id)
        assert metrics.total_projects == 1
        assert metrics.active_projects == 1
        assert metrics.average_completion == 20.0

    def test_predict_delay_logic(self):
        from app.modules.project_tracker.service import predict_delay
        from app.modules.project_tracker.schemas import DelayPredictionRequest

        req = DelayPredictionRequest(
            rainfall_mm=0,
            resource_availability=0.95,
            workforce_attendance=0.95,
            supply_delay_days=0,
            city="Abuja",
        )
        result = predict_delay(req)
        assert result.delay_risk < 0.4
        assert result.estimated_delay_days >= 0

    def test_predict_delay_high_logic(self):
        from app.modules.project_tracker.service import predict_delay
        from app.modules.project_tracker.schemas import DelayPredictionRequest

        req = DelayPredictionRequest(
            rainfall_mm=100,
            resource_availability=0.2,
            workforce_attendance=0.3,
            supply_delay_days=60,
            city="Lagos",
        )
        result = predict_delay(req)
        assert result.delay_risk > 0.5
        assert result.estimated_delay_days > 0

    def test_project_to_response(self, test_project):
        from app.modules.project_tracker.service import _project_to_response
        response = _project_to_response(test_project)
        assert response.name == test_project.name
        assert response.budget_allocated == 10000000.0
        assert response.company_id == test_project.company_id

    def test_heuristic_budget_probability(self, test_project):
        from app.modules.project_tracker.service import _heuristic_budget_probability
        prob = _heuristic_budget_probability(test_project)
        assert 0.0 <= prob <= 1.0

    def test_classify_risk(self, test_project):
        from app.modules.project_tracker.service import _classify_risk
        risk = _classify_risk(test_project, delay_prob=0.2)
        assert risk in ("low", "medium", "high")