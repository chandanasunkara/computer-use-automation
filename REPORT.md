# Design Report: Computer-Use Automation System

## 1. Architecture
The system decouples non-deterministic UI discovery from deterministic, low-cost execution:
* **Discovery Engine (LLM in the loop):** Navigates a target UI surface via an observe-decide-act loop to accomplish a natural language goal. It inspects accessibility properties, labels, and text to synthesize a reusable execution path without hardcoding fragile selectors.
* **Capability Artifact:** A versioned, declarative JSON schema representing the recorded workflow as a parameterized contract (typed inputs, typed outputs, ordered interaction steps, and success conditions).
* **Deterministic Replay Engine (Production execution):** Replays the capability artifact with 0 LLM calls. It handles step-by-step DOM interactions, multi-tier locator resolution, error handling, and output extraction.
* **Human-in-the-Loop (HITL) Coordinator:** Pauses automation during unexpected blocking states or risky operations, yielding control to a human operator within the live browser session and resuming once cleared.
* **Policy & Guardrails:** Enforces domain allowlists and scrubs sensitive PII/secrets before persisting artifacts or logs.

## 2. Artifact Schema
The capability artifact treats UI automations as typed, invocable functions:
* **Contract Specification:** Explicit `inputs` (e.g., `member_id`) and `outputs` (e.g., `savings_balance`, `member_name`) ensure calling AI agents understand what parameters must be supplied and what schema will be returned.
* **Locator Fallback Hierarchy:** Target controls are identified using semantic attributes (`role`, `name`, `label`, `text`, `test_id`). Replay resolves these with strict priority, favoring accessible names and semantic roles over volatile markup paths.
* **Step Model:** Actions (`navigate`, `click`, `type`, `extract`, `wait`) explicitly track risk levels (`safe` vs. `risky`) and parameter bindings (`{{member_id}}`).
* **Success Conditions & Checkpoints:** Post-condition assertions verify that the application has reached the expected outcome rather than assuming clicks succeeded.

## 3. Determinism & Error Handling
Enterprise back-office banking software features stable layouts but frequent runtime business exceptions. The replay engine explicitly partitions outcomes:
* **Success:** All steps execute, checkpoints pass, and declared output fields are populated.
* **Business Outcomes:** Expected business-domain conditions (e.g., "Member not found", "Account Frozen") are recognized as legitimate results rather than application crashes. Replay captures these states cleanly in the structured result contract.
* **Recoverable Conditions:** Transient network delays, loading overlays, or element attachment lags are handled via bounded retries and polling.
* **Hard Failures:** When a step fails due to an unexpected modal or broken invariant, the engine raises an exception, logs DOM/screenshot evidence, and triggers human escalation.

## 4. Heterogeneity & Multi-Tenant
* **Surface Abstraction:** Playwright drives the browser surface through `BrowserSurface`. This interface exposes high-level primitives (`observe`, `click`, `type`, `extract`) decoupled from the execution engine. Extending to legacy desktop apps (Win32/WPF) or mainframe terminals requires only implementing a native surface driver (e.g., via Windows UI Automation or pywinauto) that satisfies the same interface contract.
* **Multi-Tenant Reuse:** Core banking systems shared across credit unions with custom branding or route variations can be represented using base capability templates with tenant-specific locator/route overlays. Runtime parameterization (`{{member_id}}`, tenant host aliases) prevents recording duplicate workflows per institution.
* **Drift Detection:** Artifacts track schema versions. Replay stability telemetry flags locator regressions, prompting scoped single-step re-discovery rather than full pipeline rewrites.

## 5. Escalation & Handoff
* **Detection:** Stuck states are triggered when step execution exceeds retry thresholds, unexpected blockers appear, or a step marked `risk: "risky"` is reached.
* **Control Transfer:** The engine halts automated commands while keeping the live Playwright browser context open (preserving cookies, session storage, and form state).
* **Live Session Takeover:** A human operator takes control of the active UI session. In the demo application, an event listener logs human interactions (`/api/human-events`) to capture manual interventions.
* **Resumption:** Once the operator resolves the blocker, control transfers back to automation to complete remaining verification steps and return the final contract.

## 6. Safety
* **Domain Allowlist:** Network requests and navigations are strictly constrained to pre-approved hosts (`127.0.0.1`, `localhost`). External navigation attempts are blocked.
* **Action Gating:** Irreversible or high-risk actions (e.g., funds transfer, account deletion) are tagged as `risky` and require explicit operator confirmation before execution.
* **Data Redaction:** In-flight regex filters scrub Social Security Numbers (SSNs), payment card numbers, credentials, and sensitive financial identifiers before writing artifacts, logs, or screenshots to disk.

## 7. Cuts
* **Deliberately Omitted:** A distributed task queue (Celery/RabbitMQ), persistent database storage for run histories, and a full real-time WebSocket operator UI console.
* **Next Steps:** Automated synthesis of standalone Playwright/Pytest test scripts from saved artifacts, and policy-bounded single-step LLM self-healing on locator drift.