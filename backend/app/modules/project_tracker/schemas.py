from datetime import UTC, date, datetime
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ProjectBase(BaseModel):
    name: str
    contractor_name: str
    location: str
    state: Optional[str] = None
    lga: Optional[str] = None
    project_type: str
    start_date: date
    expected_end_date: date
    budget_allocated: float = Field(ge=0)
    budget_spent: Optional[float] = Field(default=None, ge=0)
    workforce_count: int = Field(ge=0)
    equipment_count: int = Field(ge=0)
    material_cost: float = Field(ge=0)
    completion_percentage: float = Field(ge=0, le=100)
    weather_delay_days: int = Field(ge=0)
    safety_incidents: int = Field(ge=0)
    inspection_score: float = Field(ge=0, le=100)
    task_completion_rate: float = Field(ge=0, le=1)
    daily_progress_rate: float = Field(ge=0, le=100)
    delay_status: str
    risk_level: str
    project_status: str
    company_id: Optional[int] = None
    actual_end_date: Optional[date] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    contractor_name: Optional[str] = None
    location: Optional[str] = None
    project_type: Optional[str] = None
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None
    budget_allocated: Optional[float] = Field(default=None, ge=0)
    budget_spent: Optional[float] = Field(default=None, ge=0)
    workforce_count: Optional[int] = Field(default=None, ge=0)
    equipment_count: Optional[int] = Field(default=None, ge=0)
    material_cost: Optional[float] = Field(default=None, ge=0)
    completion_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    weather_delay_days: Optional[int] = Field(default=None, ge=0)
    safety_incidents: Optional[int] = Field(default=None, ge=0)
    inspection_score: Optional[float] = Field(default=None, ge=0, le=100)
    task_completion_rate: Optional[float] = Field(default=None, ge=0, le=1)
    daily_progress_rate: Optional[float] = Field(default=None, ge=0, le=100)
    delay_status: Optional[str] = None
    risk_level: Optional[str] = None
    project_status: Optional[str] = None
    actual_end_date: Optional[date] = None

class ProjectResponse(ProjectBase):
    id: int
    start_date: Optional[date] = None
    expected_end_date: Optional[date] = None

class DashboardMetricsResponse(BaseModel):
    total_projects: int
    active_projects: int
    delayed_projects: int
    completed_projects: int
    average_completion: float
    average_budget_utilization: float
    delay_probability: float
    risk_score: float
    active_issues: int
    productivity_index: float

class WeatherResponse(BaseModel):
    city: str
    temperature_c: float
    condition: str
    description: Optional[str] = None
    humidity_pct: int
    rainfall_mm: float
    pressure_hpa: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    fetched_at: Optional[float] = None
    source: Optional[str] = None
    severe_alert: Optional[str] = None

class PredictionResponse(BaseModel):
    project_id: int
    delay_probability: float
    budget_overrun_probability: float
    risk_classification: str
    estimated_completion_date: Optional[date]
    completion_forecast: float
    cost_trend: float
    weather_context: Optional[WeatherResponse] = None

class DelayPredictionRequest(BaseModel):
    rainfall_mm: float = Field(ge=0)
    resource_availability: float = Field(ge=0, le=1)
    workforce_attendance: float = Field(ge=0, le=1)
    supply_delay_days: int = Field(ge=0)
    city: Optional[str] = None
    temperature_c: Optional[float] = Field(default=None, ge=-50, le=60)
    wind_speed_kmh: Optional[float] = Field(default=None, ge=0)

class DelayPredictionResponse(BaseModel):
    delay_risk: float
    advisory: str
    estimated_delay_days: int

class AIChatRequest(BaseModel):
    message: str

class AIChatResponse(BaseModel):
    response: str
    formatted_response: Optional[str] = None  # Well-structured markdown response
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    project_context: Optional[Dict[str, Any]] = None

class RAGQueryRequest(BaseModel):
    project_id: int
    question: str

class RAGQueryResponse(BaseModel):
    answer: str
    formatted_answer: Optional[str] = None  # Well-structured markdown response
    sources: Optional[List[str]] = None
    source_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

class DocumentUploadResponse(BaseModel):
    project_id: int
    file_name: str
    indexed_chunks: int
    message: str

class QuickPredictRequest(BaseModel):
    budget_allocated: float = Field(ge=0)
    budget_spent: float = Field(ge=0)
    workforce_count: int = Field(ge=0)
    equipment_count: int = Field(ge=0)
    material_cost: float = Field(ge=0)
    completion_percentage: float = Field(ge=0, le=100)
    weather_delay_days: int = Field(ge=0)
    safety_incidents: int = Field(ge=0)
    inspection_score: float = Field(ge=0, le=100)
    task_completion_rate: float = Field(ge=0, le=1)
    daily_progress_rate: float = Field(ge=0, le=100)

class QuickPredictResponse(BaseModel):
    delay_probability: float
    risk_level: str
    advisory: str
    key_risk_factors: List[str]
