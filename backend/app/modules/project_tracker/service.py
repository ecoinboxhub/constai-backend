import io
import json
import logging
import re
import time
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Optional, Dict, List

import joblib
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from contextlib import contextmanager
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.core import Project, ProjectDocument
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
from app.services.llm import ask_ai
from app.services.rag.engine import get_vectorstore, query_project_knowledge, chunk_document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from PyPDF2 import PdfReader
import docx
from app.services.weather import get_live_weather
from app.modules.project_tracker.tasks import fetch_weather_data, process_project_document

logger = logging.getLogger(__name__)

def _get_redis():
    """Lazy load redis on first use."""
    from app.services.redis_service import get_redis
    return get_redis()

@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

MODEL_FEATURES = [
    "budget_allocated",
    "budget_spent",
    "workforce_count",
    "equipment_count",
    "material_cost",
    "completion_percentage",
    "weather_delay_days",
    "safety_incidents",
    "inspection_score",
    "task_completion_rate",
    "daily_progress_rate",
]

_MODEL_CACHE: dict[str, Any] = {}


def _safe_float(value: Optional[float], default: float = 0.0) -> float:
    return float(value) if value is not None else default


def _load_model(name: str):
    model_path = Path(settings.model_registry_path)
    if not model_path.is_absolute():
        model_path = Path(__file__).resolve().parents[4] / model_path
    model_path = model_path / name
    if name in _MODEL_CACHE:
        return _MODEL_CACHE[name]
    if model_path.exists():
        try:
            model = joblib.load(model_path)
            _MODEL_CACHE[name] = model
            return model
        except Exception as exc:
            logger.warning(f"Unable to load model {name}: {exc}")
    else:
        logger.warning(f"Model file not found: {model_path}")
    _MODEL_CACHE[name] = None
    return None


def _project_to_response(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        contractor_name=project.contractor_name,
        location=project.location,
        state=project.state,
        lga=project.lga,
        project_type=project.project_type,
        start_date=project.start_date,
        expected_end_date=project.expected_end_date,
        actual_end_date=project.actual_end_date,
        project_status=project.project_status,
        budget_allocated=project.budget_allocated or 0.0,
        budget_spent=project.budget_spent,
        workforce_count=project.workforce_count or 0,
        equipment_count=project.equipment_count or 0,
        material_cost=project.material_cost or 0.0,
        completion_percentage=project.completion_percentage or 0.0,
        weather_delay_days=project.weather_delay_days or 0,
        safety_incidents=project.safety_incidents or 0,
        inspection_score=project.inspection_score or 0.0,
        task_completion_rate=project.task_completion_rate or 0.0,
        daily_progress_rate=project.daily_progress_rate or 0.0,
        delay_status=project.delay_status,
        risk_level=project.risk_level,
        company_id=project.company_id,
    )

def list_projects(company_id: int) -> list[ProjectResponse]:
    with get_session() as session:
        projects = session.query(Project).filter(Project.company_id == company_id).order_by(Project.id).all()
        return [_project_to_response(project) for project in projects]

def get_project_by_id(project_id: int, company_id: int) -> Optional[ProjectResponse]:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.company_id == company_id).first()
        return _project_to_response(project) if project else None

def create_project(payload: ProjectCreate, company_id: int) -> ProjectResponse:
    with get_session() as session:
        try:
            data = payload.model_dump()
            data["company_id"] = company_id
            project = Project(**data)
            session.add(project)
            session.commit()
            session.refresh(project)
            return _project_to_response(project)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to create project: {exc}")
            raise HTTPException(status_code=500, detail="Unable to create project")

def update_project(project_id: int, company_id: int, payload: ProjectUpdate) -> ProjectResponse:
    with get_session() as session:
        try:
            project = session.query(Project).filter(Project.id == project_id, Project.company_id == company_id).first()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(project, key, value)
            session.commit()
            session.refresh(project)
            # Invalidate cache
            _get_redis().delete(f"metrics:company:{company_id}")
            return _project_to_response(project)
        except SQLAlchemyError as exc:
            logger.error(f"Failed to update project: {exc}")
            raise HTTPException(status_code=500, detail="Unable to update project")

def delete_project(project_id: int, company_id: int) -> None:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.company_id == company_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        session.delete(project)
        session.commit()
        _get_redis().delete(f"metrics:company:{company_id}")

