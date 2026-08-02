# Evals — golden response sheet

10 hand-picked golden examples covering the pipeline's control-flow
branches and 4 real brands (2 top-tier, 2 mid-tier), used as a manual/
LLM-judge reference set. This is an early, hand-built version of the
"quantitative evaluation framework" flagged as future work in
CLAUDE.md §13 — not a full automated scoring pipeline.

## Brands

| Brand | Tier | Category | Competitor ref used |
|---|---|---|---|
| Nike | Top | Sportswear | Adidas |
| Patagonia | Top | Outdoor/apparel | The North Face |
| Fabindia | Mid | Indian heritage lifestyle/apparel | BlueStone |
| Mamaearth | Mid | Indian D2C personal care | Plum Goodness |

Brand voice and competitor positioning in `brands/<name>/guidelines.txt`
and `brands/<name>/competitor_refs.txt` are synthesized from public
web research (source cited at the top of each file), not internal brand
guidelines — no brand publishes those. Treat them as a reasonable public
approximation, not ground truth.

## Why 6 examples run in real mode and 4 in mock mode

The brand-showcase examples (happy path across all 4 brands, 2 of them
also in step mode) run against the **real** pipeline (`USE_MOCK=false`,
calls OpenAI) — mock mode always returns identical canned content
regardless of brand input, so it can't demonstrate actual brand-specific
generation.

The 4 control-flow edge cases (guardrail reject, eval-fail retry,
eval-fail escalate, no-assets ingestion fallback) run in **mock** mode
instead, deliberately. Those trigger keywords (`trigger_reject`,
`trigger_eval_fail`, `trigger_escalate`) only work in mock mode —
real guardrail/evaluation outcomes are genuine model judgment calls,
not reliably reproducible on demand. These 4 examples test the graph's
plumbing (does it actually stop on reject, retry once then continue,
escalate on a 2nd failure, handle empty input gracefully?), not brand
fidelity, so determinism matters more than authenticity here.

## Structure

- `golden_examples.json` — the 10 example specs: brand, scenario, mode,
  hitl_mode, brief, which brand text files to load, and expected
  structural criteria (`guardrail_passed`, `ingestion_source`,
  `eval_passed`, `escalated`, `retry_count` where applicable) plus a
  `review_focus` note for the subjective parts (does the copy actually
  sound like the brand?) that no automated check here grades — that's
  still a human/LLM-judge call, per the open item in CLAUDE.md §13.
- `brands/<name>/guidelines.txt`, `brands/<name>/competitor_refs.txt` —
  the session assets fed into each example, sourced from web research.
- `results/<id>.json` — captured actual pipeline output per example,
  written by `run_evals.py`. This is the "golden" reference for future
  regression comparison (did a later change break this example's
  structural criteria, and does the content still read as on-brand?).
- `data/<brand>/images/` — **gitignored**, not committed. Drop
  downloaded Instagram posts or other reference images here for manual/
  visual comparison. As of M7 the pipeline *can* analyze images/video
  fed through the actual upload boxes (`backend/vision.py`), but these
  golden examples still load brand/competitor text only via
  `brand_guidelines_file`/`competitor_refs_file` in `golden_examples.json`
  — files dropped in `data/` here are for human reference only, not
  wired into the eval runner.

## Schema note (M7)

`reference_image` in `content.reference_image` gained an `image_path`
key (real mode only — a local temp file path to an actually-generated
image, not just `prompt_used` anymore). None of the 10 golden examples'
`expected_criteria` assert on this field, so no example needed
updating, but a result JSON captured before M7 vs. after will differ
in that field if you diff them.

## Findings

- **`02_nike_happy_step` — wrong-brand-name bug.** With competitor info
  (Adidas) present in `competitor_refs`, the real Strategy agent's
  rationale said the campaign "positions **Adidas** as a supportive
  community," and the generated Instagram caption included the hashtag
  `#AdidasUnity` — the pipeline hallucinated the competitor's name into
  Nike's own campaign copy. Evaluation still passed it
  ("no harmful content or unsubstantiated claims present") — the
  Evaluation agent's brand-alignment check doesn't currently verify that
  generated copy actually names the brand it's being generated for, only
  tone/pillar alignment. Follow-up: either the Content Generation prompt
  needs an explicit "never name a competitor in outward-facing copy"
  guard, or the Evaluation agent's brand-alignment check needs a
  same-brand-name assertion. Not fixed as part of this eval pass — see
  `docs/tasks.md` for tracking.
- `01_nike_happy_auto` shows a milder version of the same failure mode
  without naming Adidas outright: its rationale explicitly says it's
  "moving away from individual achievement and instead fostering a
  sense of community and support" — drifting toward the communal-support
  framing that `competitor_refs.txt` flags as Adidas' differentiator,
  despite the brief and guidelines both being individual-effort framed.
  Suggests the Strategy agent reads competitor techniques as inspiration
  to *emulate* rather than *differentiate from*, at least in this case.

## Running

```bash
USE_MOCK=false python3 -m evals.run_evals   # the 6 real-mode brand examples (uses OPENAI_API_KEY, small cost)
USE_MOCK=true  python3 -m evals.run_evals   # the 4 mock-mode control-flow examples (free)
```

Each invocation only runs examples matching its own mode (the other
examples print as skipped) — run both to cover all 10. Results land in
`results/<id>.json`; structural pass/fail prints to stdout.
