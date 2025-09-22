# backend/schemas.py
from pydantic import BaseModel
from typing import List, Optional

class RegisterIn(BaseModel):
    username: str
    email: str
    password: str

class LoginIn(BaseModel):
    email: str
    password: str

class SearchIn(BaseModel):
    input_symptoms: str  # comma separated
    severity: str  # Mild/Moderate/Severe
    duration_days: int
    user_email: Optional[str] = None

class PurchaseIn(BaseModel):
    user_email: str
    condition: str
    medicine: str

class Recommendation(BaseModel):
    condition: str
    recommended_medicines: List[str]
    precautions: Optional[str]
