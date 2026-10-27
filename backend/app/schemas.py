from datetime import date, datetime
from calendar import monthrange
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

class LoginResponse(BaseModel): access_token: str; token_type: str = "bearer"
class UserOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; email:str; full_name:str; role:str
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["ADMIN", "HR", "MANAGER", "EMPLOYEE"]

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        if (
            not any(character.islower() for character in password)
            or not any(character.isupper() for character in password)
            or not any(character.isdigit() for character in password)
            or not any(not character.isalnum() for character in password)
        ):
            raise ValueError(
                "Password must include uppercase, lowercase, numeric, and special characters"
            )
        return password

class UserAdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    role: Literal["ADMIN", "HR", "MANAGER", "EMPLOYEE"] | None = None
    is_active: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self

class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, password: str) -> str:
        if (
            not any(character.islower() for character in password)
            or not any(character.isupper() for character in password)
            or not any(character.isdigit() for character in password)
            or not any(not character.isalnum() for character in password)
        ):
            raise ValueError(
                "Password must include uppercase, lowercase, numeric, and special characters"
            )
        return password

class PayrollGenerate(BaseModel):
    employee_id: int = Field(ge=1)
    period_start: date
    period_end: date
    allowances: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    bonus: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    deductions: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode="after")
    def validate_monthly_period(self):
        if (
            self.period_start.year != self.period_end.year
            or self.period_start.month != self.period_end.month
            or self.period_start.day != 1
            or self.period_end.day
            != monthrange(self.period_start.year, self.period_start.month)[1]
        ):
            raise ValueError("Payroll period must cover one full calendar month")
        return self

class PayrollStatusUpdate(BaseModel):
    status: Literal["Approved", "Paid"]

class PayrollAssistantRequest(BaseModel):
    question: str = Field(default="", max_length=500)
    period_start: date | None = None

class DepartmentCreate(BaseModel): name:str=Field(min_length=2,max_length=100); description:str|None=None
class DepartmentOut(BaseModel): model_config=ConfigDict(from_attributes=True); id:int; name:str; description:str|None=None
class EmployeeCreate(BaseModel):
    employee_code:str=Field(min_length=1,max_length=30); full_name:str=Field(min_length=2,max_length=160); email:EmailStr; job_title:str=Field(min_length=2,max_length=120); department_id:int=Field(ge=1)
    tenure_years:float=Field(default=1,ge=0,le=60); monthly_income:float=Field(default=40000,ge=0)
    job_satisfaction:int=Field(default=3,ge=1,le=4); work_life_balance:int=Field(default=3,ge=1,le=4)
    overtime:bool=False; years_since_promotion:float=Field(default=1,ge=0,le=60); joined_on:date=Field(default_factory=date.today)
class EmployeeUpdate(BaseModel):
    full_name:str|None=Field(default=None,min_length=2,max_length=160)
    job_title:str|None=Field(default=None,min_length=2,max_length=120)
    department_id:int|None=Field(default=None,ge=1)
    tenure_years:float|None=Field(default=None,ge=0,le=60)
    monthly_income:float|None=Field(default=None,ge=0)
    job_satisfaction:int|None=Field(default=None,ge=1,le=4)
    work_life_balance:int|None=Field(default=None,ge=1,le=4)
    overtime:bool|None=None
    years_since_promotion:float|None=Field(default=None,ge=0,le=60)
    is_active:bool|None=None

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

class EmployeeOut(BaseModel):
    model_config=ConfigDict(from_attributes=True); id:int; employee_code:str; full_name:str; email:str; job_title:str
    department_id:int; department_name:str; tenure_years:float; monthly_income:float; job_satisfaction:int; work_life_balance:int; overtime:bool; years_since_promotion:float; is_active:bool; joined_on:date
    user_id: int | None = None
class PredictionOut(BaseModel): id:int; employee_id:int; employee_name:str; department:str; risk_percent:float; risk_level:str; confidence_score:float; explanation:str; created_at:datetime
class InterventionCreate(BaseModel):
    employee_id: int = Field(ge=1)
    intervention_type: str = Field(default="Support check-in", min_length=2, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)

class InterventionUpdate(BaseModel):
    status: Literal["Open", "In Progress", "Completed"] | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=255)

class ShiftCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    start_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end_time: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    break_minutes: int = Field(default=0, ge=0, le=240)

    @model_validator(mode="after")
    def validate_duration(self):
        start = datetime.strptime(self.start_time, "%H:%M")
        end = datetime.strptime(self.end_time, "%H:%M")
        duration_minutes = int((end - start).total_seconds() / 60)
        if duration_minutes <= 0:
            duration_minutes += 24 * 60
        if duration_minutes == 24 * 60:
            raise ValueError("Shift start and end times cannot be the same")
        if self.break_minutes >= duration_minutes:
            raise ValueError("Break must be shorter than the shift duration")
        return self

class ShiftAssignmentCreate(BaseModel):
    employee_id: int = Field(ge=1)
    shift_id: int = Field(ge=1)
    effective_from: date = Field(default_factory=date.today)

class AttendanceAction(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)

class LeaveCreate(BaseModel):
    employee_id: int | None = Field(default=None, ge=1)
    leave_type: str = Field(min_length=2, max_length=40)
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=1000)

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date, info):
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        if start_date and end_date.year != start_date.year:
            raise ValueError("A leave request must stay within one calendar year")
        return end_date

class LeaveReview(BaseModel):
    status: Literal["Approved", "Rejected"]
    reviewer_notes: str | None = Field(default=None, max_length=1000)

class EmployeeLink(BaseModel):
    user_id: int = Field(ge=1)

class LeavePolicyCreate(BaseModel):
    leave_type: str = Field(min_length=2, max_length=40)
    year: int = Field(ge=2000, le=2100)
    annual_allowance_days: int = Field(ge=0, le=366)

class LeavePolicyUpdate(BaseModel):
    annual_allowance_days: int | None = Field(default=None, ge=0, le=366)
    is_active: bool | None = None

    @field_validator("*", mode="before")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Field cannot be null")
        return value

class NotificationRead(BaseModel):
    is_read: bool = True
