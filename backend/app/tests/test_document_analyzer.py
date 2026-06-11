import pytest
from fastapi import status

BASE = "/api/v1/document-analyzer"


class TestDocumentReview:
    def test_review_success_with_nbc(self, client):
        payload = {
            "document_text": "This structure complies with NBC 2023 standards and COREN Act requirements."
        }
        response = client.post(f"{BASE}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "confidence_score" in data
        assert "citations" in data
        assert "NBC 2023" in data["citations"]
        assert "COREN Act" in data["citations"]
        assert data["confidence_score"] >= 0.65

    def test_review_success_with_fire_safety(self, client):
        payload = {
            "document_text": "The building has proper fire exits and fire safety equipment installed."
        }
        response = client.post(f"{BASE}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "Fire Safety" in str(data["citations"])

    def test_review_empty_text(self, client):
        payload = {"document_text": ""}
        response = client.post(f"{BASE}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["confidence_score"] == 0.0
        assert "no document text" in data["summary"].lower()

    def test_review_no_specific_standards(self, client):
        payload = {
            "document_text": "General construction notes about material quality."
        }
        response = client.post(f"{BASE}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "general compliance" in str(data["citations"][0]).lower()
        assert 0.65 <= data["confidence_score"] <= 0.75

    def test_review_all_standards(self, client):
        payload = {
            "document_text": (
                "The project follows NBC 2023 standards and COREN Act regulations. "
                "All fire exits and fire safety measures are in place."
            )
        }
        response = client.post(f"{BASE}/review", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "NBC 2023" in data["citations"]
        assert "COREN Act" in data["citations"]
        assert "Fire Safety" in str(data["citations"])
        assert len(data["citations"]) >= 3
        assert data["confidence_score"] >= 0.85

    def test_review_missing_field(self, client):
        response = client.post(f"{BASE}/review", json={})
        assert response.status_code == 422


class TestDocumentService:
    def test_review_document_with_citations(self):
        from app.modules.document_analyzer.service import review_document
        from app.modules.document_analyzer.schemas import DocumentReviewRequest

        req = DocumentReviewRequest(document_text="Complies with NBC 2023 and COREN Act")
        result = review_document(req)
        assert len(result.citations) >= 2
        assert result.confidence_score > 0.7

    def test_review_document_empty(self):
        from app.modules.document_analyzer.service import review_document
        from app.modules.document_analyzer.schemas import DocumentReviewRequest

        req = DocumentReviewRequest(document_text="")
        result = review_document(req)
        assert result.confidence_score == 0.0

    def test_review_document_confidence_increases_with_citations(self):
        from app.modules.document_analyzer.service import review_document
        from app.modules.document_analyzer.schemas import DocumentReviewRequest

        basic_req = DocumentReviewRequest(document_text="General note")
        basic_result = review_document(basic_req)
        full_req = DocumentReviewRequest(
            document_text="NBC 2023 COREN Act fire safety"
        )
        full_result = review_document(full_req)
        assert full_result.confidence_score > basic_result.confidence_score

    def test_review_document_nbc_only(self):
        from app.modules.document_analyzer.service import review_document
        from app.modules.document_analyzer.schemas import DocumentReviewRequest

        req = DocumentReviewRequest(document_text="According to NBC 2023 standards")
        result = review_document(req)
        assert "NBC 2023" in result.citations

    def test_review_document_coren_only(self):
        from app.modules.document_analyzer.service import review_document
        from app.modules.document_analyzer.schemas import DocumentReviewRequest

        req = DocumentReviewRequest(document_text="Per COREN Act requirements")
        result = review_document(req)
        assert "COREN Act" in result.citations