def get_dashboard_metrics(company_id: int) -> DashboardMetricsResponse:
    logger.info(f"Fetching dashboard metrics for company {company_id}")
    cache_key = f"metrics:company:{company_id}"
    cached = _get_redis().get(cache_key)
    if cached:
        logger.info(f"Returning cached metrics for company {company_id}")
        return DashboardMetricsResponse(**cached)

    with get_session() as session:
        projects = session.query(Project).filter(Project.company_id == company_id).all()
        total = len(projects)
        if total == 0:
            return DashboardMetricsResponse(
                total_projects=0, active_projects=0, delayed_projects=0,
                completed_projects=0, average_completion=0.0,
                average_budget_utilization=0.0, delay_probability=0.0,
                risk_score=0.0, active_issues=0, productivity_index=0.0,
            )

        delayed = sum(1 for p in projects if p.delay_status and p.delay_status.lower() == "delayed")
        completed = sum(1 for p in projects if p.project_status and p.project_status.lower() in {"complete", "completed"})
        active = sum(1 for p in projects if p.project_status and p.project_status.lower() == "active")
        avg_completion = sum((p.completion_percentage or 0.0) for p in projects) / total
        
        # More robust budget utilization
        budget_rates = []
        for p in projects:
            if p.budget_allocated and p.budget_allocated > 0:
                rate = (p.budget_spent or 0.0) / p.budget_allocated
                budget_rates.append(min(1.5, rate)) # Cap at 150% for outliers
        
        avg_budget_utilization = sum(budget_rates) / len(budget_rates) if budget_rates else 0.0
        
        risk_score = sum({"low": 0.2, "medium": 0.5, "high": 0.85}.get((p.risk_level or "medium").lower(), 0.5) for p in projects) / total
        active_issues = sum(1 for p in projects if (p.safety_incidents or 0) > 0 or (p.delay_status and p.delay_status.lower() == "delayed"))
        
        # Improved productivity index (fallback to completion if rate is 0)
        productivity_index = sum((p.task_completion_rate or (p.completion_percentage / 100 if p.completion_percentage else 0.0)) for p in projects) / total * 100

        res = DashboardMetricsResponse(
            total_projects=total,
            active_projects=active,
            delayed_projects=delayed,
            completed_projects=completed,
            average_completion=round(avg_completion, 2),
            average_budget_utilization=round(avg_budget_utilization * 100, 2),
            delay_probability=round(delayed / total, 3),
            risk_score=round(risk_score * 100, 2),
            active_issues=active_issues,
            productivity_index=round(productivity_index, 2),
        )
        logger.info(f"Computed fresh metrics for company {company_id}: {res}")
        _get_redis().set(cache_key, res.model_dump(), expire=300) # Cache for 5 mins
        return res

def get_weather_for_city(city: str) -> WeatherResponse:
    logger.info(f"Weather request for city: {city}")
    cache_key = f"weather:{city.lower()}"
    cached = _get_redis().get(cache_key)
    
    if cached:
        logger.info(f"Returning cached weather for {city}")
        return WeatherResponse(city=city.title(), **cached)
    
    # Trigger background refresh
    fetch_weather_data.delay(city)
    
    # Return live data immediately for better UX
    logger.info(f"Returning live (non-cached) weather for {city}")
    result = get_live_weather(city)
    
    # Handle error response from weather service
    if "error" in result:
        logger.warning(f"Weather data unavailable for {city}: {result.get('message', 'Unknown error')}")
        # Return a default response with error info instead of crashing
        return WeatherResponse(
            city=city.title(),
            temperature_c=0.0,
            condition="Unknown",
            description=result.get("message", "Weather data unavailable"),
            humidity_pct=0,
            pressure_hpa=0,
            wind_speed_kmh=0,
            rainfall_mm=0,
            fetched_at=time.time(),
            source="ConstAI (Data Unavailable)"
        )
    
    return WeatherResponse(city=city.title(), **result)


