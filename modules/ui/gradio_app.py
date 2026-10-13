import base64
import os
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("EMBEDDING_BACKEND", "hashing")
os.environ.setdefault("VECTOR_STORE_BACKEND", "memory")
os.environ.setdefault("LLM_TIMEOUT_SECONDS", "15")
os.environ.setdefault("LLM_MAX_RETRIES", "0")

import gradio as gr

from modules.ingestion.sources import uploaded_names
from modules.ui.handlers import (
    WELCOME_MESSAGES,
    source_rows,
    submit_message,
    delete_source,
    refresh_sources,
    rebuild_chat,
    rebuild_sources,
    save_sources,
)

APP_TITLE = "TMedQA"
DEFAULT_QUESTION = "Li\u1ec7t d\u01b0\u01a1ng l\u00e0 g\u00ec?"

BASE_DIR = Path(__file__).resolve().parents[2]
LOGO_PATH = BASE_DIR / "logo" / "TMed-QA.png"

CSS = """
/* Import Google Sans & Roboto typography matching references.html */
@import url('https://fonts.googleapis.com/css2?family=Google+Sans:wght@400;500;600;700&family=Google+Sans+Text:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Roboto:wght@400;500;700&family=Roboto+Mono:wght@400;500&display=swap');

:root {
    --font-display: 'Google Sans', 'Google Sans Text', Roboto, Arial, sans-serif;
    --font-text: 'Google Sans Text', Roboto, -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    --font-mono: 'Roboto Mono', Menlo, Monaco, Consolas, monospace;

    --font-size-title: 24px;
    --font-size-heading: 18px;
    --font-size-subheading: 16px;
    --font-size-body: 14px;
    --font-size-caption: 12px;

    --color-primary: #1a73e8;
    --color-primary-hover: #1557b0;
    --color-surface: #ffffff;
    --color-background: #f8fafd;
    --color-border: #dadce0;
    --color-border-subtle: #e0e3e7;
    --color-text-primary: #1f1f1f;
    --color-text-secondary: #444746;
    --color-text-tertiary: #70757a;
    --color-badge-bg: #e8f0fe;
    --color-badge-text: #174ea6;
    --color-status-green: #34a853;

    --body-background-fill: var(--color-background);
    --body-text-color: var(--color-text-primary);
    --block-background-fill: var(--color-surface);
    --block-border-color: var(--color-border);
    --input-background-fill: var(--color-surface);
    --input-border-color: var(--color-border);
    --button-primary-background-fill: var(--color-primary);
    --button-primary-background-fill-hover: var(--color-primary-hover);
    --button-primary-text-color: #ffffff;
}

body, .gradio-container {
    background-color: var(--color-background) !important;
    color: var(--color-text-primary) !important;
    font-family: var(--font-text) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* Global typography overrides based on references.html */
.gradio-container * {
    font-family: var(--font-text) !important;
}

h1, h2, h3, h4, h5, h6,
.brand-title,
button,
.tab-nav button,
.tabs > .tab-nav > button,
.label-wrap span {
    font-family: var(--font-display) !important;
}

code, pre, .code-block {
    font-family: var(--font-mono) !important;
}

/* Brand Header Styling with TMed-QA Logo */
#brand-header-wrapper {
    margin-bottom: 12px;
}

#brand-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #ffffff;
    border: 1px solid var(--color-border);
    border-radius: 16px;
    padding: 14px 22px;
    box-shadow: 0 1px 3px rgba(60, 64, 67, 0.08), 0 1px 2px rgba(60, 64, 67, 0.04);
}

.brand-left {
    display: flex;
    align-items: center;
    gap: 16px;
}

.brand-logo-container {
    width: 52px;
    height: 52px;
    min-width: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid #e8eaed;
    overflow: hidden;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}

.brand-logo {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
}

.brand-text {
    display: flex;
    flex-direction: column;
}

.brand-title-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
}

.brand-title {
    font-size: var(--font-size-title) !important;
    font-weight: 600 !important;
    line-height: 32px !important;
    letter-spacing: -0.3px !important;
    color: var(--color-text-primary) !important;
    margin: 0 !important;
}

.brand-badge {
    font-size: 11px !important;
    font-weight: 500 !important;
    line-height: 14px !important;
    letter-spacing: 0.3px !important;
    background: var(--color-badge-bg) !important;
    color: var(--color-badge-text) !important;
    padding: 3px 9px !important;
    border-radius: 12px !important;
    text-transform: uppercase;
}

.brand-subtitle {
    font-size: var(--font-size-body) !important;
    font-weight: 400 !important;
    line-height: 20px !important;
    color: var(--color-text-secondary) !important;
    margin: 2px 0 0 0 !important;
}

.brand-right {
    display: flex;
    align-items: center;
}

.brand-status-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    background: #f1f3f4;
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid #e0e3e7;
}

.status-indicator-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--color-status-green);
    box-shadow: 0 0 0 2px rgba(52, 168, 83, 0.2);
}

.status-indicator-text {
    font-size: var(--font-size-caption) !important;
    font-weight: 500 !important;
    color: var(--color-text-secondary) !important;
}

/* Tabs Navigation matching Google Material & references.html */
.gradio-container .tab-nav {
    border-bottom: 1px solid var(--color-border) !important;
    gap: 4px;
    margin-bottom: 14px;
}

.gradio-container .tab-nav button {
    font-family: var(--font-display) !important;
    font-size: var(--font-size-body) !important;
    font-weight: 500 !important;
    letter-spacing: 0.25px !important;
    padding: 10px 18px !important;
    border-radius: 8px 8px 0 0 !important;
    color: var(--color-text-secondary) !important;
    border: none !important;
    background: transparent !important;
    transition: all 0.2s ease;
}

.gradio-container .tab-nav button.selected {
    color: var(--color-primary) !important;
    border-bottom: 3px solid var(--color-primary) !important;
    background: transparent !important;
    font-weight: 600 !important;
}

.gradio-container .tab-nav button:hover:not(.selected) {
    background: #f1f3f4 !important;
    color: var(--color-text-primary) !important;
}

/* Chatbot container */
#chatbot {
    border: 1px solid var(--color-border) !important;
    border-radius: 14px !important;
    background: #ffffff !important;
    box-shadow: 0 1px 3px rgba(60, 64, 67, 0.06) !important;
    overflow: hidden;
}

/* Chat message bubbles font & sizing */
#chatbot .message,
#chatbot [data-testid="bot"],
#chatbot [data-testid="user"],
#chatbot .message-wrap {
    font-size: 15px !important;
    line-height: 1.6 !important;
    color: var(--color-text-primary) !important;
}

#chatbot [data-testid="user"] {
    background: #e8f0fe !important;
    color: #174ea6 !important;
    border-radius: 16px 16px 4px 16px !important;
}

#chatbot [data-testid="bot"] {
    background: #f8f9fa !important;
    color: #1f1f1f !important;
    border-radius: 16px 16px 16px 4px !important;
    border: 1px solid #e8eaed !important;
}

/* Chat composer input (matching references.html textarea .er8xn style) */
#composer-row {
    align-items: center !important;
    gap: 10px !important;
    margin-top: 10px;
}

#chatbox {
    border-radius: 20px !important;
}

#chatbox textarea {
    font-family: var(--font-display) !important;
    font-size: 16px !important;
    line-height: 24px !important;
    color: var(--color-text-primary) !important;
    background: #ffffff !important;
    border: 1px solid var(--color-border) !important;
    border-radius: 16px !important;
    padding: 12px 16px !important;
    min-height: 54px !important;
    box-shadow: 0 1px 2px rgba(60, 64, 67, 0.08) !important;
    transition: border-color 0.2s, box-shadow 0.2s;
}

#chatbox textarea:focus {
    border-color: var(--color-primary) !important;
    box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2) !important;
    outline: none !important;
}

#chatbox textarea::placeholder {
    color: var(--color-text-tertiary) !important;
    font-size: 15px !important;
    opacity: 1 !important;
}

/* Action buttons matching Google Material Pill Style */
button.primary-button {
    font-family: var(--font-display) !important;
    font-size: var(--font-size-body) !important;
    font-weight: 500 !important;
    letter-spacing: 0.25px !important;
    min-height: 42px;
    background: var(--color-primary) !important;
    border-color: var(--color-primary) !important;
    color: #ffffff !important;
    border-radius: 24px !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08) !important;
    transition: all 0.2s ease;
}

button.primary-button:hover {
    background: var(--color-primary-hover) !important;
    border-color: var(--color-primary-hover) !important;
    box-shadow: 0 2px 6px rgba(26, 115, 232, 0.3) !important;
    transform: translateY(-1px);
}

.send-icon-button {
    min-width: 52px !important;
    max-width: 52px !important;
    height: 52px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    font-size: 20px !important;
    line-height: 1 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

button:not(.primary-button) {
    font-family: var(--font-display) !important;
    font-size: var(--font-size-body) !important;
    font-weight: 500 !important;
    letter-spacing: 0.25px !important;
    min-height: 40px;
    background: #ffffff !important;
    border: 1px solid var(--color-border) !important;
    color: var(--color-text-primary) !important;
    border-radius: 20px !important;
    box-shadow: 0 1px 2px rgba(60, 64, 67, 0.06) !important;
    transition: all 0.2s ease;
}

button:not(.primary-button):hover {
    background: #f8fafd !important;
    border-color: #c4c7c5 !important;
    transform: translateY(-1px);
}

/* Accordion & Section headings */
.gradio-container .label-wrap {
    color: var(--color-text-primary) !important;
    font-weight: 600 !important;
    font-size: var(--font-size-subheading) !important;
}

/* Panels and dataframes */
#source-panel, #available-source-panel {
    border: 1px solid var(--color-border) !important;
    border-radius: 12px !important;
    padding: 12px !important;
    background: #ffffff !important;
    width: 100% !important;
    box-sizing: border-box !important;
    box-shadow: 0 1px 3px rgba(60, 64, 67, 0.05) !important;
}

#source-panel th, #available-source-panel th {
    font-family: var(--font-display) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    background: #f1f3f4 !important;
    color: var(--color-text-primary) !important;
    padding: 10px 12px !important;
    border-bottom: 1px solid var(--color-border) !important;
}

#source-panel td, #available-source-panel td {
    font-size: 13px !important;
    line-height: 1.45 !important;
    color: var(--color-text-primary) !important;
    padding: 8px 12px !important;
}

/* Status lines & helper text */
#status-line, #source-status-line {
    font-size: 13px !important;
    line-height: 20px !important;
    color: var(--color-text-secondary) !important;
    min-height: 28px;
    padding: 4px 6px;
}

/* Action rows */
#action-row, #upload-row, #delete-row {
    align-items: center !important;
    gap: 8px !important;
    margin-top: 8px;
    margin-bottom: 8px;
}

.gradio-container a {
    color: var(--color-primary) !important;
    font-weight: 500 !important;
    text-decoration: none !important;
}

.gradio-container a:hover {
    text-decoration: underline !important;
}
"""


