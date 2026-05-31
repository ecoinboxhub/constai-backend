from fastapi import APIRouter

from app.modules.document_analyzer.schemas import DocumentReviewRequest, DocumentReviewResponse
from app.modules.document_analyzer.service import review_document

router = APIRouter()

@router.post("/review", response_model=DocumentReviewResponse)
def review_document_endpoint(payload: DocumentReviewRequest):
    return review_document(payload)
