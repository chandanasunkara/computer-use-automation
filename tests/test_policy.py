import pytest

from app.policy import Policy, PolicyError, redact


def test_localhost_allowed():
    Policy().check_url("http://127.0.0.1:8000/")


def test_external_host_blocked():
    with pytest.raises(PolicyError):
        Policy().check_url("https://example.com")


def test_secret_redaction():
    assert "sk-" not in redact("OPENAI_API_KEY=sk-123456789012345")
