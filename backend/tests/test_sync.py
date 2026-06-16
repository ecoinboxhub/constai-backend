def test_project_sync_insert(auth_headers, client):
    payload = {
        "client_uuid": "test-uuid-123",
        "table_name": "projects",
        "action": "INSERT",
        "payload": {
            "client_uuid": "test-uuid-123",
            "name": "Synced Project",
            "contractor_name": "Sync Contractor",
            "location": "Abuja",
            "project_type": "Building",
            "start_date": "2024-03-01",
            "expected_end_date": "2024-09-01",
            "budget_allocated": 10000000.0,
            "budget_spent": 0.0,
            "workforce_count": 30,
            "equipment_count": 5,
            "material_cost": 5000000.0,
            "completion_percentage": 0.0,
            "weather_delay_days": 0,
            "safety_incidents": 0,
            "inspection_score": 0.0,
            "task_completion_rate": 0.0,
            "daily_progress_rate": 0.0,
            "delay_status": "on_time",
            "risk_level": "low",
            "project_status": "active"
        }
    }
    resp = client.post("/api/v1/sync/reconcile", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["client_uuid"] == "test-uuid-123"
    assert "reconciled_id" in data


def test_project_sync_update_by_client_uuid(auth_headers, client):
    payload = {
        "client_uuid": "uuid-for-update",
        "table_name": "projects",
        "action": "INSERT",
        "payload": {
            "client_uuid": "uuid-for-update",
            "name": "Original Name",
            "contractor_name": "Test Contractor",
            "location": "Lagos",
            "project_type": "Road",
            "start_date": "2024-01-01",
            "expected_end_date": "2024-06-01",
            "budget_allocated": 5000000.0,
            "budget_spent": 1000000.0,
            "workforce_count": 20,
            "equipment_count": 3,
            "material_cost": 2000000.0,
            "completion_percentage": 20.0,
            "weather_delay_days": 1,
            "safety_incidents": 0,
            "inspection_score": 70.0,
            "task_completion_rate": 0.5,
            "daily_progress_rate": 1.0,
            "delay_status": "on_time",
            "risk_level": "low",
            "project_status": "active"
        }
    }
    resp1 = client.post("/api/v1/sync/reconcile", json=payload, headers=auth_headers)
    first_id = resp1.json()["reconciled_id"]

    payload["action"] = "UPDATE"
    payload["payload"]["name"] = "Updated Name"
    resp2 = client.post("/api/v1/sync/reconcile", json=payload, headers=auth_headers)
    assert resp2.json()["reconciled_id"] == first_id

    get_resp = client.get("/api/v1/project-tracker/projects", headers=auth_headers)
    projects = get_resp.json()
    names = [p["name"] for p in projects]
    assert names.count("Updated Name") == 1


def test_workforce_sync_insert(auth_headers, client):
    proj_resp = client.post("/api/v1/project-tracker/projects", json={
        "name": "Workforce Test Project",
        "contractor_name": "Test Co",
        "location": "Lagos",
        "project_type": "Building",
        "start_date": "2024-01-01",
        "expected_end_date": "2024-06-01",
        "budget_allocated": 1000000.0,
        "budget_spent": 0.0,
        "workforce_count": 10,
        "equipment_count": 2,
        "material_cost": 500000.0,
        "completion_percentage": 0.0,
        "weather_delay_days": 0,
        "safety_incidents": 0,
        "inspection_score": 0.0,
        "task_completion_rate": 0.0,
        "daily_progress_rate": 0.0,
        "delay_status": "on_time",
        "risk_level": "low",
        "project_status": "active"
    }, headers=auth_headers)
    project_id = proj_resp.json()["id"]

    payload = {
        "client_uuid": "workforce-uuid-1",
        "table_name": "workforce",
        "action": "INSERT",
        "payload": {
            "client_uuid": "workforce-uuid-1",
            "first_name": "John",
            "last_name": "Doe",
            "role": "Engineer",
            "skills": "Civil Engineering",
            "is_active": True,
            "project_id": project_id
        }
    }
    resp = client.post("/api/v1/sync/reconcile", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["client_uuid"] == "workforce-uuid-1"


def test_sync_invalid_table(auth_headers, client):
    payload = {
        "client_uuid": "test-uuid",
        "table_name": "nonexistent_table",
        "action": "INSERT",
        "payload": {"some": "data"}
    }
    resp = client.post("/api/v1/sync/reconcile", json=payload, headers=auth_headers)
    assert resp.status_code == 400


def test_sync_no_auth(client):
    payload = {
        "client_uuid": "test-uuid",
        "table_name": "projects",
        "action": "INSERT",
        "payload": {"name": "Test"}
    }
    resp = client.post("/api/v1/sync/reconcile", json=payload)
    assert resp.status_code == 401
