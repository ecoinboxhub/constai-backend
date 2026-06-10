import logging
import traceback
from datetime import UTC, datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.core import User, Company
from app.modules.auth.schemas import Token, UserCreate
from app.core.security import get_password_hash, verify_password, create_access_token, create_refresh_token

logger = logging.getLogger(__name__)


def register_user(user_in: Any, provider: str = "email") -> Dict[str, Any]:
    session: Session = SessionLocal()
    try:
        email_clean = user_in.email.strip().lower()

        existing_user = session.query(User).filter(User.username == email_clean).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists."
            )

        new_company = Company(
            name=getattr(user_in, "company_name", f"{email_clean} Company"),
            industry=getattr(user_in, "company_industry", "Construction"),
            base_currency="NGN",
            contact_email=email_clean
        )
        session.add(new_company)
        session.flush()

        password = getattr(user_in, "password", None)
        hashed = get_password_hash(password) if password else "social_auth"

        new_user = User(
            username=email_clean,
            hashed_password=hashed,
            role=getattr(user_in, "role", "admin"),
            company_id=new_company.id
        )

        session.add(new_user)
        session.commit()
        session.refresh(new_user)

        return {
            "id": str(new_user.id),
            "email": new_user.username,
            "username": new_user.username,
            "role": new_user.role,
            "company_id": new_user.company_id,
            "is_active": True
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error in register_user: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    finally:
        session.close()


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    session: Session = SessionLocal()
    try:
        user = session.query(User).filter(User.username == email.lower()).first()
        if not user:
            return None

        if verify_password(password, user.hashed_password):
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "company_id": user.company_id
            }
        return None
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        return None
    finally:
        session.close()


def create_tokens(user_id: str, role: str, company_id: Optional[int] = None) -> Token:
    if company_id is None:
        session = SessionLocal()
        try:
            user = session.query(User).filter(User.id == int(user_id)).first()
            if user:
                company_id = user.company_id
        finally:
            session.close()
    access = create_access_token(subject=user_id, role=role, company_id=company_id)
    refresh = create_refresh_token(subject=user_id, role=role, company_id=company_id)
    return Token(access_token=access, refresh_token=refresh)


async def request_otp_service(phone_number: str) -> bool:
    import random
    from datetime import timedelta
    from app.db.models.core import OTPVerification
    from app.services.sms import send_otp_via_termii

    session = SessionLocal()
    try:
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        expires = datetime.now(UTC) + timedelta(minutes=5)

        session.query(OTPVerification).filter(
            OTPVerification.phone_number == phone_number,
            OTPVerification.is_verified == False
        ).update({"expires_at": datetime.now(UTC)})

        otp_rec = OTPVerification(
            phone_number=phone_number,
            code=otp_code,
            expires_at=expires
        )
        session.add(otp_rec)
        session.commit()

        success = await send_otp_via_termii(phone_number, otp_code)
        return success
    except Exception as e:
        session.rollback()
        logger.error(f"Error in request_otp_service: {e}")
        return False
    finally:
        session.close()


async def verify_otp_service(phone_number: str, code: str) -> Dict[str, Any]:
    from app.db.models.core import OTPVerification
    session = SessionLocal()
    try:
        now = datetime.now(UTC)
        otp_rec = session.query(OTPVerification).filter(
            OTPVerification.phone_number == phone_number,
            OTPVerification.code == code,
            OTPVerification.is_verified == False,
            OTPVerification.expires_at > now
        ).first()

        if not otp_rec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid, expired, or already verified OTP code."
            )

        otp_rec.is_verified = True
        session.commit()

        user = session.query(User).filter(
            (User.phone_number == phone_number) | (User.username == f"artisan_{phone_number}")
        ).first()

        if not user:
            new_company = Company(
                name=f"Artisan_{phone_number}_Company",
                industry="Construction Services",
                country="Nigeria",
                subscription_tier="free"
            )
            session.add(new_company)
            session.flush()

            user = User(
                username=f"artisan_{phone_number}",
                hashed_password=get_password_hash(code),
                role="artisan",
                company_id=new_company.id,
                phone_number=phone_number
            )
            session.add(user)
            session.commit()
            session.refresh(user)

        return {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "company_id": user.company_id
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error in verify_otp_service: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Verification transaction failure: {str(e)}"
        )
    finally:
        session.close()
