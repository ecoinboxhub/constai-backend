# Nigeria Construction AI Platform - Endpoint Usage Guide

This guide explains how to use all current API endpoints with:
- Terminal (`curl` / PowerShell)
- Swagger UI
- Postman
- Other clients (`httpie`, Python `requests`, JavaScript `fetch`)

Base URL (local):
- `http://127.0.0.1:8000`

API prefix:
- `/api/v1`

Full docs URL:
- `http://127.0.0.1:8000/docs`

Public utility endpoints (no auth):
- `GET /api/v1/health`
- `GET /health`
- `GET /api/v1/metrics`
- `GET /metrics`

## 1. Start the API

From project root:

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Health check:

```powershell
curl http://127.0.0.1:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "timestamp": "2026-03-10T10:00:00.000000+00:00"
}
```

## 2. Authentication (Important)

Most endpoints require `Authorization: Bearer <access_token>`.

### 2.1 Get token

Endpoint:
- `POST /api/v1/integration/token`

Headers:
- `X-API-Key: <your_api_key_from_.env>`
- `Content-Type: application/json`

Body:

```json
{
  "username": "admin_user",
  "role": "admin"
}
```

Role options used by RBAC:
- `admin`
- `project_manager`
- `analyst`
- `procurement`
- `safety`
- `legal`

Sample success response:

```json
{
  "access_token": "<jwt_access_token>",
  "refresh_token": "<jwt_refresh_token>",
  "token_type": "bearer"
}
```

### 2.2 Refresh token

Endpoint:
- `POST /api/v1/integration/refresh`

Body:

```json
{
  "refresh_token": "<jwt_refresh_token>"
}
```

Sample success response:

```json
{
  "access_token": "<new_jwt_access_token>",
  "refresh_token": "<new_jwt_refresh_token>",
  "token_type": "bearer"
}
```

### 2.3 Swagger Authorize step-by-step

1. Open `http://127.0.0.1:8000/docs`
2. Run `POST /api/v1/integration/token` first and copy `access_token`
3. Click `Authorize` (top-right lock icon)
4. Paste token in Bearer field:
- `<access_token>` (token only, no `Bearer ` prefix in Swagger input)
5. Click `Authorize`, then `Close`
6. Run protected endpoints

If you see `401 Missing token`, your Bearer token was not attached.
If you see `401 Invalid token`, check that you did not paste `Bearer <token>` into Swagger; paste raw token only.

## 3. Endpoint Access Matrix

