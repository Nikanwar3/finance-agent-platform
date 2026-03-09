from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.routes import router as api_router
from .models.database import engine, Base, SessionLocal
from .models.domain import Company
from .core.config import settings
import json
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
Base.metadata.create_all(bind=engine)

def seed_database():
    db = SessionLocal()
    # Check if we already seeded
    if db.query(Company).first():
        db.close()
        return

    seed_file = "data/company_metadata.json"
    if os.path.exists(seed_file):
        with open(seed_file, "r") as f:
            companies = json.load(f)
            for c in companies:
                db_company = Company(
                    id=c["id"],
                    name=c["name"],
                    industry=c["industry"],
                    revenue_annual=c["revenue_annual"],
                    employees=c["employees"]
                )
                db.add(db_company)
        db.commit()
        logger.info("Database seeded successfully with companies.")
    else:
        logger.warning(f"Seed file not found at {seed_file}")
    db.close()

seed_database()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Welcome to Apex Capital Partners AI Agent API"}
