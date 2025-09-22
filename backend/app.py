# backend/main.py
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from .db import SessionLocal, engine
from . import models, schemas, init_db
from rapidfuzz import process, fuzz
from typing import List
import math

# initialize
init_db.init_db_from_csvs()

app = FastAPI(title="UltraPro Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------
# Auth endpoints
# -----------------
@app.post("/register")
def register_user(payload: schemas.RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(models.User).filter(models.User.email==payload.email).first()
    if exists:
        raise HTTPException(status_code=400, detail="Email already exists")
    # Note: for production, hash password
    user = models.User(username=payload.username, email=payload.email, password=payload.password)
    db.add(user)
    db.commit()
    return {"ok": True}

@app.post("/login")
def login_user(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email==payload.email, models.User.password==payload.password).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"username": user.username, "email": user.email}

# -----------------
# Search endpoint (fuzzy matching + risk scoring + recommendations)
# -----------------
@app.post("/search")
def search(payload: schemas.SearchIn, db: Session = Depends(get_db)):
    # Normalize symptoms
    input_symptoms = [s.strip().lower() for s in payload.input_symptoms.split(",") if s.strip()]
    # Load all symptoms from table
    rows = db.query(models.SymptomCondition).all()
    all_symptoms = [r.symptoms for r in rows]
    # fuzzy match each symptom to symptoms table
    condition_scores = {}
    for symptom in input_symptoms:
        if not symptom:
            continue
        best = process.extract(symptom, all_symptoms, scorer=fuzz.ratio, limit=3)
        for match, score, idx in best:
            if score >= 60:
                matched_rows = [r for r in rows if r.symptoms == match]
                for mr in matched_rows:
                    condition_scores[mr.possible_condition] = condition_scores.get(mr.possible_condition, 0) + score
    top_conditions = sorted(condition_scores.items(), key=lambda x: x[1], reverse=True)[:5]
    matched_conditions = [c for c,_ in top_conditions]

    # Calculate risk_score same as original: num_severe = count if severity==Severe (original code had bug but kept same semantics)
    num_severe = len([c for c in matched_conditions if payload.severity == "Severe"])
    risk_score = payload.duration_days * num_severe * (3 if payload.severity == "Severe" else 2 if payload.severity == "Moderate" else 1)

    results = []
    if matched_conditions:
        # join condition_medicine and condition_precautions
        for cond in matched_conditions:
            cm = db.query(models.ConditionMedicine).filter(models.ConditionMedicine.condition == cond).first()
            cp = db.query(models.ConditionPrecautions).filter(models.ConditionPrecautions.condition == cond).first()
            med_list = []
            if cm and cm.recommended_medicines:
                med_list = [m.strip() for m in cm.recommended_medicines.split(",") if m.strip()]
            precautions = cp.precautions if cp else "No precautions available"
            results.append({
                "condition": cond,
                "recommended_medicines": med_list,
                "precautions": precautions
            })

        # Compute collaborative filtering / frequently purchased for each condition:
        # Simple approach: for each condition find top medicines by purchase count across users.
        cf = {}
        for cond in matched_conditions:
            rows = db.query(models.Purchase.medicine, models.Purchase).filter(models.Purchase.condition == cond).all()
            # Using raw SQL via SQLAlchemy ORM is possible, but we'll do a simple count
            purchases = db.query(models.Purchase.medicine).filter(models.Purchase.condition==cond).all()
            meds = [m[0] for m in purchases]
            freq = {}
            for m in meds:
                freq[m] = freq.get(m, 0) + 1
            top_med = sorted(freq.items(), key=lambda x: x[1], reverse=True)
            cf[cond] = [m for m,_ in top_med[:3]]

        # Also suggest similar medicines (same category/composition) for top recommended med
        similar_suggestions = {}
        for res in results:
            if res["recommended_medicines"]:
                top_med = res["recommended_medicines"][0]
                medobj = db.query(models.Medicine).filter(models.Medicine.name==top_med).first()
                similar = []
                if medobj:
                    # find other medicines with same category or same first token of composition
                    if medobj.category:
                        others = db.query(models.Medicine.name).filter(models.Medicine.category==medobj.category, models.Medicine.name!=top_med).limit(5).all()
                        similar += [o[0] for o in others]
                    # composition token
                    token = (medobj.composition or "").split()[0] if medobj.composition else ""
                    if token:
                        others = db.query(models.Medicine.name).filter(models.Medicine.composition.like(f"%{token}%"), models.Medicine.name!=top_med).limit(5).all()
                        similar += [o[0] for o in others]
                similar_suggestions[top_med] = list(dict.fromkeys(similar))[:5]

        # Save history (like original)
        # recommended_medicine field saved as first med of last condition as in original behavior
        recommended_flat = results[-1]["recommended_medicines"][0] if results and results[-1]["recommended_medicines"] else "N/A"
        hist = models.History(
            user_email=payload.user_email or "",
            input_symptoms=", ".join(input_symptoms),
            severity=payload.severity,
            duration_days=payload.duration_days,
            risk_score=risk_score,
            conditions_found=", ".join(matched_conditions),
            recommended_medicine=recommended_flat
        )
        db.add(hist)
        db.commit()

    # Return JSON with recommendations and CF suggestions
    return {
        "matched_conditions": matched_conditions,
        "risk_score": risk_score,
        "results": results,
        "collaborative": cf,
        "similar_suggestions": similar_suggestions
    }

# -----------------
# Purchase endpoint
# -----------------
@app.post("/purchase")
def purchase(payload: schemas.PurchaseIn, db: Session = Depends(get_db)):
    p = models.Purchase(user_email=payload.user_email, condition=payload.condition, medicine=payload.medicine)
    db.add(p)
    db.commit()
    return {"ok": True}

# -----------------
# History and purchases queries
# -----------------
@app.get("/history/{user_email}")
def get_history(user_email: str, db: Session = Depends(get_db)):
    rows = db.query(models.History).filter(models.History.user_email == user_email).order_by(models.History.timestamp.desc()).all()
    out = []
    for r in rows:
        out.append({
            "id": r.id,
            "user_email": r.user_email,
            "input_symptoms": r.input_symptoms,
            "severity": r.severity,
            "duration_days": r.duration_days,
            "risk_score": r.risk_score,
            "conditions_found": r.conditions_found,
            "recommended_medicine": r.recommended_medicine,
            "timestamp": r.timestamp.isoformat()
        })
    return out

@app.get("/frequent_purchases")
def frequent_purchases(db: Session = Depends(get_db)):
    # Return most frequent medicine per condition
    sql = """
    SELECT condition, medicine, COUNT(*) as freq
    FROM purchases
    GROUP BY condition, medicine
    ORDER BY freq DESC
    """
    # use raw connection for that query
    conn = db.bind.raw_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()
    # aggregate top for each condition
    top_by_cond = {}
    for cond, med, freq in rows:
        if cond not in top_by_cond:
            top_by_cond[cond] = {"condition": cond, "medicine": med, "freq": int(freq)}
    return list(top_by_cond.values())
