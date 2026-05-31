import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base
from app.modules.auth.service import create_tokens

# 1. Setup isolated memory SQLite database for regression tests
TEST_DATABASE_URL = "sqlite:///./test_sync.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def get_test_auth_headers():
    # Issue a mock token for company_id = 1, role = admin
    tokens = create_tokens(user_id="1", role="admin", company_id=1)
    return {"Authorization": f"Bearer {tokens.access_token}"}

def test_sync_reconcile_idempotency():
    client = TestClient(app)
    headers = get_test_auth_headers()

    # Define simple mock project entity insert payload matching ReconcileItem schema
    payload = {
        "client_uuid": "test-uuid-project-101",
        "table_name": "projects",
        "action": "INSERT",
        "payload": {
            "id": 8801,
            "name": "Integration Test Road Site",
            "contractor_name": "Julius Berger",
            "location": "Abuja FCT",
            "state": "Abuja",
            "lga": "Garki",
            "project_type": "Road construction",
            "project_status": "active",
            "budget_allocated": 75000000.0,
            "budget_spent": 1200000.0,
            "workforce_count": 12,
            "equipment_count": 2,
            "material_cost": 450000.0,
            "completion_percentage": 5.0,
            "weather_delay_days": 0,
            "safety_incidents": 0,
            "inspection_score": 98.0,
            "task_completion_rate": 1.0,
            "daily_progress_rate": 0.1,
            "delay_status": "on_time",
            "risk_level": "low"
        }
    }

    # First sync run
    response = client.post("/api/v1/sync/reconcile", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["client_uuid"] == "test-uuid-project-101"

    # Second run with identical client_uuid resolves successfully (idempotent write)
    response_retry = client.post("/api/v1/sync/reconcile", json=payload, headers=headers)
    assert response_retry.status_code == 200

def test_sync_reconcile_invalid_token():
    client = TestClient(app)
    payload = {
        "client_uuid": "test-uuid-project-102",
        "table_name": "projects",
        "action": "INSERT",
        "payload": {}
    }
    
    # Run sync with no auth token
    response = client.post("/api/v1/sync/reconcile", json=payload)
    assert response.status_code == 401

def test_sync_reconcile_malformed_json():
    client = TestClient(app)
    headers = get_test_auth_headers()
    
    # Post broken payload to verify validation failure
    response = client.post("/api/v1/sync/reconcile", json={"table_name": 1234}, headers=headers)
    assert response.status_code == 422