def get_header_html() -> str:
    logo_src = ""
    if LOGO_PATH.exists():
        encoded = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
        logo_src = f"data:image/png;base64,{encoded}"

    logo_img = (
        f'<img src="{logo_src}" alt="TMed-QA Logo" class="brand-logo" />'
        if logo_src
        else ""
    )

    return f"""
    <div id="brand-header-wrapper">
        <div id="brand-header">
            <div class="brand-left">
                <div class="brand-logo-container">
                    {logo_img}
                </div>
                <div class="brand-text">
                    <div class="brand-title-wrap">
                        <h1 class="brand-title">{APP_TITLE}</h1>
                        <span class="brand-badge">Medical AI</span>
                    </div>
                    <p class="brand-subtitle">Agentic Graph Correctness RAG &bull; Tr&#7907; l&#253; tra c&#719;u y khoa ch&#237;nh x&#225;c</p>
                </div>
            </div>
            <div class="brand-right">
                <div class="brand-status-chip">
                    <span class="status-indicator-dot"></span>
                    <span class="status-indicator-text">CRAG Active</span>
                </div>
            </div>
        </div>
    </div>
    """


def create_demo():
    with gr.Blocks(title=APP_TITLE) as demo:
        gr.HTML(get_header_html(), elem_id="header-html")

        with gr.Tabs():
            with gr.Tab("Chat"):
                chatbot = gr.Chatbot(
                    value=list(WELCOME_MESSAGES),
                    label="Conversation",
                    elem_id="chatbot",
                    height=520,
                    layout="bubble",
                    show_label=False,
                    placeholder="Ask a question about the indexed sources.",
                )
                with gr.Row(elem_id="composer-row"):
                    chatbox = gr.Textbox(
                        label="Message",
                        placeholder="Ask a question about the indexed sources...",
                        lines=2,
                        max_lines=5,
                        autofocus=True,
                        scale=18,
                        elem_id="chatbox",
                    )
                    submit = gr.Button("\u27a4", variant="primary", elem_classes=["primary-button", "send-icon-button"], scale=1)

                with gr.Row(elem_id="action-row"):
                    rebuild_button = gr.Button("Rebuild vector store")

                status = gr.Markdown("Ready.", elem_id="status-line")
                with gr.Accordion("Retrieved evidence", open=True):
                    retrieved_sources = gr.Dataframe(
                        headers=["#", "Type", "Source", "Section", "Preview", "Chars"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        row_count=(0, "dynamic"),
                        column_count=(6, "fixed"),
                        wrap=True,
                        interactive=False,
                        label="Retrieved sources",
                        elem_id="source-panel",
                    )

            with gr.Tab("Sources"):
                gr.Markdown("## Available sources")
                uploader = gr.File(
                    label="Upload source files (.docx, .txt, .md)",
                    file_count="multiple",
                    file_types=[".docx", ".txt", ".md"],
                )
                with gr.Row(elem_id="upload-row"):
                    upload_button = gr.Button("Add uploaded sources", variant="primary", elem_classes=["primary-button"])
                    refresh_button = gr.Button("Refresh source list")
                    rebuild_sources_button = gr.Button("Rebuild vector store")
                with gr.Row(elem_id="delete-row"):
                    uploaded_source_select = gr.Dropdown(
                        choices=uploaded_names(),
                        label="Uploaded source to delete",
                        interactive=True,
                        scale=5,
                    )
                    delete_source_button = gr.Button("Delete uploaded source", scale=2)
                source_status = gr.Markdown("Ready.", elem_id="source-status-line")
                available_sources = gr.Dataframe(
                    value=source_rows(),
                    headers=["#", "Kind", "Name", "Status", "Path"],
                    datatype=["str", "str", "str", "str", "str"],
                    row_count=(0, "dynamic"),
                    column_count=(5, "fixed"),
                    wrap=True,
                    interactive=False,
                    label="Available sources",
                    elem_id="available-source-panel",
                )

        submit.click(submit_message, inputs=[chatbox, chatbot], outputs=[chatbot, chatbox, retrieved_sources, status])
        chatbox.submit(submit_message, inputs=[chatbox, chatbot], outputs=[chatbot, chatbox, retrieved_sources, status])
        rebuild_button.click(rebuild_chat, outputs=[status])
        upload_button.click(save_sources, inputs=[uploader], outputs=[available_sources, source_status, uploaded_source_select])
        refresh_button.click(refresh_sources, outputs=[available_sources, source_status, uploaded_source_select])
        rebuild_sources_button.click(rebuild_sources, outputs=[available_sources, source_status, uploaded_source_select])
        delete_source_button.click(
            delete_source,
            inputs=[uploaded_source_select],
            outputs=[available_sources, source_status, uploaded_source_select],
        )

    return demo


def launch_demo():
    launch_kwargs = {
        "server_name": os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        "show_error": True,
        "theme": gr.themes.Soft(primary_hue="blue", neutral_hue="slate"),
        "css": CSS,
    }

    if LOGO_PATH.exists():
        launch_kwargs["favicon_path"] = str(LOGO_PATH)

    port = os.getenv("GRADIO_SERVER_PORT", "").strip()
    if port:
        launch_kwargs["server_port"] = int(port)

    return create_demo().launch(**launch_kwargs)


if __name__ == "__main__":
    launch_demo()