# Brand Intelligence Agent

Agentic system that ingests a brand's assets, synthesizes a brand
understanding, and generates brand-aligned content across channels. Full
design and scope: [CLAUDE.md](CLAUDE.md). Build plan: [docs/tasks.md](docs/tasks.md).

**Current status:** M0 (password-gated Gradio chat UI) and M1 (full
LangGraph pipeline: guardrail → ingestion → brand DNA → competition
research → strategy → content generation → evaluation, with retry/
escalate) are done. The pipeline is **not wired into the UI yet** (M2) —
the chat still just echoes. Test the pipeline directly via CLI for now
(see below).

## Prerequisites

- Python 3.11+, or Docker
- No API key required for mock mode (default). An `OPENAI_API_KEY` is
  needed only to test the real (non-mock) pipeline path.

## Option A: Run locally with Python

```bash
git clone git@github.com:kevin19091/BrandAwareContentAgent.git
cd BrandAwareContentAgent

python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt

cp .env.example .env
# edit .env if you want a non-default APP_USER / APP_PASS

python3 -m frontend.app
```

The app starts on `http://localhost:7860`.

## Option B: Run with Docker

```bash
git clone git@github.com:kevin19091/BrandAwareContentAgent.git
cd BrandAwareContentAgent

cp .env.example .env

docker build -t brand-agent .
docker run --rm -p 7860:7860 --env-file .env brand-agent
```

The app starts on `http://localhost:7860`.

## Testing the pipeline directly (backend/CLI mode)

The pipeline (`backend/pipeline_graph.py`) isn't wired into the UI yet —
run it standalone instead. Requires the venv set up per Option A above.

**Mock mode (default, no API key needed)** — `USE_MOCK=true` in
`.env.example`, every node returns canned output:

```bash
python3 -m backend.pipeline_graph "Create a high-energy summer campaign targeting urban Gen-Z audiences, emphasizing freedom, self-expression, and adventure."
```

Special keywords anywhere in the brief exercise the other control-flow
branches in mock mode:

| Keyword | What it tests |
|---|---|
| (none) | Happy path — passes straight through |
| `trigger_reject` | Guardrail stops the run immediately, no retry |
| `trigger_eval_fail` | Evaluation fails once, retries, passes on 2nd attempt |
| `trigger_escalate` | Evaluation fails twice, retry cap hit, escalates |

**Real mode (calls OpenAI, uses API credits)** — set `USE_MOCK=false`
and `OPENAI_API_KEY=...` in `.env`, then run the same command:

```bash
python3 -m backend.pipeline_graph "Create a high-energy summer campaign targeting urban Gen-Z audiences, emphasizing freedom, self-expression, and adventure."
```

The trigger keywords above are mock-only and have no effect in real
mode — guardrail/evaluation outcomes depend on the model's actual
judgment there.

Output is the final pipeline state as JSON (brand profile, competition
insights, strategy, per-channel content, eval result) printed to stdout.

## What to test

1. **Open `http://localhost:7860`.** You should be redirected to a login
   screen — the chat UI itself must not be visible or usable before login.
2. **Log in** with the credentials from your `.env` (`APP_USER` /
   `APP_PASS`; defaults are `admin` / `changeme` if you didn't set them).
3. **Wrong credentials should be rejected** — try a bad password once to
   confirm the login screen re-prompts instead of letting you in.
4. **Send a chat message.** The app should stream back a response word by
   word (not appear all at once), prefixed with
   `Pipeline not implemented yet ... Echo: <your message>`. This confirms
   streaming works — the actual multi-agent pipeline lands in a later
   milestone.
5. **Restart and confirm the login is required again** (no session
   persists across a fresh container/process start).

## Known limitations at this stage

- The UI chat is still an echo stub — the pipeline exists but isn't
  wired in (that's M2). Test the pipeline via CLI, see above.
- No file upload yet — the CLI pipeline runs against a hardcoded
  reference brand/brief (`REFERENCE_BRIEF`/`REFERENCE_SESSION_ASSETS` in
  `backend/pipeline_graph.py`); only the `raw_input` brief is
  overridable via the CLI argument.
- No confirm checkpoint / HITL UI yet (M2).
- Not yet deployed to a public URL — testing is local/Docker only for now.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/app.py` | Gradio chat UI entry point, password gate |
| `backend/pipeline_graph.py` | LangGraph pipeline (guardrail → agents → evaluation), CLI-runnable |
| `notebooks/` | Scratch `.ipynb` notebooks (prompt/model experiments), not shipped code |
| `Dockerfile` | Container build for local or hosted deployment |
| `.env.example` | Required environment variables, copy to `.env` |
| `CLAUDE.md` | Full product/design spec |
| `docs/tasks.md` | Milestone and task breakdown |
