# WorkForce AI Pro — HR Attrition Prediction & Workforce Intelligence Platform

A runnable starter/MVP for the 5-day assignment. Stack: FastAPI, SQLAlchemy, MySQL-compatible database (SQLite default for easy local demo), JWT, Pydantic, scikit-learn, React + Vite + Tailwind, Recharts.

## Implemented core MVP
- JWT login and role-aware APIs (ADMIN, HR, MANAGER, EMPLOYEE)
- Managed account administration: no public signup; ADMIN/HR create accounts, ADMIN manages roles/status and resets passwords, with reset-driven session invalidation
- Employee directory with create, profile edit, deactivate, search, department filtering APIs, and validation
- Department create/update/delete with linked-employee safeguards and department headcount analytics
- Attendance check-in/check-out, worked-hour/overtime calculation, shift definitions/assignments, attendance CSV export, and live daily summary metrics
- Leave request/review workflow, approval history, employee self-service, and configurable per-type annual policies
- Generic monthly payroll drafts with configurable allowances, bonuses, deductions, review/payment statuses, HR/Admin totals, and employee-scoped paid payslips
- Payroll assistant with period summaries, common payroll Q&A, and explainable calculation, deduction-share, and month-over-month review flags; it cannot change payroll values
- Employee account linking by exact work-email match; HR/Admin can link an existing login or create and link an EMPLOYEE account from the employee directory
- Shift-based scheduled hours, configurable unpaid break deductions, overnight shift support, and attendance snapshots
- User-scoped in-app notifications with read/unread state and ADMIN-only system audit log
- Authenticated Server-Sent Events stream for new user-scoped notifications, with automatic frontend reconnection
- Workforce dashboard with active headcount, latest-per-employee risk KPIs, and stored attendance/leave summaries
- Trainable scikit-learn attrition model, individual and batch prediction APIs, risk bands, and human-review recommendations
- Automatic risk rescoring when an active employee's prediction-driving profile changes, stored prediction history, and current high-risk alerts
- Persistent HR intervention tracking for high-risk reviews, with status updates and ownership
- Authenticated CSV workforce, attendance, and leave reports
- Responsive React dashboard with employee, prediction, alert, intervention, attendance, leave, notification, audit, and department views
- API documentation at `/docs`, demo seed script, focused API tests, and database schema notes

> Scope note: the assignment document lists 30 modules. This package is a demonstrable MVP, not a complete enterprise HRIS. Payroll is intentionally generic: it uses the employee's monthly income plus allowances and bonus, minus configured deductions, and does not calculate statutory tax or jurisdiction-specific withholdings. The payroll assistant is transparent rule-based analysis and intent-matched Q&A, not a generative AI or payroll-calculation model. Chat, document management, dataset upload/versioning, forecasting, performance reviews, task workflows, PDF/Excel exports, public account registration, email-based password recovery, and production-grade HR policies remain out of scope. The notification stream uses short-interval database polling for this single-instance demo; multi-instance production deployments should use a shared event broker. Accounts are created by ADMIN/HR (HR may create EMPLOYEE accounts); ADMIN controls roles, account status, and password resets. Employee attendance, leave, and paid-payslip self-service requires HR/Admin to link an active EMPLOYEE account to an active employee profile with the same work email. Leave allowance is a basic calendar-year policy, not holiday-aware or accrual-based. ML output is a demo estimate trained on synthetic data; it must not be used for real employment decisions without validation, bias assessment, consent, and human review.

## 1. Backend setup (Windows PowerShell)
```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python seed.py
uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs

`python-dotenv` loads the copied `.env` file. Default demo account: `admin@workforce.local` / `Admin123!` (change immediately for any shared environment). For production set `APP_ENV=production` and a unique `SECRET_KEY` of at least 32 characters.

SQLite is the default to avoid MySQL setup blocking the demo. To use MySQL, set `DATABASE_URL` in `.env` to `mysql+pymysql://user:password@localhost:3306/workforce_ai_pro` and create that database first.

## 2. Train the demo model
In another backend terminal:
```powershell
python train_model.py
```
This creates `app/ml/attrition_model.joblib`. The API can fall back to a safe demo probability if the model file is absent.

