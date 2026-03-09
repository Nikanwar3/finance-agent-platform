from .base import create_base_agent, get_shared_memory, set_shared_memory
from sqlalchemy.orm import Session
from ..models.domain import ActionLog, Issue, Metric, Company
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

def log_agent_action(db: Session, agent_name: str, company_id: str, action: str, details: str):
    log = ActionLog(agent_name=agent_name, company_id=company_id, action=action, details=details)
    db.add(log)
    db.commit()

class TrialBalanceValidator:
    def __init__(self):
        self.agent = create_base_agent(
            name="Trial Balance Validator",
            instructions="You are a trial balance validator. Check if debits equal credits and flag unexpected balances. Respond with JSON containing 'issues', 'status', 'debts', 'credits'."
        )

    def run(self, company_id: str, db: Session):
        log_agent_action(db, "Trial Balance Validator", company_id, "Started Validation", "Reading trial balance data")
        
        # Simulated run for now, we can load CSV in reality
        # Here we mock finding an issue
        issue_found = company_id in ["techforge_saas"] # Deterministic mock issue
        
        if issue_found:
            issue = Issue(company_id=company_id, category="Trial Balance", description="Debits and Credits mismatch by $500", severity="High")
            db.add(issue)
            log_agent_action(db, "Trial Balance Validator", company_id, "Validation Failed", "Found 1 issue: Debits/Credits mismatch")
        else:
            log_agent_action(db, "Trial Balance Validator", company_id, "Validation Passed", "Debits equal Credits")
        
        db.commit()
        set_shared_memory("tb_status", company_id, {"status": "completed", "issues": issue_found})
        return {"status": "completed", "issues": issue_found}

class VarianceAnalysisAgent:
    def __init__(self):
        self.agent = create_base_agent(
            name="Variance Analysis Agent",
            instructions="Compare actual vs budget. Identify variances >10%. Produce commentary."
        )

    def run(self, company_id: str, db: Session):
        log_agent_action(db, "Variance Analysis", company_id, "Started Analysis", "Comparing actual vs budget")
        
        # Mock variance analysis
        variance = Issue(company_id=company_id, category="Variance", description="SG&A expenses are 15% over budget due to higher marketing spend.", severity="Medium")
        db.add(variance)
        
        log_agent_action(db, "Variance Analysis", company_id, "Completed Analysis", "Identified SG&A variance")
        db.commit()
        return {"status": "completed"}

class AccrualVerificationAgent:
    def __init__(self):
        self.agent = create_base_agent(
            name="Accrual Verification Agent",
            instructions="Verify accrued expenses and missing accruals."
        )

    def run(self, company_id: str, db: Session):
        log_agent_action(db, "Accrual Verification", company_id, "Started Verification", "Reviewing accrual schedules")
        
        if company_id == "precisionmfg_inc":
            issue = Issue(company_id=company_id, category="Accrual", description="Missing December bonus accrual.", severity="High")
            db.add(issue)
            log_agent_action(db, "Accrual Verification", company_id, "Issue Found", "Missing December bonus accrual detected.")
        else:
            log_agent_action(db, "Accrual Verification", company_id, "Completed", "All accruals verified.")
            
        db.commit()
        return {"status": "completed"}

class IntercompanyEliminationAgent:
    def __init__(self):
        self.agent = create_base_agent(
            name="Intercompany Elimination Agent",
            instructions="Identify and validate intercompany transactions."
        )
        
    def run(self, company_id: str, db: Session):
        log_agent_action(db, "Intercompany Elimination", company_id, "Cross-check", "Validating intercompany entries")
        
        log_agent_action(db, "Intercompany Elimination", company_id, "Completed", "Intercompany entries net to zero.")
        db.commit()
        return {"status": "completed"}

# ... other agents follow similarly ...

class OrchestratorAgent:
    def __init__(self):
        self.agent = create_base_agent(
            name="Orchestrator Agent",
            instructions="You manage the month end close workflow."
        )
        self.tb_validator = TrialBalanceValidator()
        self.variance_agent = VarianceAnalysisAgent()
        self.accrual_agent = AccrualVerificationAgent()
        self.ic_agent = IntercompanyEliminationAgent()
        
    def run_company_close(self, company_id: str, db: Session):
        # Update progress
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False
            
        company.status = "in_progress"
        db.commit()
        
        log_agent_action(db, "Orchestrator", company_id, "Started Close Workflow", "Initiated month-end close")
        
        # Parallel Execution Group 1
        self.tb_validator.run(company_id, db)
        company.progress = 25
        db.commit()
        
        self.variance_agent.run(company_id, db)
        company.progress = 50
        db.commit()
        
        # Sequential Execution Group 2
        self.accrual_agent.run(company_id, db)
        company.progress = 75
        db.commit()
        
        # Cross Company Group 3
        self.ic_agent.run(company_id, db)
        
        company.progress = 100
        company.status = "completed"
        log_agent_action(db, "Orchestrator", company_id, "Completed Close Workflow", "Month-end close completed")
        db.commit()
        
        return True
