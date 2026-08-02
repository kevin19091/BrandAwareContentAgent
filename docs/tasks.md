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
- [ ] Push to Hugging Face Spaces (Docker SDK) or Render; confirm the
      live URL loads and prompts for auth
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
- [ ] **Bug found via eval, not yet fixed:** `02_nike_happy_step` — with
      competitor info in context, the real Content Generation output
      named the competitor (Adidas) instead of the brand being generated
      for (`#AdidasUnity` in a Nike Instagram caption), and Evaluation
      still passed it. Evaluation's brand-alignment check doesn't verify
      generated copy names the correct brand. See `evals/README.md`
      Findings section for detail and suggested fix.

## M3 — Test, Fix, Redeploy (Hour 6)

Goal: full flow verified against the live deploy before going offline.

- [ ] Run the full happy path against the reference beverage scenario in
      the deployed UI
- [ ] Run the guardrail-rejection path (see M4 `trigger_reject`) and
      confirm it stops cleanly with no retry
- [ ] Run the eval-failure → retry → escalate path at least once
- [ ] Fix breakage found above
- [ ] Redeploy; re-verify the live URL

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
- [ ] Actual image-generation API call, replacing the structured-prompt-
      only output
- [ ] Live scraping fallback when no assets exist in session or library
- [ ] Actual video rendering via Runway/Veo API
