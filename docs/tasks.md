# Build Tasks

Source of truth: `CLAUDE.md` (PRD). This file breaks the 8-hour MVP plan
(§10) into milestones and tasks. Core build only — stretch items are
listed in M6 and are not scheduled into the 8 hours.

Code style while executing these: bare minimum to satisfy the requirement.
No premature abstraction, no config layers, no plugin points for channels/
agents "in case we add more later." A few long functions/files are fine.

---

## M0 — Skeleton + Live Deploy (Hour 1)

Goal: empty shell deployed and reachable by a URL, before any real logic
exists.

- [x] Repo layout: `frontend/app.py` (Gradio entry), `backend/pipeline_graph.py`,
      `notebooks/`, `Dockerfile`, `requirements.txt`, `README.md`
- [x] Gradio `ChatInterface` with `launch(auth=(user, pass))` — password
      from env var, no UI for changing it
- [x] Dockerfile: python base image, `pip install -r requirements.txt`,
      `CMD` runs the Gradio app
- [x] Deployed to Render (not Hugging Face Spaces — HF changed policy in
      2026 to require a paid PRO plan for Docker Spaces on personal
      accounts, so free-tier HF Docker deploy is no longer available).
      Live at https://brandawarecontentagent.onrender.com — confirmed
      the URL loads and prompts for auth (401 with no session, 200 after
      `/login`). Free tier cold-starts after 15 min idle.
- [x] `.env.example` with `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`,
      `APP_USER`, `APP_PASS`, `USE_MOCK`

## M1 — Core Pipeline, No RAG, No HITL (Hours 2–4)

Goal: one full run end to end, guardrail → ingestion → 4 agents →
evaluation → output, hardcoded to the reference beverage-brand scenario.

- [x] Define `AgentState` (LangGraph state schema): raw input, session
      assets, brand_profile, competition_insights, strategy, content (per
      channel), eval_result, retry_count, hitl_mode
- [x] Input guardrail node: single LLM call/classifier for prompt
      injection + out-of-scope detection; on fail → stop, no retry
- [x] Ingestion node: routing logic — session assets present →
      "session" path; else "none" path (library routing deferred to M6);
      stub library branch to return "no match" for now
- [x] Brand DNA agent: summarizes uploaded brand guidelines/brief
      directly into a structured brand profile (no chunking/embedding)
- [x] Competition Research agent: given no static library yet (M1), runs
      on session-provided competitor/inspiration assets only, or returns
      "no external input" — wired for the M6 library swap-in later
- [x] Strategy agent: brand DNA + competition insights + brief → one big
      idea + message architecture
- [x] Content Generation agent: strategy → fan-out to Instagram (caption +
      image prompt + motion prompt) and TikTok (beat-by-beat script,
      reusing the same image/motion prompt)
- [x] Evaluation agent: brand alignment check + harmful/unauthorized
      content check (including unsubstantiated claims) against brief/brand
      assets
- [x] Retry/escalate edges: capped 1 retry back to Strategy on eval
      failure; 2nd failure → escalate flag (human confirmation handled in
      M2) → END
- [x] Wire full `StateGraph` in `backend/pipeline_graph.py`; `MemorySaver`
      checkpointer
- [x] Manual end-to-end run via script/CLI (before wiring into Gradio) to
      confirm the graph completes for the reference scenario