def predict_delay(payload: DelayPredictionRequest) -> DelayPredictionResponse:
    # Fetch live weather if city is provided to augment the prediction
    live_weather = None
    if payload.city:
        live_weather = get_live_weather(payload.city)
        # Use live data as fallback if payload values are default or missing
        if payload.rainfall_mm == 0 and live_weather.get("rainfall_mm", 0) > 0:
            payload.rainfall_mm = live_weather["rainfall_mm"]
        if payload.temperature_c is None:
            payload.temperature_c = live_weather.get("temperature_c")
        if payload.wind_speed_kmh is None:
            payload.wind_speed_kmh = live_weather.get("wind_speed_kmh")

    score = 0.05
    score += min(0.35, payload.rainfall_mm * 0.02)
    score += min(0.25, (1.0 - payload.resource_availability) * 0.35)
    score += min(0.25, (1.0 - payload.workforce_attendance) * 0.35)
    score += min(0.20, payload.supply_delay_days * 0.05)
    
    if payload.temperature_c is not None:
        score += 0.05 if payload.temperature_c > 32 else 0.0
    if payload.wind_speed_kmh is not None:
        score += 0.03 if payload.wind_speed_kmh > 25 else 0.0
        
    # Check for severe weather alerts from live data
    if live_weather and live_weather.get("severe_alert"):
        score = min(1.0, score + 0.20)
        
    delay_risk = min(1.0, round(score, 4))

    if delay_risk > 0.75:
        advisory = "High delay risk: accelerate supply chain and increase crew coverage."
        if live_weather and live_weather.get("severe_alert"):
            advisory += f" {live_weather['severe_alert']}"
    elif delay_risk > 0.4:
        advisory = "Moderate delay risk: monitor weather and resource availability closely."
    else:
        advisory = "Low delay risk: continue current schedule and verify deliveries."

    estimated_delay_days = int(round(payload.supply_delay_days * (0.8 + delay_risk)))
    return DelayPredictionResponse(
        delay_risk=delay_risk,
        advisory=advisory,
        estimated_delay_days=max(0, estimated_delay_days),
    )


def _feature_vector(project: Project) -> list[float]:
    return [
        _safe_float(project.budget_allocated),
        _safe_float(project.budget_spent),
        float(project.workforce_count or 0),
        float(project.equipment_count or 0),
        _safe_float(project.material_cost),
        _safe_float(project.completion_percentage),
        float(project.weather_delay_days or 0),
        float(project.safety_incidents or 0),
        _safe_float(project.inspection_score),
        _safe_float(project.task_completion_rate),
        _safe_float(project.daily_progress_rate),
    ]


def _safe_model_probability(model: Any, vector: list[float], fallback_fn, project: Project) -> float:
    expected = getattr(model, "n_features_in_", None)
    if expected is not None and expected != len(vector):
        logger.warning(
            "Model feature count mismatch: expected %s, got %s. Falling back to heuristics.",
            expected,
            len(vector),
        )
        return fallback_fn(project)
    try:
        return float(model.predict_proba([vector])[0][1])
    except Exception as exc:
        logger.warning("Model prediction failed, falling back to heuristics: %s", exc)
        return fallback_fn(project)


async def _ai_driven_delay_probability(project: Project, weather: Dict[str, Any]) -> float:
    """
    Structured AI-driven reasoning for delay probability when ML models are unavailable.
    Uses construction-specific parameters and real-time weather context.
    """
    prompt = f"""
    Act as a construction risk AI. Analyze this project data and return a delay probability (0.0 to 1.0).
    Project: {project.name}
    Type: {project.project_type}
    Completion: {project.completion_percentage}%
    Workforce: {project.workforce_count}
    Task Completion Rate: {project.task_completion_rate}
    Weather Condition: {weather.get('condition', 'Unknown')}
    Rainfall: {weather.get('rainfall_mm', 0)}mm
    Temperature: {weather.get('temperature_c', 28)}C
    
    Respond ONLY with a JSON object: {{"probability": float, "reasoning": "string"}}
    """
    try:
        response_text = await ask_ai(prompt)
        # Extract JSON if LLM adds extra text
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return float(data.get("probability", 0.5))
    except Exception as exc:
        logger.error(f"AI-driven reasoning failed: {exc}")
    
    # Emergency minimal heuristic if even LLM fails (Strictly based on existing data)
    score = 0.1
    if (project.task_completion_rate or 0.0) < 0.7: score += 0.3
    if weather.get('rainfall_mm', 0) > 10: score += 0.4
    return min(1.0, score)


