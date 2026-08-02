import os
import time

import gradio as gr
from dotenv import load_dotenv

load_dotenv()

APP_USER = os.environ.get("APP_USER", "admin")
APP_PASS = os.environ.get("APP_PASS", "changeme")


def chat_fn(message, history):
    # Pipeline (guardrail -> ingestion -> agents -> evaluation) lands in M1.
    # This stub just proves the UI, auth, and streaming wiring work end to end.
    response = f"Pipeline not implemented yet (see docs/tasks.md, M1). Echo: {message}"
    partial = ""
    for word in response.split(" "):
        partial += word + " "
        time.sleep(0.02)
        yield partial


demo = gr.ChatInterface(
    fn=chat_fn,
    title="Brand Intelligence Agent",
    description="Upload brand assets and a brief to generate brand-aligned content.",
)

if __name__ == "__main__":
    demo.queue().launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        auth=(APP_USER, APP_PASS),
    )
