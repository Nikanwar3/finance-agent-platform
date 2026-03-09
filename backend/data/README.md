# Assignment 1: Month-End Close Sample Data

## Dataset Overview
This dataset contains realistic financial data for 8 portfolio companies spanning 3 months (Nov 2025 - Jan 2026).

## Directory Structure
```
backend/data/
├── trial_balances/       # Monthly trial balances for each company
├── budgets/             # 2026 annual budgets
├── prior_year/          # Prior year comparatives (2024-2025)
├── intercompany/        # Intercompany transactions requiring elimination
├── bank_statements/     # Mock bank statements
├── accrual_schedules/   # Standard accrual templates
└── company_metadata.json # Company profiles
```

## Known Issues (Intentional for Testing)
1. Some expenses may be miscategorized (e.g., marketing in COGS)
2. Missing accruals in December (bonus accrual not booked)
3. Some intercompany transactions missing elimination entries
4. Timing differences in prepaid expenses
