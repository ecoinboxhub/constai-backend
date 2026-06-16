def test_register_user(client):
    resp = client.post("/api/v1/auth/register", json={
        "email": "newuser@test.com",
        "username": "newuser@test.com",
        "password": "testpassword123",
        "company_name": "New Company"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "admin"
    assert "id" in data


def test_register_duplicate_email(client):
    payload = {
        "email": "dup@test.com",
        "username": "dup@test.com",
        "password": "testpassword123",
        "company_name": "Company"
    }
    client.post("/api/v1/auth/register", json=payload)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 400
    assert "already exists" in resp.text


def test_login_success(client):
    client.post("/api/v1/auth/setup-initial-admin", json={
        "email": "admin@test.com",
        "password": "testpassword123",
        "company_name": "Test Co"
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "testpassword123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_password(client):
    client.post("/api/v1/auth/setup-initial-admin", json={
        "email": "admin@test.com",
        "password": "testpassword123",
        "company_name": "Test Co"
    })
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword"
    })
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "nobody@test.com",
        "password": "testpassword123"
    })
    assert resp.status_code == 401


def test_refresh_token(client):
    client.post("/api/v1/auth/setup-initial-admin", json={
        "email": "admin@test.com",
        "password": "testpassword123",
        "company_name": "Test Co"
    })
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "admin@test.com",
        "password": "testpassword123"
    })
    refresh_token = login_resp.json()["refresh_token"]
    resp = client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {refresh_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_protected_route_no_token(client):
    resp = client.get("/api/v1/project-tracker/projects")
    assert resp.status_code == 401


def test_protected_route_with_token(auth_headers, client):
    resp = client.get("/api/v1/project-tracker/projects", headers=auth_headers)
    assert resp.status_code == 200
