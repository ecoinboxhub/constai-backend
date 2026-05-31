# Runbook

## 1) Create venv
```powershell
python -m virtualenv .venv --app-data .\.virtualenv --no-periodic-update
```

## 2) Install libraries
```powershell
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## 3) Run data + pipelines
```powershell
.\.venv\Scripts\python backend\scripts\bootstrap_data.py
.\.venv\Scripts\python backend\pipelines\models\train_project_tracker.py
.\.venv\Scripts\python backend\pipelines\models\train_procurement_forecast.py
.\.venv\Scripts\python backend\pipelines\models\train_safety_detector.py
.\.venv\Scripts\python backend\pipelines\models\train_document_analyzer.py
.\.venv\Scripts\python backend\pipelines\models\train_cost_estimator.py
.\.venv\Scripts\python backend\pipelines\models\train_maintenance_predictor.py
.\.venv\Scripts\python backend\pipelines\rag\build_indexes.py
```

## 4) Run tests
```powershell
.\.venv\Scripts\python -m pytest -q
```

## 5) Start API
```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Swagger UI:
- http://127.0.0.1:8000/docs

## 6) Quick API checks
```powershell
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/api/v1/health' -UseBasicParsing

$token = (Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/integration/token' -Headers @{ 'X-API-Key'='change-me' } -ContentType 'application/json' -Body '{"username":"demo","role":"project_manager"}').access_token

Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/v1/project-tracker/predict-delay' -Headers @{ 'Authorization'="Bearer $token" } -ContentType 'application/json' -Body '{"rainfall_mm":55,"temperature_c":31,"wind_speed_kmh":22,"resource_availability":0.7,"workforce_attendance":0.78,"supply_delay_days":4}'
```

## 7) One-command full run
```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\run_all.ps1
```

## 8) Full endpoint validation and JSON report
```powershell
.\.venv\Scripts\python backend\scripts\validate_all_endpoints.py
```

Report output:
- `artifacts/reports/api_validation_report.json`

PowerShell wrapper:
```powershell
powershell -ExecutionPolicy Bypass -File backend\scripts\run_endpoint_validation.ps1
```

Per-endpoint payload files are in:
- `backend/scripts/payloads/*.json`

Edit each payload file before running validation to test endpoint-specific request bodies.

## 9) Nginx + Ngrok (single API port model)
Core API stays on port `8000` only.

Optional infrastructure ports:
- `80` for Nginx reverse proxy to API
- `4040` for Ngrok local inspect UI

Start stack:
```powershell
docker compose up -d api worker postgres redis nginx ngrok
```

If you only want local API + Swagger:
```powershell
docker compose up -d api postgres redis
```
