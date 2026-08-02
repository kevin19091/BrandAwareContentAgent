"""
Golden-example eval runner. See evals/README.md for the mode split rationale.

Usage:
    USE_MOCK=false python3 -m evals.run_evals   # runs the 6 "real"-mode examples
    USE_MOCK=true  python3 -m evals.run_evals   # runs the 4 "mock"-mode examples

Only examples whose "mode" field matches the process's actual USE_MOCK
setting are run; the rest are skipped with a note (invoke twice to cover
all 10). Writes one JSON result file per example to evals/results/.
"""

import json
import os
from pathlib import Path

from backend.pipeline_graph import (
    USE_MOCK,
    build_graph_after_checkpoint,
    build_graph_before_checkpoint,
    make_initial_state,
)
from backend.uploads import process_uploads

EVALS_DIR = Path(__file__).parent
RESULTS_DIR = EVALS_DIR / "results"


def resolve_paths(rel_paths: list[str]) -> list[str]:
    return [str(EVALS_DIR / p) for p in rel_paths]


def run_example(example: dict) -> dict:
    session_assets = {
        "brand_guidelines": process_uploads(
            resolve_paths(example.get("brand_guidelines_files", [])), "Brand Guidelines"
        ),
        "competitor_refs": process_uploads(
            resolve_paths(example.get("competitor_refs_files", [])), "Competitor / Inspiration Refs"
        ),
    }
    state = make_initial_state(example["brief"], session_assets, example["hitl_mode"])
    config = {"configurable": {"thread_id": example["id"]}}

    before = build_graph_before_checkpoint()
    state = before.invoke(state, config)
    paused_correctly = bool(state.get("strategy")) and not state.get("content")

    if not state["guardrail_passed"]:
        return {**state, "_paused_correctly": None}

    after = build_graph_after_checkpoint()
    state = after.invoke(state, config)
    return {**state, "_paused_correctly": paused_correctly}


def grade(example: dict, result: dict) -> list[str]:
    lines = []
    expected = example["expected_criteria"]

    def check(field, actual, expected_val):
        if expected_val is None:
            return
        ok = actual == expected_val
        lines.append(f"  {'PASS' if ok else 'FAIL'} {field}: expected={expected_val!r} actual={actual!r}")

    check("guardrail_passed", result.get("guardrail_passed"), expected.get("guardrail_passed"))
    check("ingestion_source", result.get("ingestion_source"), expected.get("ingestion_source"))
    check("eval_passed", (result.get("eval_result") or {}).get("passed"), expected.get("eval_passed"))
    check("escalated", result.get("escalated"), expected.get("escalated"))
    check("retry_count", result.get("retry_count"), expected.get("retry_count"))
    if "checkpoint_pauses_after_strategy" in expected:
        check("checkpoint_pauses_after_strategy", result.get("_paused_correctly"), expected["checkpoint_pauses_after_strategy"])
    return lines


def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    examples = json.loads((EVALS_DIR / "golden_examples.json").read_text())
    current_mode = "mock" if USE_MOCK else "real"
    print(f"Running examples with mode == '{current_mode}' (USE_MOCK={USE_MOCK})\n")

    for example in examples:
        if example["mode"] != current_mode:
            print(f"[{example['id']}] skipped (mode={example['mode']}, current={current_mode})")
            continue

        print(f"[{example['id']}] {example['brand']} — {example['scenario']}")
        result = run_example(example)
        (RESULTS_DIR / f"{example['id']}.json").write_text(json.dumps(result, indent=2))
        for line in grade(example, result):
            print(line)
        print()


if __name__ == "__main__":
    main()
