# Brand Intelligence Agent — PRD

## 1. Objective

An agentic system that ingests a brand's own assets and inspiration sources,
synthesizes a brand understanding, and generates coherent, brand-aligned
creative content across multiple channels — built as an interview assignment
demonstrating retrieval, multi-modal reasoning, agent orchestration,
guardrails, human-in-the-loop control, and explainability.

**Reference scenario:** a beverage company launching a high-energy summer
campaign for urban Gen-Z audiences, emphasizing freedom, self-expression,
and adventure.

## 2. Scope

### Core (must work)
- Sequential multi-agent pipeline (see §4)
- Session-based input (uploaded assets), no live scraping
- Text + image content generation for Instagram and TikTok
- Video handled as a **prompt + reference image handoff package**, not
  rendered — a human takes this into Runway/Veo manually
- Three guardrail checks (prompt injection, brand alignment, harmful/
  unauthorized content)
- Two HITL types (input-missing, output-confirmation) with a step/auto toggle
- Capped retry (1) on evaluation failure, escalate to human on second failure
- Dockerized deployment, password-gated chat UI, streamed responses

### Stretch (design it, build only if time allows)
- WhatsApp channel (template-format text + media, no carousel)
- RAG over a static pre-seeded inspiration library (multi-brand)
- Live scraping fallback when no assets exist anywhere
- Actual video rendering via Runway/Veo API
- Actual image generation API call (vs. returning the prompt only)
- Real LangGraph `interrupt()`/resume HITL (vs. a simplified UI-level pause)

### Explicitly out of scope
- Email channel (HTML/template-driven, not LLM-native — dropped in favor
  of WhatsApp)
- URL scraping / live social media ingestion (core build)
- WhatsApp carousel format

## 3. Inputs

**Approach:** hybrid, session-scoped (Option 3 from design discussion).

- User uploads: brand guidelines (PDF/text), brief (text), a few images/
  mood board assets, optionally one short video clip (≤30s)
- Session assets are **summarized directly into a structured brand
  profile** — no chunking/embedding. The corpus is small enough that RAG
  solves a problem that doesn't exist at this scale.
- Optional static pre-seeded inspiration library (2–3 brands, embedded
  ahead of time in Qdrant) for competitor/aspirational references —
  avoids live scraping, still demonstrates real retrieval (stretch).
- No URL scraping, no live fetching, in the core build.

## 4. Agent Pipeline (sequential)

```
guardrail (injection/scope check)
  → ingestion (routing: session | library | none)
  → brand_dna_agent          [confirm]
  → competition_research_agent [confirm]   (renamed from "creative insight")
  → strategy_agent           [confirm]
  → content_generation_agent [confirm]
  → evaluation_agent (brand alignment + harmful content)
       → done → END
       → retry (max 1) → back to strategy_agent
       → escalate (2nd failure) → human confirmation → END
```

Full LangGraph state schema and DAG wiring: see `pipeline_graph.py`.

### Agent responsibilities (input source determines ownership, not output type)

| Agent | Reads | Answers |
|---|---|---|
| Brand DNA | Brand's own assets (guidelines, past campaigns) | "What does this brand consistently say about itself?" |
| Competition Research | External inspiration (competitor/aspirational assets) | "What creative techniques are working in this space?" |
| Strategy | Brand DNA + Competition Research + brief | One big idea + message architecture (not five options) |
| Content Generation | Strategy output | Fan-out per channel |
| Evaluation | Content Generation output | Brand alignment + harmful content check |

### Fallback chain (shared pattern, used by Brand DNA and Competition Research)

1. Session-uploaded assets present → summarize directly
2. No session assets, brand/category matches static library → retrieve + synthesize
3. Neither → pause and ask the user (Type A HITL)

## 5. Guardrails

1. **Input guardrail (prompt injection / out-of-scope detection)** — runs
   once, before Ingestion, on raw input. Failure = immediate stop, no
   retry, no HITL (security boundary, not a quality gate).
2. **Brand alignment** — part of the Evaluation Agent, end of pipeline.
3. **Harmful/unauthorized content** — part of the Evaluation Agent.
   Includes: safety issues, and **unsubstantiated claims (e.g. discounts,
   health/efficacy claims) not present in the original brief or brand
   assets.**

## 6. Human-in-the-loop (two distinct types)

- **Type A — input HITL:** an agent is missing something it needs to
  proceed (no assets, no library match). Blocking; implemented as a
  LangGraph `interrupt()` whose return value is consumed by the node.
- **Type B — confirmation HITL:** an agent has produced output; a human
  reviews before it flows downstream. Implemented as a lightweight gate
  node after each reasoning agent.
