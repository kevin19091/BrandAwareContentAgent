# Brand Intelligence Agent

Agentic system that ingests a brand's assets, synthesizes a brand
understanding, and generates brand-aligned content across channels. Full
design and scope: [CLAUDE.md](CLAUDE.md). Build plan: [docs/tasks.md](docs/tasks.md).

**Live demo:** https://brandawarecontentagent.onrender.com (password-
gated — ask for credentials). Free-tier Render host, so it cold-starts
after ~15 min idle; the first request after that can take 30-60s.

**Current status:** M0–M3 and M7 are done. The full pipeline (guardrail →
ingestion → brand DNA → competition research → strategy → content
generation → evaluation, with retry/escalate) is wired into a
password-gated Gradio UI with file upload, step-by-step streaming,
inline rationale, a confirm checkpoint after Strategy, and a step/auto
HITL toggle. Verified working against the live deploy, see
docs/tasks.md M3. Brand guidelines / competitor refs can be text,
image, or short video (M7) — images and video frames are analyzed by
a vision model, not just accepted and ignored — and the shared
reference image is now actually generated, not just a prompt.

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
   brief that names a brand, objective, and audience (e.g. "Launch a
   high-energy summer campaign for Fizzly, a beverage brand, targeting
   urban Gen-Z audiences" — required in real mode, see Guardrail note
   below), optionally attach files for
   Brand Guidelines / Competitor Refs (`.txt`, images, or short videos —
   see Upload formats & limits below), click **Run Pipeline**. You
   should see one chat message per pipeline step stream in — Guardrail,
   Ingestion, Brand DNA, Competition Research, Strategy, Content
   Generated (followed by a separate message showing the actual
   generated reference image, in real mode), Evaluation — each with a
   rationale toggle, ending in `Evaluation: **Passed.**`, with no pause
   in between.
4. **Step mode:** switch HITL Mode to `step`, run again. The stream
   should stop after the Strategy message with "Strategy ready for
   review..." and a **Continue** button appears, along with three
   plain fields (Big Idea, Message Architecture, Rationale) pre-filled
   with the current strategy — no JSON. Edit Big Idea (or leave it
   as-is) and click **Continue** — content generation should build on
   your edited strategy, not the original (a "Using your edited
   strategy." message confirms it took; if you didn't change anything,
   no such message appears).
5. **Multimodal upload (real mode only, `USE_MOCK=false`):** attach an
   image (e.g. a product photo or logo) to Brand Guidelines and run —
   the Brand DNA message's rationale should reference visual details a
   text-only guideline couldn't know about. Try a short video too (≤30s)
   — it gets sampled into a few frames and described the same way. Try
   uploading something over the size/duration limits (see below) — you
   should get a clear "Upload error: ..." chat message, not a crash.
6. **Guardrail rejection / insufficient brief:** the Guardrail step now
   does two things in one call — security (injection/scope) and brief
   completeness (does it name a brand, an objective, and an audience?).
   Type a brief containing `trigger_reject` anywhere — the pipeline
   should stop after one "Rejected." message, with no further steps
   (not even the Brief Completeness message). Separately, try a brief
   that never names a brand (e.g. "Launch a campaign for young
   people.") — Guardrail should pass, but the follow-up "Brief
   Completeness Check" message should say "Insufficient" and stop
   there, before Ingestion ever runs.
7. **Retry/escalate:** `trigger_eval_fail` in the brief should fail
   evaluation once, then show a "Retrying" message, then pass on the
   second attempt. `trigger_escalate` should fail twice and end on an
   "Escalated" message. (These trigger keywords only work in mock mode
   — `USE_MOCK=true`, the default.)
8. **Restart and confirm the login is required again** (no session
   persists across a fresh container/process start).

## Upload formats & limits

Brand Guidelines and Competitor / Inspiration Refs each accept up to
5 files, mixed types:

| Type | Extensions | Limit |
|---|---|---|
| Text | `.txt` | 200 KB/file |
| Image | `.png`, `.jpg`/`.jpeg`, `.webp`, `.gif` | 8 MB/file (GIF: only the first frame is used) |
| Video | `.mp4`, `.mov`, `.webm` | 30s duration + 50 MB/file |

Image and video files each trigger an extra vision-model API call per
file (video: a few calls, one per sampled frame) — real cost/latency,
gated behind `USE_MOCK` like everything else. Exceeding a limit shows
a clear chat message ("Upload error: ...") instead of crashing.

## Known limitations at this stage

- No PDF support — paste text into a `.txt` file if your source is a PDF.
- The pipeline runs the brief you type; there's no static inspiration
  library to fall back on yet if you upload nothing (`ingestion_source`
  will just be `"none"`) — that's a stretch item (M6).
- The confirm checkpoint is a plain two-call handoff in application
  code, not LangGraph's `interrupt()`/resume — see docs/tasks.md M2/M6.
- Real image generation (`gpt-image-1`) can fail for account/quota
  reasons outside this app's control (e.g. organization verification);
  `generate_image()` catches that and just omits the image rather than
  crashing the pipeline — you'd see the reference image prompt with no
  generated image message following it.
- Video output stays prompt-only (`motion_prompt`) — no actual video
  rendering, by design (see CLAUDE.md §7).

## Testing the pipeline directly (backend/CLI mode)

The pipeline also runs standalone, outside the UI — useful for quick
checks without a browser. Requires the venv set up per Option A above.

**Mock mode (default, no API key needed)** — `USE_MOCK=true` in
`.env.example`, every node returns canned output:

```bash
python3 -m backend.pipeline_graph "Create a high-energy summer campaign for Fizzly, a beverage brand, targeting urban Gen-Z audiences, emphasizing freedom, self-expression, and adventure."
```

Special keywords anywhere in the brief exercise the other control-flow
branches in mock mode:

| Keyword | What it tests |
|---|---|
| (none, with a brand/objective/audience stated) | Happy path — passes straight through |
| `trigger_reject` | Guardrail stops the run immediately, no retry |
| `trigger_incomplete_brief` | Guardrail's security check passes, but the brief-completeness check fails (no brand name) — stops before Ingestion, no retry |
| `trigger_eval_fail` | Evaluation fails once, retries, passes on 2nd attempt |
| `trigger_escalate` | Evaluation fails twice, retry cap hit, escalates |

Note: a real (non-mock) brief must actually name a brand, state an
objective, and state a target audience — Guardrail's combined check
now rejects briefs missing any of these, same as it rejects prompt
injection.

**Real mode (calls OpenAI, uses API credits)** — set `USE_MOCK=false`
and `OPENAI_API_KEY=...` in `.env`, then run the same command:

```bash
python3 -m backend.pipeline_graph "Create a high-energy summer campaign for Fizzly, a beverage brand, targeting urban Gen-Z audiences, emphasizing freedom, self-expression, and adventure."
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
| `backend/uploads.py` | Upload validation (size/count limits) and text/image/video routing |
| `backend/vision.py` | Vision description, video frame extraction, real image generation |
| `notebooks/` | Scratch `.ipynb` notebooks (prompt/model experiments), not shipped code |
| `Dockerfile` | Container build for local or hosted deployment |
| `.env.example` | Required environment variables, copy to `.env` |
| `CLAUDE.md` | Full product/design spec |
| `docs/tasks.md` | Milestone and task breakdown |
