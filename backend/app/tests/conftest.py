import os
import sys
from datetime import date
from pathlib import Path
import uuid as _uuid

os.environ["DATABASE_URL"] = "sqlite:///./test_constai.db"
os.environ["REDIS_URL"] = ""
os.environ["CELERY_BROKER_URL"] = ""
os.environ["GEMINI_API_KEY"] = ""
os.environ["GROQ_API_KEY"] = ""
os.environ["OPENROUTER_API_KEY"] = ""
os.environ["OPENWEATHER_API_KEY"] = ""
os.environ["TERMII_API_KEY"] = ""
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DEBUG"] = "false"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.core import User, Company, Project

test_db_path = Path(__file__).resolve().parents[1] / "test_constai.db"
test_db_url = f"sqlite:///{test_db_path}"
settings.database_url = test_db_url
settings.redis_url = ""
settings.openweather_api_key = ""
settings.gemini_api_key = ""
settings.groq_api_key = ""
settings.openrouter_api_key = ""

# Reset redis singleton so it re-reads the empty redis_url
import app.services.redis_service as rs_mod
rs_mod._redis_instance = None

engine = create_engine(
    test_db_url,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import app.db.session as db_session_module
db_session_module._engine = engine
db_session_module._SessionLocal = TestSessionLocal
db_session_module.SessionLocal = TestSessionLocal

from app.db.session import Base


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        test_db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(scope="function", autouse=True)
def refresh_db():
    for table in reversed(Base.metadata.sorted_tables):
        with engine.connect() as conn:
            conn.execute(table.delete())
            conn.commit()


@pytest.fixture(scope="function")
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client():
    from app.main import app, ensure_db_initialized

    original_ensure = ensure_db_initialized

    def noop_db_init():
        pass

    import app.main as main_module
    main_module.ensure_db_initialized = noop_db_init
    main_module._db_initialized = True
    main_module._db_init_attempted = True

    with TestClient(app) as test_client:
        yield test_client

    main_module.ensure_db_initialized = original_ensure
    main_module._db_initialized = False
    main_module._db_init_attempted = False


@pytest.fixture(scope="function")
def test_company(db_session):
    company = Company(
        name=f"Test Construction Co {_uuid.uuid4().hex[:8]}",
        industry="Construction",
        base_currency="NGN",
        contact_email="test@construction.com",
    )
    db_session.add(company)
    db_session.commit()
    return company


@pytest.fixture(scope="function")
def test_user(db_session, test_company):
    from app.core.security import get_password_hash
    user = User(
        username=f"testuser_{_uuid.uuid4().hex[:8]}@test.com",
        hashed_password=get_password_hash("testpassword123"),
        role="admin",
        company_id=test_company.id,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    from app.core.security import create_access_token
    token = create_access_token(
        subject=str(test_user.id),
        role=test_user.role,
        company_id=test_user.company_id,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_project(db_session, test_user):
    project = Project(
        name=f"Test Project {_uuid.uuid4().hex[:8]}",
        contractor_name="Test Contractor",
        location="Lagos",
        state="Lagos",
        lga="Ikeja",
        project_type="Building",
        start_date=date(2024, 1, 1),
        expected_end_date=date(2024, 12, 31),
        budget_allocated=10000000.0,
        budget_spent=2000000.0,
        workforce_count=50,
        equipment_count=10,
        material_cost=500000.0,
        completion_percentage=20.0,
        weather_delay_days=0,
        safety_incidents=0,
        inspection_score=95.0,
        task_completion_rate=0.8,
        daily_progress_rate=1.5,
        delay_status="on_time",
        risk_level="low",
        project_status="active",
        company_id=test_user.company_id,
    )
    db_session.add(project)
    db_session.commit()
    return project