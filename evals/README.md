# Evals — golden response sheet

15 hand-picked golden examples covering the pipeline's control-flow
branches, 4 real brands (2 top-tier, 2 mid-tier) with hand-researched
text profiles, and 4 more examples re-running those same brands/briefs
against real downloaded Instagram media instead of text (M7 multimodal
ingestion). Used as a manual/LLM-judge reference set. This is an
early, hand-built version of the "quantitative evaluation framework"
flagged as future work in CLAUDE.md §13 — not a full automated scoring
pipeline.

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

## Multimodal examples (11-14) — real Instagram media, not committed

Examples `11_nike_multimodal` through `14_mamaearth_multimodal` reuse
the same brand/brief as `01`/`03`/`04`/`06` but swap the text
`guidelines.txt` for real video/image files downloaded from each
brand's official Instagram (via `yt-dlp`) — testing whether M7's
vision pipeline (ffmpeg frame extraction + `gpt-4o-mini` vision) alone
can produce a comparably on-brand profile with zero hand-written text.
`13_fabindia_multimodal` specifically mixes one video + two images in
a single upload box, to exercise M7's multi-file/mixed-type ingestion.

These four examples' source media live in `data/<brand>/instagram/`
and are **not committed** — same as the rest of `data/`, and doubly so
here since downloaded Instagram content is third-party copyrighted
material that shouldn't be redistributed via a public git repo. This
means examples 11-14 **only run locally after re-downloading the same
posts** (see the `review_focus` field on each example for the exact
`yt-dlp` source). They're not reproducible from a fresh clone the way
1-10 are — that's expected and by design, not an oversight.

## Required brief elements

`guardrail_node` now does two things in one LLM call: the original
security check (injection/scope), and a brief-completeness check — a
usable brief must name a brand/product, a campaign objective, and a
target audience, or the run stops with a clear message before
Ingestion. This was added specifically to fix the wrong-brand-name bug
(see Findings) — the extracted `brand_name` is threaded through every
downstream prompt as an explicit anchor. All real-mode examples' briefs
were updated to name their brand accordingly (e.g. "Launch a
new-season **Nike** campaign...") so they still pass. `07_reject_guardrail`
is deliberately left as pure injection text (not a real brief) since
its security check should reject it before completeness is ever
evaluated. `15_insufficient_brief` (new, mock) specifically tests the
completeness-rejection branch via the `trigger_incomplete_brief`
keyword.

## Why 10 examples run in real mode and 5 in mock mode

The brand-showcase examples (happy path across all 4 brands, 2 of them
also in step mode, plus the 4 multimodal examples) run against the
**real** pipeline (`USE_MOCK=false`, calls OpenAI) — mock mode always
returns identical canned content regardless of brand input or uploaded
media, so it can't demonstrate actual brand-specific generation or
exercise real vision analysis.

The 5 control-flow edge cases (guardrail reject, insufficient brief,
eval-fail retry, eval-fail escalate, no-assets ingestion fallback) run
in **mock** mode instead, deliberately. Those trigger keywords
(`trigger_reject`, `trigger_incomplete_brief`, `trigger_eval_fail`,
`trigger_escalate`) only work in mock mode — real guardrail/evaluation
outcomes are genuine model judgment calls, not reliably reproducible
on demand. These 5 examples test the graph's plumbing (does it
actually stop on reject, stop on an incomplete brief, retry once then
continue, escalate on a 2nd failure, handle empty input gracefully?),
not brand fidelity, so determinism matters more than authenticity here.

## Structure

- `golden_examples.json` — all 15 example specs: brand, scenario, mode,
  hitl_mode, brief, `brand_guidelines_files`/`competitor_refs_files`
  (lists of paths — text, image, and/or video, resolved relative to
  `evals/` and passed through `backend.uploads.process_uploads`, the
  same router the live app uses), and expected structural criteria
  (`guardrail_passed`, `brief_check_passed`, `ingestion_source`,
  `eval_passed`, `escalated`, `retry_count` where applicable) plus a
  `review_focus` note for the
  subjective parts (does the copy actually sound like the brand?) that
  no automated check here grades — that's still a human/LLM-judge call,
  per the open item in CLAUDE.md §13.
