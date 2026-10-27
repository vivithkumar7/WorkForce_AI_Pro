"""Train a demonstration classifier on synthetic data; replace with approved, representative data."""
import random
import pandas as pd
import joblib
from pathlib import Path
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
random.seed(42); rows=[]
for _ in range(1800):
    tenure=random.uniform(0,15); income=random.uniform(25000,150000); sat=random.randint(1,4); balance=random.randint(1,4); overtime=random.randint(0,1); promo=random.uniform(0,10)
    logit=-1.5 + overtime*.9 + (3-sat)*.65 + (3-balance)*.45 + promo*.12 - min(tenure,10)*.08 - (income-60000)/150000
    prob=1/(1+__import__('math').exp(-logit)); label=int(random.random()<prob)
    rows.append([tenure,income,sat,balance,overtime,promo,label])
df=pd.DataFrame(rows,columns=["tenure_years","monthly_income","job_satisfaction","work_life_balance","overtime","years_since_promotion","attrition"])
X=df.drop(columns="attrition"); y=df["attrition"]
model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,class_weight="balanced",random_state=42)); model.fit(X,y)
out=Path(__file__).parent/"app"/"ml"/"attrition_model.joblib"; joblib.dump(model,out); print(f"Saved demo model: {out}; synthetic training accuracy={model.score(X,y):.3f}")
