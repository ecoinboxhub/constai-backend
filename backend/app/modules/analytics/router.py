from fastapi import APIRouter, Depends
from app.modules.project_tracker.service import get_dashboard_metrics
from app.core.security import decode_token

router = APIRouter()

@router.get("")
def get_analytics(token: dict = Depends(decode_token)):
    return get_dashboard_metrics(company_id=token.get("company_id"))
