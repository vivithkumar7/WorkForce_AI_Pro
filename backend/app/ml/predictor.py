from pathlib import Path
from functools import lru_cache
import joblib
MODEL_PATH=Path(__file__).with_name("attrition_model.joblib")
FEATURES=["tenure_years","monthly_income","job_satisfaction","work_life_balance","overtime","years_since_promotion"]

@lru_cache(maxsize=1)
def load_model():
    return joblib.load(MODEL_PATH)

def predict(employee):
    values=[[employee.tenure_years, employee.monthly_income, employee.job_satisfaction, employee.work_life_balance, int(employee.overtime), employee.years_since_promotion]]
    if MODEL_PATH.exists():
        model=load_model(); probability=float(model.predict_proba(values)[0][1]); version="sklearn-logistic-v1"
    else:
        # Transparent demo heuristic until the model is trained.
        score=0.12 + (0.12 if employee.overtime else 0) + max(0,3-employee.job_satisfaction)*0.13 + max(0,3-employee.work_life_balance)*0.09 + min(employee.years_since_promotion,5)*0.025 - min(employee.tenure_years,8)*0.012
        probability=max(0.03,min(0.94,score)); version="demo-heuristic-v1"
    risk=round(probability*100,1)
    level="High" if risk>=65 else "Medium" if risk>=35 else "Low"
    factors=[]
    if employee.overtime: factors.append("frequent overtime flag")
    if employee.job_satisfaction<=2: factors.append("low job satisfaction")
    if employee.work_life_balance<=2: factors.append("work-life balance concern")
    if employee.years_since_promotion>=3: factors.append("long time since promotion")
    if not factors: factors.append("no strong demo risk signals")
    return {"risk_percent":risk,"risk_level":level,"confidence_score":round(max(probability,1-probability)*100,1),"explanation":"Signals: " + ", ".join(factors),"model_version":version}
