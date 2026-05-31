from pydantic import BaseModel
from typing import List

class DocumentReviewRequest(BaseModel):
    document_text: str
    analysis_type: str = "legal_compliance"

class DocumentReviewResponse(BaseModel):
    summary: str
    confidence_score: float
    citations: List[str] = []
