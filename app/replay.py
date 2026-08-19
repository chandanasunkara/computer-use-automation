from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Capability, RunResult, RunStatus
from .policy import Policy, PolicyError, redact
from .surface import BrowserSurface, SurfaceError


def substitute(value: str | None, inputs: dict[str, Any]) -> str | None:
    if value is None:
        return None
    for key, val in inputs.items():
        value = value.replace("{{" + key + "}}", str(val))
    return value


def replay(
    surface: BrowserSurface,
    capability: Capability,
    inputs: dict[str, Any],
    base_url: str,
    intervention: bool = False,
) -> RunResult:
    policy = Policy()
    evidence = Path("evidence/replay")
    evidence.mkdir(parents=True, exist_ok=True)

    try:
        policy.check_url(base_url)
        surface.navigate(base_url)

        # Install a real same-session human event logger. The operator can use the
        # exact browser session if an intervention is requested.
        surface.install_human_event_logger("http://127.0.0.1:8000/api/human-events")
        outputs: dict[str, Any] = {}

        for step in capability.steps:
            if step.action.value == "navigate":
                url = substitute(step.value, inputs) or base_url
                policy.check_url(url)
                surface.navigate(url)

            elif step.action.value == "click":
                policy.check_action("click")
                surface.click(target=step.target)

            elif step.action.value == "type":
                policy.check_action("type")
                surface.type(substitute(step.value, inputs) or "", target=step.target)

            elif step.action.value == "extract":
                policy.check_action("extract")
                value = surface.extract(target=step.target)
                # Numeric currency extraction is normalized for the declared output.
                if step.output:
                    cleaned = value.replace("$", "").replace(",", "").strip()
                    try:
                        value = float(cleaned)
                    except ValueError:
                        pass
                    outputs[step.output] = value

            elif step.action.value == "wait":
                surface.page.wait_for_timeout(500)

            elif step.action.value == "finish":
                break

            # Check known business outcome after each state-changing step.
            text = surface.visible_text()

            # Optional demo-only intervention: keep the same live browser session,
            # expose it to a human, and resume after manual action.
            if intervention and "Member Details" in text and "INTERVENTION_REQUIRED" not in text:
                surface.page.evaluate(
                    '() => {\n                        const box = document.createElement(\'div\');\n                        box.id = \'automation-intervention\';\n                        box.innerHTML = \'<div style="position:fixed;top:20px;right:20px;background:#fef3c7;border:3px solid #f59e0b;padding:20px;z-index:99999;font-family:Arial"><strong>INTERVENTION_REQUIRED</strong><br>Human review required. Close this panel when done.</div>\';\n                        document.body.appendChild(box);\n                    }'
                )
                surface.screenshot("evidence/intervention/current-session.png")
                print("\nHuman intervention requested.")
                print("The same browser session is paused. Perform the required action in the browser.")
                input("Press Enter after the human action is complete... ")
                surface.screenshot("evidence/intervention/resumed-session.png")
                Path("evidence/intervention/handoff.json").write_text(
                    json.dumps({"status": "resumed", "same_session": True}, indent=2),
                    encoding="utf-8",
                )
            if "Member not found" in text:
                return RunResult(
                    status=RunStatus.business_outcome,
                    capability_id=capability.capability_id,
                    code="MEMBER_NOT_FOUND",
                    message="The requested member does not exist.",
                    llm_calls=0,
                )

            if "INTERVENTION_REQUIRED" in text or intervention and step.id == capability.steps[-1].id:
                surface.screenshot("evidence/intervention/current-session.png")
                print("\nHuman intervention requested.")
                print("The same browser session is paused. Perform the required action in the browser.")
                input("Press Enter after the human action is complete... ")
                surface.screenshot("evidence/intervention/resumed-session.png")

        # Final checkpoint.
        if not surface.wait_for_text("Member Details", timeout=3000):
            surface.screenshot("evidence/replay/checkpoint-failure.png")
            return RunResult(
                status=RunStatus.failure,
                capability_id=capability.capability_id,
                code="CHECKPOINT_FAILED",
                message="Replay completed its steps but the final checkpoint was not observed.",
                expected="Member Details",
                observed=redact(surface.visible_text()[:1000]),
                evidence="evidence/replay/checkpoint-failure.png",
                llm_calls=0,
            )

        # Re-extract declared outputs from their stable locators so the returned
        # values are based on the replay, not discovery memory.
        outputs: dict[str, Any] = {}
        for step in capability.steps:
            if step.action.value == "extract" and step.output:
                value = surface.extract(target=step.target)
                cleaned = value.replace("$", "").replace(",", "").strip()
                try:
                    value = float(cleaned)
                except ValueError:
                    pass
                outputs[step.output] = value

        surface.screenshot("evidence/replay/success.png")
        return RunResult(
            status=RunStatus.success,
            capability_id=capability.capability_id,
            outputs=outputs,
            llm_calls=0,
        )

    except PolicyError as exc:
        return RunResult(
            status=RunStatus.safety_blocked,
            capability_id=capability.capability_id,
            code="POLICY_BLOCKED",
            message=redact(str(exc)),
            llm_calls=0,
        )
    except Exception as exc:
        surface.screenshot("evidence/replay/failure.png")
        return RunResult(
            status=RunStatus.failure,
            capability_id=capability.capability_id,
            code="REPLAY_FAILURE",
            message=redact(str(exc)),
            evidence="evidence/replay/failure.png",
            llm_calls=0,
        )
