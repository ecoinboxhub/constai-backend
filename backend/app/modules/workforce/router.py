from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.db.session import SessionLocal
from app.db.models.core import Workforce
from app.core.security import decode_token

router = APIRouter()


class WorkforceCreate(BaseModel):
    first_name: str
    last_name: str
    role: str
    skills: Optional[str] = None
    project_id: Optional[str] = None


class WorkforceResponse(WorkforceCreate):
    id: int
    is_active: bool


@router.post("", response_model=WorkforceResponse)
def create_worker(worker: WorkforceCreate, token: dict = Depends(decode_token)):
    db = SessionLocal()
    try:
        pid = int(worker.project_id) if worker.project_id and str(worker.project_id).strip() else None
        new_worker = Workforce(
            first_name=worker.first_name,
            last_name=worker.last_name,
            role=worker.role,
            skills=worker.skills,
            project_id=pid,
            company_id=token.get("company_id")
        )
        db.add(new_worker)
        db.commit()
        db.refresh(new_worker)
        return {
            "id": new_worker.id,
            "first_name": new_worker.first_name,
            "last_name": new_worker.last_name,
            "role": new_worker.role,
            "skills": new_worker.skills,
            "is_active": new_worker.is_active,
            "project_id": str(new_worker.project_id) if new_worker.project_id else None
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("", response_model=List[WorkforceResponse])
def get_workforce(token: dict = Depends(decode_token)):
    db = SessionLocal()
    try:
        company_id = token.get("company_id")
        workers = db.query(Workforce).filter(Workforce.company_id == company_id).all()
        return [
            {
                "id": w.id,
                "first_name": w.first_name,
                "last_name": w.last_name,
                "role": w.role,
                "skills": w.skills,
                "is_active": w.is_active,
                "project_id": str(w.project_id) if w.project_id else None
            } for w in workers
        ]
    finally:
        db.close()
