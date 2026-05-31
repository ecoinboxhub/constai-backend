# Nigeria Construction AI Platform (Backend MVP)

AI-powered construction project tracking backend for Nigerian projects, focused on delay prediction, budget overrun forecasting, risk classification, and document intelligence.

## Scope
- Backend-only MVP (no frontend)
- FastAPI API gateway with JWT authentication
- Project tracker module with ML predictions
- RAG-powered document search
- Gemini and Groq AI integration
- SQLite database for local development

## Repository Structure
- `backend/app/main.py`: FastAPI entrypoint
- `backend/app/api/v1/router.py`: API gateway routing
- `backend/app/modules/project_tracker/`: Project tracker module
- `backend/app/services/llm.py`: LLM integration (Gemini/Groq)
- `backend/app/services/rag/engine.py`: RAG pipeline
- `backend/pipelines/models/train_project_tracker.py`: Model training
- `backend/pipelines/rag/build_indexes.py`: RAG index building

## Quickstart
1. Create env file:
```bash
cp .env.example .env
```
2. Install:
```bash
pip install -r requirements.txt
```
3. Initialize database:
```bash
python -c "from app.db.session import init_db; init_db()"
```
4. Run API:
```bash
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000
```
5. Open docs:
- `http://localhost:8000/docs`

## API Endpoints

### Project Tracker (`/api/v1/project-tracker/`)
- `GET /projects` - List all projects
- `GET /projects/{project_id}` - Get single project
- `POST /projects` - Create new project
- `PUT /projects/{project_id}` - Update project
- `DELETE /projects/{project_id}` - Delete project
- `GET /analytics` - Get dashboard metrics
- `GET /predictions/{project_id}` - Get project predictions
- `POST /chat` - AI-powered project assistant
- `POST /rag/query` - RAG-powered document search
- `POST /documents/upload` - Upload & index project documents

## Auth Flow
1. Register user:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123","role":"analyst"}'
```
2. Login:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}'
```
3. Use token as `Bearer` for protected routes.

## Deployment
- Dockerized image available
- Provide runtime secrets via env vars (`API_KEY`, `JWT_SECRET`, DB credentials, API keys)

## Metrics Targets (MVP Contract)
- Delay Prediction accuracy: `> 0.70`
- Budget Overrun accuracy: `> 0.70`
- Risk Classification accuracy: `> 0.80`

## Important Implementation Note
This repository includes production-style architecture and runnable pipelines, but external data ingestion from live Nigerian supplier/weather/tender sources and cloud deployment require valid credentials and network access in your environment. Replace synthetic bootstrap datasets with approved real datasets to validate final KPI claims.

## Compliance and Ethics
See:
- `docs/ETHICS_AND_COMPLIANCE.md`
- `docs/ARCHITECTURE.md`
- `docs/API_ENDPOINTS.md`
- `docs/ENDPOINT_USAGE_GUIDE.md`
- `docs/FAQ.md`
