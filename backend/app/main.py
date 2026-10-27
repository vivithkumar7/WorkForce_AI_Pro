import asyncio
import csv
import io
import json
import os
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, OAuth2PasswordRequestForm
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from . import models, schemas
from .database import Base, SessionLocal, engine, get_db, upgrade_legacy_columns
from .ml.predictor import predict
from .security import (
    create_access_token,
    authenticate_access_token,
    get_current_user,
    hash_password,
    require_roles,
    verify_password,
)

Base.metadata.create_all(bind=engine)
upgrade_legacy_columns()

app = FastAPI(
    title="WorkForce AI Pro API",
    version="1.0.0",
    description="HR workforce analytics and demo attrition risk APIs",
)
origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREDICTION_BATCH_LIMIT = 500
notification_stream_bearer = HTTPBearer(auto_error=False)


def latest_prediction_ids(db: Session):
    return (
        db.query(func.max(models.Prediction.id).label("id"))
        .group_by(models.Prediction.employee_id)
        .subquery()
    )


def current_predictions(db: Session):
    latest_ids = latest_prediction_ids(db)
    return (
        db.query(models.Prediction)
        .join(latest_ids, models.Prediction.id == latest_ids.c.id)
        .join(models.Employee, models.Prediction.employee_id == models.Employee.id)
        .filter(models.Employee.is_active.is_(True))
        .options(
            joinedload(models.Prediction.employee).joinedload(models.Employee.department)
        )
    )


def prediction_response(row: models.Prediction) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_name": row.employee.full_name,
        "department": row.employee.department.name,
        "risk_percent": row.risk_percent,
        "risk_level": row.risk_level,
        "confidence_score": row.confidence_score,
        "explanation": row.explanation,
        "created_at": row.created_at.isoformat(),
    }


def record_audit(
    db: Session,
    actor: models.User,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: str = "",
) -> None:
    db.add(
        models.AuditLog(
            actor_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details[:1000],
        )
    )


def notify_roles(
    db: Session,
    roles: tuple[str, ...],
    title: str,
    message: str,
) -> None:
    recipients = db.query(models.User).filter(
        models.User.role.in_(roles),
        models.User.is_active.is_(True),
    )
    db.add_all(
        [
            models.Notification(
                user_id=user.id,
                title=title,
                message=message[:1000],
            )
            for user in recipients
        ]
    )


def notify_user(
    db: Session,
    user_id: int | None,
    title: str,
    message: str,
) -> None:
    if user_id is None:
        return
    db.add(
        models.Notification(
            user_id=user_id,
            title=title,
            message=message[:1000],
        )
    )


def linked_employee(db: Session, user: models.User) -> models.Employee:
    employee = db.query(models.Employee).filter(
        models.Employee.user_id == user.id,
        models.Employee.is_active.is_(True),
    ).first()
    if not employee:
        raise HTTPException(
            status_code=403,
            detail="Your account is not linked to an active employee profile",
        )
    return employee


def resolve_employee_id(
    db: Session,
    user: models.User,
    requested_employee_id: int | None,
    allowed_roles: tuple[str, ...] = ("ADMIN", "HR"),
) -> int:
    if user.role == "EMPLOYEE":
        employee = linked_employee(db, user)
        if requested_employee_id is not None and requested_employee_id != employee.id:
            raise HTTPException(status_code=403, detail="Cannot access another employee record")
        return employee.id
    if user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    if requested_employee_id is None:
        raise HTTPException(status_code=422, detail="employee_id is required")
    return requested_employee_id


def notify_risk_transition(
    db: Session,
    employee: models.Employee,
    prediction: models.Prediction,
) -> None:
    previous = (
        db.query(models.Prediction)
        .filter(models.Prediction.employee_id == employee.id)
        .order_by(models.Prediction.id.desc())
        .first()
    )
    if prediction.risk_level == "High" and (
        previous is None or previous.risk_level != "High"
    ):
        notify_roles(
            db,
            ("ADMIN", "HR"),
            "High attrition risk flagged",
            f"{employee.full_name} has entered the high-risk band and needs confidential human review.",
        )


def payroll_response(row: models.PayrollRecord) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_code": row.employee.employee_code,
        "employee_name": row.employee.full_name,
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "base_salary": float(row.base_salary),
        "allowances": float(row.allowances),
        "bonus": float(row.bonus),
        "deductions": float(row.deductions),
        "net_pay": float(row.net_pay),
        "status": row.status,
        "created_at": row.created_at.isoformat(),
    }


@app.get("/")
def root():
    return {"name": "WorkForce AI Pro API", "docs": "/docs", "status": "running"}


