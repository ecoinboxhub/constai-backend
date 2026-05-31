# Architecture Overview

## Backend Services
- FastAPI app with modular routers under `backend/app/modules`
- Role-based access control enforced through JWT claims
- API-key gated token issuance endpoint for service-to-service trust bootstrapping

## Data and Modeling
- Raw/processed datasets under `data/`
- Model artifacts under `artifacts/models`
- Reproducible workflows in `dvc.yaml`
- ML experiments tracked with MLflow

## Storage Strategy
- PostgreSQL configured for transactional data via `DATABASE_URL`
- MongoDB optional for semi-structured logs/doc chunks
- Chroma/Pinecone switchable by env (`VECTOR_STORE`)

## RAG Pattern
- Corpus bootstrap pipeline writes reference text for regulation-aware retrieval
- Production extension: ingest COREN/ILO/FIDIC/legal corpora, chunk, embed, index, retrieve, then ground model output

## Deployment
- Docker + Compose for local deployment
- Render blueprint provided (`render.yaml`)
- CI pipeline runs lint/tests/bootstrap