| Endpoint | Method | Auth | Allowed roles |
|---|---|---|---|
| `/api/v1/health` | GET | No | N/A |
| `/api/v1/metrics` | GET | No | N/A |
| `/api/v1/integration/token` | POST | `X-API-Key` | N/A |
| `/api/v1/integration/refresh` | POST | No | N/A |
| `/api/v1/integration/module-status` | GET | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/integration/endpoints` | GET | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/project-tracker/predict-delay` | POST | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/procurement/supplier-intelligence` | POST | Bearer | `admin`, `procurement`, `project_manager` |
| `/api/v1/safety/analyze-log` | POST | Bearer | `admin`, `safety`, `project_manager` |
| `/api/v1/document-analyzer/review` | POST | Bearer | `admin`, `legal`, `project_manager` |
| `/api/v1/cost-estimator/estimate` | POST | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/workforce/optimize` | POST | Bearer | `admin`, `project_manager` |
| `/api/v1/maintenance/predict` | POST | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/progress-visualizer/analyze` | POST | Bearer | `admin`, `project_manager`, `analyst` |
| `/api/v1/tender-analyzer/analyze` | POST | Bearer | `admin`, `legal`, `project_manager` |

## 4. Integration Endpoints

### 4.1 POST /api/v1/integration/token

Purpose:
- Issue access + refresh JWT tokens.

### 4.2 POST /api/v1/integration/refresh

Purpose:
- Rotate tokens using valid refresh token.

### 4.3 GET /api/v1/integration/module-status

Auth:
- Bearer token required.
- Allowed roles: `admin`, `project_manager`, `analyst`

Sample response:

```json
{
  "items": [
    {
      "module": "project_tracker",
      "completion_pct": 75,
      "algorithms": ["LSTM", "DecisionTree", "RandomForest"],
      "metric_name": "f1_score",
      "metric_value": 0.71,
      "target": "> 0.70",
      "blockers": "Needs larger real labeled delay dataset"
    }
  ]
}
```

### 4.4 GET /api/v1/integration/endpoints

Auth:
- Bearer token required.
- Allowed roles: `admin`, `project_manager`, `analyst`

Sample response:

```json
{
  "items": [
    {
      "method": "POST",
      "path": "/api/v1/project-tracker/predict-delay",
      "module": "project_tracker"
    }
  ]
}
```

## 5. Core Module Endpoints

All endpoints below require Bearer auth.

### 4.1 Project Tracker

Endpoint:
- `POST /api/v1/project-tracker/predict-delay`

Allowed roles:
- `admin`, `project_manager`, `analyst`

Request:

```json
{
  "rainfall_mm": 30,
  "temperature_c": 31,
  "wind_speed_kmh": 18,
  "resource_availability": 0.82,
  "workforce_attendance": 0.9,
  "supply_delay_days": 2,
  "city": "Lagos"
}
```

Response:

```json
{
  "delay_risk": 0.5341,
  "will_delay": false,
  "model_stack": ["LSTM", "DecisionTree", "RandomForest"]
}
```

### 4.2 Procurement Assistant

Endpoint:
- `POST /api/v1/procurement/supplier-intelligence`

Allowed roles:
- `admin`, `procurement`, `project_manager`

Request:

```json
{
  "material": "cement",
  "location": "Lagos",
  "horizon_days": 30
}
```

Response:

```json
{
  "material": "cement",
  "quotes": [
    {
      "supplier": "Dangote",
      "latest_price_ngn": 12000,
      "forecast_price_ngn": 12180,
      "reliability_score": 0.79
    }
  ],
  "best_supplier": "Dangote"
}
```

### 4.3 Safety Dashboard

Endpoint:
- `POST /api/v1/safety/analyze-log`

Allowed roles:
- `admin`, `safety`, `project_manager`

Request:

```json
{
  "project_id": "PRJ-001",
  "city": "Abuja",
  "log_text": "Workers entered scaffold zone without helmet near electrical cables."
}
```

Response:

```json
{
  "project_id": "PRJ-001",
  "findings": [
    {
      "hazard": "PPE violation",
      "severity": "high",
      "confidence": 0.82,
      "regulation_reference": "COREN Act 2018",
      "recommended_action": "Enforce hard-hat compliance immediately."
    }
  ],
  "recall_target": 0.8
}
```

### 4.4 Document Analyzer

Endpoint:
- `POST /api/v1/document-analyzer/review`

Allowed roles:
- `admin`, `legal`, `project_manager`

Request:

```json
{
  "title": "Subcontract Agreement",
  "text": "This agreement covers payment terms, variation procedure, dispute resolution, health and safety obligations, and termination."
}
```

Response:

```json
{
  "title": "Subcontract Agreement",
  "clauses": [
    {
      "clause": "payment terms",
      "present": true,
      "comment": "Found",
      "confidence": 0.9
    }
  ],
  "compliance_score": 80
}
```

### 4.5 Cost Estimator

Endpoint:
- `POST /api/v1/cost-estimator/estimate`

Allowed roles:
- `admin`, `project_manager`, `analyst`

Request:

```json
{
  "area_sqm": 1500,
  "floors": 2,
  "complexity_index": 1.1,
  "labor_cost_index": 1.0,
  "materials_cost_index": 1.2
}
```

Response:

```json
{
  "estimated_cost_ngn": 871200000,
  "model_family": "XGBoost + ElasticNet Ensemble",
  "target_mape": 0.1
}
```

### 4.6 Workforce Scheduler

Endpoint:
- `POST /api/v1/workforce/optimize`

Allowed roles:
- `admin`, `project_manager`

Request:

```json
{
  "shift_hours": 8,
  "groups": [
    { "role": "mason", "required": 10, "available": 12 },
    { "role": "welder", "required": 4, "available": 3 }
  ]
}
```

Response:

```json
{
  "schedule": [
    { "role": "mason", "allocated": 10, "utilization": 0.833 },
    { "role": "welder", "allocated": 3, "utilization": 1.0 }
  ],
  "idle_rate": 0.2,
  "optimization_method": "greedy"
}
```

### 4.7 Maintenance Predictor

Endpoint:
- `POST /api/v1/maintenance/predict`

Allowed roles:
- `admin`, `project_manager`, `analyst`

Request:

```json
{
  "equipment_type": "excavator",
  "runtime_hours": 950,
  "vibration_index": 6.2,
  "temperature_c": 41,
  "last_maintenance_days": 72
}
```

Response:

```json
{
  "failure_risk": 0.7442,
  "maintenance_due_in_days": 7
}
```

### 4.8 Progress Visualizer

Endpoint:
- `POST /api/v1/progress-visualizer/analyze`

Allowed roles:
- `admin`, `project_manager`, `analyst`

Request (without image, manual completion input):

```json
{
  "planned_completion_pct": 60,
  "detected_completion_pct": 52
}
```

Request (with image):

```json
{
  "planned_completion_pct": 60,
  "image_base64": "<base64_image_data>"
}
```

Response:

```json
{
  "deviation_pct": 8,
  "exceeds_threshold": false,
  "threshold_pct": 15,
  "detected_objects": [],
  "ppe_compliance_score": 0.0,
  "detected_completion_pct": 52
}
```

### 4.9 Tender Analyzer

Endpoint:
- `POST /api/v1/tender-analyzer/analyze`

Allowed roles:
- `admin`, `legal`, `project_manager`

Request:

```json
{
  "tender_id": "TND-2026-014",
  "text": "The tender includes liquidated damages, unrealistic timeline, and currency fluctuation clauses."
}
```

Response:

```json
{
  "tender_id": "TND-2026-014",
  "risks": [
    { "risk": "High penalty exposure", "level": "high", "confidence": 0.87 },
    { "risk": "Schedule risk", "level": "high", "confidence": 0.84 },
    { "risk": "FX risk", "level": "medium", "confidence": 0.76 }
  ],
  "summary": "High penalty exposure Schedule risk FX risk"
}
```

## 6. Terminal Usage (Step-by-step)

Set variables:

```powershell
$BASE_URL = "http://127.0.0.1:8000"
$API_KEY = "<your_api_key>"
```

Get token:

```powershell
$tokenResp = Invoke-RestMethod -Method POST `
  -Uri "$BASE_URL/api/v1/integration/token" `
  -Headers @{ "X-API-Key" = $API_KEY } `
  -ContentType "application/json" `
  -Body '{"username":"admin_user","role":"admin"}'

