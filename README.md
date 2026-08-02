# Brand Intelligence Agent

Agentic system that ingests a brand's assets, synthesizes a brand
understanding, and generates brand-aligned content across channels. Full
design and scope: [CLAUDE.md](CLAUDE.md). Build plan: [docs/tasks.md](docs/tasks.md).

**Current status:** M0–M2 are done. The full pipeline (guardrail →
ingestion → brand DNA → competition research → strategy → content
generation → evaluation, with retry/escalate) is wired into a
password-gated Gradio UI with file upload, step-by-step streaming,
inline rationale, a confirm checkpoint after Strategy, and a step/auto
HITL toggle.

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

## What to test

1. **Open `http://localhost:7860`.** You should be redirected to a login
   screen — the chat UI itself must not be visible or usable before login.
2. **Log in** with the credentials from your `.env` (`APP_USER` /
   `APP_PASS`; defaults are `admin` / `changeme` if you didn't set them).
   Try a bad password once first — it should re-prompt, not let you in.
3. **Auto mode (default):** leave the HITL Mode radio on `auto`, type a
   brief (e.g. "Launch a high-energy summer campaign for a beverage
   brand targeting urban Gen-Z audiences"), optionally attach `.txt`
   files for Brand Guidelines / Competitor Refs, click **Run Pipeline**.
   You should see one chat message per pipeline step stream in — Guardrail,
   Ingestion, Brand DNA, Competition Research, Strategy, Content
   Generated, Evaluation — each with a rationale line, ending in
   `Evaluation: PASSED`, with no pause in between.
4. **Step mode:** switch HITL Mode to `step`, run again. The stream
   should stop after the Strategy message with "Strategy ready for
   review..." and a **Continue** button appears, along with an "Edit
   Strategy (JSON)" box pre-filled with the current strategy. Edit the
   `big_idea` field (or leave it as-is) and click **Continue** — content
   generation should build on your edited strategy, not the original
   (a "Using your edited strategy." message confirms it took). Try
   breaking the JSON on purpose too — it should show a parse-error
   message and let you fix it and click Continue again, rather than
   losing the pause.
5. **Guardrail rejection:** type a brief containing `trigger_reject`
   anywhere — the pipeline should stop after one "REJECTED" message,
   with no further steps.
6. **Retry/escalate:** `trigger_eval_fail` in the brief should fail
   evaluation once, then show a "Retrying" message, then pass on the
   second attempt. `trigger_escalate` should fail twice and end on an
   "Escalated" message. (These trigger keywords only work in mock mode
   — `USE_MOCK=true`, the default.)
7. **Restart and confirm the login is required again** (no session
   persists across a fresh container/process start).

## Known limitations at this stage

- Brand guidelines / competitor refs are `.txt` upload only, not PDF —
  paste the text into a `.txt` file if your source is a PDF.
- Uploaded images are accepted and stored but not analyzed by any
  agent (no vision call) — text-only generation per the MVP scope.
- The pipeline runs the brief you type; there's no static inspiration
  library to fall back on yet if you upload nothing (`ingestion_source`
  will just be `"none"`) — that's a stretch item (M6).
- The confirm checkpoint is a plain two-call handoff in application
  code, not LangGraph's `interrupt()`/resume — see docs/tasks.md M2/M6.
- Not yet deployed to a public URL — testing is local/Docker only for now.

## Testing the pipeline directly (backend/CLI mode)

The pipeline also runs standalone, outside the UI — useful for quick
checks without a browser. Requires the venv set up per Option A above.

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

## Project layout

| Path | Purpose |
|---|---|
| `frontend/app.py` | Gradio `Blocks` UI: password gate, file upload, streaming, HITL toggle |
| `backend/pipeline_graph.py` | LangGraph pipeline (guardrail → agents → evaluation), CLI-runnable |
| `notebooks/` | Scratch `.ipynb` notebooks (prompt/model experiments), not shipped code |
| `Dockerfile` | Container build for local or hosted deployment |
| `.env.example` | Required environment variables, copy to `.env` |
| `CLAUDE.md` | Full product/design spec |
| `docs/tasks.md` | Milestone and task breakdown |