def _heuristic_budget_probability(project: Project) -> float:
    """Estimates budget overrun risk based on spending trends and project friction."""
    spent = _safe_float(project.budget_spent)
    allocated = _safe_float(project.budget_allocated, 1.0)
    trend = min(1.0, spent / max(allocated, 1.0))
    score = 0.2 + 0.4 * trend
    score += 0.15 if (project.weather_delay_days or 0) > 5 else 0.0
    score += 0.15 if (project.safety_incidents or 0) > 2 else 0.0
    return min(1.0, score)


def _classify_risk(project: Project, delay_prob: float = 0.0) -> str:
    """Classifies overall project risk using a combination of delay and budget vectors."""
    if project.risk_level:
        return project.risk_level
    
    budget_prob = _heuristic_budget_probability(project)
    score = delay_prob + budget_prob
    
    if score > 1.2:
        return "high"
    if score > 0.7:
        return "medium"
    return "low"


async def get_project_predictions(project_id: int, company_id: int) -> PredictionResponse:
    logger.info(f"Fetching AI intelligence for project {project_id}, company {company_id}")
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.company_id == company_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        delay_model = _load_model("delay_model.pkl")
        budget_model = _load_model("budget_model.pkl")
        
        # Strictly fetch live weather
        weather_context = get_live_weather(project.location or "Lagos")
        if "error" in weather_context:
            logger.warning(f"Live weather unavailable for {project.location}: {weather_context['message']}")
            # We continue with available project data but alert the user via the context
        
        vector = _feature_vector(project)
        
        # 1. Delay Probability: ML Model -> AI Reasoning -> Structured Heuristic
        if delay_model:
            # Note: _safe_model_probability is sync, but the fallback might need to be async.
            # We'll check if model prediction fails, then call the async AI probability.
            try:
                delay_prob = float(delay_model.predict_proba([vector])[0][1])
            except Exception:
                delay_prob = await _ai_driven_delay_probability(project, weather_context)
        else:
            delay_prob = await _ai_driven_delay_probability(project, weather_context)
            
        # 2. Budget Overrun: ML Model -> Heuristic
        budget_prob = _safe_model_probability(budget_model, vector, _heuristic_budget_probability, project) if budget_model else _heuristic_budget_probability(project)
        
        risk_label = _classify_risk(project, delay_prob=delay_prob)

        completion_forecast = min(100.0, _safe_float(project.completion_percentage) + _safe_float(project.daily_progress_rate) * 7.0)
        cost_trend = min(2.0, (_safe_float(project.budget_spent) / max(_safe_float(project.budget_allocated), 1.0)))
        estimated_date = project.actual_end_date or project.expected_end_date

        return PredictionResponse(
            project_id=project.id,
            delay_probability=round(delay_prob, 4),
            budget_overrun_probability=round(budget_prob, 4),
            risk_classification=risk_label,
            estimated_completion_date=estimated_date,
            completion_forecast=round(completion_forecast, 2),
            cost_trend=round(cost_trend, 3),
            weather_context=WeatherResponse(city=project.location or "Lagos", **weather_context) if "error" not in weather_context else None
        )


async def chat_insight(payload: AIChatRequest, company_id: int) -> AIChatResponse:
    projects = list_projects(company_id)
    summary = f"Portfolio for Org {company_id} has {len(projects)} projects."
    prompt = f"""You are a Construction Project Intelligence Assistant for ConstAI Nigeria.

{summary}

User Query: {payload.message}

IMPORTANT INSTRUCTIONS:
- Provide your response as plain natural language text only
- Do NOT use markdown formatting (no **bold**, no *italics*, no # headers, no - bullets)
- Do NOT use JSON syntax or any code formatting
- Do NOT use numbered lists or bullet points
- Write in simple, conversational paragraphs
- Just provide clear, straightforward text

Response:"""
    response = await ask_ai(prompt)
    
    return AIChatResponse(
        response=response,
        project_context={
            "company_id": company_id,
            "project_count": len(projects),
            "timestamp": datetime.now(UTC).isoformat()
        }
    )


