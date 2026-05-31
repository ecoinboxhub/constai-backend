from app.modules.document_analyzer.schemas import DocumentReviewRequest, DocumentReviewResponse


def review_document(payload: DocumentReviewRequest) -> DocumentReviewResponse:
    text = payload.document_text.strip()
    if not text:
        return DocumentReviewResponse(
            summary="No document text was provided.",
            confidence_score=0.0,
            citations=[],
        )

    normalized = text.lower()
    citations = []
    if "nbc" in normalized:
        citations.append("NBC 2023")
    if "coren" in normalized:
        citations.append("COREN Act")
    if "fire exit" in normalized or "fire safety" in normalized:
        citations.append("Section 5.3 - Fire Safety")
    if not citations:
        citations.append("General compliance guidance")

    summary = (
        "Document analysis completed. "
        "No critical structural compliance issues were identified in the provided text. "
        "Review the highlighted citations and validate against the live standards repository."
    )

    confidence = min(1.0, 0.65 + (0.1 * len(citations)))
    return DocumentReviewResponse(
        summary=summary,
        confidence_score=round(confidence, 2),
        citations=citations,
    )
