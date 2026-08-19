from __future__ import annotations

import re
from urllib.parse import urlparse

SAFE_ACTIONS = {"navigate", "click", "type", "extract", "wait", "finish"}
RISKY_ACTIONS = {"submit_transaction", "delete_record", "create_account"}


class PolicyError(Exception):
    pass


class Policy:
    def __init__(self, allowed_hosts: set[str] | None = None):
        self.allowed_hosts = allowed_hosts or {"127.0.0.1", "localhost"}

    def check_url(self, url: str) -> None:
        host = urlparse(url).hostname
        if host not in self.allowed_hosts:
            raise PolicyError(f"Navigation blocked by allowlist: {host}")

    def check_action(self, action: str) -> None:
        if action not in SAFE_ACTIONS:
            raise PolicyError(f"Action blocked by allowlist: {action}")

    def requires_confirmation(self, action: str) -> bool:
        return action in RISKY_ACTIONS


def redact(value: str) -> str:
    value = re.sub(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+", r"\1=<REDACTED>", value)
    value = re.sub(r"sk-[A-Za-z0-9_-]{10,}", "<REDACTED>", value)
    return value