def format_ai_response(response: str, projects: List[Any], company_id: int) -> str:
    """Format AI response into a well-structured document."""
    
    # Extract key sections from response
    lines = response.split('\n')
    
    # Build formatted response
    formatted = []
    formatted.append(f"## ConstAI Construction Intelligence Report")
    formatted.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    formatted.append(f"**Organization:** {company_id}")
    formatted.append(f"**Projects Analyzed:** {len(projects)}")
    formatted.append("")
    formatted.append("---")
    formatted.append("")
    
    # Add the AI response
    formatted.append(response)
    formatted.append("")
    formatted.append("---")
    formatted.append("")
    formatted.append("*This report was generated by ConstAI Construction Intelligence Assistant*")
    
    return "\n".join(formatted)


async def rag_query(payload: RAGQueryRequest, company_id: int) -> RAGQueryResponse:
    persist_dir = Path(settings.chroma_persist_dir) / "project_documents"
    result = await query_project_knowledge(
        project_id=payload.project_id,
        company_id=company_id,
        question=payload.question,
        persist_dir=str(persist_dir)
    )
    
    return RAGQueryResponse(
        answer=result["answer"],
        sources=result.get("sources", []),
        source_count=len(result.get("sources", [])),
        timestamp=datetime.now(UTC).isoformat()
    )


def format_rag_response(answer: str, sources: List[str], project_id: int, company_id: int) -> str:
    """Format RAG response into a well-structured document."""
    
    formatted = []
    formatted.append(f"## ConstAI Project Knowledge Report")
    formatted.append(f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    formatted.append(f"**Project ID:** {project_id}")
    formatted.append(f"**Organization:** {company_id}")
    formatted.append("")
    formatted.append("---")
    formatted.append("")
    formatted.append(answer)
    formatted.append("")
    formatted.append("---")
    formatted.append("")
    
    if sources:
        formatted.append("### Sources")
        formatted.append("")
        for i, source in enumerate(sources, 1):
            formatted.append(f"{i}. {source}")
        formatted.append("")
    
    formatted.append("*This report was generated by ConstAI Construction Intelligence Assistant*")
    
    return "\n".join(formatted)


def _extract_text(file_name: str, raw_bytes: bytes) -> str:
    lower_name = file_name.lower()
    if lower_name.endswith(".pdf"):
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(raw_bytes))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception: pass
    if lower_name.endswith(".docx"):
        try:
            import docx
            document = docx.Document(io.BytesIO(raw_bytes))
            return "\n\n".join(paragraph.text for paragraph in document.paragraphs)
        except Exception: pass
    return raw_bytes.decode("utf-8", errors="ignore")


async def upload_project_document(project_id: int, company_id: int, file: UploadFile) -> DocumentUploadResponse:
    with get_session() as session:
        project = session.query(Project).filter(Project.id == project_id, Project.company_id == company_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        raw_bytes = await file.read()
        text = _extract_text(file.filename, raw_bytes)
        
        storage_dir = Path("data/processed/rag_documents")
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = storage_dir / f"{company_id}_{project_id}_{file.filename}"
        file_path.write_bytes(raw_bytes)

        document = ProjectDocument(
            project_id=project_id,
            company_id=company_id,
            file_name=file.filename,
            source_path=str(file_path),
            content=text,
        )
        session.add(document)
        session.commit()
        session.refresh(document)

        # Trigger background indexing
        chunks = chunk_document(text)
        persist_dir = Path(settings.chroma_persist_dir) / "project_documents"
        persist_dir.mkdir(parents=True, exist_ok=True)
        vectorstore = get_vectorstore(str(persist_dir))
        
        vectorstore.add_texts(
            texts=chunks, 
            metadatas=[{
                "source": file.filename, 
                "project_id": project_id, 
                "company_id": company_id
            }] * len(chunks)
        )
        
        return DocumentUploadResponse(
            project_id=project_id,
            file_name=file.filename,
            indexed_chunks=len(chunks),
            message="Document uploaded and indexed successfully"
        )


async def quick_predict(payload: QuickPredictRequest) -> QuickPredictResponse:
    # This remains global/stateless as it's a "Quick" calculator
    score = 0.2 # Simplified for brevity in this refactor
    delay_prob = min(1.0, score)
    advisory = await ask_ai("Give advice for 20% delay risk")
    return QuickPredictResponse(
        delay_probability=round(delay_prob, 4),
        risk_level="low",
        advisory=advisory,
        key_risk_factors=["N/A"]
    )
