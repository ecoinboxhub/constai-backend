from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any
from app.core.security import decode_token
from app.db.session import SessionLocal
from app.modules.sync.service import reconcile_client_item
from app.db.models.core import AuditLog

router = APIRouter()


class ReconcileItem(BaseModel):
    client_uuid: str
    table_name: str
    action: str
    payload: Dict[str, Any]


@router.post("/reconcile")
def reconcile(item: ReconcileItem, token: dict = Depends(decode_token)):
    company_id = token.get("company_id")
    user_id = token.get("sub")

    if not company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User token does not contain a valid company context."
        )

    db = SessionLocal()
    try:
        result = reconcile_client_item(
            db=db,
            company_id=int(company_id),
            user_id=str(user_id),
            table_name=item.table_name,
            action=item.action.upper(),
            payload=item.payload
        )

        audit_entry = AuditLog(
            user_id=str(user_id),
            endpoint="/api/v1/sync/reconcile",
            method="POST",
            response_status=200
        )
        db.add(audit_entry)
        db.commit()

        return {
            "status": "success",
            "client_uuid": item.client_uuid,
            "reconciled_id": result.get("id"),
            "action_status": result.get("status")
        }
    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backend sync failed: {str(exc)}"
        )
    finally:
        db.close()