- `brands/<name>/guidelines.txt`, `brands/<name>/competitor_refs.txt` —
  the hand-researched text session assets used by examples 1-10.
- `data/<brand>/instagram/` — **gitignored**, not committed (see above)
  — the real downloaded media used by examples 11-14.
- `results/<id>.json` — captured actual pipeline output per example,
  written by `run_evals.py`. This is the "golden" reference for future
  regression comparison (did a later change break this example's
  structural criteria, and does the content still read as on-brand?).

## Schema note (M7)

`reference_image` in `content.reference_image` gained an `image_path`
key (real mode only — a local temp file path to an actually-generated
image, not just `prompt_used` anymore). None of the golden examples'
`expected_criteria` assert on this field, so no example needed
updating, but a result JSON captured before M7 vs. after will differ
in that field if you diff them.

## Findings

- **Wrong-brand-name bug — FIXED, 3 instances.** `02_nike_happy_step`:
  with competitor info (Adidas) present in `competitor_refs`, the real
  Strategy agent's rationale said the campaign "positions **Adidas** as
  a supportive community," and the generated Instagram caption included
  the hashtag `#AdidasUnity`. `01_nike_happy_auto` showed a milder
  version — drifting toward Adidas' communal-support framing without
  naming it outright. `11_nike_multimodal` showed it a third time with
  *zero text in the loop* (brand DNA derived purely from a real Nike
  video) — the Strategy rationale named "competitors like Nike and
  Adidas," listing Nike as its own competitor. Evaluation passed all
  three ("no harmful content or unsubstantiated claims present") since
  its brand-alignment check only looked at tone/pillar match, never
  whether the copy names the correct brand.

  **Root cause:** `competition_insights` gave the model an explicit,
  named proper noun (the competitor) while the brand itself was only
  ever a bag of adjectives (voice/pillars/visual_style) with no name
  anchor anywhere in state — nothing to definitively distinguish "self"
  from "the other brand in context."

  **Fix:** two-pronged, in `backend/pipeline_graph.py`. (1)
  `guardrail_node` now also extracts and validates `brand_name` from
  the brief (see "Required brief elements" below) and threads it
  explicitly through the Strategy/Content Generation/Evaluation
  prompts as `writing for the brand "{brand_name}"` — giving the model
  a concrete anchor instead of forcing it to infer identity from
  adjectives alone. (2) Evaluation's prompt now explicitly checks for
  competitor misattribution as a distinct failure condition. Re-ran all
  three examples after the fix: `brand_name` extracted correctly as
  "Nike" in each, zero mentions of Adidas anywhere in any output, and
  captions even picked up the real `#JustDoIt` tagline — a sign the
  explicit name let the model draw on genuine brand knowledge instead
  of guessing. See `golden_examples.md` for the current captured output.
- **`14_mamaearth_multimodal` — brand voice drifted under vision-only
  input.** With brand DNA derived purely from one real Mamaearth video
  (no text), the resulting voice came back "sophisticated," "luxury,"
  and "elevate your parenting journey" — a notably different register
  from the toxin-free/reassuring/affordable positioning the text
  research established (`06_mamaearth_happy_auto`'s profile). Not
  necessarily wrong (the video may genuinely read as polished/premium),
  but it's a real signal that single-video brand inference is more
  sensitive to which specific clip gets uploaded than text research is
  — worth keeping in mind if this pipeline is ever used with only one
  piece of media as the entire brand-DNA source.

## Running

```bash
USE_MOCK=false python3 -m evals.run_evals   # the 10 real-mode brand examples, incl. 4 multimodal (uses OPENAI_API_KEY, real cost — video examples do several vision calls each)
USE_MOCK=true  python3 -m evals.run_evals   # the 5 mock-mode control-flow examples (free)
```

Each invocation only runs examples matching its own mode (the other
examples print as skipped) — run both to cover all 15. Examples 11-14
additionally require their source media present locally under
`data/<brand>/instagram/` (see above) or they'll fail on missing
files. Results land in `results/<id>.json`; structural pass/fail
prints to stdout.
