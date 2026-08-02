import os
import uuid

import gradio as gr
from dotenv import load_dotenv

from backend.pipeline_graph import (
    build_graph_after_checkpoint,
    build_graph_before_checkpoint,
    make_initial_state,
)

load_dotenv()

APP_USER = os.environ.get("APP_USER", "admin")
APP_PASS = os.environ.get("APP_PASS", "changeme")


def read_text_file(path: str | None) -> str:
    if not path:
        return ""
    with open(path, "r", errors="ignore") as f:
        return f.read()


def format_node_message(node_name: str, output: dict) -> str:
    if node_name == "guardrail":
        if output["guardrail_passed"]:
            return f"**Guardrail:** passed — {output['guardrail_reason']}"
        return f"**Guardrail:** REJECTED — {output['guardrail_reason']}"
    if node_name == "ingestion":
        return f"**Ingestion:** source = `{output['ingestion_source']}`"
    if node_name == "brand_dna":
        p = output["brand_profile"]
        return (
            f"**Brand DNA:** pillars = {', '.join(p.get('pillars', []))}\n\n"
            f"Rationale: {p.get('rationale', '')}"
        )
    if node_name == "competition_research":
        c = output["competition_insights"]
        return (
            f"**Competition Research:** techniques = {', '.join(c.get('techniques', []))}\n\n"
            f"Rationale: {c.get('rationale', '')}"
        )
    if node_name in ("strategy", "retry_strategy"):
        s = output["strategy"]
        return f"**Strategy:** {s.get('big_idea', '')}\n\nRationale: {s.get('rationale', '')}"
    if node_name == "content_generation":
        c = output["content"]
        ig = c.get("instagram", {})
        tk = c.get("tiktok", {})
        return (
            f"**Content Generated**\n\n"
            f"Instagram caption: {ig.get('caption', '')}\n"
            f"Rationale: {ig.get('brand_alignment_note', '')}\n\n"
            f"TikTok shot list: {len(tk.get('shot_list', []))} beats\n"
            f"Rationale: {tk.get('brand_alignment_note', '')}"
        )
    if node_name == "evaluation":
        e = output["eval_result"]
        verdict = "PASSED" if e.get("passed") else "FAILED"
        return f"**Evaluation:** {verdict} — {e.get('reason', '')}"
    if node_name == "increment_retry":
        return f"**Retrying** (attempt {output['retry_count']})..."
    if node_name == "escalate":
        return "**Escalated:** evaluation failed twice. Stopping for human review."
    return f"**{node_name}:** {output}"


def stream_graph(graph, state, thread_id, history):
    config = {"configurable": {"thread_id": thread_id}}
    for update in graph.stream(state, config, stream_mode="updates"):
        for node_name, node_output in update.items():
            state = {**state, **node_output}
            history = history + [{"role": "assistant", "content": format_node_message(node_name, node_output)}]
            yield state, history


def start_pipeline(brief, brand_file, competitor_file, images, hitl_mode, history):
    history = history or []
    if not brief or not brief.strip():
        history = history + [{"role": "assistant", "content": "Please enter a brief before running."}]
        yield history, None, gr.update(visible=False)
        return

    session_assets = {
        "brand_guidelines": read_text_file(brand_file),
        "competitor_refs": read_text_file(competitor_file),
        "images": list(images) if images else [],
    }
    state = make_initial_state(brief, session_assets, hitl_mode)
    thread_id = str(uuid.uuid4())
    history = history + [{"role": "user", "content": brief}]
    yield history, None, gr.update(visible=False)

    graph = build_graph_before_checkpoint()
    for state, history in stream_graph(graph, state, thread_id, history):
        yield history, None, gr.update(visible=False)

    if not state["guardrail_passed"]:
        yield history, None, gr.update(visible=False)
        return

    pending = {"state": state, "thread_id": thread_id}
    if hitl_mode == "step":
        history = history + [
            {
                "role": "assistant",
                "content": "Strategy ready for review. Click **Continue** to generate content.",
            }
        ]
        yield history, pending, gr.update(visible=True)
        return

    # auto mode: same code path, just no UI block — continue immediately.
    for history, pending in continue_pipeline(pending, history):
        yield history, pending, gr.update(visible=False)


def continue_pipeline(pending, history):
    history = history or []
    if not pending:
        yield history, None
        return

    state, thread_id = pending["state"], pending["thread_id"]
    graph = build_graph_after_checkpoint()
    for state, history in stream_graph(graph, state, thread_id, history):
        yield history, None

    yield history, None


def on_continue_click(pending, history):
    for history, pending in continue_pipeline(pending, history):
        yield history, pending, gr.update(visible=False)


with gr.Blocks(title="Brand Intelligence Agent") as demo:
    gr.Markdown(
        "# Brand Intelligence Agent\n"
        "Upload brand assets and a brief to generate brand-aligned content. "
        "Pipeline: guardrail -> ingestion -> brand DNA -> competition research -> "
        "strategy -> (confirm) -> content generation -> evaluation."
    )
    pending_state = gr.State(None)

    with gr.Row():
        with gr.Column(scale=2):
            chatbot = gr.Chatbot(label="Pipeline Output", height=500, group_consecutive_messages=False)
            continue_btn = gr.Button("Continue", visible=False, variant="primary")
        with gr.Column(scale=1):
            brief = gr.Textbox(label="Brief", lines=4, placeholder="Describe the campaign...")
            brand_file = gr.File(label="Brand Guidelines (.txt)", file_types=[".txt"])
            competitor_file = gr.File(label="Competitor / Inspiration Refs (.txt)", file_types=[".txt"])
            images = gr.File(label="Images / Mood Board", file_count="multiple")
            hitl_mode = gr.Radio(["auto", "step"], value="auto", label="HITL Mode")
            run_btn = gr.Button("Run Pipeline", variant="primary")

    run_btn.click(
        fn=start_pipeline,
        inputs=[brief, brand_file, competitor_file, images, hitl_mode, chatbot],
        outputs=[chatbot, pending_state, continue_btn],
    )
    continue_btn.click(
        fn=on_continue_click,
        inputs=[pending_state, chatbot],
        outputs=[chatbot, pending_state, continue_btn],
    )

if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        auth=(APP_USER, APP_PASS),
    )
