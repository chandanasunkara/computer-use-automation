from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .models import AgentAction, Locator
from .policy import Policy
from .surface import BrowserSurface

load_dotenv(override=True)

SYSTEM_PROMPT = """
You are the discovery controller for a computer-use automation system.

You must complete the user's goal using only the observed local UI.

Available actions:
- click: click one observed element
- type: fill one observed input with a value
- extract: read text/value from one observed element and assign output_name
- wait: wait for the page to settle
- finish: only when the goal is visibly complete

Return exactly one JSON action.

Rules:
- Use target_index from the current observation.
- Never invent an index.
- Prefer semantic controls such as Member ID, Search, Member Name, and Savings Balance.
- Do not navigate outside the supplied target.
- Do not perform risky actions unless explicitly required and safe.
- If a business outcome such as "Member not found" is visible, use finish.
- Do NOT finish immediately after clicking Search if the requested outputs are visible.
- When the requested information is visible, use extract actions to capture ALL
  requested outputs before using finish.
- For a member savings lookup, extract:
  1. member_name
  2. savings_balance
- For extract, output_name must be the semantic name of the requested output.
- Only use finish after all requested outputs have been extracted or a business
  outcome such as "Member not found" is visible.
"""


def _client() -> OpenAI:
    load_dotenv(override=True)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    if not base_url:
        raise RuntimeError("OPENAI_BASE_URL is missing.")

    print(f"LLM base URL: {base_url}")
    print(f"LLM model: {os.getenv('OPENAI_MODEL')}")

    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


def ask_llm(
    client: OpenAI,
    goal: str,
    observation: list[dict[str, Any]],
    page_text: str,
    step: int,
) -> AgentAction:
    prompt = {
        "goal": goal,
        "step": step,
        "observation": observation,
        "page_text": page_text[:5000],
        "instruction": (
            "Choose exactly one next action. "
            "Return ONLY a single valid JSON object. "
            "Do not include markdown, explanations, or code fences. "
            "When requested information is visible, extract every requested "
            "output before finishing."
        ),
    }

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "openai/gpt-oss-20b"),
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": json.dumps(prompt),
            },
        ],
        temperature=0,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("LLM returned an empty response.")

    # Remove accidental markdown code fences.
    content = content.strip()

    if content.startswith("```"):
        content = content.removeprefix("```json").strip()
        content = content.removeprefix("```").strip()

        if content.endswith("```"):
            content = content[:-3].strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"LLM returned invalid JSON:\n{content}"
        ) from exc

    return AgentAction.model_validate(data)


def semantic_locator(element: dict[str, Any]) -> Locator:
    return Locator(
        role=element.get("role"),
        name=element.get("name"),
        label=element.get("label"),
        test_id=element.get("test_id"),
        text=element.get("text") if not element.get("name") else None,
    )


def discover(
    surface: BrowserSurface,
    goal: str,
    base_url: str,
    max_steps: int = 12,
):
    client = _client()
    policy = Policy()
    policy.check_url(base_url)

    surface.navigate(base_url)

    actions: list[dict[str, Any]] = []
    outputs: dict[str, Any] = {}

    evidence = Path("evidence/discovery")
    evidence.mkdir(parents=True, exist_ok=True)

    log_path = evidence / "discovery.jsonl"
    log_path.write_text("", encoding="utf-8")

    llm_calls = 0

    for step_no in range(1, max_steps + 1):
        observation = surface.observe()
        page_text = surface.visible_text()

        surface.screenshot(
            str(evidence / f"step-{step_no}.png")
        )

        action = ask_llm(
            client,
            goal,
            observation,
            page_text,
            step_no,
        )

        llm_calls += 1

        record = {
            "step": step_no,
            "action": action.model_dump(),
            "observation": observation,
        }

        with log_path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(record, default=str) + "\n"
            )

        if action.action == "finish":
            break

        if action.target_index is None and action.action != "wait":
            raise RuntimeError(
                "LLM returned an action without a target index."
            )

        target = next(
            (
                x
                for x in observation
                if x["index"] == action.target_index
            ),
            None,
        )

        if not target and action.action != "wait":
            raise RuntimeError(
                f"Target index {action.target_index} no longer exists."
            )

        if action.action == "click":
            surface.click(index=action.target_index)

            actions.append(
                {
                    "id": f"step_{step_no}",
                    "action": "click",
                    "target": semantic_locator(target).model_dump(
                        exclude_none=True
                    ),
                    "expected": target.get("name")
                    or target.get("text"),
                    "risk": "safe",
                }
            )

        elif action.action == "type":
            surface.type(
                action.value or "",
                index=action.target_index,
            )

            actions.append(
                {
                    "id": f"step_{step_no}",
                    "action": "type",
                    "target": semantic_locator(target).model_dump(
                        exclude_none=True
                    ),
                    "value": (
                        "{{member_id}}"
                        if (action.value or "").isdigit()
                        else action.value
                    ),
                    "risk": "safe",
                }
            )

        elif action.action == "extract":
            value = surface.extract(
                index=action.target_index
            )

            output_name = action.output_name or "value"

            outputs[output_name] = value

            actions.append(
                {
                    "id": f"step_{step_no}",
                    "action": "extract",
                    "target": semantic_locator(target).model_dump(
                        exclude_none=True
                    ),
                    "output": output_name,
                    "expected": target.get("name")
                    or target.get("text"),
                    "risk": "safe",
                }
            )

        elif action.action == "wait":
            surface.page.wait_for_timeout(500)

    return actions, outputs, llm_calls