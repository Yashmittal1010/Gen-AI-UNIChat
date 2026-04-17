"""
UNIchat Server - Python API Backend
Clara RAG + Custom Inference Engine + SQLite Database
"""

import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from clara_rag import ClaraRAG
from inference_engine import InferenceEngine
from database import save_message, log_analytics, get_session_history, get_stats, create_session

# ──────────────────────────────────────────────
# System Prompt
# ──────────────────────────────────────────────
SYSTEM_PROMPT = (
    "You are UNIchat, Manipal University Jaipur's official chatbot. "
    "You help students with queries about admissions, academics, campus life, placements, and more.\n\n"
    "Rules:\n"
    "- Be friendly, concise, and conversational - like texting a helpful friend\n"
    "- ONLY use information from the provided context. Never make things up.\n"
    "- If context doesn't cover the question, say you're not sure and provide contact info: "
    "Toll-free 18001020128, WhatsApp +91 83062 48211, Email admissions@jaipur.manipal.edu\n"
    "- Use bullet points for lists, keep responses under 150 words\n"
    "- Don't start with greetings - just answer directly\n"
    "- You can use casual language and emojis sparingly"
)

# ──────────────────────────────────────────────
# App Init
# ──────────────────────────────────────────────
app = FastAPI(title="UNIchat API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join("static", "index.html"))

rag = ClaraRAG()
engine = InferenceEngine()


# ──────────────────────────────────────────────
# Models
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    sources: list[dict] = []
    backend: str = "rag-only"
    session_id: str = ""


# ──────────────────────────────────────────────
# RAG-only formatter
# ──────────────────────────────────────────────
def format_rag_response(results: list[dict]) -> str:
    if not results:
        return (
            "Hmm, I don't have specific info on that. "
            "You can reach out directly:\n\n"
            "- Toll-free: 18001020128\n"
            "- WhatsApp: +91 83062 48211\n"
            "- Email: admissions@jaipur.manipal.edu\n"
            "- Website: jaipur.manipal.edu"
        )

    best = results[0]["entry"]
    answer = best["answer"]

    if len(results) > 1 and results[1]["score"] > 0.1:
        extra = results[1]["entry"]
        if extra["answer"] not in answer:
            answer += "\n\n" + extra["answer"]

    return answer


# ──────────────────────────────────────────────
# Chat API
# ──────────────────────────────────────────────
@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    start_time = time.time()

    # Session management
    session_id = req.session_id or create_session()

    # Save user message
    save_message(session_id, "user", req.message)

    # Clara RAG retrieval
    rag_results = rag.query(req.message, top_k=3)
    sources = [
        {"section": r["entry"]["section"], "category": r["entry"]["category"], "score": r["score"]}
        for r in rag_results
    ]

    # Generate response
    if engine.is_available:
        context = rag.get_context(req.message, top_k=3)
        full_prompt = SYSTEM_PROMPT + "\n\nContext from MUJ knowledge base:\n" + context
        response_text = engine.generate(full_prompt, req.message)

        if not response_text:
            response_text = format_rag_response(rag_results)
            backend = "rag-only"
        else:
            backend = engine.backend or "unknown"
    else:
        response_text = format_rag_response(rag_results)
        backend = "rag-only"

    # Save bot response
    save_message(session_id, "bot", response_text, backend, sources)

    # Log analytics
    elapsed_ms = int((time.time() - start_time) * 1000)
    top_section = sources[0]["section"] if sources else ""
    top_category = sources[0]["category"] if sources else ""
    top_score = sources[0]["score"] if sources else 0.0
    log_analytics(req.message, top_section, top_category, top_score, backend, elapsed_ms)

    return ChatResponse(
        response=response_text,
        sources=sources,
        backend=backend,
        session_id=session_id,
    )


# ──────────────────────────────────────────────
# Session History
# ──────────────────────────────────────────────
@app.get("/api/history/{session_id}")
async def history(session_id: str):
    return {"messages": get_session_history(session_id)}


# ──────────────────────────────────────────────
# Health & Stats
# ──────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "entries": len(rag.entries),
        "engine": engine.get_status(),
        "stats": get_stats(),
    }
