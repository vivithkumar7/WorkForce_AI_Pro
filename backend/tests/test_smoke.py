import pytest
import asyncio
from datetime import date, datetime, timedelta
from calendar import monthrange
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app import main as main_module
from app import database as database_module
from app.database import Base, get_db
from app.ml import predictor
from app.main import app, attendance_response
from app.security import create_access_token, hash_password


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setattr(predictor, "MODEL_PATH", tmp_path / "missing-model.joblib")
    predictor.load_model.cache_clear()
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    monkeypatch.setattr(main_module, "SessionLocal", testing_session)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    db = testing_session()
    department = models.Department(name="Engineering")
    db.add(department)
    db.flush()
    test_password_hash = hash_password("TestPass123!")
    admin = models.User(
        email="admin@example.com",
        full_name="Test Admin",
        hashed_password=test_password_hash,
        role="ADMIN",
    )
    manager = models.User(
        email="manager@example.com",
        full_name="Test Manager",
        hashed_password=test_password_hash,
        role="MANAGER",
    )
    hr_user = models.User(
        email="hr@example.com",
        full_name="Test HR",
        hashed_password=test_password_hash,
        role="HR",
    )
    employee_user = models.User(
        email="high@example.com",
        full_name="Test Employee",
        hashed_password=test_password_hash,
        role="EMPLOYEE",
    )
    employee = models.Employee(
        employee_code="EMP001",
        full_name="High Risk",
        email="high@example.com",
        job_title="Engineer",
        department_id=department.id,
        tenure_years=0,
        monthly_income=50000,
        job_satisfaction=1,
        work_life_balance=1,
        overtime=True,
        years_since_promotion=5,
    )
    second_employee = models.Employee(
        employee_code="EMP002",
        full_name="Low Risk",
        email="low@example.com",
        job_title="Analyst",
        department_id=department.id,
        tenure_years=8,
        monthly_income=70000,
        job_satisfaction=4,
        work_life_balance=4,
        overtime=False,
        years_since_promotion=0,
    )
    db.add_all([admin, manager, hr_user, employee_user, employee, second_employee])
    db.flush()
    db.add(
        models.LeavePolicy(
            leave_type="Annual",
            year=date.today().year,
            annual_allowance_days=20,
            created_by_id=admin.id,
        )
    )
    db.commit()
    employee_id = employee.id
    second_employee_id = second_employee.id
    department_id = department.id
    db.close()

    with TestClient(app) as client:
        yield client, employee_id, second_employee_id, department_id

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    predictor.load_model.cache_clear()


def auth_headers(role="ADMIN", subject="admin@example.com"):
    if subject == "admin@example.com" and role != "ADMIN":
        subject = {
            "MANAGER": "manager@example.com",
            "HR": "hr@example.com",
            "EMPLOYEE": "high@example.com",
        }.get(role, subject)
    return {"Authorization": f"Bearer {create_access_token(subject, role)}"}


def test_root_and_openapi(api):
    client, *_ = api
    assert client.get("/").json()["status"] == "running"
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/api/notifications/stream").status_code == 401
    assert client.get(
        "/api/notifications/stream?after_id=-1",
        headers=auth_headers(),
    ).status_code == 422


def test_notification_stream_is_user_scoped(api):
    client, *_ = api
    db = main_module.SessionLocal()
    admin = db.query(models.User).filter_by(email="admin@example.com").one()
    manager = db.query(models.User).filter_by(email="manager@example.com").one()
    db.add_all(
        [
            models.Notification(
                user_id=admin.id,
                title="Admin alert",
                message="Visible to admin",
            ),
            models.Notification(
                user_id=manager.id,
                title="Manager alert",
                message="Visible to manager",
            ),
        ]
    )
    db.commit()
    admin_id = admin.id
    db.close()

    async def read_first_event():
        stream = main_module.notification_event_stream(
            admin_id,
            0,
        )
        return await stream.__anext__()

    event = asyncio.run(read_first_event())
    assert "event: notifications" in event
    assert "Admin alert" in event
    assert "Manager alert" not in event


