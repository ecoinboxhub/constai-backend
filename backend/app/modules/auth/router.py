from fastapi import APIRouter, HTTPException, status, Depends, Header
from pydantic import BaseModel, EmailStr, Field
from app.modules.auth.schemas import Token, UserCreate, UserLogin, UserResponse, SocialSyncCreate, OTPRequest, OTPVerify, PasswordResetRequest, PasswordReset, ChangePassword
from app.modules.auth.service import authenticate_user, create_tokens, register_user, request_otp_service, verify_otp_service, request_password_reset, reset_password, change_password, setup_initial_admin, admin_reset_password
from app.core.security import bearer, refresh_access_token, decode_token
from fastapi.security import HTTPAuthorizationCredentials
from typing import Annotated, Optional
from app.core.config import settings

router = APIRouter()

class InitialAdminSetup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    company_name: str


@router.post("/setup-initial-admin")
def setup_initial_admin_endpoint(req: InitialAdminSetup):
    return setup_initial_admin(req.email, req.password, req.company_name)


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate):
    return register_user(user_in, provider="email")

@router.post("/social-sync", response_model=Token)
def social_sync(user_in: SocialSyncCreate):
    user = register_user(user_in, provider=user_in.provider)
    return create_tokens(user_id=str(user["id"]), role=user["role"], company_id=user.get("company_id"))

@router.post("/login", response_model=Token)
def login(user_login: UserLogin):
    user = authenticate_user(user_login.email, user_login.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    return create_tokens(user_id=str(user["id"]), role=user["role"], company_id=user.get("company_id"))

@router.post("/refresh", response_model=Token)
def refresh(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]):
    if not credentials:
        raise HTTPException(status_code=401, detail="Refresh token required")
    new_access, new_refresh = refresh_access_token(credentials.credentials)
    return Token(access_token=new_access, refresh_token=new_refresh)


@router.post("/request-otp")
async def request_otp(otp_in: OTPRequest):
    success = await request_otp_service(otp_in.phone_number)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to send OTP message. Please check input phone format or try again."
        )
    return {"message": "Verification code dispatched successfully."}


@router.post("/verify-otp", response_model=Token)
async def verify_otp(otp_in: OTPVerify):
    user_payload = await verify_otp_service(otp_in.phone_number, otp_in.code)
    return create_tokens(
        user_id=str(user_payload["id"]),
        role=user_payload["role"],
        company_id=user_payload.get("company_id")
    )


@router.post("/request-password-reset")
def request_password_reset_endpoint(req: PasswordResetRequest):
    return request_password_reset(req.email)


@router.post("/reset-password")
def reset_password_endpoint(req: PasswordReset):
    return reset_password(req.token, req.new_password)


class AdminPasswordReset(BaseModel):
    email: EmailStr
    new_password: str = Field(min_length=8)


@router.post("/admin-reset-password")
def admin_reset_password_endpoint(req: AdminPasswordReset, x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    if not x_api_key or x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Valid X-API-Key header required.")
    return admin_reset_password(req.email, req.new_password)


@router.post("/change-password")
def change_password_endpoint(req: ChangePassword, token: dict = Depends(decode_token)):
    return change_password(int(token["sub"]), req.current_password, req.new_password)
