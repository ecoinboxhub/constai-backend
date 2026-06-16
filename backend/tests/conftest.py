import os

os.environ["DATABASE_URL"] = "sqlite:///./test_constai.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base
from app.main import app
from app.core.config import settings
from app.db import session as db_session

TEST_DATABASE_URL = "sqlite:///./test_constai.db"
settings.database_url = TEST_DATABASE_URL

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_session._engine = engine
db_session._SessionLocal = TestingSessionLocal


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def auth_headers(client):
    client.post("/api/v1/auth/setup-initial-admin", json={
        "email": "admin@test.com",
        "password": "testpassword123",
        "company_name": "Test Company"
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "testpassword123"
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
