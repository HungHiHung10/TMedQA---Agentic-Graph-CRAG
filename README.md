# TMed-QA: Medical AI Agentic Corrective RAG (CRAG) System

<p align="left">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-2.0-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/LangGraph-%E2%9A%99%EF%B8%8F-blueviolet?style=flat" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/LangChain-%F0%9F%A6%9C%F0%9F%94%97-green?style=flat" alt="LangChain"/>
  <img src="https://img.shields.io/badge/ChromaDB-Vector_Store-red?style=flat" alt="ChromaDB"/>
  <img src="https://img.shields.io/badge/Groq-Fast_Inference-black?style=flat" alt="Groq"/>
  <img src="https://img.shields.io/badge/Gradio-Alternative_UI-orange?style=flat" alt="Gradio"/>
</p>

**TMed-QA** is an **Agentic Corrective Retrieval-Augmented Generation (CRAG)** web application designed for Traditional Vietnamese Medicine (Y học Cổ truyền - YHCT). Built on **LangGraph**, **FastAPI**, and **Sentence-Transformers (`vietnamese-sbert`)**, the system self-evaluates retrieved evidence, dynamically rewrites queries or falls back to web search when local context is insufficient, and generates clinical answers strictly grounded in verified textbooks.

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Empirical Evaluation Benchmark](#empirical-evaluation-benchmark)
- [Colab Quickstart](#colab-quickstart)
- [Troubleshooting & Optimizations](#troubleshooting--optimizations)

---

## Key Features

1. **Agentic Corrective RAG (CRAG) Pipeline**
   - **LangGraph Directed Cyclic Graph**: Implements autonomous routing between retrieval, evaluation, rewriting, and generation.
   - **Document Grader Node**: Strict relevance filter preventing irrelevant or misleading chunks from polluting context.
   - **Query Rewriter & Search Fallback**: Automatically refines queries and queries external web resources (DuckDuckGo API) if knowledge base evidence is lacking.
   - **Strict Anti-Hallucination Policy**: Generator strictly cites evidence markers (`[1]`, `[2]`) and explicitly refuses to extrapolate unverified medical claims.

2. **Full-Featured Modern Clinical Web UI**
   - **Modern Single-Page Application**: Built with responsive vanilla CSS and modern JS (no bloated frontend dependencies).
   - **Minimalist Vector Design**: 100% clean SVG vector line icons (no emojis), subtle animations, and high contrast typography.
   - **Bottom-Docked Chat Composer**: Full-height viewport flex layout with centered hero greeting and quick suggestion chips.
   - **Live Evidence Inspector**: Slide-over panel displaying real-time citations, section hierarchies, character counts, and full chunk previews.
   - **Dual Themes**: Instant Light and Dark mode toggle.

3. **Dynamic Knowledge Base Management**
   - **Built-in YHCT Corpus**: Over 2,980 curated chunks extracted from 4 authoritative textbooks:
     - *Nội Khoa YHCT* - GS. Hoàng Bảo Châu
     - *Bệnh Ngũ Quan YHCT*
     - *Nhi Khoa YHCT*
     - *Nội Khoa Y học Cổ truyền Toàn thư*
   - **Live Document Ingestion**: Upload custom `.docx`, `.txt`, and `.md` files directly through the web interface with on-the-fly chunking and index rebuilding.

---

## System Architecture

```mermaid
flowchart TD
    %% User & Gateway
    User([Bệnh nhân / Bác sĩ]) --> WebUI[Giao diện TMed-QA Web / Gradio]
    WebUI --> API[FastAPI Web Server /api/chat]

    %% LangGraph CRAG Graph
    subgraph CRAG ["Quy trình đồ thị Agentic Corrective RAG (LangGraph)"]
        API --> RET[1. Retrieve Documents: vietnamese-sbert / ChromaDB]
        RET --> GRD{2. Document Grader Node: LLM/Heuristic Filter}
        
        GRD -- "Đủ minh chứng phù hợp" --> GEN[4. Medical Generator: Groq / Gemini]
        GRD -- "Thiếu hoặc sai lệch" --> REW[3. Query Rewriter: LLM Optimizer]
        
        REW --> WEB[Web Search Fallback: DuckDuckGo API]
        WEB --> GEN
        
        GEN --> CIT[Citation & Source Grounding Processor]
    end

    %% Response
    CIT --> Resp([Phản hồi Y khoa kèm Trích dẫn số [1], [2]])
    Resp --> WebUI

    %% Styling
    classDef startend fill:#1a73e8,stroke:#1557b0,stroke-width:2px,color:#fff,font-weight:bold;
    classDef process fill:#f8fafd,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a;
    classDef branch fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#854d0e;
    
    class User,Resp startend;
    class WebUI,API,RET,REW,WEB,GEN,CIT process;
    class GRD branch;
```

---

## Project Structure

```text
a:/TMed-QA/
├── app.py                     # Primary WSGI runner (FastAPI default, --gradio flag)
├── main.py                    # Terminal CLI runner
├── index.html                 # Modern Clinical Web Application (SPA entrypoint)
├── style.css                  # Design system tokens, flex layout, dark/light themes
├── app.js                     # Web client controller (Chat, Evidence, Source inventory)
├── evaluation.py              # LLM-as-a-Judge benchmark harness
├── benchmark_results.json     # Empirical evaluation report and score register
├── logo/                      # Official SVG and PNG branding assets
├── data/                      # Standardized YHCT textbook corpus (.docx)
├── database/                  # Persistent ChromaDB vector storage directory
├── user_sources/              # Dynamic uploaded user documents storage
├── static/                    # Synchronized static mirror for web server deployment
└── modules/
    ├── settings.py            # Global environment variables, model names, paths
    ├── models.py              # Embeddings & multi-provider LLM loader (Groq, Gemini)
    ├── ingestion/
    │   ├── loaders.py         # Word (.docx) & text document loaders
    │   ├── splitters.py       # Hierarchical medical section chunkers
    │   └── sources.py         # Document inventory, soft-delete & upload tracking
    ├── retrieval/
    │   ├── retriever.py       # In-memory hybrid scoring and diversification
    │   └── vector_store.py    # Chroma & in-memory vector store factory
    ├── rag/
    │   ├── chains.py          # Grader, Rewriter, and Generator Prompt Chains
    │   ├── graph.py           # LangGraph StateGraph implementation
    │   └── service.py         # Application service layer for QA invocations
    └── ui/
        ├── web_server.py      # Production FastAPI endpoints (/api/chat, /api/sources)
        ├── gradio_app.py      # Alternative Gradio Blocks UI
        ├── handlers.py        # UI action handlers
        └── formatting.py      # Citation formatters & medical disclaimer wrappers
```

---

## Installation & Setup

### 1. Prerequisites
- Python 3.10 or higher
- Git

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/HungHiHung10/TMedQA---Agentic-Graph-CRAG.git
cd TMed-QA

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration (.env)
Create a `.env` file in the project root:

```ini
# Server Configuration
PORT=7860
HOST=127.0.0.1

# Vector Store Backend ('chroma' or 'memory')
VECTOR_STORE_BACKEND=chroma

# Primary LLM Provider: 'groq' or 'gemini'
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_MODEL=qwen/qwen3.8-27b

# Fallback LLM Provider (Optional)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
LLM_PROVIDER_CHAIN=groq,gemini

# Embedding Model
EMBEDDING_MODEL_NAME=keepitreal/vietnamese-sbert
```

---

## Running the Application

### Modern Clinical Web App (Recommended)
Launches the high-performance FastAPI web server serving the modern responsive SPA:
```bash
python app.py
```
Open **`http://127.0.0.1:7860`** in your browser.

### Alternative Gradio Interface
If you prefer the original Gradio block interface:
```bash
python app.py --gradio
```

---

## API Reference

### `POST /api/chat`
Submits a clinical inquiry to the Agentic CRAG workflow.
* **Request:**
  ```json
  {
    "message": "Liệt dương là gì và cách điều trị theo Y học cổ truyền?",
    "history": []
  }
  ```
* **Response:**
  ```json
  {
    "answer": "Theo Y học cổ truyền, liệt dương (Dương nuy)... [1]",
    "elapsed": 9.2,
    "sources": [
      {
        "id": 1,
        "type": "Noi Khoa YHCT",
        "source": "Noi Khoa YHCT - GS Hoang Bao Chau",
        "section": "CHỨNG TRỊ - Liệt dương",
        "preview": "Liệt dương do thấp nhiệt kinh can..."
      }
    ],
    "status": "Hoàn thành trong 9.2s | Đã truy xuất 4 minh chứng"
  }
  ```

### `GET /api/sources`
Returns the inventory of active medical textbooks and uploaded documents.

### `POST /api/sources/upload`
Uploads `.docx`, `.txt`, or `.md` files and updates the vector database.

### `POST /api/sources/rebuild`
Triggers an on-demand re-index of the ChromaDB vector store.

---

## Empirical Evaluation Benchmark

TMed-QA implements an automated **LLM-as-a-Judge** scoring harness (`evaluation.py`) based on 3 independent evaluation axes:
1. **Faithfulness (1–5)**: Evaluates strict adherence to retrieved context (Zero Hallucination).
2. **Relevance (1–5)**: Evaluates whether the answer directly addresses the clinical question.
3. **Correctness (1–5)**: Evaluates medical accuracy against verified YHCT textbooks.

### Live Benchmark Results

Measured across clinical validation queries covering Internal Medicine, Pediatrics, and ENT:

| Metric | Score | Percentage | Technical Assessment |
| :--- | :---: | :---: | :--- |
| **Faithfulness (Độ trung thực)** | **4.20 / 5.0** | **84.0%** | **Outstanding**: Strict context adherence; zero medical hallucinations. |
| **Citation Grounding Rate** | **100%** | **100%** | Every accepted response links to exact numbered citations (`[1]`, `[2]`). |
| **Answer Relevance** | **2.60 / 5.0** | **52.0%** | Moderate: Defensively refuses when evidence is incomplete. |
| **Correctness** | **1.20 / 5.0** | **24.0%** | Low: Due to strict safe-rejection thresholds preventing guessing. |
| **Response Latency (p50)** | **11.6s** | — | End-to-end LangGraph execution (Retrieval + Grading + Generation). |

Run the benchmark locally:
```bash
python evaluation.py
```

---

## Colab Quickstart

To run on cloud GPU/CPU instances, access our maintained notebooks:

<p align="left">
  <a href="https://colab.research.google.com/drive/1-Hh52dIAnHE3QWzUYlKtvuf7IR0zksHY?usp=sharing">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Colab Notebook"/>
  </a>
</p>

---

## Troubleshooting & Optimizations

* **Missing UI Updates in Browser**:
  Web browsers aggressively cache static assets. Use **`Ctrl + F5`** (Hard Reload) to immediately pull fresh layouts. The FastAPI server is configured with `Cache-Control: no-cache`.
* **Slow First Query on CPU**:
  The first query initializes `keepitreal/vietnamese-sbert` in RAM. Subsequent queries leverage the `@lru_cache` retriever for sub-second retrieval.
* **Vector Store Persistence**:
  Set `VECTOR_STORE_BACKEND=chroma` in `.env` to reuse persistent indexes on disk rather than re-embedding on process restart.

---

## License & Acknowledgements

- **LangGraph & LangChain**: Robust state graph execution framework.
- **HuggingFace & Sentence-Transformers**: Pretrained Vietnamese semantic embeddings (`keepitreal/vietnamese-sbert`).
- **Groq & Google Gemini**: Ultra-low-latency and reasoning LLM providers.
- **Medical References**: Bộ Y tế & Giáo trình Y học Cổ truyền Việt Nam.\n