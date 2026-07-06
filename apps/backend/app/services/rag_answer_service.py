"""Cited RAG answer orchestration over retrieved document chunks.

Purpose: Retrieves relevant chunks, builds a grounded prompt, calls the LLM
service, validates citations, and returns structured cited answers.
Interactions: Uses search_service.py, llm_service.py, and rag_query_repository.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.config import settings
from app.schemas.rag import RagCitation, RagQueryResponse
from app.schemas.search import SearchResultItem
from app.services.llm_service import LLMError, LLMQuotaError, LLMRequest, generate_json
from app.services.rag_query_repository import insert_rag_query
from app.services.search_service import SearchError, search_document_chunks

RAG_PROMPT_SCHEMA_VERSION = "rag-answer-v1"

RAG_SYSTEM_INSTRUCTIONS = """You are an aviation document intelligence assistant.
Answer questions using ONLY the supplied source excerpts from uploaded aviation PDFs.

Rules:
- Provide informational answers grounded in the sources. Do not give operational flight advice.
- Cite every factual claim using source IDs like [S1], [S2] inline in the answer text.
- If the sources do not contain enough evidence to answer the question, set insufficient_evidence to true and provide a brief explanation in answer.
- Keep answers concise, clear, and aviation-focused. 
- Return ONLY valid JSON with no markdown fences.

Required JSON shape:
{
  "answer": "string with inline [S1] citations",
  "citations": ["S1", "S2"],
  "insufficient_evidence": false
}"""


class RagAnswerError(Exception):
    """Raised when cited RAG answering cannot be completed."""


@dataclass(frozen=True)
class _RagSource:
    source_id: str
    chunk: SearchResultItem


INSUFFICIENT_EVIDENCE_MESSAGE = (
    "The retrieved document excerpts do not contain enough evidence to answer "
    "this question confidently."
)
RAG_LLM_MAX_OUTPUT_TOKENS = 2048


def _resolve_top_k(top_k: int | None) -> int:
    if top_k is not None:
        return min(top_k, settings.search_max_top_k)
    return min(settings.rag_answer_top_k, settings.search_max_top_k)


def _filter_results(results: list[SearchResultItem]) -> list[SearchResultItem]:
    threshold = settings.rag_min_similarity
    return [result for result in results if result.similarity >= threshold]


def _build_sources(results: list[SearchResultItem]) -> list[_RagSource]:
    return [
        _RagSource(source_id=f"S{index}", chunk=chunk)
        for index, chunk in enumerate(results, start=1)
    ]


def _truncate_source_text(text: str) -> str:
    normalized = text.strip()
    max_chars = settings.rag_max_source_text_chars
    if max_chars <= 0 or len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars].rstrip()}..."


def _format_source_block(sources: list[_RagSource]) -> str:
    lines = ["Sources:"]
    for source in sources:
        chunk = source.chunk
        page = chunk.page_number if chunk.page_number is not None else "unknown"
        section = chunk.section_title or "none"
        text = _truncate_source_text(chunk.text)
        lines.extend(
            [
                f"[{source.source_id}]",
                f"chunk_id: {chunk.chunk_id}",
                f"document: {chunk.document_name}",
                f"page: {page}",
                f"section: {section}",
                f"text: {text}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def build_rag_prompt(question: str, sources: list[_RagSource]) -> str:
    return (
        f"Question: {question.strip()}\n\n"
        f"{_format_source_block(sources)}"
    )


def _filter_citations(
    sources: list[_RagSource],
    citation_ids: list[str],
) -> list[RagCitation]:
    source_map = {source.source_id: source for source in sources}
    citations: list[RagCitation] = []
    seen: set[str] = set()

    for citation_id in citation_ids:
        if citation_id in seen:
            continue
        source = source_map.get(citation_id)
        if source is None:
            continue
        seen.add(citation_id)
        citations.append(
            RagCitation(
                source_id=source.source_id,
                chunk_id=source.chunk.chunk_id,
                document_id=source.chunk.document_id,
                document_name=source.chunk.document_name,
                chunk_index=source.chunk.chunk_index,
                text=source.chunk.text,
                page_number=source.chunk.page_number,
                section_title=source.chunk.section_title,
                similarity=source.chunk.similarity,
            )
        )

    return citations


def _insufficient_response(query: str, *, answer: str | None = None) -> RagQueryResponse:
    return RagQueryResponse(
        query=query,
        answer=answer or INSUFFICIENT_EVIDENCE_MESSAGE,
        citations=[],
        insufficient_evidence=True,
        used_chunk_count=0,
    )


def answer_document_question(
    query: str,
    *,
    document_id: UUID | None = None,
    top_k: int | None = None,
    persist: bool = True,
) -> RagQueryResponse:
    normalized_query = query.strip()
    if not normalized_query:
        raise RagAnswerError("Query must not be empty.")

    limit = _resolve_top_k(top_k)

    try:
        search_response = search_document_chunks(
            normalized_query,
            document_id=document_id,
            top_k=limit,
        )
    except SearchError as exc:
        raise RagAnswerError(str(exc)) from exc

    filtered_results = _filter_results(search_response.results)
    if not filtered_results:
        response = _insufficient_response(normalized_query)
        if persist:
            insert_rag_query(
                query=normalized_query,
                answer=response.answer,
                document_id=document_id,
                retrieved_chunk_ids=[],
            )
        return response

    sources = _build_sources(filtered_results)
    user_content = build_rag_prompt(normalized_query, sources)

    try:
        llm_payload = generate_json(
            LLMRequest(
                system_instructions=RAG_SYSTEM_INSTRUCTIONS,
                user_content=user_content,
                schema_version=RAG_PROMPT_SCHEMA_VERSION,
                cache_namespace="rag-answer",
                max_output_tokens=max(
                    settings.llm_max_output_tokens,
                    RAG_LLM_MAX_OUTPUT_TOKENS,
                ),
            )
        )
    except LLMQuotaError:
        raise
    except LLMError as exc:
        raise RagAnswerError(str(exc)) from exc

    insufficient = bool(llm_payload.get("insufficient_evidence", False))
    answer_text = str(llm_payload.get("answer", "")).strip()
    raw_citations = llm_payload.get("citations", [])
    citation_ids = [
        str(item).strip()
        for item in raw_citations
        if isinstance(item, (str, int)) and str(item).strip()
    ]

    if insufficient or not answer_text:
        response = _insufficient_response(
            normalized_query,
            answer=answer_text or None,
        )
        response = response.model_copy(update={"used_chunk_count": len(sources)})
        if persist:
            insert_rag_query(
                query=normalized_query,
                answer=response.answer,
                document_id=document_id,
                retrieved_chunk_ids=[source.chunk.chunk_id for source in sources],
            )
        return response

    citations = _filter_citations(sources, citation_ids)
    if not citations:
        response = _insufficient_response(normalized_query)
        response = response.model_copy(update={"used_chunk_count": len(sources)})
        if persist:
            insert_rag_query(
                query=normalized_query,
                answer=response.answer,
                document_id=document_id,
                retrieved_chunk_ids=[source.chunk.chunk_id for source in sources],
            )
        return response

    response = RagQueryResponse(
        query=normalized_query,
        answer=answer_text,
        citations=citations,
        insufficient_evidence=False,
        used_chunk_count=len(sources),
    )

    if persist:
        insert_rag_query(
            query=normalized_query,
            answer=response.answer,
            document_id=document_id,
            retrieved_chunk_ids=[citation.chunk_id for citation in citations],
        )

    return response