def test_authentication_and_employee_department_name(api):
    client, employee_id, *_ = api
    assert client.get("/api/employees").status_code == 401

    response = client.post(
        "/api/auth/login",
        data={"username": "admin@example.com", "password": "TestPass123!"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    employee_response = client.get(
        f"/api/employees/{employee_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert employee_response.status_code == 200
    assert employee_response.json()["department_name"] == "Engineering"


def test_managed_user_creation_role_updates_and_password_reset(api):
    client, *_ = api
    admin_headers = auth_headers()
    payload = {
        "email": "new.user@example.com",
        "full_name": "New User",
        "password": "InitialPass123!",
        "role": "EMPLOYEE",
    }
    created = client.post("/api/admin/users", json=payload, headers=admin_headers)
    assert created.status_code == 201
    assert created.json()["role"] == "EMPLOYEE"
    assert "hashed_password" not in created.json()
    assert client.get("/api/admin/users", headers=admin_headers).status_code == 200
    assert client.post(
        "/api/admin/users",
        json={**payload, "email": "duplicate@example.com", "password": "weak"},
        headers=admin_headers,
    ).status_code == 422
    assert client.post(
        "/api/admin/users",
        json=payload,
        headers=admin_headers,
    ).status_code == 409

    hr_headers = auth_headers(role="HR")
    hr_payload = {
        "email": "hr.created@example.com",
        "full_name": "HR Created Employee",
        "password": "InitialPass123!",
        "role": "EMPLOYEE",
    }
    assert client.post(
        "/api/admin/users",
        json=hr_payload,
        headers=hr_headers,
    ).status_code == 201
    assert client.post(
        "/api/admin/users",
        json={**hr_payload, "role": "HR"},
        headers=hr_headers,
    ).status_code == 403

    login = client.post(
        "/api/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert login.status_code == 200
    old_token_headers = {
        "Authorization": f"Bearer {login.json()['access_token']}"
    }
    assert client.get("/api/auth/me", headers=old_token_headers).status_code == 200

    assert client.post(
        f"/api/admin/users/{created.json()['id']}/reset-password",
        json={"password": "ReplacementPass456!"},
        headers=admin_headers,
    ).status_code == 200
    assert client.get("/api/auth/me", headers=old_token_headers).status_code == 401
    assert client.post(
        "/api/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    ).status_code == 401
    new_login = client.post(
        "/api/auth/login",
        data={"username": payload["email"], "password": "ReplacementPass456!"},
    )
    assert new_login.status_code == 200
    assert client.patch(
        f"/api/admin/users/{created.json()['id']}",
        json={"role": "MANAGER", "is_active": False},
        headers=admin_headers,
    ).json()["is_active"] is False
    assert client.get("/api/admin/users", headers=auth_headers(role="MANAGER")).status_code == 403


def test_employee_validation_and_role_access(api):
    client, employee_id, _, department_id = api
    headers = auth_headers()
    payload = {
        "employee_code": "EMP003",
        "full_name": "New Employee",
        "email": "new@example.com",
        "job_title": "Specialist",
        "department_id": department_id,
    }
    assert client.post("/api/employees", json=payload, headers=headers).status_code == 201
    assert len(client.get("/api/ai/predictions", headers=headers).json()) == 1
    assert client.post("/api/employees", json=payload, headers=headers).status_code == 409

    invalid_department = {
        **payload,
        "employee_code": "EMP004",
        "email": "other@example.com",
        "department_id": 999,
    }
    assert client.post(
        "/api/employees",
        json=invalid_department,
        headers=headers,
    ).status_code == 404
    assert client.put(
        f"/api/employees/{employee_id}",
        json={"department_id": 999},
        headers=headers,
    ).status_code == 404
    assert client.put(
        f"/api/employees/{employee_id}",
        json={"job_satisfaction": 5},
        headers=headers,
    ).status_code == 422
    assert client.put(
        f"/api/employees/{employee_id}",
        json={"job_title": None},
        headers=headers,
    ).status_code == 422
    assert client.post(
        "/api/employees",
        json={**payload, "employee_code": "EMP005"},
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403


def test_batch_predictions_dashboard_and_current_alerts(api):
    client, high_risk_id, _, department_id = api
    headers = auth_headers()

    batch = client.post("/api/ai/predict", headers=headers)
    assert batch.status_code == 200
    assert batch.json()["processed_count"] == 2
    assert batch.json()["high_risk_count"] == 1

    dashboard = client.get("/api/dashboard/summary", headers=headers).json()
    assert dashboard["total_employees"] == 2
    assert dashboard["department_headcount"] == [
        {"department": "Engineering", "employees": 2}
    ]
    assert dashboard["high_risk_employees"] == 1
    assert dashboard["average_attrition_risk"] == 41.8
    assert len(dashboard["recent_predictions"]) == 2
    alerts = client.get("/api/ai/alerts", headers=headers).json()
    assert [alert["employee_id"] for alert in alerts] == [high_risk_id]
    notifications = client.get(
        "/api/notifications?unread_only=true",
        headers=headers,
    ).json()
    assert any(item["title"] == "High attrition risk flagged" for item in notifications)

    update = client.put(
        f"/api/employees/{high_risk_id}",
        json={
            "tenure_years": 8,
            "job_satisfaction": 4,
            "work_life_balance": 4,
            "overtime": False,
            "years_since_promotion": 0,
        },
        headers=headers,
    )
    assert update.status_code == 200
    after_profile_update = client.get(
        "/api/dashboard/summary",
        headers=headers,
    ).json()
    assert after_profile_update["high_risk_employees"] == 0
    assert after_profile_update["average_attrition_risk"] == 3.0
    assert client.post(
        f"/api/ai/predict/{high_risk_id}",
        headers=headers,
    ).status_code == 200

    refreshed_dashboard = client.get(
        "/api/dashboard/summary",
        headers=headers,
    ).json()
    assert refreshed_dashboard["high_risk_employees"] == 0
    assert refreshed_dashboard["average_attrition_risk"] == 3.0
    assert client.get("/api/ai/alerts", headers=headers).json() == []
    assert len(client.get("/api/ai/predictions", headers=headers).json()) == 4

    assert client.delete(
        f"/api/employees/{high_risk_id}",
        headers=headers,
    ).status_code == 200
    after_deactivation = client.get("/api/dashboard/summary", headers=headers).json()
    assert after_deactivation["total_employees"] == 1
    assert after_deactivation["department_headcount"] == [
        {"department": "Engineering", "employees": 1}
    ]
    assert after_deactivation["high_risk_employees"] == 0
    assert after_deactivation["average_attrition_risk"] == 3.0
    assert department_id > 0


def test_manager_can_predict_but_employee_cannot(api):
    client, employee_id, *_ = api
    manager_headers = auth_headers(role="MANAGER")
    assert client.post(
        f"/api/ai/predict/{employee_id}",
        headers=manager_headers,
    ).status_code == 200
    assert client.post(
        "/api/ai/predict",
        headers=auth_headers(role="EMPLOYEE"),
    ).status_code == 403
    employee_headers = auth_headers(role="EMPLOYEE")
    assert client.get("/api/employees", headers=employee_headers).status_code == 403
    assert client.get("/api/dashboard/summary", headers=employee_headers).status_code == 403
    assert client.get("/api/ai/predictions", headers=employee_headers).status_code == 403
    assert client.get("/api/ai/alerts", headers=employee_headers).status_code == 403
    assert client.post(
        "/api/attendance/check-in",
        json={"employee_id": employee_id},
        headers=manager_headers,
    ).status_code == 403
    assert client.post(
        "/api/employees",
        json={
            "employee_code": "EMP999",
            "full_name": "Unauthorized Employee",
            "email": "unauthorized@example.com",
            "job_title": "Specialist",
            "department_id": 1,
        },
        headers=auth_headers(role="ADMIN", subject="manager@example.com"),
    ).status_code == 403


def test_intervention_workflow_and_workforce_report(api):
    client, employee_id, _, _ = api
    headers = auth_headers()

    intervention = client.post(
        "/api/interventions",
        json={
            "employee_id": employee_id,
            "intervention_type": "Support check-in",
            "notes": "Review workload and growth opportunities.",
        },
        headers=headers,
    )
    assert intervention.status_code == 201
    created = intervention.json()
    assert created["status"] == "Open"
    assert created["employee_name"] == "High Risk"
    assert created["created_by"] == "Test Admin"

    updated = client.patch(
        f"/api/interventions/{created['id']}",
        json={"status": "In Progress"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "In Progress"
    assert client.get(
        "/api/interventions?status=In%20Progress",
        headers=headers,
    ).json()[0]["id"] == created["id"]

    report = client.get("/api/reports/workforce.csv", headers=headers)
    assert report.status_code == 200
    assert report.headers["content-type"].startswith("text/csv")
    assert 'filename="workforce-analytics.csv"' in report.headers["content-disposition"]
    assert "employee_code,employee_name,department,job_title" in report.text
    assert "EMP001,High Risk,Engineering,Engineer" in report.text

    assert client.post(
        "/api/interventions",
        json={"employee_id": employee_id},
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403
    assert client.get(
        "/api/interventions",
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403
    assert client.get(
        "/api/reports/workforce.csv",
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403
    assert client.get("/api/reports/workforce.csv").status_code == 401


def test_department_crud_and_audit_access(api):
    client, _, _, department_id = api
    headers = auth_headers()
    created = client.post(
        "/api/departments",
        json={"name": "Operations", "description": "Business operations"},
        headers=headers,
    )
    assert created.status_code == 200
    created_id = created.json()["id"]
    changed = client.put(
        f"/api/departments/{created_id}",
        json={"name": "People Operations"},
        headers=headers,
    )
    assert changed.status_code == 200
    assert changed.json()["name"] == "People Operations"
    assert client.put(
        f"/api/departments/{created_id}",
        json={"name": "Engineering"},
        headers=headers,
    ).status_code == 409
    assert client.delete(
        f"/api/departments/{department_id}",
        headers=headers,
    ).status_code == 409
    assert client.delete(
        f"/api/departments/{created_id}",
        headers=headers,
    ).status_code == 200
    assert client.get(
        "/api/audit-logs",
        headers=headers,
    ).json()[0]["action"] == "department.deleted"
    assert client.get(
        "/api/audit-logs",
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403


def test_dashboard_daily_metrics_use_stored_attendance_and_leave(api):
    client, employee_id, second_employee_id, _ = api
    headers = auth_headers()
    today = date.today()
    attendance = client.post(
        "/api/attendance/check-in",
        json={"employee_id": employee_id},
        headers=headers,
    )
    assert attendance.status_code == 201

    approved_request = client.post(
        "/api/leaves",
        json={
            "employee_id": employee_id,
            "leave_type": "Annual",
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "reason": "Personal day",
        },
        headers=headers,
    )
    assert approved_request.status_code == 201
    assert client.patch(
        f"/api/leaves/{approved_request.json()['id']}",
        json={"status": "Approved"},
        headers=headers,
    ).status_code == 200

    pending_request = client.post(
        "/api/leaves",
        json={
            "employee_id": second_employee_id,
            "leave_type": "Annual",
            "start_date": today.isoformat(),
            "end_date": today.isoformat(),
            "reason": "Personal day",
        },
        headers=headers,
    )
    assert pending_request.status_code == 201

    summary = client.get("/api/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["attendance_check_ins_today"] == 1
    assert summary.json()["attendance_open_sessions_today"] == 1
    assert summary.json()["approved_leave_today"] == 1
    assert summary.json()["pending_leave_requests"] == 1


def test_attendance_shift_and_csv_report(api):
    client, employee_id, _, _ = api
    headers = auth_headers()

    shift = client.post(
        "/api/shifts",
        json={"name": "Day shift", "start_time": "09:00", "end_time": "17:00"},
        headers=headers,
    )
    assert shift.status_code == 201
    assignment = client.post(
        "/api/shifts/assignments",
        json={"employee_id": employee_id, "shift_id": shift.json()["id"]},
        headers=headers,
    )
    assert assignment.status_code == 201
    assert assignment.json()["shift_name"] == "Day shift"
    assert client.get(
        f"/api/shifts/assignments?employee_id={employee_id}",
        headers=headers,
    ).json()[0]["employee_name"] == "High Risk"
    assert client.post(
        "/api/shifts/assignments",
        json={"employee_id": employee_id, "shift_id": shift.json()["id"]},
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403

    check_in = client.post(
        "/api/attendance/check-in",
        json={"employee_id": employee_id},
        headers=headers,
    )
    assert check_in.status_code == 201
    assert check_in.json()["check_out"] is None
    assert client.post(
        "/api/attendance/check-in",
        json={"employee_id": employee_id},
        headers=headers,
    ).status_code == 409
    check_out = client.post(
        "/api/attendance/check-out",
        json={"employee_id": employee_id},
        headers=headers,
    )
    assert check_out.status_code == 200
    assert check_out.json()["worked_hours"] is not None
    assert check_out.json()["overtime_hours"] == 0
    assert len(client.get("/api/attendance", headers=headers).json()) == 1
    report = client.get("/api/reports/attendance.csv", headers=headers)
    assert report.status_code == 200
    assert "employee_name,check_in,check_out" in report.text
    assert "High Risk" in report.text


def test_leave_approval_balance_notifications_and_rbac(api):
    client, employee_id, _, _ = api
    headers = auth_headers()

    request = client.post(
        "/api/leaves",
        json={
            "employee_id": employee_id,
            "leave_type": "Annual",
            "start_date": "2026-11-02",
            "end_date": "2026-11-04",
            "reason": "Personal time off",
        },
        headers=headers,
    )
    assert request.status_code == 201
    assert request.json()["calendar_days"] == 3
    assert client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Approved"},
        headers=headers,
    ).json()["status"] == "Approved"
    assert client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Rejected"},
        headers=headers,
    ).status_code == 409
    balance = client.get(
        f"/api/leaves/balance/{employee_id}",
        headers=headers,
    ).json()
    assert balance["approved_days_used"] == 3
    assert balance["remaining_days"] == 17

    notifications = client.get("/api/notifications?unread_only=true", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()[0]["title"] == "Leave request submitted"
    notification_id = notifications.json()[0]["id"]
    assert client.patch(
        f"/api/notifications/{notification_id}/read",
        headers=headers,
    ).json()["is_read"] is True
    assert client.get(
        "/api/notifications?unread_only=true",
        headers=headers,
    ).json() == []

    manager_headers = auth_headers(role="MANAGER")
    assert client.get("/api/leaves", headers=manager_headers).status_code == 403
    assert client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Rejected"},
        headers=manager_headers,
    ).status_code == 403
    assert client.get("/api/notifications").status_code == 401


def test_leave_csv_report_filters_and_role_access(api):
    client, employee_id, second_employee_id, _ = api
    headers = auth_headers()
    today = date.today()
    requests = []
    for selected_id, reason in [
        (employee_id, "Personal day"),
        (second_employee_id, "Medical appointment"),
    ]:
        response = client.post(
            "/api/leaves",
            json={
                "employee_id": selected_id,
                "leave_type": "Annual",
                "start_date": today.isoformat(),
                "end_date": today.isoformat(),
                "reason": reason,
            },
            headers=headers,
        )
        assert response.status_code == 201
        requests.append(response.json())
    assert client.patch(
        f"/api/leaves/{requests[0]['id']}",
        json={"status": "Approved"},
        headers=headers,
    ).status_code == 200

    report = client.get(
        f"/api/reports/leaves.csv?status=Approved&employee_id={employee_id}"
        f"&start_date={today.isoformat()}&end_date={today.isoformat()}",
        headers=headers,
    )
    assert report.status_code == 200
    assert 'filename="leave-report.csv"' in report.headers["content-disposition"]
    assert "employee_code,employee_name,leave_type" in report.text
    assert "Personal day" in report.text
    assert "Medical appointment" not in report.text
    assert client.get(
        f"/api/reports/leaves.csv?start_date={today.isoformat()}"
        f"&end_date={(today - timedelta(days=1)).isoformat()}",
        headers=headers,
    ).status_code == 422
    assert client.get(
        "/api/reports/leaves.csv",
        headers=auth_headers(role="MANAGER"),
    ).status_code == 403


def test_employee_linked_self_service_is_scoped(api):
    client, employee_id, other_employee_id, _ = api
    admin_headers = auth_headers()
    accounts = client.get("/api/users", headers=admin_headers).json()
    employee_account = next(account for account in accounts if account["email"] == "high@example.com")
    assert client.put(
        f"/api/employees/{employee_id}/account",
        json={"user_id": employee_account["id"]},
        headers=admin_headers,
    ).status_code == 200
    assert client.put(
        f"/api/employees/{other_employee_id}/account",
        json={"user_id": employee_account["id"]},
        headers=admin_headers,
    ).status_code == 409

    employee_headers = auth_headers(role="EMPLOYEE")
    profile = client.get("/api/me/employee", headers=employee_headers)
    assert profile.status_code == 200
    assert profile.json()["id"] == employee_id
    assert client.get("/api/employees", headers=employee_headers).status_code == 403
    assert client.get("/api/dashboard/summary", headers=employee_headers).status_code == 403

    check_in = client.post(
        "/api/attendance/check-in",
        json={},
        headers=employee_headers,
    )
    assert check_in.status_code == 201
    assert check_in.json()["employee_id"] == employee_id
    assert client.get(
        f"/api/attendance?employee_id={other_employee_id}",
        headers=employee_headers,
    ).status_code == 403
    assert len(client.get("/api/attendance", headers=employee_headers).json()) == 1

    today = date.today()
    request = client.post(
        "/api/leaves",
        json={
            "leave_type": "Annual",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=1)).isoformat(),
            "reason": "Personal time",
        },
        headers=employee_headers,
    )
    assert request.status_code == 201
    assert request.json()["employee_id"] == employee_id
    assert len(client.get("/api/leaves", headers=employee_headers).json()) == 1
    assert client.get(
        f"/api/leaves?employee_id={other_employee_id}",
        headers=employee_headers,
    ).status_code == 403
    balance = client.get("/api/leaves/balance", headers=employee_headers)
    assert balance.status_code == 200
    assert balance.json()["employee_id"] == employee_id

    approved = client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Approved"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    employee_notifications = client.get(
        "/api/notifications",
        headers=employee_headers,
    ).json()
    assert any(item["title"] == "Leave request approved" for item in employee_notifications)


def test_configurable_leave_policy_and_approval_limit(api):
    client, employee_id, _, _ = api
    headers = auth_headers()
    year = date.today().year
    policy = client.post(
        "/api/leave-policies",
        json={
            "leave_type": "Study",
            "year": year,
            "annual_allowance_days": 2,
        },
        headers=headers,
    )
    assert policy.status_code == 201
    policy_id = policy.json()["id"]
    today = date.today()
    request = client.post(
        "/api/leaves",
        json={
            "employee_id": employee_id,
            "leave_type": "Study",
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=2)).isoformat(),
            "reason": "Training",
        },
        headers=headers,
    )
    assert request.status_code == 201
    assert client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Approved"},
        headers=headers,
    ).status_code == 409
    assert client.patch(
        f"/api/leave-policies/{policy_id}",
        json={"annual_allowance_days": 4},
        headers=headers,
    ).json()["annual_allowance_days"] == 4
    assert client.patch(
        f"/api/leaves/{request.json()['id']}",
        json={"status": "Approved"},
        headers=headers,
    ).status_code == 200
    assert client.get(
        f"/api/leaves/balance/{employee_id}?leave_type=Study&year={year}",
        headers=headers,
    ).json()["remaining_days"] == 1
    assert client.patch(
        f"/api/leave-policies/{policy_id}",
        json={"annual_allowance_days": 1},
        headers=headers,
    ).status_code == 409


def test_overnight_shift_break_and_attendance_day_rules(api):
    client, employee_id, _, _ = api
    headers = auth_headers()
    shift = client.post(
        "/api/shifts",
        json={
            "name": "Night shift",
            "start_time": "22:00",
            "end_time": "06:00",
            "break_minutes": 30,
        },
        headers=headers,
    )
    assert shift.status_code == 201
    assignment = client.post(
        "/api/shifts/assignments",
        json={
            "employee_id": employee_id,
            "shift_id": shift.json()["id"],
            "effective_from": date.today().isoformat(),
        },
        headers=headers,
    )
    assert assignment.status_code == 201
    assert client.post(
        "/api/shifts",
        json={"name": "Invalid shift", "start_time": "09:00", "end_time": "09:00"},
        headers=headers,
    ).status_code == 422

    shift_model = models.Shift(
        name="Night test",
        start_time="22:00",
        end_time="06:00",
        break_minutes=30,
    )
    employee = models.Employee(full_name="Overnight worker")
    record = models.AttendanceRecord(
        employee_id=employee_id,
        check_in=datetime(2026, 10, 22, 22, 0),
        check_out=datetime(2026, 10, 23, 7, 0),
    )
    record.employee = employee
    record.shift = shift_model
    result = attendance_response(record)
    assert result["worked_hours"] == 8.5
    assert result["scheduled_hours"] == 7.5
    assert result["overtime_hours"] == 1.0


def test_legacy_column_upgrade_is_idempotent(monkeypatch):
    legacy_engine = create_engine("sqlite://")
    with legacy_engine.begin() as connection:
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE employees (id INTEGER PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE shifts (id INTEGER PRIMARY KEY)"))
        connection.execute(
            text("CREATE TABLE attendance_records (id INTEGER PRIMARY KEY)")
        )
    monkeypatch.setattr(database_module, "engine", legacy_engine)

    database_module.upgrade_legacy_columns()
    database_module.upgrade_legacy_columns()

    inspector = inspect(legacy_engine)
    employee_columns = {
        column["name"] for column in inspector.get_columns("employees")
    }
    shift_columns = {column["name"] for column in inspector.get_columns("shifts")}
    attendance_columns = {
        column["name"] for column in inspector.get_columns("attendance_records")
    }
    assert "user_id" in employee_columns
    assert "session_version" in {
        column["name"] for column in inspector.get_columns("users")
    }
    assert "break_minutes" in shift_columns
    assert "shift_id" in attendance_columns
    assert any(
        index["name"] == "uq_employees_user_id"
        for index in inspector.get_indexes("employees")
    )
    legacy_engine.dispose()


def test_payroll_generation_transitions_privacy_and_dashboard(api):
    client, employee_id, second_employee_id, _ = api
    admin_headers = auth_headers()
    hr_headers = auth_headers(role="HR")
    employee_headers = auth_headers(role="EMPLOYEE")
    manager_headers = auth_headers(role="MANAGER")
    today = date.today()
    period_start = date(today.year, today.month, 1)
    period_end = date(today.year, today.month, monthrange(today.year, today.month)[1])
    payload = {
        "employee_id": employee_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "allowances": "1250.50",
        "bonus": "500.00",
        "deductions": "1000.25",
    }

    assert client.get("/api/payroll", headers=manager_headers).status_code == 403
    assert client.post("/api/payroll", json=payload, headers=employee_headers).status_code == 403
    assert client.post(
        "/api/payroll",
        json={**payload, "period_start": date(today.year, today.month, 2).isoformat()},
        headers=hr_headers,
    ).status_code == 422
    assert client.post(
        "/api/payroll",
        json={**payload, "deductions": "52000"},
        headers=hr_headers,
    ).status_code == 422

    created = client.post("/api/payroll", json=payload, headers=hr_headers)
    assert created.status_code == 201
    payroll = created.json()
    assert payroll["base_salary"] == 50000
    assert payroll["net_pay"] == 50750.25
    assert payroll["status"] == "Draft"
    assert client.post("/api/payroll", json=payload, headers=admin_headers).status_code == 409
    assert client.patch(
        f"/api/payroll/{payroll['id']}/status",
        json={"status": "Paid"},
        headers=admin_headers,
    ).status_code == 409

    second_payload = {
        **payload,
        "employee_id": second_employee_id,
        "allowances": 0,
        "bonus": 0,
        "deductions": 0,
    }
    assert client.post(
        "/api/payroll",
        json=second_payload,
        headers=admin_headers,
    ).status_code == 201
    previous_period_start = (
        date(today.year - 1, 12, 1)
        if today.month == 1
        else date(today.year, today.month - 1, 1)
    )
    previous_period_end = date(
        previous_period_start.year,
        previous_period_start.month,
        monthrange(previous_period_start.year, previous_period_start.month)[1],
    )
    assert client.post(
        "/api/payroll",
        json={
            **second_payload,
            "period_start": previous_period_start.isoformat(),
            "period_end": previous_period_end.isoformat(),
            "deductions": 40000,
        },
        headers=admin_headers,
    ).status_code == 201

    assistant_summary = client.post(
        "/api/payroll/assistant",
        json={"question": "What is the total payroll?"},
        headers=hr_headers,
    )
    assert assistant_summary.status_code == 200
    assert assistant_summary.json()["record_count"] == 2
    assert assistant_summary.json()["totals"]["net_pay"] == 120750.25
    breakdown = client.post(
        "/api/payroll/assistant",
        json={"question": "Show the salary breakdown"},
        headers=hr_headers,
    ).json()
    assert "base salary 120,000.00" in breakdown["answer"]
    assert "net pay 120,750.25" in breakdown["answer"]
    assert any(
        alert["category"] == "Large month-over-month change"
        for alert in assistant_summary.json()["alerts"]
    )
    previous_insights = client.post(
        "/api/payroll/assistant",
        json={"period_start": previous_period_start.isoformat()},
        headers=admin_headers,
    ).json()
    assert any(
        alert["category"] == "High deduction share"
        for alert in previous_insights["alerts"]
    )
    assert client.post(
        "/api/payroll/assistant",
        json={},
        headers=manager_headers,
    ).status_code == 403

    employee_account = next(
        account
        for account in client.get("/api/users", headers=admin_headers).json()
        if account["email"] == "high@example.com"
    )
    assert client.put(
        f"/api/employees/{employee_id}/account",
        json={"user_id": employee_account["id"]},
        headers=admin_headers,
    ).status_code == 200
    assert client.get("/api/payroll", headers=employee_headers).json() == []
    assert client.get(
        f"/api/payroll?employee_id={second_employee_id}",
        headers=employee_headers,
    ).status_code == 403
    assert client.patch(
        f"/api/payroll/{payroll['id']}/status",
        json={"status": "Approved"},
        headers=hr_headers,
    ).json()["status"] == "Approved"
    assert client.get("/api/payroll", headers=employee_headers).json() == []
    assert client.patch(
        f"/api/payroll/{payroll['id']}/status",
        json={"status": "Paid"},
        headers=admin_headers,
    ).json()["status"] == "Paid"
    own_payslips = client.get("/api/payroll", headers=employee_headers)
    assert own_payslips.status_code == 200
    assert [row["id"] for row in own_payslips.json()] == [payroll["id"]]
    employee_insights = client.post(
        "/api/payroll/assistant",
        json={"question": "How much are deductions?"},
        headers=employee_headers,
    )
    assert employee_insights.status_code == 200
    assert employee_insights.json()["record_count"] == 1
    assert employee_insights.json()["totals"]["net_pay"] == 50750.25
    assert "1,000.25" in employee_insights.json()["answer"]
    assert client.patch(
        f"/api/payroll/{payroll['id']}/status",
        json={"status": "Approved"},
        headers=admin_headers,
    ).status_code == 409

    admin_summary = client.get("/api/dashboard/summary", headers=admin_headers).json()
    manager_summary = client.get("/api/dashboard/summary", headers=manager_headers).json()
    assert admin_summary["payroll_records_this_month"] == 2
    assert admin_summary["payroll_net_total_this_month"] == 120750.25
    assert "payroll_net_total_this_month" not in manager_summary
