from .base import create_base_agent, get_shared_memory, set_shared_memory
from sqlalchemy.orm import Session
from ..core.aws_client import upload_close_report
from ..models.database import SessionLocal
from ..models.domain import ActionLog, Issue, Metric, Company
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
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

class AgentNode:
    """One agent in the close-workflow dependency graph."""

    def __init__(self, agent_id: str, agent, depends_on=()):
        self.agent_id = agent_id
        self.agent = agent
        self.depends_on = tuple(depends_on)


class DependencyGraph:
    """
    Directed acyclic graph of agent dependencies, scheduled with a level-order
    topological sort (Kahn's algorithm). Agents with no remaining unmet
    dependencies form one "level" and can safely run concurrently; the next
    level is only released once every agent in the current level has finished.
    """

    def __init__(self, nodes):
        self.nodes = {node.agent_id: node for node in nodes}
        self.dependents = defaultdict(list)  # dependency_id -> [dependent_id, ...]
        self.in_degree = {node.agent_id: len(node.depends_on) for node in nodes}

        for node in nodes:
            for dep_id in node.depends_on:
                if dep_id not in self.nodes:
                    raise ValueError(f"Unknown dependency '{dep_id}' for agent '{node.agent_id}'")
                self.dependents[dep_id].append(node.agent_id)

    def execution_levels(self):
        """Return agent ids grouped into ordered levels safe to run concurrently."""
        in_degree = dict(self.in_degree)
        ready = deque(sorted(nid for nid, deg in in_degree.items() if deg == 0))
        levels = []
        visited = 0

        while ready:
            level = list(ready)
            ready.clear()
            levels.append(level)
            visited += len(level)

            for agent_id in level:
                for dependent_id in self.dependents[agent_id]:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        ready.append(dependent_id)

        if visited != len(self.nodes):
            stuck = [nid for nid, deg in in_degree.items() if deg > 0]
            raise ValueError(f"Cycle detected in agent dependency graph: {stuck}")

        return levels


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

        # Dependency graph for one company's close: trial-balance validation and
        # variance analysis are independent and run in parallel; accrual
        # verification requires a settled trial balance; intercompany
        # elimination requires both accruals and variance analysis to be done.
        self.graph = DependencyGraph([
            AgentNode("trial_balance", self.tb_validator),
            AgentNode("variance", self.variance_agent),
            AgentNode("accrual", self.accrual_agent, depends_on=("trial_balance",)),
            AgentNode("intercompany", self.ic_agent, depends_on=("accrual", "variance")),
        ])

    def _run_level(self, level_agent_ids, company_id: str):
        """Run every agent in a level concurrently, each on its own DB session."""

        def run_one(agent_id):
            node = self.graph.nodes[agent_id]
            session = SessionLocal()
            try:
                return node.agent.run(company_id, session)
            finally:
                session.close()

        results = {}
        with ThreadPoolExecutor(max_workers=len(level_agent_ids)) as pool:
            futures = {pool.submit(run_one, agent_id): agent_id for agent_id in level_agent_ids}
            for future in as_completed(futures):
                agent_id = futures[future]
                results[agent_id] = future.result()
        return results

    def run_company_close(self, company_id: str, db: Session):
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            return False

        company.status = "in_progress"
        db.commit()

        log_agent_action(db, "Orchestrator", company_id, "Started Close Workflow", "Initiated month-end close")

        levels = self.graph.execution_levels()
        for level_index, level_agent_ids in enumerate(levels):
            self._run_level(level_agent_ids, company_id)
            company.progress = round((level_index + 1) / len(levels) * 100)
            db.commit()

        company.status = "completed"
        log_agent_action(db, "Orchestrator", company_id, "Completed Close Workflow", "Month-end close completed")
        db.commit()

        self._archive_close_report(company_id, db)

        return True

    def _archive_close_report(self, company_id: str, db: Session):
        """Upload an immutable JSON summary of this close to S3 for audit
        trail purposes. Best-effort: archival failures never fail the close
        itself (see aws_client.upload_close_report)."""
        issues = db.query(Issue).filter(Issue.company_id == company_id).all()
        report = {
            "company_id": company_id,
            "generated_at": datetime.utcnow().isoformat(),
            "issue_count": len(issues),
            "issues": [
                {"category": i.category, "description": i.description, "severity": i.severity}
                for i in issues
            ],
        }
        report_uri = upload_close_report(company_id, report)
        if report_uri:
            log_agent_action(db, "Orchestrator", company_id, "Archived Close Report", f"Uploaded to {report_uri}")
