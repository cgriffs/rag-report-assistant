"""RAG Report Assistant API.

Endpoints:
- GET  /health     service status and generation mode
- GET  /documents  indexed documents with chunk counts
- POST /documents  upload a PDF or Markdown document and index it
- POST /ask        ask a question, get an answer with citations

On startup the sample documents in backend/sample_docs are indexed so the
demo works immediately.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .chunking import chunk_document
from .config import Settings, load_settings
from .ingest import extract_text
from .qa import compose_extractive_answer, compose_llm_answer
from .retrieval import DocumentIndex

SAMPLE_DOCS_DIR = Path(__file__).resolve().parent.parent / "sample_docs"


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int | None = None


class Citation(BaseModel):
    ref: int
    document: str
    chunk_id: str
    score: float
    excerpt: str


class AskResponse(BaseModel):
    answer: str
    mode: str
    citations: list[Citation]


class DocumentInfo(BaseModel):
    name: str
    chunks: int


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    index = DocumentIndex()
    documents: dict[str, int] = {}

    def add_document(name: str, text: str) -> int:
        chunks = chunk_document(
            name, text, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap
        )
        if not chunks:
            raise ValueError(f"No readable text found in '{name}'.")
        index.add(chunks)
        documents[name] = documents.get(name, 0) + len(chunks)
        return len(chunks)

    if SAMPLE_DOCS_DIR.is_dir():
        for path in sorted(SAMPLE_DOCS_DIR.glob("*.md")):
            add_document(path.name, path.read_text(encoding="utf-8"))

    app = FastAPI(
        title="RAG Report Assistant",
        description=(
            "Ask plain language questions of business documents and get "
            "answers with citations back to the source passages."
        ),
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.index = index

    @app.get("/health")
    def health() -> dict:
        return {
            "status": "ok",
            "mode": "azure-openai" if settings.llm_enabled else "extractive-demo",
            "documents": len(documents),
            "chunks": len(index.chunks),
        }

    @app.get("/documents", response_model=list[DocumentInfo])
    def list_documents() -> list[DocumentInfo]:
        return [
            DocumentInfo(name=name, chunks=count)
            for name, count in sorted(documents.items())
        ]

    @app.post("/documents", response_model=DocumentInfo, status_code=201)
    async def upload_document(file: UploadFile = File(...)) -> DocumentInfo:
        data = await file.read()
        try:
            text = extract_text(file.filename or "upload", data)
            count = add_document(file.filename or "upload", text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DocumentInfo(name=file.filename or "upload", chunks=count)

    @app.post("/ask", response_model=AskResponse)
    def ask(request: AskRequest) -> AskResponse:
        top_k = request.top_k or settings.default_top_k
        results = index.search(request.question, top_k=top_k)
        citations = [
            Citation(
                ref=rank,
                document=item.chunk.document_name,
                chunk_id=item.chunk.chunk_id,
                score=round(item.score, 4),
                excerpt=item.chunk.text[:280],
            )
            for rank, item in enumerate(results, start=1)
        ]
        answer = None
        mode = "extractive-demo"
        if settings.llm_enabled:
            answer = compose_llm_answer(request.question, results, settings)
            if answer:
                mode = "azure-openai"
        if answer is None:
            answer = compose_extractive_answer(request.question, results)
        return AskResponse(answer=answer, mode=mode, citations=citations)

    return app


app = create_app()