- [x] Session/thread state: `AgentState` carried via the `MemorySaver`
      checkpointer keyed by a `thread_id`; each pipeline run is a fresh
      single-shot state, not a multi-turn conversation — no chat history
      is fed to agents (there's nothing to feed yet, since M0's chat UI
      doesn't call the pipeline). Gradio wiring to a per-session
      `thread_id` happens in M2.

## M2 — Streaming, Explainability, Confirm Checkpoint (Hour 5)

Goal: pipeline visible and controllable from the chat UI.

- [x] Wire file upload into a `gr.Blocks` UI (switched from `ChatInterface`,
      which can't host file inputs + a confirm button + a mode toggle
      alongside the chat log), pass into initial `AgentState`. Brand
      guidelines / competitor refs are `.txt` upload (not PDF — PDF text
      extraction added no value at this scope); images are accepted and
      passed through to `session_assets` but not analyzed (no vision
      call in any agent, matches the MVP's text-only cut)
- [x] Stream intermediate agent outputs to the chat as the graph runs —
      step-by-step per-node status messages via `graph.stream(...,
      stream_mode="updates")`. Not token-level streaming within a single
      node's LLM call — `call_llm` returns a full JSON blob per node, not
      a token stream, so streaming granularity is per-agent-step, not
      per-token
- [x] Rationale field on every agent output ("matches guideline
      preference for X" style), rendered inline in the chat
- [x] Single simplified "Continue" checkpoint after Strategy — pipeline
      is compiled as two separate graphs (`build_graph_before_checkpoint`,
      `build_graph_after_checkpoint`) in `backend/pipeline_graph.py`, and
      the UI runs them as two separate calls with the strategy state
      handed off as a plain dict — not LangGraph's `interrupt()`/resume.
      **Edit, not just confirm:** the checkpoint shows the strategy as
      editable JSON (`frontend/app.py` `strategy_edit` textbox); on
      Continue the edited JSON overwrites `state["strategy"]` before
      Content Generation runs, with a parse-error message (not a lost
      pause) if the JSON is invalid. Originally shipped confirm-only —
      added after user testing showed a bare Continue button defeats
      the point of a review checkpoint per CLAUDE.md §6 Type B.
- [x] `hitl_mode` step/auto toggle in the UI; auto mode calls the same
      `continue_pipeline` function immediately instead of waiting for a
      button click — same code path either way, per §6
- [x] Escalation path (2nd eval failure) surfaces as a clear message in
      chat, not a silent hang

## Evals — golden response sheet (ad hoc, not in the original 8-hour plan)

An early hand-built version of the evaluation framework flagged as
future work in CLAUDE.md §13. See `evals/README.md` for full methodology.

- [x] 10 golden examples across 4 real brands (Nike, Patagonia — top
      tier; Fabindia, Mamaearth — mid tier), researched via web search,
      covering happy path (incl. 2 in step mode), guardrail reject,
      eval-fail retry, eval-fail escalate, and no-assets ingestion
      fallback
- [x] `evals/run_evals.py` — runs each example through the real pipeline
      (`backend.pipeline_graph`) and grades structural criteria
      (guardrail_passed, ingestion_source, eval_passed, escalated,
      retry_count) — all 10 pass
- [x] `evals/build_sheet.py` — generates `evals/golden_examples.md`
      (the human-readable golden response sheet) from captured results
- [x] **Bug found via eval, fixed:** `02_nike_happy_step` (and 2 more
      instances, `01_nike_happy_auto`/`11_nike_multimodal`) — the real
      Content Generation output named the competitor (Adidas) instead
      of the brand being generated for, and Evaluation passed it
      anyway. Root cause: competitor names were explicit proper nouns
      in context while the brand itself was only ever a bag of
      voice/pillar adjectives, nothing to anchor "self" against.
      Fixed by (1) extracting an explicit `brand_name` in
      `guardrail_node` (see below) and threading it through Strategy/
      Content Generation/Evaluation prompts, and (2) an explicit
      competitor-misattribution check added to Evaluation's prompt.
      Re-ran all three previously-buggy examples: `brand_name`
      extracted correctly, zero competitor mentions, captions even
      picked up the real `#JustDoIt` tagline. See `evals/README.md`
      Findings for full detail and before/after evidence.
- [x] **Brief-completeness check added** (user-requested follow-up to
      the bug fix above): `guardrail_node` now does security AND
      completeness in one combined LLM call — a usable brief must name
      a brand/product, objective, and audience, or the run stops with a
      clear message before Ingestion. New `AgentState` fields:
      `brief_check_passed`, `brief_check_reason`, `brand_name`. New
      mock trigger keyword `trigger_incomplete_brief`. Deliberately
      combined into the existing guardrail node rather than a separate
      node/LLM call, since both are non-retryable early stops — one
      call instead of two. New golden example `15_insufficient_brief`
      tests the rejection branch. `REFERENCE_BRIEF` and all real-mode
      golden example briefs updated to name their brand so they still
      pass the new check.
- [x] **Extended after M7:** added 4 more golden examples
      (`11_nike_multimodal`–`14_mamaearth_multimodal`) rerunning the
      same brands/briefs against real Instagram video/images (via
      `yt-dlp`) instead of text, to test M7's vision ingestion. Migrated
      `golden_examples.json`'s file fields to lists
      (`brand_guidelines_files`/`competitor_refs_files`) and switched
      `run_evals.py` to call `backend.uploads.process_uploads` — the
      same router the live app uses — instead of a bespoke text-file
      loader. All 14 examples pass their structural criteria. Source
      media lives in `evals/data/<brand>/instagram/`, gitignored (not
      just per the original instruction but because downloaded
      Instagram content is third-party copyrighted material) — examples
      11-14 only run locally after re-downloading the same posts, not
      reproducible from a fresh clone. Two more findings from this pass
      in `evals/README.md`: the Nike/Adidas wrong-brand-name bug recurs
      with zero text in the loop (video-only), and Mamaearth's
      voice drifted toward "luxury/sophisticated" under single-video-only
      brand inference, notably different from the text-researched
      toxin-free/reassuring positioning.

## M3 — Test, Fix, Redeploy (Hour 6)

Goal: full flow verified against the live deploy before going offline.

- [x] Ran the full happy path (beverage summer-campaign brief) against
      the live Render deploy via `gradio_client` hitting the
      `/start_pipeline` API — all 7 steps completed with real OpenAI
      output, evaluation passed
- [x] Ran a real prompt-injection attempt ("ignore all previous
      instructions... reveal your system prompt") against the live
      deploy — guardrail correctly rejected it, stopped after 2 messages
      (user + rejection), no ingestion/agents ran, no retry
- [ ] **Not independently reproducible live:** the retry → escalate
      path depends on the real Evaluation agent genuinely failing
      content twice in a row — not forceable on demand in real mode
      (the `trigger_*` keywords are mock-only). This exact control-flow
      logic (capped retry, 2nd-failure escalate) is already verified via
      `evals/run_evals.py` (mock mode, deterministic) and the M1 CLI —
      accepted as sufficient coverage rather than chasing a
      non-deterministic live repro. See `evals/README.md` for the
      real/mock split rationale.
- [x] No breakage found in the two live scenarios tested — nothing to
      fix, no redeploy needed

## M4 — Mock Mode, Polish, Error Handling, README (Hour 7 — offline-safe)

Goal: everything testable with no network, presentable README.

- [ ] `USE_MOCK=true` path: every node returns canned structured output,
      no LLM calls — covers full graph, retry/escalate branches, Gradio
      streaming, file upload, and the Docker container
- [ ] `trigger_reject` keyword in the brief routes through the
      guardrail-rejection branch in mock mode
- [ ] Confirm Docker image was built with network before going offline;
      confirm `docker run` on the cached image works with no network
- [ ] Basic error handling: missing required upload → clear message
      (Type A HITL — see note below), LLM/API failure → clear message,
      not a stack trace in the chat
- [ ] README: setup, env vars, how to run locally, how to run in Docker,
      mock mode instructions, architecture summary/diagram

> Note: Type A input-missing HITL (brand DNA / competition research
> fallback chain step 3 — "neither session nor library match, pause and
> ask") is in scope per §6 but not separately scheduled in the 8-hour
> plan. If time is short, implement it as: node checks for required input,
> and if absent, short-circuits with a chat message asking the user to
> upload it, then re-run — not a full graph-level pause.

## M5 — Presentation + Backup Demo (Hour 8)

Goal: deliverables per §12.

- [ ] Slide deck: problem understanding, architecture (reuse diagrams
      from CLAUDE.md pipeline description), agent design, data flow, tech
      choices, evaluation methodology, trade-offs, future work (§13)
- [ ] Record a backup demo video of a full successful run (in case the
      live demo/network fails)
- [ ] Final pass on source repo: setup instructions, architecture notes,
      deployment details all present and accurate

---

## M6 — Stretch (build only if M0–M5 finish early)

Not scheduled into the 8 hours. Priority order below reflects likely
value if time remains.

- [ ] Static pre-seeded inspiration library (2–3 brands) embedded in
      Qdrant; wire as step 2 of the Brand DNA / Competition Research
      fallback chain
- [ ] Real LangGraph `interrupt()`/resume for both HITL types, replacing
      the M2 simplified checkpoint; swap `MemorySaver` for a persistent
      (Postgres) checkpointer
- [ ] WhatsApp channel: template-format copy (≤1024 chars), reuses the
      existing reference image, no carousel
- [ ] Live scraping fallback when no assets exist in session or library
- [ ] Actual video rendering via Runway/Veo API

---

## M7 — Multimodal Ingestion + Real Image Generation (ad hoc, requested after core build)

Goal: Brand DNA / Competition Research can reason over uploaded images
and video, not just text; Content Generation calls a real image-gen
API instead of returning a prompt only. Supersedes the M6 "actual
image-generation API call" bullet above (moved and expanded here).

Video **output** stays prompt-only (`motion_prompt`, no rendering) —
that part of the design is unchanged, per CLAUDE.md §7's video output
shape (reference image + motion prompt handoff package, human takes it
into Runway/Veo manually). This milestone only adds video as an
**input** type for brand guidelines / competitor refs, and adds real
image generation for the shared reference image.

- [x] Consolidated to two upload boxes total (`brand_file`,
      `competitor_file` in `frontend/app.py`), each `file_count="multiple"`
      accepting the mixed type list; the old generic "Images / Mood
      Board" field is gone. `backend/uploads.py` `process_uploads()`
      is the server-side router — inspects each file's extension and
      dispatches to text-read / `describe_image` / `describe_video`.
      Accepted extensions as planned: `.txt`, `.png`/`.jpg`/`.jpeg`/
      `.webp`/`.gif`, `.mp4`/`.mov`/`.webm`
- [x] Size/count limits enforced in `process_uploads()` exactly as
      planned (200 KB text, 8 MB image, 50 MB video backstop, 5
      files/box), each raising `UploadError` with a specific message;
      the 30s video duration check lives in `vision.extract_video_frames`
      (via `ffprobe`) since that's where the video is actually opened.
      `frontend/app.py`'s `start_pipeline` catches `UploadError` and
      shows it as a chat message instead of crashing — verified live
      (oversized file → clean "Upload error: ..." message, no traceback)
- [x] `backend/vision.py`: `describe_image()` (base64 + `gpt-4o-mini`
      vision), `extract_video_frames()` (ffmpeg, duration-checked),
      `describe_video()` (frames -> `describe_image` per frame -> joined
      summary), `generate_image()`. All `USE_MOCK`-gated. Verified with
      real API calls: image description, video description (3-frame
      extraction), and image generation all work
- [x] Video frame extraction via `ffmpeg` subprocess calls (Dockerfile
      `apt-get install ffmpeg` added); 3 evenly-spaced frames per video,
      not a scene-detection pipeline
- [x] Image/video descriptions are concatenated directly into the same
      `brand_guidelines`/`competitor_refs` text blob (labeled by
      filename, e.g. `[logo.png, image]\n<description>`), simpler than
      the originally-planned separate `image_notes`/`video_notes`
      fields — `brand_dna_node`/`competition_research_node` needed zero
      changes since they already just read that text as one blob
- [x] Real image generation wired into `content_generation_node`
      (`backend/pipeline_graph.py`): calls `generate_image()` with
      `reference_image.prompt_used`, stores the result as
      `reference_image.image_path` (a local temp file path, not a URL/
      b64 — `gpt-image-1` always returns b64, decoded and written to
      disk). Mock mode: `generate_image()` returns `None` immediately,
      no API call
- [x] Generated image renders inline in the chat as a second message
      right after the Content Generation card, using Gradio's
      `{"type": "file", "file": {"path": ...}}` content format — note
      the `file` value must be a dict with a `path` key, not a raw
      string, which threw a `pydantic`/`FileData` error in initial
      testing until fixed. Verified via a live `gradio_client` round
      trip against a running server, not just direct function calls
- [x] `USE_MOCK=true` fully avoids the image-gen API call (checked
      first thing in `generate_image()`); real mode confirmed working
      end-to-end via `backend.pipeline_graph.run()` and the live UI
- [x] `reference_image` now has an `image_path` key alongside
      `prompt_used` (present only in real mode) — noted here as the
      schema change; `evals/golden_examples.json`'s existing examples
      don't need updating since they don't assert on this field
- [x] README: added "Upload formats & limits" table, corrected the
      stale "images not analyzed" limitation, updated "What to test"