@app.post("/api/auth/login", response_model=schemas.LoginResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.email == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    return {
        "access_token": create_access_token(
            user.email,
            user.role,
            user.session_version,
        ),
        "token_type": "bearer",
    }


@app.get("/api/auth/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@app.get("/api/users")
def list_employee_accounts(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    rows = db.query(models.User).filter(
        models.User.role == "EMPLOYEE",
        models.User.is_active.is_(True),
    ).order_by(models.User.full_name).limit(500).all()
    linked_user_ids = {
        employee.user_id
        for employee in db.query(models.Employee.user_id).filter(
            models.Employee.user_id.is_not(None)
        )
    }
    return [
        {
            "id": row.id,
            "full_name": row.full_name,
            "email": row.email,
            "is_linked": row.id in linked_user_ids,
        }
        for row in rows
    ]


@app.get("/api/admin/users")
def list_managed_users(
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    rows = db.query(models.User).order_by(
        models.User.full_name,
        models.User.id,
    ).limit(limit).all()
    return [
        {
            "id": row.id,
            "email": row.email,
            "full_name": row.full_name,
            "role": row.role,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@app.post("/api/admin/users", status_code=201)
def create_managed_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    if user.role == "HR" and payload.role != "EMPLOYEE":
        raise HTTPException(
            status_code=403,
            detail="HR can create EMPLOYEE accounts only",
        )
    email = str(payload.email).casefold()
    existing = db.query(models.User).filter(
        func.lower(models.User.email) == email
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    row = models.User(
        email=email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(row)
    db.flush()
    record_audit(db, user, "user.created", "user", row.id, f"role={row.role}")
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "role": row.role,
        "is_active": row.is_active,
    }


@app.patch("/api/admin/users/{user_id}")
def update_managed_user(
    user_id: int,
    payload: schemas.UserAdminUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN")),
):
    row = db.get(models.User, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    updates = payload.model_dump(exclude_unset=True)
    next_role = updates.get("role", row.role)
    next_active = updates.get("is_active", row.is_active)
    if row.id == user.id and (next_role != "ADMIN" or not next_active):
        raise HTTPException(
            status_code=409,
            detail="You cannot remove your own active ADMIN access",
        )
    if row.role == "ADMIN" and (next_role != "ADMIN" or not next_active):
        remaining_admins = db.query(models.User).filter(
            models.User.role == "ADMIN",
            models.User.is_active.is_(True),
            models.User.id != row.id,
        ).count()
        if remaining_admins == 0:
            raise HTTPException(
                status_code=409,
                detail="At least one active ADMIN account must remain",
            )
    for field, value in updates.items():
        setattr(row, field, value)
    record_audit(
        db,
        user,
        "user.updated",
        "user",
        row.id,
        ", ".join(f"{field}={value}" for field, value in updates.items()),
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "role": row.role,
        "is_active": row.is_active,
    }


@app.post("/api/admin/users/{user_id}/reset-password")
def reset_managed_user_password(
    user_id: int,
    payload: schemas.PasswordReset,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN")),
):
    row = db.get(models.User, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    row.hashed_password = hash_password(payload.password)
    row.session_version = os.urandom(16).hex()
    record_audit(db, user, "user.password_reset", "user", row.id)
    db.commit()
    return {
        "message": "Password reset successfully. The user must sign in with the new password."
    }


@app.get("/api/departments", response_model=list[schemas.DepartmentOut])
def departments(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return db.query(models.Department).order_by(models.Department.name).all()


@app.post("/api/departments", response_model=schemas.DepartmentOut)
def create_department(
    payload: schemas.DepartmentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    if db.query(models.Department).filter(models.Department.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Department already exists")
    row = models.Department(**payload.model_dump())
    db.add(row)
    db.flush()
    record_audit(db, user, "department.created", "department", row.id, row.name)
    db.commit()
    db.refresh(row)
    return row


@app.put("/api/departments/{department_id}", response_model=schemas.DepartmentOut)
def update_department(
    department_id: int,
    payload: schemas.DepartmentUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.get(models.Department, department_id)
    if not row:
        raise HTTPException(status_code=404, detail="Department not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide department fields to update")
    if "name" in updates and db.query(models.Department).filter(
        models.Department.name == updates["name"],
        models.Department.id != department_id,
    ).first():
        raise HTTPException(status_code=409, detail="Department already exists")
    for key, value in updates.items():
        setattr(row, key, value)
    record_audit(db, user, "department.updated", "department", row.id, row.name)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/api/departments/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.get(models.Department, department_id)
    if not row:
        raise HTTPException(status_code=404, detail="Department not found")
    if db.query(models.Employee).filter(
        models.Employee.department_id == department_id
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Reassign or deactivate department employees before deletion",
        )
    record_audit(db, user, "department.deleted", "department", row.id, row.name)
    db.delete(row)
    db.commit()
    return {"message": "Department deleted"}


@app.get("/api/employees", response_model=list[schemas.EmployeeOut])
def employees(
    q: str | None = Query(default=None, max_length=120),
    department_id: int | None = Query(default=None, ge=1),
    active: bool | None = True,
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    query = db.query(models.Employee).options(joinedload(models.Employee.department))
    if q:
        search = f"%{q.strip()}%"
        query = query.filter(
            (models.Employee.full_name.ilike(search))
            | (models.Employee.email.ilike(search))
            | (models.Employee.employee_code.ilike(search))
        )
    if department_id is not None:
        query = query.filter(models.Employee.department_id == department_id)
    if active is not None:
        query = query.filter(models.Employee.is_active.is_(active))
    return query.order_by(models.Employee.full_name).limit(limit).all()


@app.post("/api/employees", response_model=schemas.EmployeeOut, status_code=201)
def create_employee(
    payload: schemas.EmployeeCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    duplicate = db.query(models.Employee).filter(
        (models.Employee.email == payload.email)
        | (models.Employee.employee_code == payload.employee_code)
    ).first()
    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Employee email or code already exists",
        )
    if not db.query(models.Department).filter(
        models.Department.id == payload.department_id
    ).first():
        raise HTTPException(status_code=404, detail="Department not found")
    row = models.Employee(**payload.model_dump())
    db.add(row)
    db.flush()
    prediction = create_prediction(row)
    notify_risk_transition(db, row, prediction)
    db.add(prediction)
    record_audit(db, user, "employee.created", "employee", row.id, row.employee_code)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/employees/{employee_id}", response_model=schemas.EmployeeOut)
def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    row = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(models.Employee.id == employee_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    return row


@app.get("/api/me/employee", response_model=schemas.EmployeeOut)
def my_employee_profile(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("EMPLOYEE")),
):
    employee = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(
            models.Employee.user_id == user.id,
            models.Employee.is_active.is_(True),
        )
        .first()
    )
    if not employee:
        raise HTTPException(
            status_code=403,
            detail="Your account is not linked to an active employee profile",
        )
    return employee


@app.put("/api/employees/{employee_id}/account")
def link_employee_account(
    employee_id: int,
    payload: schemas.EmployeeLink,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    employee = db.get(models.Employee, employee_id)
    account = db.get(models.User, payload.user_id)
    if not employee or not employee.is_active:
        raise HTTPException(status_code=404, detail="Active employee not found")
    if not account or not account.is_active or account.role != "EMPLOYEE":
        raise HTTPException(status_code=404, detail="Active EMPLOYEE account not found")
    if employee.email.casefold() != account.email.casefold():
        raise HTTPException(
            status_code=409,
            detail="Employee and account email addresses must match",
        )
    existing = db.query(models.Employee).filter(
        models.Employee.user_id == account.id,
        models.Employee.id != employee.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Account is already linked to another employee")
    employee.user_id = account.id
    record_audit(db, user, "employee.account_linked", "employee", employee.id, account.email)
    db.commit()
    return {"employee_id": employee.id, "user_id": account.id, "linked": True}


@app.put("/api/employees/{employee_id}", response_model=schemas.EmployeeOut)
def update_employee(
    employee_id: int,
    payload: schemas.EmployeeUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.get(models.Employee, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    updates = payload.model_dump(exclude_unset=True)
    if "department_id" in updates and not db.query(models.Department).filter(
        models.Department.id == updates["department_id"]
    ).first():
        raise HTTPException(status_code=404, detail="Department not found")
    for key, value in updates.items():
        setattr(row, key, value)
    prediction_fields = {
        "tenure_years",
        "monthly_income",
        "job_satisfaction",
        "work_life_balance",
        "overtime",
        "years_since_promotion",
        "is_active",
    }
    if row.is_active and prediction_fields.intersection(updates):
        prediction = create_prediction(row)
        notify_risk_transition(db, row, prediction)
        db.add(prediction)
    record_audit(db, user, "employee.updated", "employee", row.id, row.employee_code)
    db.commit()
    db.refresh(row)
    return row


@app.delete("/api/employees/{employee_id}")
def deactivate_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.get(models.Employee, employee_id)
    if not row:
        raise HTTPException(status_code=404, detail="Employee not found")
    row.is_active = False
    record_audit(db, user, "employee.deactivated", "employee", row.id, row.employee_code)
    db.commit()
    return {"message": "Employee deactivated"}


@app.get("/api/dashboard/summary")
def dashboard(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    active_count = db.query(models.Employee).filter(
        models.Employee.is_active.is_(True)
    ).count()
    department_count = db.query(models.Department).count()
    latest = current_predictions(db).all()
    latest.sort(key=lambda prediction: (prediction.created_at, prediction.id), reverse=True)
    attendance_day = datetime.now(timezone.utc).date()
    day_start = datetime.combine(attendance_day, datetime.min.time())
    day_end = datetime.combine(attendance_day, datetime.max.time())
    attendance_today = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.check_in >= day_start,
        models.AttendanceRecord.check_in <= day_end,
    ).all()
    approved_leave_today = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= date.today(),
        models.LeaveRequest.end_date >= date.today(),
    ).count()
    pending_leave_requests = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.status == "Pending"
    ).count()

    department_rows = (
        db.query(models.Department.name, func.count(models.Employee.id))
        .outerjoin(
            models.Employee,
            (models.Employee.department_id == models.Department.id)
            & models.Employee.is_active.is_(True),
        )
        .group_by(models.Department.id, models.Department.name)
        .order_by(models.Department.name)
        .all()
    )
    summary = {
        "total_employees": active_count,
        "departments": department_count,
        "attendance_check_ins_today": len(attendance_today),
        "attendance_open_sessions_today": sum(
            record.check_out is None for record in attendance_today
        ),
        "approved_leave_today": approved_leave_today,
        "pending_leave_requests": pending_leave_requests,
        "high_risk_employees": sum(
            prediction.risk_level == "High" for prediction in latest
        ),
        "average_attrition_risk": (
            round(sum(prediction.risk_percent for prediction in latest) / len(latest), 1)
            if latest
            else 0
        ),
        "department_headcount": [
            {"department": name, "employees": count}
            for name, count in department_rows
        ],
        "recent_predictions": [
            {
                "employee_id": prediction.employee_id,
                "employee_name": prediction.employee.full_name,
                "department": prediction.employee.department.name,
                "risk_percent": prediction.risk_percent,
                "risk_level": prediction.risk_level,
                "created_at": prediction.created_at.isoformat(),
            }
            for prediction in latest[:6]
        ],
    }
    if user.role in ("ADMIN", "HR"):
        payroll_month = date(attendance_day.year, attendance_day.month, 1)
        payroll_count = db.query(models.PayrollRecord).filter(
            models.PayrollRecord.period_start == payroll_month
        ).count()
        payroll_total = db.query(
            func.coalesce(func.sum(models.PayrollRecord.net_pay), 0)
        ).filter(
            models.PayrollRecord.period_start == payroll_month
        ).scalar()
        summary["payroll_records_this_month"] = payroll_count
        summary["payroll_net_total_this_month"] = float(payroll_total or 0)
    return summary


def create_prediction(employee: models.Employee) -> models.Prediction:
    return models.Prediction(employee_id=employee.id, **predict(employee))


@app.get("/api/payroll")
def list_payroll(
    employee_id: int | None = Query(default=None, ge=1),
    period_start: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    query = db.query(models.PayrollRecord)
    if user.role == "EMPLOYEE":
        own_employee_id = linked_employee(db, user).id
        if employee_id is not None and employee_id != own_employee_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot access another employee's payroll",
            )
        employee_id = own_employee_id
        query = query.filter(models.PayrollRecord.status == "Paid")
    if employee_id is not None:
        query = query.filter(models.PayrollRecord.employee_id == employee_id)
    if period_start is not None:
        query = query.filter(models.PayrollRecord.period_start == period_start)
    rows = query.order_by(
        models.PayrollRecord.period_start.desc(),
        models.PayrollRecord.id.desc(),
    ).limit(limit).all()
    return [payroll_response(row) for row in rows]


@app.post("/api/payroll/assistant")
def payroll_assistant(
    payload: schemas.PayrollAssistantRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    query = db.query(models.PayrollRecord).options(
        joinedload(models.PayrollRecord.employee)
    )
    if user.role == "EMPLOYEE":
        employee_id = linked_employee(db, user).id
        query = query.filter(
            models.PayrollRecord.employee_id == employee_id,
            models.PayrollRecord.status == "Paid",
        )
    if payload.period_start:
        query = query.filter(
            models.PayrollRecord.period_start == payload.period_start
        )
        period_start = payload.period_start
    else:
        period_start = query.with_entities(
            func.max(models.PayrollRecord.period_start)
        ).scalar()
        if period_start is not None:
            query = query.filter(
                models.PayrollRecord.period_start == period_start
            )

    if period_start is None:
        return {
            "period_start": None,
            "record_count": 0,
            "totals": {
                "base_salary": 0,
                "allowances": 0,
                "gross_pay": 0,
                "net_pay": 0,
                "deductions": 0,
                "bonuses": 0,
                "average_net_pay": 0,
            },
            "status_counts": {},
            "alerts": [],
            "answer": "There are no payroll records available in your account scope yet.",
        }

    rows = query.options(
        joinedload(models.PayrollRecord.employee)
    ).order_by(models.PayrollRecord.employee_id).all()
    employee_ids = [row.employee_id for row in rows]
    previous_month = (
        date(period_start.year - 1, 12, 1)
        if period_start.month == 1
        else date(period_start.year, period_start.month - 1, 1)
    )
    previous_rows = []
    if employee_ids:
        previous_rows = db.query(models.PayrollRecord).filter(
            models.PayrollRecord.employee_id.in_(employee_ids),
            models.PayrollRecord.period_start == previous_month,
        ).all()
    previous_by_employee = {row.employee_id: row for row in previous_rows}

    totals = {
        "base_salary": Decimal("0.00"),
        "allowances": Decimal("0.00"),
        "gross_pay": Decimal("0.00"),
        "net_pay": Decimal("0.00"),
        "deductions": Decimal("0.00"),
        "bonuses": Decimal("0.00"),
    }
    status_counts: dict[str, int] = {}
    alerts = []
    for row in rows:
        base = Decimal(row.base_salary)
        allowances = Decimal(row.allowances)
        bonus = Decimal(row.bonus)
        deductions = Decimal(row.deductions)
        net = Decimal(row.net_pay)
        gross = base + allowances + bonus
        totals["base_salary"] += base
        totals["allowances"] += allowances
        totals["gross_pay"] += gross
        totals["net_pay"] += net
        totals["deductions"] += deductions
        totals["bonuses"] += bonus
        status_counts[row.status] = status_counts.get(row.status, 0) + 1

        def add_alert(category: str, message: str) -> None:
            alerts.append(
                {
                    "payroll_id": row.id,
                    "employee_name": row.employee.full_name,
                    "category": category,
                    "message": message,
                }
            )

        expected_net = gross - deductions
        if abs(net - expected_net) > Decimal("0.01"):
            add_alert(
                "Calculation mismatch",
                "Stored net pay does not match base salary + allowances + bonus - deductions.",
            )
        if gross > 0 and deductions / gross >= Decimal("0.40"):
            add_alert(
                "High deduction share",
                "Deductions are at least 40% of gross pay; review the entry and applicable policy.",
            )
        previous = previous_by_employee.get(row.employee_id)
        if previous and Decimal(previous.net_pay) > 0:
            change_ratio = abs(net - Decimal(previous.net_pay)) / Decimal(
                previous.net_pay
            )
            if change_ratio > Decimal("0.20"):
                add_alert(
                    "Large month-over-month change",
                    "Net pay changed by more than 20% from the previous month; verify the reason.",
                )

    record_count = len(rows)
    average_net = (
        totals["net_pay"] / record_count
        if record_count
        else Decimal("0.00")
    )
    question = payload.question.casefold()
    period_label = period_start.strftime("%B %Y")
    if not rows:
        answer = f"There are no payroll records for {period_label} in your account scope."
    elif "breakdown" in question or "salary" in question:
        answer = (
            f"{period_label} payroll breakdown: base salary "
            f"{totals['base_salary']:,.2f}, allowances {totals['allowances']:,.2f}, "
            f"bonuses {totals['bonuses']:,.2f}, deductions "
            f"{totals['deductions']:,.2f}, and net pay {totals['net_pay']:,.2f}."
        )
    elif "deduction" in question:
        answer = (
            f"Total deductions for {period_label} are "
            f"{totals['deductions']:,.2f} across {record_count} payroll record(s)."
        )
    elif "bonus" in question:
        answer = (
            f"Total bonuses for {period_label} are "
            f"{totals['bonuses']:,.2f} across {record_count} payroll record(s)."
        )
    elif "average" in question or "avg" in question:
        answer = (
            f"Average net pay for {period_label} is "
            f"{average_net:,.2f} across {record_count} payroll record(s)."
        )
    elif any(word in question for word in ("how many", "employee", "record", "count")):
        answer = (
            f"There are {record_count} payroll record(s) for {period_label}. "
            f"Status counts: {', '.join(f'{status}: {count}' for status, count in sorted(status_counts.items()))}."
        )
    else:
        answer = (
            f"For {period_label}, net payroll is {totals['net_pay']:,.2f} "
            f"across {record_count} record(s), with {len(alerts)} item(s) flagged for review."
        )

    return {
        "period_start": period_start.isoformat(),
        "record_count": record_count,
        "totals": {
            key: float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            for key, value in totals.items()
        }
        | {
            "average_net_pay": float(
                average_net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
        },
        "status_counts": status_counts,
        "alerts": alerts[:100],
        "answer": answer,
    }


@app.post("/api/payroll", status_code=201)
def generate_payroll(
    payload: schemas.PayrollGenerate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == payload.employee_id,
        models.Employee.is_active.is_(True),
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Active employee not found")
    existing = db.query(models.PayrollRecord).filter(
        models.PayrollRecord.employee_id == employee.id,
        models.PayrollRecord.period_start == payload.period_start,
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Payroll already exists for this employee and period",
        )
    base_salary = Decimal(str(employee.monthly_income)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    gross_pay = base_salary + payload.allowances + payload.bonus
    if payload.deductions > gross_pay:
        raise HTTPException(
            status_code=422,
            detail="Deductions cannot exceed gross pay",
        )
    row = models.PayrollRecord(
        employee_id=employee.id,
        period_start=payload.period_start,
        period_end=payload.period_end,
        base_salary=base_salary,
        allowances=payload.allowances,
        bonus=payload.bonus,
        deductions=payload.deductions,
        net_pay=gross_pay - payload.deductions,
        status="Draft",
        generated_by_id=user.id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        user,
        "payroll.generated",
        "payroll",
        row.id,
        f"employee={employee.employee_code}; period={payload.period_start.isoformat()}",
    )
    db.commit()
    db.refresh(row)
    row.employee = employee
    return payroll_response(row)


@app.patch("/api/payroll/{payroll_id}/status")
def update_payroll_status(
    payroll_id: int,
    payload: schemas.PayrollStatusUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.query(models.PayrollRecord).options(
        joinedload(models.PayrollRecord.employee)
    ).filter(models.PayrollRecord.id == payroll_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Payroll record not found")
    allowed_transition = (
        (row.status == "Draft" and payload.status == "Approved")
        or (row.status == "Approved" and payload.status == "Paid")
    )
    if not allowed_transition:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change payroll from {row.status} to {payload.status}",
        )
    row.status = payload.status
    record_audit(
        db,
        user,
        f"payroll.{payload.status.lower()}",
        "payroll",
        row.id,
        row.employee.employee_code,
    )
    notify_user(
        db,
        row.employee.user_id,
        f"Payroll {payload.status.lower()}",
        f"Your payroll for {row.period_start:%B %Y} is {payload.status.lower()}.",
    )
    db.commit()
    db.refresh(row)
    return payroll_response(row)


@app.post("/api/ai/predict/{employee_id}")
def predict_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    employee = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(
            models.Employee.id == employee_id,
            models.Employee.is_active.is_(True),
        )
        .first()
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Active employee not found")
    row = create_prediction(employee)
    notify_risk_transition(db, employee, row)
    record_audit(db, user, "prediction.created", "employee", employee.id, row.risk_level)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        **prediction_response(row),
        "alert_triggered": row.risk_level == "High",
    }


@app.post("/api/ai/predict")
def predict_active_employees(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    employees_to_score = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(models.Employee.is_active.is_(True))
        .order_by(models.Employee.id)
        .limit(PREDICTION_BATCH_LIMIT + 1)
        .all()
    )
    if len(employees_to_score) > PREDICTION_BATCH_LIMIT:
        raise HTTPException(
            status_code=413,
            detail=f"Batch prediction is limited to {PREDICTION_BATCH_LIMIT} active employees",
        )
    rows = []
    for employee in employees_to_score:
        row = create_prediction(employee)
        notify_risk_transition(db, employee, row)
        rows.append(row)
    record_audit(
        db,
        user,
        "predictions.batch_created",
        "workforce",
        None,
        f"processed={len(rows)}",
    )
    db.add_all(rows)
    db.commit()
    high_risk_count = sum(row.risk_level == "High" for row in rows)
    return {
        "processed_count": len(rows),
        "high_risk_count": high_risk_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/ai/predictions")
def predictions(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    rows = (
        db.query(models.Prediction)
        .options(
            joinedload(models.Prediction.employee).joinedload(
                models.Employee.department
            )
        )
        .order_by(models.Prediction.created_at.desc(), models.Prediction.id.desc())
        .limit(limit)
        .all()
    )
    return [prediction_response(row) for row in rows]


@app.get("/api/ai/alerts")
def alerts(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "MANAGER")),
):
    rows = current_predictions(db).filter(
        models.Prediction.risk_level == "High"
    ).order_by(models.Prediction.created_at.desc()).limit(50).all()
    return [
        {
            "id": row.id,
            "employee_id": row.employee_id,
            "employee_name": row.employee.full_name,
            "department": row.employee.department.name,
            "risk_percent": row.risk_percent,
            "priority": "HIGH",
            "recommendation": (
                "Schedule a confidential HR check-in; review workload, growth "
                "opportunities, and support needs."
            ),
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def intervention_response(row: models.Intervention) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_name": row.employee.full_name,
        "department": row.employee.department.name,
        "created_by": row.created_by.full_name,
        "intervention_type": row.intervention_type,
        "status": row.status,
        "notes": row.notes,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
    }


@app.get("/api/interventions")
def interventions(
    status: str | None = Query(default=None, pattern="^(Open|In Progress|Completed)$"),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    query = (
        db.query(models.Intervention)
        .options(
            joinedload(models.Intervention.employee).joinedload(
                models.Employee.department
            ),
            joinedload(models.Intervention.created_by),
        )
    )
    if status:
        query = query.filter(models.Intervention.status == status)
    rows = query.order_by(
        models.Intervention.updated_at.desc(), models.Intervention.id.desc()
    ).limit(200).all()
    return [intervention_response(row) for row in rows]


@app.post("/api/interventions", status_code=201)
def create_intervention(
    payload: schemas.InterventionCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    employee = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(
            models.Employee.id == payload.employee_id,
            models.Employee.is_active.is_(True),
        )
        .first()
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Active employee not found")
    row = models.Intervention(
        **payload.model_dump(),
        created_by_id=user.id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        user,
        "intervention.created",
        "intervention",
        row.id,
        employee.employee_code,
    )
    db.commit()
    db.refresh(row)
    row.employee = employee
    row.created_by = user
    return intervention_response(row)


@app.patch("/api/interventions/{intervention_id}")
def update_intervention(
    intervention_id: int,
    payload: schemas.InterventionUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = (
        db.query(models.Intervention)
        .options(
            joinedload(models.Intervention.employee).joinedload(
                models.Employee.department
            ),
            joinedload(models.Intervention.created_by),
        )
        .filter(models.Intervention.id == intervention_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Intervention not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide a status or notes update")
    for key, value in updates.items():
        setattr(row, key, value)
    record_audit(
        db,
        user,
        "intervention.updated",
        "intervention",
        row.id,
        ",".join(updates.keys()),
    )
    db.commit()
    db.refresh(row)
    return intervention_response(row)


@app.get("/api/reports/workforce.csv")
def workforce_report(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    employees = (
        db.query(models.Employee)
        .options(joinedload(models.Employee.department))
        .filter(models.Employee.is_active.is_(True))
        .order_by(models.Employee.employee_code)
        .all()
    )
    latest_by_employee = {
        row.employee_id: row for row in current_predictions(db).all()
    }
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "employee_code",
            "employee_name",
            "department",
            "job_title",
            "risk_percent",
            "risk_level",
            "confidence_score",
            "prediction_created_at",
        ]
    )
    for employee in employees:
        prediction = latest_by_employee.get(employee.id)
        writer.writerow(
            [
                employee.employee_code,
                employee.full_name,
                employee.department.name,
                employee.job_title,
                prediction.risk_percent if prediction else "",
                prediction.risk_level if prediction else "",
                prediction.confidence_score if prediction else "",
                prediction.created_at.isoformat() if prediction else "",
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="workforce-analytics.csv"'},
    )


@app.post("/api/shifts", status_code=201)
def create_shift(
    payload: schemas.ShiftCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    if db.query(models.Shift).filter(models.Shift.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Shift already exists")
    row = models.Shift(**payload.model_dump())
    db.add(row)
    db.flush()
    record_audit(db, user, "shift.created", "shift", row.id, row.name)
    db.commit()
    db.refresh(row)
    return row


@app.get("/api/shifts")
def list_shifts(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return db.query(models.Shift).filter(
        models.Shift.is_active.is_(True)
    ).order_by(models.Shift.name).all()


@app.post("/api/shifts/assignments", status_code=201)
def assign_shift(
    payload: schemas.ShiftAssignmentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    employee = db.query(models.Employee).filter(
        models.Employee.id == payload.employee_id,
        models.Employee.is_active.is_(True),
    ).first()
    shift = db.query(models.Shift).filter(
        models.Shift.id == payload.shift_id,
        models.Shift.is_active.is_(True),
    ).first()
    if not employee or not shift:
        raise HTTPException(status_code=404, detail="Active employee or shift not found")
    row = models.ShiftAssignment(
        **payload.model_dump(),
        assigned_by_id=user.id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        user,
        "shift.assigned",
        "employee",
        employee.id,
        f"{shift.name} effective {payload.effective_from.isoformat()}",
    )
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_name": employee.full_name,
        "shift_id": shift.id,
        "shift_name": shift.name,
        "start_time": shift.start_time,
        "end_time": shift.end_time,
        "effective_from": row.effective_from.isoformat(),
    }


def attendance_response(row: models.AttendanceRecord) -> dict:
    elapsed_hours = (
        max(0, (row.check_out - row.check_in).total_seconds() / 3600)
        if row.check_out
        else None
    )
    worked_hours = (
        round(max(0, elapsed_hours - (row.shift.break_minutes / 60)), 2)
        if elapsed_hours is not None and row.shift
        else round(elapsed_hours, 2) if elapsed_hours is not None else None
    )
    scheduled_hours = 8.0
    if row.shift:
        start = time.fromisoformat(row.shift.start_time)
        end = time.fromisoformat(row.shift.end_time)
        scheduled_hours = (
            datetime.combine(date.min, end) - datetime.combine(date.min, start)
        ).total_seconds() / 3600
        if scheduled_hours <= 0:
            scheduled_hours += 24
        scheduled_hours = max(
            0,
            scheduled_hours - (row.shift.break_minutes / 60),
        )
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_name": row.employee.full_name,
        "check_in": row.check_in.isoformat(),
        "check_out": row.check_out.isoformat() if row.check_out else None,
        "worked_hours": worked_hours,
        "scheduled_hours": round(scheduled_hours, 2),
        "overtime_hours": max(0, round(worked_hours - scheduled_hours, 2)) if worked_hours is not None else None,
    }


@app.get("/api/attendance")
def list_attendance(
    employee_id: int | None = Query(default=None, ge=1),
    work_date: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    if user.role == "EMPLOYEE":
        own_employee_id = linked_employee(db, user).id
        if employee_id is not None and employee_id != own_employee_id:
            raise HTTPException(status_code=403, detail="Cannot access another employee's attendance")
        employee_id = own_employee_id
    query = db.query(models.AttendanceRecord).options(
        joinedload(models.AttendanceRecord.employee),
        joinedload(models.AttendanceRecord.shift),
    )
    if employee_id is not None:
        query = query.filter(models.AttendanceRecord.employee_id == employee_id)
    if work_date is not None:
        start = datetime.combine(work_date, datetime.min.time())
        end = datetime.combine(work_date, datetime.max.time())
        query = query.filter(
            models.AttendanceRecord.check_in >= start,
            models.AttendanceRecord.check_in <= end,
        )
    rows = query.order_by(models.AttendanceRecord.check_in.desc()).limit(limit).all()
    return [attendance_response(row) for row in rows]


@app.post("/api/attendance/check-in", status_code=201)
def attendance_check_in(
    payload: schemas.AttendanceAction,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    employee_id = resolve_employee_id(db, user, payload.employee_id)
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.is_active.is_(True),
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Active employee not found")
    today_start = datetime.combine(datetime.now(timezone.utc).date(), datetime.min.time())
    tomorrow_start = today_start + timedelta(days=1)
    existing_today = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.employee_id == employee.id,
        models.AttendanceRecord.check_in >= today_start,
        models.AttendanceRecord.check_in < tomorrow_start,
    ).first()
    if existing_today:
        raise HTTPException(status_code=409, detail="Attendance is already recorded for today")
    open_record = db.query(models.AttendanceRecord).filter(
        models.AttendanceRecord.employee_id == employee.id,
        models.AttendanceRecord.check_out.is_(None),
    ).first()
    if open_record:
        raise HTTPException(status_code=409, detail="Employee is already checked in")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    assignment = (
        db.query(models.ShiftAssignment)
        .filter(
            models.ShiftAssignment.employee_id == employee.id,
            models.ShiftAssignment.effective_from <= now.date(),
        )
        .order_by(
            models.ShiftAssignment.effective_from.desc(),
            models.ShiftAssignment.id.desc(),
        )
        .first()
    )
    row = models.AttendanceRecord(
        employee_id=employee.id,
        shift_id=assignment.shift_id if assignment else None,
        check_in=now,
    )
    db.add(row)
    db.flush()
    record_audit(db, user, "attendance.checked_in", "attendance", row.id, employee.employee_code)
    db.commit()
    db.refresh(row)
    row.employee = employee
    if assignment:
        row.shift = assignment.shift
    return attendance_response(row)


@app.post("/api/attendance/check-out")
def attendance_check_out(
    payload: schemas.AttendanceAction,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    employee_id = resolve_employee_id(db, user, payload.employee_id)
    row = (
        db.query(models.AttendanceRecord)
        .options(
            joinedload(models.AttendanceRecord.employee),
            joinedload(models.AttendanceRecord.shift),
        )
        .filter(
            models.AttendanceRecord.employee_id == employee_id,
            models.AttendanceRecord.check_out.is_(None),
        )
        .order_by(models.AttendanceRecord.check_in.desc())
        .first()
    )
    if not row:
        raise HTTPException(status_code=409, detail="Employee has no open check-in")
    row.check_out = datetime.now(timezone.utc).replace(tzinfo=None)
    record_audit(
        db,
        user,
        "attendance.checked_out",
        "attendance",
        row.id,
        row.employee.employee_code,
    )
    db.commit()
    db.refresh(row)
    return attendance_response(row)


@app.get("/api/shifts/assignments")
def list_shift_assignments(
    employee_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    query = db.query(models.ShiftAssignment).options(
        joinedload(models.ShiftAssignment.employee),
        joinedload(models.ShiftAssignment.shift),
    )
    if employee_id is not None:
        query = query.filter(models.ShiftAssignment.employee_id == employee_id)
    rows = query.order_by(models.ShiftAssignment.effective_from.desc()).limit(200).all()
    return [
        {
            "id": row.id,
            "employee_id": row.employee_id,
            "employee_name": row.employee.full_name,
            "shift_id": row.shift_id,
            "shift_name": row.shift.name,
            "start_time": row.shift.start_time,
            "end_time": row.shift.end_time,
            "effective_from": row.effective_from.isoformat(),
        }
        for row in rows
    ]


def leave_response(row: models.LeaveRequest) -> dict:
    return {
        "id": row.id,
        "employee_id": row.employee_id,
        "employee_name": row.employee.full_name,
        "leave_type": row.leave_type,
        "start_date": row.start_date.isoformat(),
        "end_date": row.end_date.isoformat(),
        "calendar_days": (row.end_date - row.start_date).days + 1,
        "reason": row.reason,
        "status": row.status,
        "reviewer_notes": row.reviewer_notes,
        "reviewed_by": row.reviewed_by.full_name if row.reviewed_by else None,
        "created_at": row.created_at.isoformat(),
    }


def leave_allowance(
    db: Session,
    leave_type: str,
    year: int,
) -> int:
    policy = db.query(models.LeavePolicy).filter(
        models.LeavePolicy.leave_type == leave_type,
        models.LeavePolicy.year == year,
        models.LeavePolicy.is_active.is_(True),
    ).first()
    if not policy:
        raise HTTPException(
            status_code=409,
            detail=f"No active {leave_type} leave policy exists for {year}",
        )
    return policy.annual_allowance_days


def approved_leave_days(
    db: Session,
    employee_id: int | None,
    leave_type: str,
    year: int,
) -> int | dict[int, int]:
    year_start = date(year, 1, 1)
    year_end = date(year, 12, 31)
    query = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.leave_type == leave_type,
        models.LeaveRequest.status == "Approved",
        models.LeaveRequest.start_date <= year_end,
        models.LeaveRequest.end_date >= year_start,
    )
    if employee_id is not None:
        query = query.filter(models.LeaveRequest.employee_id == employee_id)
    requests = query.all()
    days_by_employee: dict[int, int] = {}
    for request in requests:
        days_by_employee[request.employee_id] = days_by_employee.get(request.employee_id, 0) + (
            min(request.end_date, year_end) - max(request.start_date, year_start)
        ).days + 1
    return days_by_employee if employee_id is None else days_by_employee.get(employee_id, 0)


@app.get("/api/leaves")
def list_leave_requests(
    status: str | None = Query(default=None, pattern="^(Pending|Approved|Rejected)$"),
    employee_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    query = db.query(models.LeaveRequest).options(
        joinedload(models.LeaveRequest.employee),
        joinedload(models.LeaveRequest.reviewed_by),
    )
    if status:
        query = query.filter(models.LeaveRequest.status == status)
    if user.role == "EMPLOYEE":
        query = query.filter(
            models.LeaveRequest.employee_id == linked_employee(db, user).id
        )
    if employee_id is not None:
        if user.role == "EMPLOYEE" and employee_id != linked_employee(db, user).id:
            raise HTTPException(status_code=403, detail="Cannot access another employee's leave")
        query = query.filter(models.LeaveRequest.employee_id == employee_id)
    rows = query.order_by(models.LeaveRequest.created_at.desc()).limit(200).all()
    return [leave_response(row) for row in rows]


@app.post("/api/leaves", status_code=201)
def create_leave_request(
    payload: schemas.LeaveCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    employee_id = resolve_employee_id(db, user, payload.employee_id)
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id,
        models.Employee.is_active.is_(True),
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Active employee not found")
    existing = db.query(models.LeaveRequest).filter(
        models.LeaveRequest.employee_id == employee.id,
        models.LeaveRequest.status.in_(("Pending", "Approved")),
        models.LeaveRequest.start_date <= payload.end_date,
        models.LeaveRequest.end_date >= payload.start_date,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Leave dates overlap an existing request")
    leave_allowance(db, payload.leave_type, payload.start_date.year)
    row = models.LeaveRequest(
        **payload.model_dump(exclude={"employee_id"}),
        employee_id=employee.id,
    )
    db.add(row)
    db.flush()
    record_audit(db, user, "leave.requested", "leave", row.id, employee.employee_code)
    notify_roles(
        db,
        ("ADMIN", "HR"),
        "Leave request submitted",
        f"{employee.full_name} submitted a {payload.leave_type} leave request for review.",
    )
    db.commit()
    db.refresh(row)
    row.employee = employee
    return leave_response(row)


@app.patch("/api/leaves/{leave_id}")
def review_leave_request(
    leave_id: int,
    payload: schemas.LeaveReview,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = (
        db.query(models.LeaveRequest)
        .options(joinedload(models.LeaveRequest.employee))
        .filter(models.LeaveRequest.id == leave_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if row.status != "Pending":
        raise HTTPException(status_code=409, detail="Leave request has already been reviewed")
    if payload.status == "Approved":
        allowance = leave_allowance(db, row.leave_type, row.start_date.year)
        used_days = approved_leave_days(
            db,
            row.employee_id,
            row.leave_type,
            row.start_date.year,
        )
        requested_days = (row.end_date - row.start_date).days + 1
        if used_days + requested_days > allowance:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Approval exceeds the {allowance}-day {row.leave_type} "
                    f"allowance for {row.start_date.year}"
                ),
            )
    row.status = payload.status
    row.reviewer_notes = payload.reviewer_notes
    row.reviewed_by_id = user.id
    record_audit(
        db,
        user,
        f"leave.{payload.status.lower()}",
        "leave",
        row.id,
        row.employee.employee_code,
    )
    notify_user(
        db,
        row.employee.user_id,
        f"Leave request {payload.status.lower()}",
        f"Your {row.leave_type} leave request for {row.start_date} to {row.end_date} was {payload.status.lower()}.",
    )
    db.commit()
    db.refresh(row)
    return leave_response(row)


@app.get("/api/leaves/balance")
@app.get("/api/leaves/balance/{employee_id}")
def leave_balance(
    employee_id: int | None = None,
    leave_type: str = Query(default="Annual", min_length=2, max_length=40),
    year: int = Query(default_factory=lambda: date.today().year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR", "EMPLOYEE")),
):
    employee_id = resolve_employee_id(db, user, employee_id)
    employee = db.query(models.Employee).filter(
        models.Employee.id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    allowance = leave_allowance(db, leave_type, year)
    used = approved_leave_days(db, employee_id, leave_type, year)
    return {
        "employee_id": employee_id,
        "leave_type": leave_type,
        "year": year,
        "annual_allowance_days": allowance,
        "approved_days_used": used,
        "remaining_days": max(0, allowance - used),
        "calculation": "Inclusive calendar days from approved requests; policy is configurable by leave type and year.",
    }


@app.get("/api/leave-policies")
def list_leave_policies(
    year: int | None = Query(default=None, ge=2000, le=2100),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    query = db.query(models.LeavePolicy)
    if year is not None:
        query = query.filter(models.LeavePolicy.year == year)
    rows = query.order_by(
        models.LeavePolicy.year.desc(),
        models.LeavePolicy.leave_type,
    ).limit(300).all()
    return [
        {
            "id": row.id,
            "leave_type": row.leave_type,
            "year": row.year,
            "annual_allowance_days": row.annual_allowance_days,
            "is_active": row.is_active,
        }
        for row in rows
    ]


@app.post("/api/leave-policies", status_code=201)
def create_leave_policy(
    payload: schemas.LeavePolicyCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    if db.query(models.LeavePolicy).filter(
        models.LeavePolicy.leave_type == payload.leave_type,
        models.LeavePolicy.year == payload.year,
    ).first():
        raise HTTPException(status_code=409, detail="Policy already exists for this leave type and year")
    row = models.LeavePolicy(
        **payload.model_dump(),
        created_by_id=user.id,
    )
    db.add(row)
    db.flush()
    record_audit(db, user, "leave_policy.created", "leave_policy", row.id, payload.leave_type)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "leave_type": row.leave_type,
        "year": row.year,
        "annual_allowance_days": row.annual_allowance_days,
        "is_active": row.is_active,
    }


@app.patch("/api/leave-policies/{policy_id}")
def update_leave_policy(
    policy_id: int,
    payload: schemas.LeavePolicyUpdate,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    row = db.get(models.LeavePolicy, policy_id)
    if not row:
        raise HTTPException(status_code=404, detail="Leave policy not found")
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide policy fields to update")
    if "annual_allowance_days" in updates:
        usage = approved_leave_days(
            db,
            employee_id=None,
            leave_type=row.leave_type,
            year=row.year,
        )
        if max(usage.values(), default=0) > updates["annual_allowance_days"]:
            raise HTTPException(
                status_code=409,
                detail="Policy allowance is below already approved leave for an employee",
            )
    for key, value in updates.items():
        setattr(row, key, value)
    record_audit(db, user, "leave_policy.updated", "leave_policy", row.id, row.leave_type)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "leave_type": row.leave_type,
        "year": row.year,
        "annual_allowance_days": row.annual_allowance_days,
        "is_active": row.is_active,
    }


@app.get("/api/notifications")
def list_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    )
    if unread_only:
        query = query.filter(models.Notification.is_read.is_(False))
    rows = query.order_by(
        models.Notification.created_at.desc(),
        models.Notification.id.desc(),
    ).limit(100).all()
    return [
        {
            "id": row.id,
            "title": row.title,
            "message": row.message,
            "is_read": row.is_read,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


def read_pending_notifications(user_id: int, after_id: int) -> list[dict]:
    with SessionLocal() as stream_db:
        rows = (
            stream_db.query(models.Notification)
            .filter(
                models.Notification.user_id == user_id,
                models.Notification.id > after_id,
            )
            .order_by(models.Notification.id.asc())
            .limit(100)
            .all()
        )
        return [
            {
                "id": row.id,
                "title": row.title,
                "message": row.message,
                "is_read": row.is_read,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


async def notification_event_stream(user_id: int, after_id: int):
    last_heartbeat = asyncio.get_running_loop().time()
    while True:
        notifications = await asyncio.to_thread(
            read_pending_notifications,
            user_id,
            after_id,
        )

        if notifications:
            after_id = notifications[-1]["id"]
            yield (
                f"id: {after_id}\nevent: notifications\n"
                f"data: {json.dumps(notifications)}\n\n"
            )
        elif asyncio.get_running_loop().time() - last_heartbeat >= 15:
            yield ": keep-alive\n\n"
            last_heartbeat = asyncio.get_running_loop().time()

        await asyncio.sleep(2)


@app.get("/api/notifications/stream")
def stream_notifications(
    after_id: int = Query(default=0, ge=0),
    credentials: HTTPAuthorizationCredentials | None = Depends(notification_stream_bearer),
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    with SessionLocal() as auth_db:
        user = authenticate_access_token(credentials.credentials, auth_db)
        user_id = user.id

    return StreamingResponse(
        notification_event_stream(user_id, after_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    row = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == user.id,
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Notification not found")
    row.is_read = True
    record_audit(
        db,
        user,
        "notification.read",
        "notification",
        row.id,
    )
    db.commit()
    return {"id": row.id, "is_read": row.is_read}


@app.get("/api/audit-logs")
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN")),
):
    rows = db.query(models.AuditLog).options(
        joinedload(models.AuditLog.actor)
    ).order_by(
        models.AuditLog.created_at.desc(),
        models.AuditLog.id.desc(),
    ).limit(limit).all()
    return [
        {
            "id": row.id,
            "actor_id": row.actor_id,
            "actor_name": row.actor.full_name,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@app.get("/api/reports/attendance.csv")
def attendance_report(
    work_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    rows = list_attendance(
        employee_id=None,
        work_date=work_date,
        limit=500,
        db=db,
        user=user,
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "employee_id",
            "employee_name",
            "check_in",
            "check_out",
            "worked_hours",
            "scheduled_hours",
            "overtime_hours",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendance-report.csv"'},
    )


@app.get("/api/reports/leaves.csv")
def leave_report(
    status: str | None = Query(
        default=None,
        pattern="^(Pending|Approved|Rejected)$",
    ),
    employee_id: int | None = Query(default=None, ge=1),
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_roles("ADMIN", "HR")),
):
    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=422,
            detail="end_date must be on or after start_date",
        )
    query = db.query(models.LeaveRequest).options(
        joinedload(models.LeaveRequest.employee),
        joinedload(models.LeaveRequest.reviewed_by),
    )
    if status:
        query = query.filter(models.LeaveRequest.status == status)
    if employee_id is not None:
        query = query.filter(models.LeaveRequest.employee_id == employee_id)
    if start_date:
        query = query.filter(models.LeaveRequest.end_date >= start_date)
    if end_date:
        query = query.filter(models.LeaveRequest.start_date <= end_date)
    rows = query.order_by(
        models.LeaveRequest.created_at.desc(),
        models.LeaveRequest.id.desc(),
    ).limit(5000).all()
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "employee_id",
            "employee_code",
            "employee_name",
            "leave_type",
            "start_date",
            "end_date",
            "calendar_days",
            "status",
            "reason",
            "reviewed_by",
            "reviewer_notes",
            "created_at",
        ],
    )
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.id,
                "employee_id": row.employee_id,
                "employee_code": row.employee.employee_code,
                "employee_name": row.employee.full_name,
                "leave_type": row.leave_type,
                "start_date": row.start_date.isoformat(),
                "end_date": row.end_date.isoformat(),
                "calendar_days": (row.end_date - row.start_date).days + 1,
                "status": row.status,
                "reason": row.reason,
                "reviewed_by": row.reviewed_by.full_name if row.reviewed_by else "",
                "reviewer_notes": row.reviewer_notes or "",
                "created_at": row.created_at.isoformat(),
            }
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leave-report.csv"'},
    )
