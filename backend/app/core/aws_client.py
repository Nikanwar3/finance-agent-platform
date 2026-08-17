"""S3 archival of month-end close reports.

Every completed close produces an immutable JSON summary that's uploaded to
S3 for audit trail purposes. If no bucket is configured (e.g. running purely
locally without AWS credentials), this degrades to a no-op — the same
graceful-fallback pattern used for Redis via MockRedis.
"""
import json
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from .config import settings

logger = logging.getLogger(__name__)


def _build_s3_client():
    if not settings.AWS_S3_BUCKET:
        logger.info("s3_archival_disabled", extra={"reason": "AWS_S3_BUCKET not configured"})
        return None
    try:
        return boto3.client("s3", region_name=settings.AWS_REGION)
    except (BotoCoreError, NoCredentialsError):
        logger.warning("s3_client_init_failed", exc_info=True)
        return None


s3_client = _build_s3_client()


def upload_close_report(company_id: str, report: dict) -> str | None:
    """Upload a close report to S3, returning its s3:// URI, or None if
    archival is disabled/unavailable. Never raises — a failed upload should
    not fail the close workflow itself."""
    if s3_client is None:
        return None

    key = f"close-reports/{company_id}/{report['generated_at']}.json"
    try:
        s3_client.put_object(
            Bucket=settings.AWS_S3_BUCKET,
            Key=key,
            Body=json.dumps(report).encode("utf-8"),
            ContentType="application/json",
        )
        return f"s3://{settings.AWS_S3_BUCKET}/{key}"
    except (BotoCoreError, ClientError):
        logger.exception("s3_upload_failed", extra={"company_id": company_id, "key": key})
        return None
