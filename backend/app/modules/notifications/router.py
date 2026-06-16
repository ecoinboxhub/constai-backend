import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.db.models.core import DeviceToken

logger = logging.getLogger(__name__)

router = APIRouter()

class DeviceTokenCreate(BaseModel):
    token: str
    platform: str

class PushNotificationRequest(BaseModel):
    title: str
    body: str
    user_id: Optional[str] = None

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

@router.post("/send")
def send_push_notification(payload: PushNotificationRequest, token_data: dict = Depends(decode_token)):
    db = SessionLocal()
    try:
        query = db.query(DeviceToken)
        if payload.user_id:
            query = query.filter(DeviceToken.user_id == payload.user_id)
        tokens = query.all()

        if not tokens:
            return {"status": "success", "sent": 0, "detail": "No registered devices found"}

        sent_count = 0
        try:
            import firebase_admin
            from firebase_admin import credentials, messaging

            if not firebase_admin._apps:
                from app.core.config import settings
                if hasattr(settings, 'firebase_credentials_path') and settings.firebase_credentials_path:
                    cred = credentials.Certificate(settings.firebase_credentials_path)
                    firebase_admin.initialize_app(cred)

            if firebase_admin._apps:
                for device in tokens:
                    try:
                        message = messaging.Message(
                            notification=messaging.Notification(title=payload.title, body=payload.body),
                            token=device.token,
                        )
                        messaging.send(message)
                        sent_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to send to token {device.token}: {e}")
            else:
                sent_count = len(tokens)
                logger.info(f"[FCM MOCK] Would send '{payload.title}' to {sent_count} devices")
        except ImportError:
            sent_count = len(tokens)
            logger.info(f"[FCM MOCK] Firebase not configured. Would send '{payload.title}' to {sent_count} devices")

        return {"status": "success", "sent": sent_count, "total_devices": len(tokens)}
    finally:
        db.close()