- **Step / auto toggle** (`hitl_mode`): step = every confirm gate pauses;
  auto = gates auto-pass unless something is already flagged. Same code
  path either way — auto mode doesn't take a different route, it just
  doesn't block.
- Auto mode cannot resolve a genuine Type A pause (no assets anywhere) —
  this should fail gracefully with a clear message rather than hang.

## 7. Channels

| Channel | Priority | Output shape |
|---|---|---|
| Instagram | Core | Caption + generated reference image + motion prompt |
| TikTok/Reels | Core | Beat-by-beat script/shot list, reuses the same reference image + motion prompt |
| WhatsApp | Stretch | Template-format copy (≤1024 chars), text + media only, reuses the same reference image |

**Design principle:** one visual asset generated once, multiple channel
agents write channel-appropriate copy around it — not independent
generation per channel.

### Video output shape (no live rendering)

```json
{
  "reference_image": { "url": "...", "prompt_used": "..." },
  "motion_prompt": "camera movement, pacing, duration — video-model vocabulary",
  "style_tags": ["..."],
  "brand_alignment_note": "why this matches the brand profile, with source",
  "usage_note": "reference image = first-frame anchor; motion prompt = camera behavior over time"
}
```

## 8. Explainability

Every agent output should carry a short rationale tied to a retrieved/
summarized source (e.g. "matches guideline preference for X, p.4 of
guidelines"). Cheap to add, satisfies a real chunk of the assignment's
evaluation criteria.

## 9. Tech Stack

- **Orchestration:** LangGraph (StateGraph, conditional edges, `interrupt()`)
- **UI:** Gradio (`ChatInterface` + `launch(auth=...)` — built-in password
  gate and token streaming, chosen over Streamlit specifically for this)
- **Deployment:** Docker container; Hugging Face Spaces (Docker SDK) or
  Render for a fast public URL from a Dockerfile
- **Vector store (stretch only):** Qdrant, session-scoped collections for
  any future chunked corpus (static inspiration library), not used for
  session assets
- **Checkpointer:** `MemorySaver` for the demo; swap for persistent
  (Postgres) checkpointer so interrupts survive a restart in production

## 10. 8-Hour MVP Build Plan

Given a hard 8-hour budget, the full design above is the target
architecture, not the demo scope. Demo cuts:

- No RAG/Qdrant — direct context for session assets
- No video ingestion — text + image only
- No image-gen API call — return the structured prompt only
- WhatsApp cut entirely
- No real `interrupt()`/resume — a single simplified "Continue" checkpoint
  after Strategy, implemented as a two-step UI flow, not a graph pause
- No live scraping fallback

Keep: full sequential pipeline and control flow, capped retry, one real
confirm checkpoint, rationale fields for explainability.

| Hour | Task |
|---|---|
| 1 | Gradio skeleton + password gate + deploy immediately (empty shell, live URL from hour 1) |
| 2–4 | LangGraph pipeline, no RAG, no HITL yet — one full run working end to end |
| 5 | Streaming + explainability rendering + one confirm checkpoint |
| 6 (today ends) | Test full flow, fix breakage, redeploy |
| 7 (offline/flight) | Mock-mode testing (see §11), UI polish, error handling, README |
| 8 | Presentation deck (reuse architecture diagrams) + backup demo recording |

## 11. Offline / No-LLM Testing (mock mode)

`pipeline_graph.py` supports `USE_MOCK=true` — every node returns canned,
structured output instead of calling an LLM, so the full graph, retry/
escalate branches, Gradio streaming UI, file upload handling, and Docker
container can all be tested with no network connection.

- Type `trigger_reject` in the brief to test the guardrail-rejection branch
- Docker image must be **built** before going offline (`pip install` needs
  network); `docker run` on the cached image needs no network at runtime

## 12. Deliverables (per assignment brief)

1. **Presentation** — problem understanding, architecture (reuse diagrams
   from this design process), agent design, data flow, tech choices,
   evaluation methodology, trade-offs, future enhancements
2. **Working system** — deployed, URL-accessible, chat interface, visible
   intermediate reasoning
3. **Source repo** — code, setup instructions, architecture docs,
   deployment details

## 13. Open Items / Future Work (name explicitly, don't hand-wave)

- Quantitative evaluation framework for retrieval quality, agent
  performance, creativity scoring, latency — not yet designed in detail;
  flag as future work with a concrete direction (e.g. LLM-as-judge against
  a defined rubric for creativity, not an undefined "creativity score")
- Per-tenant isolation strategy for the static library at scale
  (namespace-per-tenant vs. metadata filtering)
- Live scraping fallback implementation
- Real video rendering integration and its cost/latency handling