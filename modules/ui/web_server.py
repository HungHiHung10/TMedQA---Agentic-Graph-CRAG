import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from modules.ingestion.sources import (
    SUPPORTED_USER_SOURCE_EXTS,
    deleted_sources,
    list_sources,
    restore_source,
    safe_filename,
    uploaded_names,
)
from modules.rag.service import answer_question as run_question, clear_retriever, rebuild_store
from modules.settings import (
    BASE_DIR,
    EMBEDDING_MODEL_NAME,
    LLM_MODEL,
    LLM_PROVIDER,
    RETRIEVAL_K,
    USER_SOURCES_DIR,
)
from modules.ui.formatting import (
    finalize_answer,
    format_retrieved_sources,
    preview,
    section_label,
    source_label,
    source_type,
)
from modules.ui.handlers import delete_source as handler_delete_source

STATIC_DIR = BASE_DIR / "static"
LOGO_PATH = BASE_DIR / "logo" / "TMed-QA.png"

app = FastAPI(title="TMed-QA API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, str]]] = None


class DeleteSourceRequest(BaseModel):
    filename: str


@app.get("/logo/TMed-QA.png")
async def get_brand_logo():
    if LOGO_PATH.exists():
        return FileResponse(LOGO_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.get("/api/system/info")
async def get_system_info():
    return {
        "title": "TMed-QA",
        "description": "Agentic Graph Correctness RAG (CRAG) Medical Assistant",
        "embedding_model": EMBEDDING_MODEL_NAME,
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL or "Auto",
        "retrieval_k": RETRIEVAL_K,
        "status": "online",
    }


@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    question = (req.message or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Vui lòng nhập câu hỏi.")

    try:
        result, elapsed = run_question(question)
        documents = result.get("documents", [])
        final_answer = finalize_answer(question, result.get("generation", ""), documents)

        formatted_docs = []
        for index, doc in enumerate(documents, start=1):
            metadata = getattr(doc, "metadata", {}) or {}
            content = getattr(doc, "page_content", str(doc)) or ""
            formatted_docs.append({
                "id": index,
                "type": source_type(metadata),
                "source": source_label(metadata),
                "section": section_label(metadata),
                "preview": preview(content, limit=280),
                "content": content,
                "chars": len(content),
            })

        return {
            "answer": final_answer,
            "raw_generation": result.get("generation", ""),
            "elapsed": round(elapsed, 2),
            "sources": formatted_docs,
            "status": f"Hoàn thành trong {elapsed:.1f}s | Đã truy xuất {len(documents)} minh chứng",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý câu hỏi: {exc}")


@app.get("/api/sources")
async def api_get_sources():
    try:
        sources_list = list_sources()
        uploaded_files = uploaded_names()
        return {
            "sources": sources_list,
            "uploaded": uploaded_files,
            "count": len(sources_list),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy danh sách nguồn: {exc}")


@app.post("/api/sources/upload")
async def api_upload_sources(files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Không có tệp nào được chọn.")

    USER_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    skipped = []

    for file in files:
        filename = file.filename or ""
        suffix = Path(filename).suffix.lower()
        if suffix not in SUPPORTED_USER_SOURCE_EXTS:
            skipped.append(filename)
            continue

        clean_name = safe_filename(filename)
        target = USER_SOURCES_DIR / clean_name
        counter = 1
        while target.exists() and target.name not in deleted_sources():
            target = USER_SOURCES_DIR / f"{target.stem}_{counter}{target.suffix}"
            counter += 1

        with open(target, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        restore_source(target.name)
        saved.append(target.name)

    clear_retriever()

    message_parts = []
    if saved:
        message_parts.append(f"Đã tải lên {len(saved)} tệp: {', '.join(saved)}.")
        message_parts.append("Bộ nhớ đệm retriever đã được xóa sạch. Hệ thống sẵn sàng tra cứu với dữ liệu mới.")
    if skipped:
        message_parts.append(f"Bỏ qua tệp không hỗ trợ: {', '.join(skipped)}.")

    return {
        "saved": saved,
        "skipped": skipped,
        "message": " ".join(message_parts) if message_parts else "Không có tệp hợp lệ nào được tải lên.",
        "sources": list_sources(),
        "uploaded": uploaded_names(),
    }


@app.post("/api/sources/delete")
async def api_delete_source(req: DeleteSourceRequest):
    filename = (req.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="Tên tệp không được để trống.")

    rows, status_msg, choices = handler_delete_source(filename)
    return {
        "status": status_msg,
        "sources": list_sources(),
        "uploaded": uploaded_names(),
    }


@app.post("/api/sources/rebuild")
async def api_rebuild_store():
    try:
        msg = rebuild_store()
        return {
            "status": "success",
            "message": msg,
            "sources": list_sources(),
            "uploaded": uploaded_names(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Tái lập thất bại: {exc}")


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/style.css")
async def get_style_css():
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    root_css = BASE_DIR / "style.css"
    if root_css.exists():
        return FileResponse(root_css, media_type="text/css", headers=headers)
    css_file = STATIC_DIR / "style.css"
    if css_file.exists():
        return FileResponse(css_file, media_type="text/css", headers=headers)
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js")
async def get_app_js():
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    root_js = BASE_DIR / "app.js"
    if root_js.exists():
        return FileResponse(root_js, media_type="application/javascript", headers=headers)
    js_file = STATIC_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript", headers=headers)
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/favicon.ico")
async def get_favicon():
    if LOGO_PATH.exists():
        return FileResponse(LOGO_PATH, media_type="image/png")
    raise HTTPException(status_code=404, detail="favicon not found")


@app.get("/")
async def root_index():
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    root_index = BASE_DIR / "index.html"
    if root_index.exists():
        return FileResponse(root_index, headers=headers)
    static_index = STATIC_DIR / "index.html"
    if static_index.exists():
        return FileResponse(static_index, headers=headers)
    return JSONResponse({"message": "TMed-QA API Server Running. index.html not found."})
