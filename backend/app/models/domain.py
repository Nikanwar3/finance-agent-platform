from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    industry = Column(String)
    revenue_annual = Column(Float)
    employees = Column(Integer)
    status = Column(String, default="pending")  # pending, in_progress, completed, error
    progress = Column(Integer, default=0)

class Issue(Base):
    __tablename__ = "issues"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"))
    category = Column(String)  # variance, accrual, intercompany, etc.
    description = Column(String)
    severity = Column(String)  # high, medium, low
    status = Column(String, default="open")  # open, addressed, ignored
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")

class Metric(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, ForeignKey("companies.id"))
    name = Column(String) # Revenue, EBITDA, Cash
    value = Column(Float)
    period = Column(String)

    company = relationship("Company")

class ActionLog(Base):
    __tablename__ = "action_logs"
    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True)
    action = Column(String)
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company")
