from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str = Field(min_length=8)
    role: str = "admin"  # First user is admin for the company
    company_name: str
    company_industry: Optional[str] = "Construction"

class SocialSyncCreate(UserBase):
    supabase_id: str
    provider: str
    role: str = "analyst"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    role: str
    is_active: bool = True

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class OTPRequest(BaseModel):
    phone_number: str = Field(..., description="Phone number starting with international prefix, e.g., +234...")


class OTPVerify(BaseModel):
    phone_number: str
    code: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)

