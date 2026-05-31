from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.db.models.core import DeviceToken

router = APIRouter()

class DeviceTokenCreate(BaseModel):
    token: str
    platform: str

@router.post("/register-token")
def register_device_token(payload: DeviceTokenCreate, token_data: dict = Depends(decode_token)):
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token subject")
    
    db = SessionLocal()
    try:
        # Check if this token is already registered
        existing = db.query(DeviceToken).filter(DeviceToken.token == payload.token).first()
        if existing:
            existing.user_id = str(user_id)
            existing.platform = payload.platform
            db.commit()
            return {"status": "success", "detail": "Token updated successfully"}
        
        new_token = DeviceToken(
            user_id=str(user_id),
            token=payload.token,
            platform=payload.platform
        )
        db.add(new_token)
        db.commit()
        return {"status": "success", "detail": "Token registered successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()
