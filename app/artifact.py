from __future__ import annotations

import json
from pathlib import Path
from .models import Capability, Step


def save_capability(capability: Capability, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(capability.model_dump_json(indent=2), encoding="utf-8")


def load_capability(path: str | Path) -> Capability:
    return Capability.model_validate_json(Path(path).read_text(encoding="utf-8"))


def capability_from_discovery(actions: list[dict], goal: str, inputs: dict, outputs: dict) -> Capability:
    steps = [Step.model_validate(a) for a in actions]
    return Capability(
        capability_id="member.lookup_savings_balance",
        version="1.0.0",
        description=goal,
        target={"surface": "web", "application": "local-bank-demo"},
        inputs=inputs,
        outputs=outputs,
        steps=steps,
        success_condition="member details are visible and declared outputs were extracted",
    )
