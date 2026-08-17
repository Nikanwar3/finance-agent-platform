from app.core.aws_client import upload_close_report


def test_upload_disabled_returns_none_when_no_bucket_configured(monkeypatch):
    """With no AWS_S3_BUCKET configured (the default/local-dev case), close
    archival should degrade to a no-op rather than raising — mirrors the
    Redis MockRedis fallback pattern used elsewhere in this codebase."""
    monkeypatch.setattr("app.core.aws_client.s3_client", None)

    result = upload_close_report("acme_corp", {"generated_at": "2026-01-31T00:00:00"})

    assert result is None


def test_upload_returns_s3_uri_on_success(monkeypatch):
    class FakeS3Client:
        def __init__(self):
            self.calls = []

        def put_object(self, **kwargs):
            self.calls.append(kwargs)

    fake_client = FakeS3Client()
    monkeypatch.setattr("app.core.aws_client.s3_client", fake_client)
    monkeypatch.setattr("app.core.aws_client.settings.AWS_S3_BUCKET", "test-bucket")

    result = upload_close_report("acme_corp", {"generated_at": "2026-01-31T00:00:00"})

    assert result == "s3://test-bucket/close-reports/acme_corp/2026-01-31T00:00:00.json"
    assert fake_client.calls[0]["Bucket"] == "test-bucket"


def test_upload_returns_none_on_client_error(monkeypatch):
    from botocore.exceptions import ClientError

    class FailingS3Client:
        def put_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "500", "Message": "boom"}}, "PutObject")

    monkeypatch.setattr("app.core.aws_client.s3_client", FailingS3Client())
    monkeypatch.setattr("app.core.aws_client.settings.AWS_S3_BUCKET", "test-bucket")

    result = upload_close_report("acme_corp", {"generated_at": "2026-01-31T00:00:00"})

    assert result is None
