from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ModelInfo(BaseModel):
    status: str
    version: Optional[str] = None
    algorithm: Optional[str] = None
    features: list = []
    model_name: Optional[str] = None
    training_date: Optional[str] = None
    best_f1: Optional[float] = None
    best_r2: Optional[float] = None
    classes: Optional[list] = None
    n_features: Optional[int] = None
    error: Optional[str] = None


class ModelHealthResponse(BaseModel):
    status: str
    models: dict


class TrainResult(BaseModel):
    model_name: str
    status: str
    algorithm: Optional[str] = None
    metrics: dict = {}
    message: Optional[str] = None


class TrainResponse(BaseModel):
    status: str
    dataset: str
    results: list[TrainResult]
    message: str


class PredictionRecord(BaseModel):
    id: int
    project_id: Optional[int] = None
    company_id: Optional[int] = None
    features_json: Optional[dict] = None
    delay_risk: float
    will_delay: bool
    model_version: str
    created_at: datetime


class PredictionHistoryResponse(BaseModel):
    predictions: list[PredictionRecord]
    total: int
    page: int
    page_size: int
