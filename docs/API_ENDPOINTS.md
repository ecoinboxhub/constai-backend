# API Endpoints

Base URL prefix: `/api/v1`

## Health
- `GET /health`

## Integration Suite
- `POST /integration/token`
  - Headers: `X-API-Key`
  - Body: `username`, `role`
  - Returns JWT
- `GET /integration/module-status`
  - Auth: Bearer (`admin`, `project_manager`, `analyst`)
- `GET /integration/endpoints`
  - Auth: Bearer (`admin`, `project_manager`, `analyst`)

## Project Tracker
- `POST /project-tracker/predict-delay`

## Procurement Assistant
- `POST /procurement/supplier-intelligence`

## Safety Dashboard
- `POST /safety/analyze-log`

## Document Analyzer
- `POST /document-analyzer/review`

## Cost Estimator
- `POST /cost-estimator/estimate`

## Workforce Scheduler
- `POST /workforce/optimize`

## Maintenance Predictor
- `POST /maintenance/predict`

## Progress Visualizer
- `POST /progress-visualizer/analyze`

## Tender Analyzer
- `POST /tender-analyzer/analyze`

## Runtime Verification
Run this in PowerShell to list all routes from the app object:

```powershell
@'
import sys
sys.path.insert(0, 'backend')
from app.main import app
for r in app.routes:
    methods = ','.join(sorted(list(r.methods))) if getattr(r, 'methods', None) else ''
    print(f"{methods}\t{r.path}")
'@ | python -
```