## 3. Frontend setup
```powershell
cd frontend
npm install
npm run dev
```
Open the Vite URL (usually http://localhost:5173). Login with the demo account above. Frontend API URL defaults to `http://127.0.0.1:8000`.

## 4. Test
```powershell
cd backend
pytest -q
```

## Main API routes
- `POST /api/auth/login` — OAuth2 form login; returns JWT
- `GET /api/auth/me` — current user
- `GET/POST /api/admin/users` — list and create managed user accounts (HR may create EMPLOYEE accounts)
- `PATCH /api/admin/users/{id}` — ADMIN-only role/name/status management with last-admin safeguards
- `POST /api/admin/users/{id}/reset-password` — ADMIN-only password reset; invalidates application sessions
- `GET/POST /api/employees` — search/list/create employees (`limit` up to 500)
- `GET/PUT/DELETE /api/employees/{id}` — employee details/update/deactivate
- `GET/POST /api/departments` — department list/create
- `GET /api/dashboard/summary` — workforce KPIs
- `GET /api/payroll?employee_id=ID&period_start=YYYY-MM-DD` — payroll records for ADMIN/HR; employees may view only their own paid payslips
- `POST /api/payroll/assistant` — period totals, payroll Q&A, and explainable review flags; employees only see their own paid records, and the assistant never edits payroll
- `POST /api/payroll` — generate an ADMIN/HR monthly payroll draft for an active employee
- `PATCH /api/payroll/{id}/status` — ADMIN/HR transition Draft → Approved → Paid
- `POST /api/ai/predict/{employee_id}` — create an individual attrition risk prediction
- `POST /api/ai/predict` — score all active employees in one batch (maximum 500)
- `GET /api/ai/predictions` — prediction history
- `GET /api/ai/alerts` — high-risk employee alerts
- `GET/POST /api/interventions` — list interventions and start a support check-in (ADMIN/HR only)
- `PATCH /api/interventions/{id}` — update intervention status or notes (ADMIN/HR)
- `POST/GET /api/shifts` — create/list shifts; `POST /api/shifts/assignments` assigns an active employee shift (ADMIN/HR)
- `POST /api/attendance/check-in`, `POST /api/attendance/check-out`, `GET /api/attendance` — ADMIN/HR may manage attendance; linked EMPLOYEE accounts may access their own attendance
- `POST/GET /api/leaves`, `PATCH /api/leaves/{id}` — linked employees submit/view their own requests; ADMIN/HR may review requests and access the workforce queue
- `GET /api/leaves/balance?leave_type=Annual&year=YYYY` or `/api/leaves/balance/{employee_id}` — personal balance for employees, or a selected employee's balance for ADMIN/HR
- `GET/POST /api/leave-policies`, `PATCH /api/leave-policies/{id}` — configure allowance, year, and active state (ADMIN/HR)
- `GET /api/me/employee`, `GET /api/users`, `PUT /api/employees/{id}/account` — self profile and HR/Admin employee account linking
- `GET /api/notifications`, `PATCH /api/notifications/{id}/read` — personal notification inbox and read status
- `GET /api/notifications/stream?after_id=ID` — authenticated Server-Sent Events stream of new notifications for the current user
- `GET /api/audit-logs` — administrative action history (ADMIN only)
- `GET /api/reports/workforce.csv`, `GET /api/reports/attendance.csv` — workforce and attendance CSV exports (ADMIN/HR only)
- `GET /api/reports/leaves.csv` — leave CSV export, optionally filtered by status, employee, and date range (ADMIN/HR only)

New employees are scored on creation. Changes to tenure, monthly income, satisfaction, work-life balance, overtime, promotion timing, or active status save a new risk prediction in the same transaction. This updates current alert and dashboard data without requiring a separate batch run. Dashboard daily attendance metrics and attendance report date filters use UTC dates because attendance timestamps are stored as naive UTC datetimes; leave-date metrics use calendar dates. CSV reports include employee identifiers, name, department, job title, and the latest risk score/confidence when available; workforce reports are restricted to ADMIN/HR. Leave reports may be filtered by status, employee, and overlapping date range and are capped at 5,000 records. Attendance records snapshot the assigned shift at check-in; worked hours subtract its unpaid break, scheduled hours account for overnight shifts, and overtime is the excess above the shift's net scheduled duration (8 hours when no shift is assigned). A linked EMPLOYEE account can check in/out, view only its own attendance and leave requests, and view only its paid payslips. Leave requests must stay within one calendar year; approved usage is counted as inclusive calendar days against the configured active policy for that leave type and year. Seed data creates 20 Annual and 10 Sick days for the current year. These are basic policies, not holiday-aware or accrual-based. Payroll periods must cover one full calendar month, and only one record per employee/month is allowed. Payroll uses the employee's monthly income as base salary, rounds monetary values to two decimal places, and rejects deductions greater than gross pay. It does not compute taxes. The legacy-schema startup migration adds the employee account link, session version, and attendance/shift fields; `payroll_records` is created by SQLAlchemy metadata on startup. MySQL migration behavior should be validated in the target deployment before production use.

## Five-day delivery plan
| Day | Priority | Exit criteria |
|---|---|---|
| 1 | Authentication, database schema, seed data, and role checks | Local login succeeds; schema and demo data are repeatable. Registration/password recovery remain planned. |
| 2 | Employee, department, attendance, and leave management | Employee/department CRUD, shift rules, HR operations, and linked employee self-service validated |
| 3 | Attrition model and monitoring APIs | Individual/batch scoring, automatic rescoring, prediction history, alerts, notifications, and limitations documented |
| 4 | Workforce dashboard and API integration | Dashboard, workforce operations, interventions, audit history, and CSV reports use stored API data |
| 5 | Integration testing, demo evidence, API/schema docs, and release review | Backend tests and frontend build pass; demo flow, screenshots, and remaining scope recorded |

The 30-module specification is a broader roadmap; chat, documents, dataset management, forecasting, real-time monitoring, and other Phase 2/3 features are not implemented in this core MVP.
