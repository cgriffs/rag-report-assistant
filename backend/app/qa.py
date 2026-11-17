"""Answer composition.

Two modes:

- Extractive (default, no API key): the answer is composed from the most
  relevant sentences of the retrieved chunks, and every sentence carries a
  citation marker such as [1] that maps to the citations list.
- Azure OpenAI (when configured): the chat model writes the answer from the
  retrieved context only, with the same citation markers. Any failure falls
  back to extractive mode so the demo never hard-fails.
"""

from __future__ import annotations

import re

import httpx

from .config import Settings
from .retrieval import ScoredChunk, tokenize

_SENTENCE_RE = re.compile(r"[^.!?]+[.!?]")


def _sentences(text: str) -> list[str]:
    # Drop markdown headings and sample-data disclaimers so answers are
    # composed of body sentences only.
    lines = [
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    ]
    cleaned = " ".join(lines)
    found = [s.strip() for s in _SENTENCE_RE.findall(cleaned)]
    return [
        s for s in found if len(s) > 25 and not s.startswith("Note:")
    ]


def compose_extractive_answer(
    question: str, results: list[ScoredChunk], max_sentences: int = 4
) -> str:
    """Build a cited answer from retrieved passages."""
    if not results:
        return (
            "I could not find anything in the indexed documents that answers "
            "that question. Try rephrasing it, or add the document that "
            "covers the topic."
        )
    question_terms = set(tokenize(question))
    candidates: list[tuple[float, int, str]] = []
    for rank, item in enumerate(results, start=1):
        for sentence in _sentences(item.chunk.text):
            overlap = len(question_terms & set(tokenize(sentence)))
            candidates.append((item.score + 0.05 * overlap, rank, sentence))
    candidates.sort(key=lambda entry: entry[0], reverse=True)

    picked: list[tuple[int, str]] = []
    seen: set[str] = set()
    for _, rank, sentence in candidates:
        if sentence in seen:
            continue
        seen.add(sentence)
        picked.append((rank, sentence))
        if len(picked) >= max_sentences:
            break
    picked.sort(key=lambda entry: entry[0])
    return " ".join(f"{sentence} [{rank}]" for rank, sentence in picked)


def compose_llm_answer(
    question: str, results: list[ScoredChunk], settings: Settings
) -> str | None:
    """Ask Azure OpenAI to answer from the retrieved context, or return None."""
    context = "\n\n".join(
        f"[{rank}] Source: {item.chunk.document_name}, {item.chunk.chunk_id}\n"
        f"{item.chunk.text}"
        for rank, item in enumerate(results, start=1)
    )
    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You answer questions about business documents. Use only "
                    "the provided context. Cite every claim with the bracket "
                    "number of its source, for example [1]. If the context "
                    "does not answer the question, say so plainly."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        "temperature": 0.2,
    }
    url = (
        f"{settings.azure_openai_endpoint.rstrip('/')}/openai/deployments/"
        f"{settings.azure_openai_chat_deployment}/chat/completions"
        f"?api-version={settings.azure_openai_api_version}"
    )
    try:
        response = httpx.post(
            url,
            json=payload,
            headers={"api-key": settings.azure_openai_api_key or ""},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
