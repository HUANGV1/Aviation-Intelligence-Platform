"""Document RAG tool backed by the existing cited answer pipeline."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.schemas.rag import RagCitation, RagQueryResponse
from app.services.rag_answer_service import RagAnswerError, answer_document_question
from app.tools.base import ToolContext, ToolDefinition, ToolResult


DOCUMENT_SEARCH_TOOL_NAME = "document_search"

DOCUMENT_SEARCH_DEFINITION = ToolDefinition(
    name=DOCUMENT_SEARCH_TOOL_NAME,
    description=(
        "Search uploaded aviation PDF documents and return a cited answer grounded "
        "in retrieved source excerpts. Use when the user asks about document content, "
        "accident reports, FAA guidance, procedures, or anything that requires evidence "
        "from uploaded or processed documents."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The question to answer using document retrieval.",
            },
            "document_id": {
                "type": "string",
                "description": (
                    "Optional UUID of a single document to scope retrieval. "
                    "Omit to search all processed documents."
                ),
            },
            "top_k": {
                "type": "integer",
                "description": "Optional number of chunks to retrieve (1-10).",
            },
        },
        "required": ["query"],
    },
)


def _serialize_citation(citation: RagCitation) -> dict[str, Any]:
    return citation.model_dump(mode="json")


def _serialize_rag_response(response: RagQueryResponse) -> dict[str, Any]:
    return {
        "query": response.query,
        "answer": response.answer,
        "citations": [_serialize_citation(c) for c in response.citations],
        "insufficient_evidence": response.insufficient_evidence,
        "used_chunk_count": response.used_chunk_count,
    }


def _build_summary(response: RagQueryResponse) -> str:
    if response.insufficient_evidence:
        return "No sufficient document evidence found."
    citation_count = len(response.citations)
    chunk_label = "chunk" if response.used_chunk_count == 1 else "chunks"
    source_label = "source" if citation_count == 1 else "sources"
    return (
        f"Searched documents using {response.used_chunk_count} {chunk_label} "
        f"and returned {citation_count} cited {source_label}."
    )


class DocumentSearchTool:
    """Agent tool that wraps answer_document_question without weakening citations."""

    definition = DOCUMENT_SEARCH_DEFINITION

    def execute(self, arguments: dict[str, Any], context: ToolContext) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="Document search failed.",
                error="query is required.",
            )

        document_id: UUID | None = context.document_id
        raw_document_id = arguments.get("document_id")
        if raw_document_id:
            try:
                document_id = UUID(str(raw_document_id))
            except ValueError:
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    summary="Document search failed.",
                    error="document_id must be a valid UUID.",
                )

        top_k = arguments.get("top_k")
        parsed_top_k: int | None = None
        if top_k is not None:
            try:
                parsed_top_k = int(top_k)
            except (TypeError, ValueError):
                return ToolResult(
                    tool_name=self.definition.name,
                    success=False,
                    summary="Document search failed.",
                    error="top_k must be an integer between 1 and 10.",
                )

        try:
            response = answer_document_question(
                query,
                document_id=document_id,
                top_k=parsed_top_k,
                persist=False,
            )
        except RagAnswerError as exc:
            return ToolResult(
                tool_name=self.definition.name,
                success=False,
                summary="Document search failed.",
                error=str(exc),
            )

        return ToolResult(
            tool_name=self.definition.name,
            success=True,
            summary=_build_summary(response),
            data=_serialize_rag_response(response),
        )
