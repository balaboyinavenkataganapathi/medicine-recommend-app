# backend/init_db.py
"""
Load CSVs into DB tables if empty. Expects CSVs to be present in the same folder as backend.
Files required:
 - medicines_realistic.csv (columns: name, composition, category, side_effects)
 - symptom_condition_curated.csv (columns: symptoms, possible_condition)
 - condition_medicine_realistic.csv (columns: condition, recommended_medicines)
 - condition_precautions_realistic.csv (columns: condition, precautions)
"""
import pandas as pd
import os
from .db import SessionLocal, engine
from .models import Medicine, SymptomCondition, ConditionMedicine, ConditionPrecautions, Base

def init_db_from_csvs():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    # If medicines table empty -> load
    if session.query(Medicine).first() is None:
        mpath = os.path.join(os.path.dirname(__file__), "expanded_medicines.csv")
        if os.path.exists(mpath):
            df = pd.read_csv(mpath).fillna("")
            for _, r in df.iterrows():
                m = Medicine(name=str(r.get("name","")).strip(), composition=str(r.get("composition","")), category=str(r.get("category","")), side_effects=str(r.get("side_effects","")))
                session.add(m)
            session.commit()

    if session.query(SymptomCondition).first() is None:
        p = os.path.join(os.path.dirname(__file__), "expanded_sympton_condition.csv")
        if os.path.exists(p):
            df = pd.read_csv(p).fillna("")
            for _, r in df.iterrows():
                s = SymptomCondition(symptoms=str(r.get("symptoms","")).strip(), possible_condition=str(r.get("possible_condition","")).strip())
                session.add(s)
            session.commit()

    if session.query(ConditionMedicine).first() is None:
        p = os.path.join(os.path.dirname(__file__), "expanded_condition_medicine.csv")
        if os.path.exists(p):
            df = pd.read_csv(p).fillna("")
            for _, r in df.iterrows():
                cm = ConditionMedicine(condition=str(r.get("condition","")).strip(), recommended_medicines=str(r.get("recommended_medicines","")))
                session.add(cm)
            session.commit()

    if session.query(ConditionPrecautions).first() is None:
        p = os.path.join(os.path.dirname(__file__), "expanded_condition_precautions.csv")
        if os.path.exists(p):
            df = pd.read_csv(p).fillna("")
            for _, r in df.iterrows():
                cp = ConditionPrecautions(condition=str(r.get("condition","")).strip(), precautions=str(r.get("precautions","")))
                session.add(cp)
            session.commit()
    session.close()
