"""FastAPI application exposing semantic search and answering over the TUIR."""
from __future__ import annotations

import logging
import os
from threading import Lock, Thread
from typing import Dict, Iterable, List, Optional

import faiss
import torch
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

from . import history
from .ingest import (
    INDEX_PATH,
    METADATA_PATH,
    ensure_document,
    ingest_document,
    load_index,
)

LOGGER = logging.getLogger(__name__)

app = FastAPI(title="TUIR Extractor", version="1.0.0")

INDEX_LOCK = Lock()
INDEX: Optional[faiss.IndexFlatIP] = None
METADATA: List[Dict[str, object]] = []
EMBEDDER = None

MODEL_LOCK = Lock()
MODEL = None
TOKENIZER = None

DEFAULT_TOP_K = 5
DEFAULT_MAX_NEW_TOKENS = int(os.getenv("TUIR_MAX_NEW_TOKENS", "512"))
DEFAULT_TEMPERATURE = float(os.getenv("TUIR_TEMPERATURE", "0.2"))
MODEL_NAME = os.getenv("TUIR_LLM_MODEL", "tiiuae/falcon-7b-instruct")
LOCAL_ONLY = os.getenv("TUIR_LOCAL_ONLY", "1") != "0"


class QueryRequest(BaseModel):
    question: str = Field(..., description="Question posed by the user")
    top_k: int = Field(DEFAULT_TOP_K, ge=1, le=20, description="Number of sections to retrieve")


class SectionResult(BaseModel):
    id: int
    text: str
    score: float


class QueryResponse(BaseModel):
    question: str
    sections: List[SectionResult]


class AnswerRequest(QueryRequest):
    session_id: str = Field(..., description="Conversation session identifier")
    max_new_tokens: int = Field(DEFAULT_MAX_NEW_TOKENS, ge=32, le=2048)
    temperature: float = Field(DEFAULT_TEMPERATURE, ge=0.0, le=1.0)


class HistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]


def _lazy_load_index() -> None:
    global INDEX, METADATA, EMBEDDER
    with INDEX_LOCK:
        if INDEX is not None and METADATA and EMBEDDER is not None:
            return
        if not INDEX_PATH.exists() or not METADATA_PATH.exists():
            LOGGER.info("Vector index missing – running ingestion pipeline")
            ingest_document()
        INDEX, METADATA, EMBEDDER = load_index()
        LOGGER.info("Loaded FAISS index with %d vectors", INDEX.ntotal)


def _load_llm():
    global MODEL, TOKENIZER
    with MODEL_LOCK:
        if MODEL is not None and TOKENIZER is not None:
            return MODEL, TOKENIZER
        LOGGER.info("Loading language model: %s", MODEL_NAME)
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                MODEL_NAME, local_files_only=LOCAL_ONLY, trust_remote_code=True
            )
            model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
                device_map="auto" if torch.cuda.is_available() else None,
                local_files_only=LOCAL_ONLY,
                trust_remote_code=True,
            )
        except Exception as exc:  # pragma: no cover - runtime failure surface
            LOGGER.exception("Failed to load language model")
            raise RuntimeError(
                "Unable to load local language model. Ensure weights are available in the cache."
            ) from exc
        TOKENIZER = tokenizer
        MODEL = model
        return MODEL, TOKENIZER


def _retrieve_sections(question: str, top_k: int) -> List[SectionResult]:
    _lazy_load_index()
    assert INDEX is not None and METADATA and EMBEDDER is not None

    query_vector = EMBEDDER.encode([question])
    faiss.normalize_L2(query_vector)
    distances, indices = INDEX.search(query_vector, top_k)
    results: List[SectionResult] = []
    for score, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        metadata = METADATA[idx]
        section_id = int(metadata["id"]) if "id" in metadata else int(idx)
        text = str(metadata.get("text", ""))
        results.append(SectionResult(id=section_id, text=text, score=float(score)))
    return results


def _format_prompt(
    question: str, sections: Iterable[SectionResult], history_messages: List[Dict[str, str]]
) -> str:
    context_blocks = []
    for item in sections:
        context_blocks.append(f"[Section {item.id}]\n{item.text}")
    context = "\n\n".join(context_blocks)

    history_lines = []
    for message in history_messages:
        speaker = message.get("role", "user").capitalize()
        history_lines.append(f"{speaker}: {message.get('content', '')}")
    history_text = "\n".join(history_lines)

    prompt = (
        "You are a helpful assistant that answers questions about the Italian TUIR (Testo Unico delle Imposte sui Redditi).\n"
        "Use only the provided context sections to construct your answer. If the answer is not present, say you do not know.\n"
        "Context:\n"
        f"{context}\n\n"
        "Conversation so far:\n"
        f"{history_text}\n\n"
        f"User: {question}\nAssistant:"
    )
    return prompt


def _stream_response(prompt: str, *, max_new_tokens: int, temperature: float):
    model, tokenizer = _load_llm()
    device = model.device
    inputs = tokenizer(prompt, return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}
    streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

    generation_kwargs = dict(
        **inputs,
        streamer=streamer,
        max_new_tokens=max_new_tokens,
        do_sample=temperature > 0,
        temperature=temperature if temperature > 0 else 1.0,
        top_p=0.95,
    )

    thread = Thread(target=model.generate, kwargs=generation_kwargs)
    thread.start()

    try:
        for token in streamer:
            yield token
    finally:
        thread.join()


@app.on_event("startup")
def _startup_event() -> None:  # pragma: no cover - FastAPI startup
    logging.basicConfig(level=logging.INFO)
    ensure_document()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        sections = _retrieve_sections(request.question, request.top_k)
    except Exception as exc:  # pragma: no cover - runtime error propagation
        LOGGER.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return QueryResponse(question=request.question, sections=sections)


@app.get("/history/{session_id}", response_model=HistoryResponse)
def get_history_endpoint(session_id: str) -> HistoryResponse:
    messages = history.get_history(session_id)
    return HistoryResponse(session_id=session_id, messages=messages)


@app.delete("/history/{session_id}")
def clear_history_endpoint(session_id: str) -> JSONResponse:
    history.clear_history(session_id)
    return JSONResponse({"status": "cleared", "session_id": session_id})


@app.post("/answer")
def answer(request: AnswerRequest):
    try:
        sections = _retrieve_sections(request.question, request.top_k)
    except Exception as exc:  # pragma: no cover
        LOGGER.exception("Retrieval failed")
        raise HTTPException(status_code=500, detail="Failed to retrieve relevant sections") from exc

    try:
        _load_llm()
    except RuntimeError as exc:  # pragma: no cover - surface configuration errors
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    history.append_message(request.session_id, "user", request.question)
    prior_messages = history.get_history(request.session_id)[:-1]
    prompt = _format_prompt(request.question, sections, prior_messages)

    def response_generator():
        answer_text_parts: List[str] = []
        try:
            for token in _stream_response(
                prompt,
                max_new_tokens=request.max_new_tokens,
                temperature=request.temperature,
            ):
                answer_text_parts.append(token)
                yield token
        finally:
            final_answer = "".join(answer_text_parts).strip()
            history.append_message(request.session_id, "assistant", final_answer)

    return StreamingResponse(response_generator(), media_type="text/plain")
