from datetime import date
from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password
Base.metadata.create_all(bind=engine)
db=SessionLocal()
try:
    if not db.query(models.User).filter_by(email="admin@workforce.local").first():
        db.add(models.User(email="admin@workforce.local",full_name="WorkForce Admin",hashed_password=hash_password("Admin123!"),role="ADMIN"))
    dept_names=[("Engineering","Product and engineering"),("Sales","Revenue and customer growth"),("Human Resources","People operations"),("Finance","Finance and operations"),("Customer Support","Customer experience")]
    for name,desc in dept_names:
        if not db.query(models.Department).filter_by(name=name).first(): db.add(models.Department(name=name,description=desc))
    db.commit()
    admin_user=db.query(models.User).filter_by(email="admin@workforce.local").first()
    for leave_type, allowance in [("Annual",20),("Sick",10)]:
        if not db.query(models.LeavePolicy).filter_by(leave_type=leave_type,year=date.today().year).first():
            db.add(models.LeavePolicy(leave_type=leave_type,year=date.today().year,annual_allowance_days=allowance,created_by_id=admin_user.id))
    db.commit()
    depts={d.name:d.id for d in db.query(models.Department).all()}
    samples=[("EMP001","Aarav Kumar","aarav@example.com","Software Engineer","Engineering",4.2,65000,4,4,False,1),("EMP002","Priya Sharma","priya@example.com","Sales Executive","Sales",2.1,42000,2,3,True,3),("EMP003","Rahul Patel","rahul@example.com","HR Associate","Human Resources",1.4,38000,3,4,False,1), ("EMP004","Meera Iyer","meera@example.com","Data Analyst","Engineering",5.0,72000,2,2,True,4), ("EMP005","Karthik Raj","karthik@example.com","Accountant","Finance",3.3,48000,3,3,False,2), ("EMP006","Ananya Das","ananya@example.com","Support Specialist","Customer Support",1.8,35000,1,2,True,4), ("EMP007","Vikram Singh","vikram@example.com","Product Manager","Engineering",6.5,95000,4,3,False,1), ("EMP008","Sneha Nair","sneha@example.com","Sales Manager","Sales",4.0,80000,2,2,True,3), ("EMP009","Arjun Menon","arjun@example.com","Recruiter","Human Resources",2.8,46000,4,4,False,1), ("EMP010","Ishita Roy","ishita@example.com","Financial Analyst","Finance",3.7,58000,3,3,False,2)]
    for code,name,email,title,dept,tenure,income,sat,balance,ot,promo in samples:
        if not db.query(models.Employee).filter_by(employee_code=code).first():
            db.add(models.Employee(employee_code=code,full_name=name,email=email,job_title=title,department_id=depts[dept],tenure_years=tenure,monthly_income=income,job_satisfaction=sat,work_life_balance=balance,overtime=ot,years_since_promotion=promo))
    db.commit(); print("Seed complete. Login: admin@workforce.local / Admin123!")
finally: db.close()
