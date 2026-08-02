# Brand Intelligence Agent

Agentic system that ingests a brand's assets, synthesizes a brand
understanding, and generates brand-aligned content across channels. Full
design and scope: [CLAUDE.md](CLAUDE.md). Build plan: [docs/tasks.md](docs/tasks.md).

**Current status:** M0 skeleton only — password-gated Gradio chat UI that
echoes input back with streaming. The real pipeline (guardrails, agents,
evaluation) is not wired in yet (see M1 in docs/tasks.md). This README
covers testing what exists today.

## Prerequisites

- Python 3.11+, or Docker
- No API keys required yet at this stage (nothing calls an LLM)

## Option A: Run locally with Python

```bash
git clone git@github.com:kevin19091/BrandAwareContentAgent.git
cd BrandAwareContentAgent

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env if you want a non-default APP_USER / APP_PASS

python -m frontend.app
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

- No file upload, no brand pipeline, no guardrails yet — the chat is a
  wiring check, not the product.
- `USE_MOCK` in `.env.example` is a placeholder for a later milestone (M4)
  and has no effect on the current app.
- Not yet deployed to a public URL — testing is local/Docker only for now.

## Project layout

| Path | Purpose |
|---|---|
| `frontend/app.py` | Gradio chat UI entry point, password gate |
| `backend/pipeline_graph.py` | LangGraph pipeline (placeholder, built in M1) |
| `notebooks/` | Scratch `.ipynb` notebooks (prompt/model experiments), not shipped code |
| `Dockerfile` | Container build for local or hosted deployment |
| `.env.example` | Required environment variables, copy to `.env` |
| `CLAUDE.md` | Full product/design spec |
| `docs/tasks.md` | Milestone and task breakdown |
