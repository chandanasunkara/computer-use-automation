# Computer-Use Automation System

A focused implementation of the interface.ai take-home project.

The system demonstrates:

1. Natural-language goal -> genuine LLM-driven browser discovery
2. Successful discovery -> versioned, typed capability artifact
3. Artifact -> deterministic replay with zero LLM decisions
4. Business outcomes, recoverable errors, and hard failures
5. Configurable safety allowlist and risky-action confirmation
6. Human takeover of the same live browser session
7. Evidence for discovery, replay, failure, and handoff

## Architecture

```text
Goal
  |
  v
Discovery Agent (LLM)
  |
  +--> observe UI
  +--> decide structured action
  +--> execute action
  |
  v
Capability Artifact
  |
  v
Deterministic Replay Engine (NO LLM)
  |
  +--> success
  +--> business outcome
  +--> recoverable error
  +--> hard failure
  |
  v
Human intervention when automation cannot safely continue
```

## Requirements

- Python 3.10+
- An OpenAI API key for the genuine discovery run
- Playwright Chromium

Playwright's Python installation requires the package plus browser binaries. See the official documentation:
https://playwright.dev/python/docs/library

## Windows PowerShell setup

```powershell
git clone <YOUR_PUBLIC_REPO_URL>
cd computer-use-automation

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

Copy-Item .env.example .env
```

Edit `.env` and set:

```text
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=openai/gpt-oss-20b
BASE_URL=http://127.0.0.1:8000
HEADLESS=false
MAX_STEPS=12
```

Do not commit `.env`.

## macOS / Linux setup

```bash
git clone <YOUR_PUBLIC_REPO_URL>
cd computer-use-automation

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium

cp .env.example .env
```

## 1. Start the local banking application

Terminal 1:

```bash
python -m demo_app
```

The app will be available at:

```text
http://127.0.0.1:8000
```

The demo contains mock data only.

## 2. Run the genuine LLM discovery

Terminal 2:

```bash
python -m app.cli discover --goal "Look up member 12345 and return their current savings balance"
```

The browser opens visibly because `HEADLESS=false`.

The agent observes the UI, asks the LLM what to do, performs the action, and records the successful run as:

```text
artifacts/member_lookup.json
```

Discovery evidence is written to:

```text
evidence/discovery/
```

The assignment requires at least one genuine LLM-driven run against a live surface, so do not replace this step with a hard-coded demo when preparing the submission.

## 3. Replay without the LLM

After discovery:

```bash
python -m app.cli replay artifacts/member_lookup.json --member-id 12345
```

Replay does not initialize or call the LLM. It executes only the saved artifact.

Expected result:

```text
SUCCESS
member_name: John Smith
savings_balance: 8120.00
llm_calls: 0
```

## 4. Demonstrate a business outcome

```bash
python -m app.cli replay artifacts/member_lookup.json --member-id 99999
```

Expected result:

```text
BUSINESS_OUTCOME
MEMBER_NOT_FOUND
```

This is deliberately not treated as a crash.

## 5. Demonstrate human takeover

Run:

```bash
python -m app.cli replay artifacts/member_lookup.json --member-id 12345 --intervention
```

The application displays an intervention dialog. The replay pauses on the same browser session.

Close the dialog manually in the browser. The page records human UI events. Return to the terminal and press Enter to resume.

Evidence is written under:

```text
evidence/intervention/
```

## 6. Run tests

```bash
pytest -q
```

For a visible browser run:

```bash
pytest -q --headed
```

## 7. What is in the repository

```text
computer-use-automation/
├── app/
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py              # LLM discovery loop (observe-decide-act)
│   ├── artifact.py           # Capability schema validation and persistence
│   ├── cli.py                # Command-line interface entry point
│   ├── models.py             # Pydantic data models and execution contracts
│   ├── policy.py             # Domain allowlisting and PII/secret scrubbing
│   ├── replay.py             # Deterministic, model-free execution engine
│   └── surface.py            # BrowserSurface DOM and accessibility abstraction
├── artifacts/
│   ├── .gitkeep
│   └── member_lookup.json    # Versioned, typed capability artifact
├── demo_app/
│   ├── __init__.py
│   └── __main__.py           # Local core banking servicing UI
├── evidence/
│   ├── discovery/            # Discovery run traces and transcripts
│   ├── errors/               # Business outcome and exception logs
│   ├── intervention/         # Human takeover event recordings
│   └── replay/               # Deterministic execution logs and snapshots
├── tests/
│   ├── test_artifact.py      # Artifact schema invariant tests
│   ├── test_policy.py        # Allowlist and redaction security tests
│   └── test_replay_contract.py # Model-free replay verification tests
├── .gitignore
├── README.md
├── REPORT.md                 # Technical design and trade-off write-up
└── requirements.txt
```

## Design boundary

The browser-specific implementation is behind `BrowserSurface`. The artifact describes controls semantically rather than storing raw model transcripts. A future legacy-web or desktop adapter can implement the same observe/act seam.

Replay is intentionally model-free. The model discovers; the artifact becomes the capability; replay is the production execution path.

## Security

- Only the configured local host is allowed by default.
- Navigation outside the allowlist is blocked.
- Risky actions require explicit confirmation.
- Secrets are loaded from environment variables and never written to artifacts.
- Redaction is applied to logs.
- The demo contains no real financial data.

## Submission checklist

Before publishing:

```bash
python -m pytest tests/ -v
git status
git diff -- .env
```

Confirm that `.env` is not tracked.

Then:

```bash
git init
git add .
git commit -m "Build computer-use automation system"
git branch -M main
git remote add origin <YOUR_PUBLIC_REPO_URL>
git push -u origin main
```