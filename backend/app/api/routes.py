from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from ..models.database import get_db, init_db
from ..models.domain import Company, Issue, Metric, ActionLog
from ..schemas.domain import CompanyResponse, IssueResponse, MetricResponse, ActionLogResponse
from ..agents.agent_workflows import OrchestratorAgent
from fastapi.background import BackgroundTasks
import asyncio
import json

router = APIRouter()
orchestrator = OrchestratorAgent()

# WebSockets connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@router.get("/companies", response_model=List[CompanyResponse])
def get_companies(db: Session = Depends(get_db)):
    return db.query(Company).all()

@router.get("/companies/{company_id}", response_model=CompanyResponse)
def get_company(company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get("/companies/{company_id}/issues", response_model=List[IssueResponse])
def get_company_issues(company_id: str, db: Session = Depends(get_db)):
    return db.query(Issue).filter(Issue.company_id == company_id).all()

@router.get("/issues", response_model=List[IssueResponse])
def get_all_issues(db: Session = Depends(get_db)):
    return db.query(Issue).all()

@router.get("/logs", response_model=List[ActionLogResponse])
def get_logs(db: Session = Depends(get_db)):
    return db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(100).all()

def start_close_process(company_id: str, db: Session):
    orchestrator.run_company_close(company_id, db)
    # Ping websocket theoretically
    event = {"event": "agent_update", "action": "close_completed", "company_id": company_id}
    # Can't easily use asyncio inside sync thread without event loop trick
    # In a real app we would use Celery + Redis PubSub for scalable websockets
    
@router.post("/close/{company_id}")
def run_month_end_close(company_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    background_tasks.add_task(start_close_process, company_id, db)
    return {"message": "Close process started"}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Just keep the connection alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)
