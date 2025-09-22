# backend/models.py
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(128))
    email = Column(String(256), unique=True, index=True, nullable=False)
    password = Column(String(256), nullable=False)

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(256), index=True)
    input_symptoms = Column(Text)
    severity = Column(String(32))
    duration_days = Column(Integer)
    risk_score = Column(Float)
    conditions_found = Column(Text)
    recommended_medicine = Column(String(256))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String(256), index=True)
    condition = Column(String(256))
    medicine = Column(String(256))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

# Tables to store CSV data
class Medicine(Base):
    __tablename__ = "medicines"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), unique=True, index=True)
    composition = Column(Text)
    category = Column(String(128), nullable=True)
    side_effects = Column(Text, nullable=True)

class SymptomCondition(Base):
    __tablename__ = "symptom_condition"
    id = Column(Integer, primary_key=True, index=True)
    symptoms = Column(String(256), index=True)
    possible_condition = Column(String(256), index=True)

class ConditionMedicine(Base):
    __tablename__ = "condition_medicine"
    id = Column(Integer, primary_key=True, index=True)
    condition = Column(String(256), index=True)
    recommended_medicines = Column(Text)

class ConditionPrecautions(Base):
    __tablename__ = "condition_precautions"
    id = Column(Integer, primary_key=True, index=True)
    condition = Column(String(256), index=True)
    precautions = Column(Text)
