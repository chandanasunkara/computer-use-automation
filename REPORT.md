# Architecture

The system is split into five boundaries: a discovery agent, a browser surface, an artifact recorder, a deterministic replay engine, and policy/escalation services. Discovery accepts a natural-language goal and repeatedly observes the current UI, asks the LLM for one structured action, executes it, and records the successful actions. The browser surface exposes a small computer-use interface so the agent does not depend directly on Playwright.

I chose a local banking-style web application because the assignment permits a local sample application and it gives us a realistic multi-step back-office surface without using real credentials or financial data. Playwright is used for browser interaction because it provides reliable waiting and semantic locators while still allowing a future surface adapter for less structured applications.

The main trade-off is using structured DOM/accessibility-like observations instead of screenshot-only computer vision. This makes the implementation smaller and replay more deterministic. The `BrowserSurface` seam can later support screenshots, accessibility trees, legacy DOMs, or desktop automation without changing the artifact contract.

# Artifact schema

A capability artifact is versioned and independent of the LLM transcript. It contains:

- capability ID and artifact version
- target surface/application
- typed input parameters
- typed outputs
- ordered steps
- semantic target locators
- action type and parameter binding
- checkpoint/success condition
- policy metadata

A target records semantic information such as role, accessible name, label, and text rather than generated CSS paths. Replay resolves the locator against the current page. The locator strategy prefers role/name and label-based matching and uses a stable application attribute only when available.

This makes the artifact understandable to a human reviewer and callable by an agent. A future capability catalog could expose these artifacts as typed functions.

# Determinism & error handling

Discovery is model-driven. Replay is not. The replay executor receives an artifact and input parameters and executes the exact ordered actions. It never creates an LLM client.

Each action has a checkpoint or the capability has a final success condition. Replay waits for expected UI state, resolves the declared target, executes the action, and verifies the expected result.

Errors are classified into four useful categories:

1. Business outcomes: expected domain results such as `MEMBER_NOT_FOUND`.
2. Recoverable conditions: transient loading or a known dismissible interstitial.
3. Hard failures: unexpected application state, missing controls, or checkpoint failure.
4. Safety/intervention: blocked action or a state requiring a human.

A failure includes the capability, step ID, expected state, observed state, and evidence path. A screenshot is captured for hard failures and intervention states.

# Heterogeneity & multi-tenant

The artifact is independent of Playwright. `BrowserSurface` is the perception/action seam. A legacy web adapter could implement the same operations using accessibility data, semantic DOM inspection, screenshots, or coordinates. A desktop adapter could expose the same contract using OS accessibility APIs.

For multi-tenant reuse, artifacts should identify the vendor application and version rather than a tenant-specific URL. A base artifact can have tenant/version overrides for routes, labels, or locator alternatives. Replay can validate an application fingerprint before execution and fail closed when the version is unsupported. A later canonicalization layer could normalize routes and tenant-specific values into parameterized forms.

I deliberately do not build multi-tenant infrastructure because the assignment asks for the design rather than the infrastructure.

# Escalation & handoff

When automation reaches a state it cannot safely interpret, it creates an intervention request containing the capability, goal, current step, reason, screenshot, and session identifier. The replay pauses without destroying the browser session.

For this focused implementation, the operator surface is intentionally minimal: the same visible browser is exposed to the human. The human performs the required action, and a small event listener records clicks/input events to the evidence log. The operator then signals resume in the terminal. The executor continues using the same page/session.

This demonstrates the important seam: automation can pause, transfer control, preserve context, and resume.

# Safety

The policy engine enforces an explicit host allowlist and action allowlist. Navigation to an unapproved host is blocked. Actions are classified as safe or risky. Risky actions such as submitting a transaction or deleting data require explicit confirmation rather than unattended execution.

The demo uses only fake data. Environment secrets are never stored in artifacts or logs. Redaction replaces known secret-like values with `<REDACTED>`. `.env` is ignored by git.

The safety model is intentionally conservative: when policy cannot establish that an action is permitted, execution stops and requests intervention.

# Cuts

I intentionally leave out distributed execution, queues, Kubernetes, a production operator dashboard, desktop automation, real banking integrations, and automated cross-tenant migration. Those are not necessary to prove the core record-once/replay-many model.

With more time I would add a capability catalog API, artifact approval states, replay stability scoring across multiple runs, richer accessibility-tree support, and a bounded recovery mechanism for a single failed step. The core architecture leaves clean seams for each of these additions.
