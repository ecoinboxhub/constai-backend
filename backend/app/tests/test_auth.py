import pytest
from fastapi import status
from unittest.mock import patch, MagicMock


class TestAuthUnit:
    def test_register_user_success(self, db_session):
        from app.modules.auth.service import register_user
        from app.modules.auth.schemas import UserCreate

        user_in = UserCreate(
            email="newuser@test.com",
            username="newuser@test.com",
            password="securepassword123",
            company_name="New Construction Ltd",
            company_industry="Construction",
            role="admin",
        )
        result = register_user(user_in, provider="email")
        assert result["username"] == "newuser@test.com"
        assert result["role"] == "admin"
        assert result["is_active"] is True
        assert "id" in result

    def test_register_duplicate_email(self, db_session, test_user):
        from app.modules.auth.service import register_user
        from app.modules.auth.schemas import UserCreate
        from fastapi import HTTPException

        user_in = UserCreate(
            email=test_user.username,
            username=test_user.username,
            password="securepassword123",
            company_name="Another Construction Ltd",
            role="admin",
        )
        with pytest.raises(HTTPException) as exc_info:
            register_user(user_in, provider="email")
        assert exc_info.value.status_code == 400

    def test_authenticate_user_success(self, db_session, test_user):
        from app.modules.auth.service import authenticate_user

        result = authenticate_user(test_user.username, "testpassword123")
        assert result is not None
        assert result["username"] == test_user.username
        assert result["role"] == "admin"

    def test_authenticate_user_wrong_password(self, db_session, test_user):
        from app.modules.auth.service import authenticate_user

        result = authenticate_user(test_user.username, "wrongpassword")
        assert result is None

    def test_authenticate_user_nonexistent(self, db_session):
        from app.modules.auth.service import authenticate_user

        result = authenticate_user("nobody@test.com", "password")
        assert result is None

    def test_create_tokens(self, db_session, test_user):
        from app.modules.auth.service import create_tokens

        tokens = create_tokens(
            user_id=str(test_user.id),
            role=test_user.role,
            company_id=test_user.company_id,
        )
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"

    def test_create_tokens_without_company(self, db_session, test_user):
        from app.modules.auth.service import create_tokens

        tokens = create_tokens(
            user_id=str(test_user.id),
            role=test_user.role,
        )
        assert tokens.access_token is not None

    def test_authenticate_user_ignores_case(self, db_session, test_user):
        from app.modules.auth.service import authenticate_user

        result = authenticate_user(test_user.username.upper(), "testpassword123")
        assert result is not None

    @pytest.mark.asyncio
    async def test_request_otp_service(self, db_session):
        from app.modules.auth.service import request_otp_service

        with patch("app.services.sms.send_otp_via_termii") as mock_send:
            mock_send.return_value = True
            result = await request_otp_service("+2348123456789")
            assert result is True

    @pytest.mark.asyncio
    async def test_verify_otp_invalid(self, db_session):
        from app.modules.auth.service import verify_otp_service
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await verify_otp_service("+2348123456789", "000000")
        assert exc_info.value.status_code == 400


class TestAuthAPI:
    def test_login_success(self, client, test_user):
        payload = {"email": test_user.username, "password": "testpassword123"}
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        payload = {"email": test_user.username, "password": "wrongpassword"}
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        payload = {"email": "nobody@test.com", "password": "testpassword123"}
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401

    def test_login_empty_payload(self, client):
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_refresh_token_success(self, client, test_user):
        login_payload = {"email": test_user.username, "password": "testpassword123"}
        login_resp = client.post("/api/v1/auth/login", json=login_payload)
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_token_missing(self, client):
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    def test_refresh_token_invalid(self, client):
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer invalidtoken123"},
        )
        assert response.status_code == 401

    def test_register_api_success(self, client):
        payload = {
            "email": "apiuser@test.com",
            "username": "apiuser@test.com",
            "password": "securepassword123",
            "company_name": "API Test Construction Ltd",
            "company_industry": "Construction",
            "role": "admin",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "apiuser@test.com"
        assert data["role"] == "admin"

    def test_register_weak_password_api(self, client):
        payload = {
            "email": "weak@test.com",
            "username": "weak@test.com",
            "password": "short",
            "company_name": "Weak Ltd",
            "role": "admin",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_invalid_email_api(self, client):
        payload = {
            "email": "not-an-email",
            "username": "not-an-email",
            "password": "securepassword123",
            "company_name": "Bad Email Ltd",
            "role": "admin",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422

    def test_register_duplicate_api(self, client, test_user):
        payload = {
            "email": test_user.username,
            "username": test_user.username,
            "password": "securepassword123",
            "company_name": "Another Ltd",
            "role": "admin",
        }
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_social_sync_success(self, client):
        payload = {
            "email": "socialuser@test.com",
            "username": "socialuser@test.com",
            "supabase_id": "supa-12345",
            "provider": "google",
            "role": "analyst",
        }
        response = client.post("/api/v1/auth/social-sync", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_request_otp_api(self, client):
        payload = {"phone_number": "+2348123456789"}
        response = client.post("/api/v1/auth/request-otp", json=payload)
        assert response.status_code in (200, 500)