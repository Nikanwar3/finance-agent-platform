# AWS Deployment

Target architecture for running this platform on AWS in production. The
GitHub Actions workflow at `.github/workflows/deploy.yml` builds the backend
image, pushes it to ECR, and rolls out a new ECS task revision using the
template in this directory — this doc describes the infrastructure that
workflow assumes already exists.

## Architecture

```
Internet
   │
   ▼
Application Load Balancer (ALB, public subnets)
   │
   ▼
ECS Fargate Service — "backend" (private subnets, autoscaled on CPU/req count)
   │                              ECS Fargate Service — "worker" (Celery consumer,
   │                               same image, `celery -A app.core.celery_app worker`)
   ├── RDS PostgreSQL (Multi-AZ)  — primary state: companies, issues, action logs
   ├── ElastiCache Redis          — agent shared-memory, Celery broker, pub/sub,
   │                                 rate-limit counters
   └── S3 bucket                 — immutable month-end close report archive

Secrets Manager  — DATABASE_URL / REDIS_URL / OPENAI_API_KEY, injected into
                     both ECS services as `secrets` (never baked into the image)
ECR              — backend image registry
CloudWatch Logs  — structured JSON logs from both services (see
                     app/core/logging_config.py), queryable by request_id
```

## One-time setup (before the deploy workflow can run)

1. **ECR repository**: `finance-platform-backend`.
2. **RDS PostgreSQL** instance/cluster; store its connection string in
   Secrets Manager as `finance-platform/database-url`.
3. **ElastiCache Redis** cluster; store its URL as `finance-platform/redis-url`.
4. **S3 bucket** for close-report archival; store its name as
   `finance-platform/s3-bucket`. Enable versioning + a lifecycle policy if
   you want automatic tiering to Glacier for older reports.
5. **ECS cluster** (`finance-platform-cluster`) with two Fargate services:
   - `finance-platform-backend` — runs the task definition in
     `ecs-task-definition.json`, behind the ALB.
   - `finance-platform-worker` — same image, override the container command
     to `celery -A app.core.celery_app worker --loglevel=info`, no ALB/health
     check needed.
6. **IAM roles**: an execution role (pulls the image, reads secrets, writes
   logs) and a task role (the app's own AWS permissions — S3 `PutObject` on
   the close-report bucket).
7. **GitHub OIDC deploy role**: an IAM role GitHub Actions can assume via
   `aws-actions/configure-aws-credentials` (no long-lived AWS keys stored in
   GitHub). Store its ARN as the `AWS_DEPLOY_ROLE_ARN` repo secret, and the
   target region as `AWS_REGION`.

## Deploying

- **Automatic**: push a tag matching `v*` (e.g. `git tag v1.2.0 && git push --tags`).
- **Manual**: trigger `Deploy to AWS` from the Actions tab (`workflow_dispatch`).

Each run builds the backend image, tags it with the commit SHA, pushes to
ECR, renders a new task definition revision with that image, and updates the
`finance-platform-backend` ECS service — then waits for the new tasks to pass
their health check before finishing.

## Why this shape

- **Fargate over EC2**: no instance/AMI patching for a project this size;
  scales the backend and worker services independently.
- **Worker as its own ECS service, not a sidecar**: the Celery consumer has
  a completely different failure/scaling profile (CPU-bound agent workflows,
  no ALB traffic) from the API — coupling them would mean over-provisioning
  one to satisfy the other.
- **Secrets Manager, not task-definition env vars**: `DATABASE_URL` and
  `REDIS_URL` contain credentials; ECS resolves `secrets` at task-start time
  so they never appear in the task definition, CloudFormation, or `docker
  inspect` output.
