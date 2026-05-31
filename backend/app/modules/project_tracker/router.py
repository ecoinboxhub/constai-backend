from app.modules.project_tracker.schemas import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    DashboardMetricsResponse,
    PredictionResponse,
    WeatherResponse,
    DelayPredictionRequest,
    DelayPredictionResponse,
    AIChatRequest,
    AIChatResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    DocumentUploadResponse,
    QuickPredictRequest,
    QuickPredictResponse,
)
from app.modules.project_tracker.service import (
    list_projects,
    get_project_by_id,
    create_project,
    update_project,
    delete_project,
    get_dashboard_metrics,
    get_project_predictions,
    chat_insight,
    rag_query,
    upload_project_document,
    get_weather_for_city,
    predict_delay,
    quick_predict,
)

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from app.core.security import decode_token

router = APIRouter()

@router.get("/projects", response_model=list[ProjectResponse])
def get_projects_endpoint(token: dict = Depends(decode_token)):
    return list_projects(company_id=token.get("company_id"))

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_endpoint(project_id: int, token: dict = Depends(decode_token)):
    project = get_project_by_id(project_id, company_id=token.get("company_id"))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/projects", response_model=ProjectResponse, status_code=201)
def create_project_endpoint(payload: ProjectCreate, token: dict = Depends(decode_token)):
    return create_project(payload, company_id=token.get("company_id"))

@router.put("/projects/{project_id}", response_model=ProjectResponse)
def update_project_endpoint(project_id: int, payload: ProjectUpdate, token: dict = Depends(decode_token)):
    return update_project(project_id, token.get("company_id"), payload)

@router.delete("/projects/{project_id}")
def delete_project_endpoint(project_id: int, token: dict = Depends(decode_token)):
    delete_project(project_id, token.get("company_id"))
    return {"detail": "Project deleted"}

@router.get("/analytics", response_model=DashboardMetricsResponse)
def analytics_endpoint(token: dict = Depends(decode_token)):
    return get_dashboard_metrics(company_id=token.get("company_id"))

@router.get("/predictions/{project_id}", response_model=PredictionResponse)
async def predictions_endpoint(project_id: int, token: dict = Depends(decode_token)):
    return await get_project_predictions(project_id, company_id=token.get("company_id"))

@router.post("/chat", response_model=AIChatResponse)
async def chat_endpoint(payload: AIChatRequest, token: dict = Depends(decode_token)):
    return await chat_insight(payload, company_id=token.get("company_id"))

@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query_endpoint(payload: RAGQueryRequest, token: dict = Depends(decode_token)):
    return await rag_query(payload, company_id=token.get("company_id"))

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document_endpoint(
    project_id: int = Query(...),
    file: UploadFile = File(...),
    token: dict = Depends(decode_token)
):
    return await upload_project_document(project_id, token.get("company_id"), file)

@router.get("/weather/{city}", response_model=WeatherResponse)
def get_weather_endpoint(city: str):
    # Weather is global, no company_id needed
    return get_weather_for_city(city)

@router.post("/predict-delay", response_model=DelayPredictionResponse)
def predict_delay_endpoint(payload: DelayPredictionRequest):
    return predict_delay(payload)

@router.post("/quick-predict", response_model=QuickPredictResponse)
async def quick_predict_endpoint(payload: QuickPredictRequest):
    return await quick_predict(payload)
