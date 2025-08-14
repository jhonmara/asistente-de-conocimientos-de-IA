import os
import io
import json
from typing import List, Optional

import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Depends, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI

from app.db.models import init_db, get_session, Note, FileAsset, ChatMessage
from app.rag.chunker import chunk_text
from app.rag.store import VectorStore
from app.tools.wiki import wiki_lookup

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

engine, SessionLocal = init_db(DATABASE_URL)

app = FastAPI(title="Mini RAG Assistant Pro")

origins = [o.strip() for o in CORS_ORIGINS.split(",")] if CORS_ORIGINS else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI and vector store
client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

vs = VectorStore(embed_model=OPENAI_EMBED_MODEL, persist_dir="./data")

class ChatTurn(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatTurn]
    use_rag: bool = True
    use_wiki: bool = True

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/notes")
def list_notes(session=Depends(get_session(SessionLocal))):
    rows = session.query(Note).order_by(Note.created_at.desc()).limit(100).all()
    return [{"id": r.id, "title": r.title, "created_at": r.created_at.isoformat()} for r in rows]

@app.post("/tools/note")
def tool_note(title: str = Body(...), body: str = Body(...), session=Depends(get_session(SessionLocal))):
    n = Note(title=title, body=body)
    session.add(n)
    session.commit()
    session.refresh(n)
    return {"id": n.id, "title": n.title}

@app.post("/upload")
async def upload(file: UploadFile = File(...), session=Depends(get_session(SessionLocal))):
    data_dir = "./uploads"
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, file.filename)
    with open(path, "wb") as f:
        f.write(await file.read())

    fa = FileAsset(filename=file.filename, mime_type=file.content_type or "application/octet-stream", path=path)
    session.add(fa)
    session.commit()

    # Index file content
    text = ""
    try:
        if file.filename.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        elif file.filename.lower().endswith(".md"):
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        elif file.filename.lower().endswith(".csv"):
            df = pd.read_csv(path)
            text = df.to_csv(index=False)
        else:
            # Fallback: treat as bytes
            with open(path, "rb") as fh:
                raw = fh.read(4096)
            text = f"Archivo subido: {file.filename} ({len(raw)} bytes de muestra)"
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"No se pudo leer el archivo: {e}")

    chunks = chunk_text(text)
    vs.add_texts(chunks, metadatas=[{"source": file.filename}] * len(chunks))
    return {"ok": True, "file": file.filename, "chunks_indexed": len(chunks)}

@app.get("/search/wiki")
def search_wiki(q: str):
    return wiki_lookup(q)

@app.post("/chat")
def chat(req: ChatRequest, session=Depends(get_session(SessionLocal))):
    if client is None:
        raise HTTPException(status_code=400, detail="Falta OPENAI_API_KEY en el backend.")

    user_msg = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
    tools_used = []

    context = ""
    sources = []
    if req.use_rag and user_msg:
        docs = vs.search(user_msg, k=4)
        if docs:
            context = "\n\n".join([d["text"] for d in docs])
            sources = [d.get("metadata", {}) for d in docs]
            tools_used.append("RAG")

    if req.use_wiki and user_msg:
        try:
            wiki_res = wiki_lookup(user_msg)
            if wiki_res.get("summary"):
                context += f"\n\n[WIKIPEDIA]\n{wiki_res['summary']}"
                tools_used.append("Wikipedia")
        except Exception:
            pass

    sys_prompt = "Eres un asistente técnico y conciso. Si usas contexto externo, cita las fuentes brevemente."

    messages = [{"role": "system", "content": sys_prompt}] + [m.model_dump() for m in req.messages]
    if context:
        messages.append({"role": "system", "content": f"Contexto:\n{context}"})

    resp = client.chat.completions.create(
        model=OPENAI_CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    answer = resp.choices[0].message.content or ""

    # Persist last user+assistant turns
    session.add(ChatMessage(role="user", content=user_msg))
    session.add(ChatMessage(role="assistant", content=answer))
    session.commit()

    extra = {}
    if sources:
        extra["sources"] = sources
    if tools_used:
        answer += f"\n\n(Herramientas: {', '.join(tools_used)})"

    return {"answer": answer, **extra}
