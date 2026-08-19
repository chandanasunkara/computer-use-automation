from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from .agent import discover
from .artifact import capability_from_discovery, load_capability, save_capability
from .replay import replay
from .surface import BrowserSurface

load_dotenv()


def run_discover(args):
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=os.getenv("HEADLESS", "false").lower() == "true")
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        surface = BrowserSurface(page)
        actions, outputs, llm_calls = discover(
            surface,
            args.goal,
            base_url,
            int(os.getenv("MAX_STEPS", "12")),
        )

        # The example capability is parameterized around member_id. Discovery may
        # have typed a concrete value; the recorder replaces that with a parameter.
        capability = capability_from_discovery(
            actions,
            args.goal,
            inputs={"member_id": {"type": "string", "required": True}},
            outputs={
                "savings_balance": {"type": "number"},
                "member_name": {"type": "string"},
            },
        )

        path = Path("artifacts/member_lookup.json")
        save_capability(capability, path)
        Path("evidence/discovery/result.json").write_text(
            json.dumps(
                {
                    "status": "success",
                    "artifact": str(path),
                    "llm_calls": llm_calls,
                    "discovery_outputs": outputs,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Discovery complete. Artifact: {path}")
        print(f"LLM calls: {llm_calls}")
        browser.close()


def run_replay(args):
    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    capability = load_capability(args.artifact)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        surface = BrowserSurface(page)
        result = replay(
            surface,
            capability,
            {"member_id": args.member_id},
            base_url,
            intervention=args.intervention,
        )

        Path("evidence/replay/result.json").write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )
        print(result.model_dump_json(indent=2))
        browser.close()


def main():
    parser = argparse.ArgumentParser(description="Computer-use automation demo")
    sub = parser.add_subparsers(required=True)

    d = sub.add_parser("discover")
    d.add_argument("--goal", required=True)
    d.set_defaults(func=run_discover)

    r = sub.add_parser("replay")
    r.add_argument("artifact")
    r.add_argument("--member-id", required=True)
    r.add_argument("--intervention", action="store_true")
    r.set_defaults(func=run_replay)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
