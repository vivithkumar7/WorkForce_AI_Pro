import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./workforce.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
class Base(DeclarativeBase): pass

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()


def upgrade_legacy_columns():
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        user_columns = {
            column["name"] for column in inspector.get_columns("users")
        }
        if "session_version" not in user_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN session_version "
                        "VARCHAR(32) NOT NULL DEFAULT ''"
                    )
                )

    inspector = inspect(engine)
    if "employees" in inspector.get_table_names():
        employee_columns = {
            column["name"] for column in inspector.get_columns("employees")
        }
        if "user_id" not in employee_columns:
            with engine.begin() as connection:
                reference = (
                    ""
                    if engine.dialect.name == "mysql"
                    else " REFERENCES users(id)"
                )
                connection.execute(
                    text(
                        "ALTER TABLE employees ADD COLUMN user_id "
                        f"INTEGER NULL{reference}"
                    )
                )
        inspector = inspect(engine)
        employee_indexes = {
            index["name"] for index in inspector.get_indexes("employees")
        }
        employee_unique_constraints = inspector.get_unique_constraints("employees")
        user_id_is_unique = (
            "uq_employees_user_id" in employee_indexes
            or any(
                constraint["column_names"] == ["user_id"]
                for constraint in employee_unique_constraints
            )
        )
        if not user_id_is_unique:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "CREATE UNIQUE INDEX uq_employees_user_id "
                        "ON employees (user_id)"
                    )
                )
        if engine.dialect.name == "mysql":
            inspector = inspect(engine)
            employee_foreign_keys = {
                key["name"] for key in inspector.get_foreign_keys("employees")
            }
            if "fk_employees_user_id" not in employee_foreign_keys:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "ALTER TABLE employees ADD CONSTRAINT "
                            "fk_employees_user_id FOREIGN KEY (user_id) REFERENCES users(id)"
                        )
                    )

    inspector = inspect(engine)
    if "shifts" in inspector.get_table_names():
        shift_columns = {
            column["name"] for column in inspector.get_columns("shifts")
        }
        if "break_minutes" not in shift_columns:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "ALTER TABLE shifts ADD COLUMN break_minutes "
                        "INTEGER NOT NULL DEFAULT 0"
                    )
                )

    inspector = inspect(engine)
    if "attendance_records" in inspector.get_table_names():
        attendance_columns = {
            column["name"]
            for column in inspector.get_columns("attendance_records")
        }
        if "shift_id" not in attendance_columns:
            with engine.begin() as connection:
                reference = (
                    ""
                    if engine.dialect.name == "mysql"
                    else " REFERENCES shifts(id)"
                )
                connection.execute(
                    text(
                        "ALTER TABLE attendance_records ADD COLUMN shift_id "
                        f"INTEGER NULL{reference}"
                    )
                )
        if engine.dialect.name == "mysql":
            inspector = inspect(engine)
            attendance_foreign_keys = {
                key["name"]
                for key in inspector.get_foreign_keys("attendance_records")
            }
            if "fk_attendance_shift_id" not in attendance_foreign_keys:
                with engine.begin() as connection:
                    connection.execute(
                        text(
                            "ALTER TABLE attendance_records ADD CONSTRAINT "
                            "fk_attendance_shift_id FOREIGN KEY (shift_id) REFERENCES shifts(id)"
                        )
                    )
