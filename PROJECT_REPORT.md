# WorkForce AI Pro — Project Report

## Objective
Build an AI-assisted workforce intelligence platform to support HR teams with workforce KPIs, employee records, attrition-risk estimates, alerts, and a review workflow.

## Architecture
- React/Vite/Tailwind UI → Axios → FastAPI REST API
- FastAPI → Pydantic validation → SQLAlchemy ORM → SQLite by default / MySQL in configured deployment
- Attrition API → scikit-learn pipeline (or documented heuristic fallback) → prediction history
- JWT bearer token protects APIs; ADMIN and HR can manage employee data, managers can request predictions, authenticated roles can view dashboards.

## Current demo flow
1. Seed demo employees and departments.
2. Admin signs in and receives a JWT.
3. Dashboard requests workforce summary and employee list.
4. HR/Admin/Manager triggers individual or batch AI prediction for active employees.
5. Prediction stores risk percentage, risk band, model version, confidence-like score, and signal explanation.
6. Latest-per-active-employee scores determine the dashboard KPI and current high-risk alerts; all scores remain in prediction history.

## Data model
`users`, `departments`, `employees`, and `predictions`. Foreign keys connect employees to departments and predictions to employees. See `backend/schema.sql`.

## Validation
- API OpenAPI documentation: `/docs`
- API tests: `py -m pytest -q`
- Frontend production build: `npm run build`

## Live test evidence
On 23 October 2026, the running local Swagger UI and authenticated dashboard were checked. The API health route, Swagger UI, OpenAPI schema (39 paths), demo ADMIN login, authenticated identity, and dashboard summary succeeded; an unauthenticated employee-list request returned 401. The backend suite passed (17 tests), and the frontend production build completed successfully with a bundle-size advisory.

Evidence, including full-page and readable screenshots, is in [evidence/](./evidence/):
- [10-page live test report](./evidence/WorkForce_AI_Pro_Live_Test_Report.pdf)
- [Swagger full-page screenshot](./evidence/swagger-live.png) and [route screenshot](./evidence/swagger-routes.png)
- [Dashboard full-page screenshot](./evidence/dashboard-live.png) and [summary screenshot](./evidence/dashboard-summary.png)

## Delivery plan
See the five-day schedule in [README.md](./README.md). The plan prioritizes auth/schema and seed data, workforce CRUD, prediction and monitoring APIs, frontend integration, then final tests and demo evidence.

## Important limitations
The training dataset is synthetic and only demonstrates the ML pipeline. A reported score is not a validated probability of resignation, and the confidence-like field is not a calibrated model confidence. The displayed monthly trend is illustrative. Before production use: validate on representative, consented data; check fairness and data leakage; calibrate probabilities; log model versions; encrypt secrets; add rate limiting, password reset, audit trail, monitoring, backups, and formal human review. Never make employment decisions automatically from a risk score.

## Roadmap to cover the full 30-module specification
Attendance/shifts → leave → payroll/payslips → notifications → chat → documents → dataset versioning → forecasting → interventions/follow-up → report export → audit logs → workflow/tasks → performance reviews → advanced search → live feed/WebSockets → integration and load tests.
