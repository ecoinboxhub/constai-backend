from fastapi import APIRouter, Depends
from app.core.security import decode_token

router = APIRouter()

@router.get("")
def get_dashboard():
    return {"status": "success", "detail": "Dashboard data"}


@router.get("/stats")
def get_dashboard_stats(token: dict = Depends(decode_token)):
    from app.modules.project_tracker.service import get_dashboard_metrics
    from app.modules.project_tracker.schemas import DashboardMetricsResponse

    metrics: DashboardMetricsResponse = get_dashboard_metrics(company_id=token.get("company_id"))
    return {
        "active_projects": metrics.active_projects,
        "on_schedule": metrics.active_projects - metrics.delayed_projects,
        "at_risk": metrics.delayed_projects,
        "completed": metrics.completed_projects,
    }
