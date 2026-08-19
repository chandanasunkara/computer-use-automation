from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    navigate = "navigate"
    click = "click"
    type = "type"
    extract = "extract"
    wait = "wait"
    finish = "finish"


class Locator(BaseModel):
    role: str | None = None
    name: str | None = None
    label: str | None = None
    test_id: str | None = None
    text: str | None = None


class Step(BaseModel):
    id: str
    action: ActionType
    target: Locator | None = None
    value: str | None = None
    output: str | None = None
    expected: str | None = None
    risk: str = "safe"


class Capability(BaseModel):
    schema_version: str = "1.0"
    capability_id: str
    version: str = "1.0.0"
    description: str
    target: dict[str, str]
    inputs: dict[str, dict[str, Any]]
    outputs: dict[str, dict[str, Any]]
    steps: list[Step]
    success_condition: str


class RunStatus(str, Enum):
    success = "success"
    business_outcome = "business_outcome"
    recoverable = "recoverable"
    failure = "failure"
    safety_blocked = "safety_blocked"
    intervention_required = "intervention_required"


class RunResult(BaseModel):
    status: RunStatus
    capability_id: str
    outputs: dict[str, Any] = Field(default_factory=dict)
    code: str | None = None
    message: str | None = None
    step_id: str | None = None
    expected: str | None = None
    observed: str | None = None
    evidence: str | None = None
    llm_calls: int = 0


class AgentAction(BaseModel):
    action: str
    target_index: int | None = None
    value: str | None = None
    output_name: str | None = None
    reason: str = ""
