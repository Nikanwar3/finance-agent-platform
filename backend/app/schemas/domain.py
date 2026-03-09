from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CompanyBase(BaseModel):
    id: str
    name: str
    industry: str
    revenue_annual: float
    employees: int
    status: str
    progress: int

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    class Config:
        orm_mode = True

class IssueBase(BaseModel):
    category: str
    description: str
    severity: str
    status: str

class IssueResponse(IssueBase):
    id: int
    company_id: str
    created_at: datetime
    class Config:
        orm_mode = True

class MetricResponse(BaseModel):
    id: int
    company_id: str
    name: str
    value: float
    period: str
    class Config:
        orm_mode = True

class ActionLogResponse(BaseModel):
    id: int
    agent_name: str
    company_id: Optional[str]
    action: str
    details: str
    timestamp: datetime
    class Config:
        orm_mode = True