$ACCESS = $tokenResp.access_token
$REFRESH = $tokenResp.refresh_token
```

Call protected endpoint:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "$BASE_URL/api/v1/project-tracker/predict-delay" `
  -Headers @{ "Authorization" = "Bearer $ACCESS" } `
  -ContentType "application/json" `
  -Body '{"rainfall_mm":30,"temperature_c":31,"wind_speed_kmh":18,"resource_availability":0.82,"workforce_attendance":0.9,"supply_delay_days":2,"city":"Lagos"}'
```

Refresh token:

```powershell
Invoke-RestMethod -Method POST `
  -Uri "$BASE_URL/api/v1/integration/refresh" `
  -ContentType "application/json" `
  -Body ("{""refresh_token"":""" + $REFRESH + """}")
```

## 7. Postman Usage (Step-by-step)

1. Create environment variables:
- `base_url = http://127.0.0.1:8000`
- `api_key = <your_api_key>`
- `access_token =`
- `refresh_token =`

2. Request: `POST {{base_url}}/api/v1/integration/token`
- Header: `X-API-Key: {{api_key}}`
- Body raw JSON:
```json
{
  "username": "admin_user",
  "role": "admin"
}
```

3. In Tests tab, save tokens:

```javascript
const data = pm.response.json();
pm.environment.set("access_token", data.access_token);
pm.environment.set("refresh_token", data.refresh_token);
```

4. For protected endpoints, add header:
- `Authorization: Bearer {{access_token}}`

5. To refresh:
- `POST {{base_url}}/api/v1/integration/refresh`
- Body:
```json
{
  "refresh_token": "{{refresh_token}}"
}
```

## 8. Other Platforms

### 7.1 HTTPie

Get token:

```bash
http POST :8000/api/v1/integration/token X-API-Key:<your_api_key> username=admin_user role=admin
```

Protected endpoint:

```bash
http POST :8000/api/v1/cost-estimator/estimate Authorization:"Bearer <access_token>" area_sqm:=1500 floors:=2 complexity_index:=1.1 labor_cost_index:=1.0 materials_cost_index:=1.2
```

### 7.2 Python requests

```python
import requests

base = "http://127.0.0.1:8000"
api_key = "<your_api_key>"

tok = requests.post(
    f"{base}/api/v1/integration/token",
    headers={"X-API-Key": api_key},
    json={"username": "admin_user", "role": "admin"},
).json()

access = tok["access_token"]

res = requests.get(
    f"{base}/api/v1/integration/endpoints",
    headers={"Authorization": f"Bearer {access}"},
)
print(res.status_code, res.json())
```

### 7.3 JavaScript fetch

```javascript
const base = "http://127.0.0.1:8000";
const apiKey = "<your_api_key>";

const tokRes = await fetch(`${base}/api/v1/integration/token`, {
  method: "POST",
  headers: { "Content-Type": "application/json", "X-API-Key": apiKey },
  body: JSON.stringify({ username: "admin_user", role: "admin" })
});
const tok = await tokRes.json();

const res = await fetch(`${base}/api/v1/integration/module-status`, {
  headers: { Authorization: `Bearer ${tok.access_token}` }
});
console.log(await res.json());
```

## 9. Error Prevention Checklist

1. Confirm API is running on `127.0.0.1:8000`.
2. Use correct `.env` `API_KEY`.
3. Always call `/integration/token` first.
4. Pass Bearer token on protected endpoints.
5. Use a role allowed for the target endpoint.
6. Ensure request body satisfies schema constraints (for example min text length, value ranges).
7. If `401 Invalid token`, refresh token or issue a new token.
8. If `403 Insufficient role`, request a token with appropriate role.

## 10. Existing Local Validation Scripts

You can also run the provided scripts from root:

```powershell
.\backend\scripts\test_project_tracker_auth.ps1
.\backend\scripts\run_endpoint_validation.ps1
```

Per-endpoint payload templates are in:
- `backend/scripts/payloads/`
