from fastapi import APIRouter, HTTPException, status, Depends
from app.modules.auth.schemas import Token, UserCreate, UserLogin, UserResponse, SocialSyncCreate, OTPRequest, OTPVerify
from app.modules.auth.service import authenticate_user, create_tokens, register_user, request_otp_service, verify_otp_service
from app.core.security import bearer, refresh_access_token
from fastapi.security import HTTPAuthorizationCredentials
from typing import Annotated

router = APIRouter()

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
