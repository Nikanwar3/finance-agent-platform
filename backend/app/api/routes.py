from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from ..models.database import get_db
from ..models.domain import Company, Issue, ActionLog
from ..schemas.domain import CompanyResponse, IssueResponse, ActionLogResponse
from ..core.exceptions import CompanyNotFoundError, CloseAlreadyInProgressError
from ..core.rate_limit import limiter
from ..workers.tasks import run_company_close_task

router = APIRouter()

# Requests/minute allowed for the (cheap) list/read endpoints vs. the
# (expensive — enqueues a multi-agent workflow) close-trigger endpoint.
LIST_RATE_LIMIT = "60/minute"
CLOSE_RATE_LIMIT = "5/minute"


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
@limiter.limit(LIST_RATE_LIMIT)
def get_companies(request: Request, db: Session = Depends(get_db)):
    return db.query(Company).all()

@router.get("/companies/{company_id}", response_model=CompanyResponse)
@limiter.limit(LIST_RATE_LIMIT)
def get_company(request: Request, company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise CompanyNotFoundError(company_id)
    return company

@router.get("/companies/{company_id}/issues", response_model=List[IssueResponse])
@limiter.limit(LIST_RATE_LIMIT)
def get_company_issues(request: Request, company_id: str, db: Session = Depends(get_db)):
    return db.query(Issue).filter(Issue.company_id == company_id).all()

@router.get("/issues", response_model=List[IssueResponse])
@limiter.limit(LIST_RATE_LIMIT)
def get_all_issues(request: Request, db: Session = Depends(get_db)):
    return db.query(Issue).all()

@router.get("/logs", response_model=List[ActionLogResponse])
@limiter.limit(LIST_RATE_LIMIT)
def get_logs(request: Request, db: Session = Depends(get_db)):
    return db.query(ActionLog).order_by(ActionLog.timestamp.desc()).limit(100).all()

@router.post("/close/{company_id}")
@limiter.limit(CLOSE_RATE_LIMIT)
def run_month_end_close(request: Request, company_id: str, db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise CompanyNotFoundError(company_id)
    if company.status == "in_progress":
        raise CloseAlreadyInProgressError(company_id)

    # Enqueue onto the Celery/Redis task queue and return immediately — the
    # actual multi-agent close workflow runs in a separate `worker` process
    # (see docker-compose.yml), not on this request's thread.
    run_company_close_task.delay(company_id)
    return {"message": "Close process queued", "company_id": company_id}

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
            # Just keep the connection alive; server -> client updates are
            # pushed via ConnectionManager.broadcast() from the Redis
            # pub/sub relay (see services/pubsub_relay.py), not in response
            # to anything the client sends here.
    except WebSocketDisconnect:
        manager.disconnect(websocket)
