/**
 * Purpose: Cited document Q&A UI for grounded answers from processed PDFs.
 * Interactions: Uses lib/api.ts to call POST /rag/query and displays answers
 * with supporting citation cards.
 */
"use client";

import { useEffect, useMemo, useState } from "react";

import type { Document, RagCitation, RagQueryResponse } from "@/lib/api";
import { queryRag } from "@/lib/api";

type CitedAnswerProps = {
  documents: Document[];
};

export function CitedAnswer({ documents }: CitedAnswerProps) {
  const processedDocuments = useMemo(
    () => documents.filter((document) => document.status === "processed"),
    [documents],
  );

  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [response, setResponse] = useState<RagQueryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasAsked, setHasAsked] = useState(false);

  useEffect(() => {
    if (
      documentId &&
      !processedDocuments.some((document) => document.id === documentId)
    ) {
      setDocumentId("");
    }
  }, [documentId, processedDocuments]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a question about your documents.");
      return;
    }

    setLoading(true);
    setError(null);

    const { data, error: queryError } = await queryRag({
      query: trimmedQuery,
      document_id: documentId || undefined,
    });

    setLoading(false);
    setHasAsked(true);

    if (queryError || !data) {
      setResponse(null);
      setError(queryError ?? "Answer request failed.");
      return;
    }

    setResponse(data);
  }

  return (
    <section className="search-panel">
      <div className="section-header">
        <h2>Ask Cited Questions</h2>
        <span className="meta-text">
          Available: {processedDocuments.length} processed document
          {processedDocuments.length === 1 ? "" : "s"}
        </span>
      </div>

      <p className="helper-text">
        Ask questions about processed aviation PDFs. Answers are grounded in
        retrieved source excerpts and include citations you can inspect.
      </p>

      <form className="search-form" onSubmit={handleSubmit}>
        <label className="field-label" htmlFor="rag-query">
          Question
        </label>
        <input
          id="rag-query"
          className="text-input"
          type="text"
          value={query}
          placeholder="What were the contributing factors in this report?"
          onChange={(event) => setQuery(event.target.value)}
        />

        <label className="field-label" htmlFor="rag-document">
          Document scope
        </label>
        <select
          id="rag-document"
          className="select-input"
          value={documentId}
          onChange={(event) => setDocumentId(event.target.value)}
        >
          <option value="">All processed documents</option>
          {processedDocuments.map((document) => (
            <option key={document.id} value={document.id}>
              {document.original_filename}
            </option>
          ))}
        </select>

        <button type="submit" className="button primary" disabled={loading}>
          {loading ? "Generating answer..." : "Ask question"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {hasAsked && !error && response?.insufficient_evidence && (
        <div className="empty-state search-empty-state insufficient-evidence-state">
          <p>Insufficient evidence in retrieved sources.</p>
          <p className="helper-text">{response.answer}</p>
        </div>
      )}

      {response && !response.insufficient_evidence && (
        <div className="rag-answer-panel">
          <p className="helper-text">
            Answer for &quot;{response.query}&quot; using {response.used_chunk_count}{" "}
            source excerpt{response.used_chunk_count === 1 ? "" : "s"}
          </p>
          <div className="rag-answer-text">{response.answer}</div>

          {response.citations.length > 0 && (
            <div className="rag-citations">
              <h3 className="rag-citations-heading">Sources</h3>
              <ul className="search-results-list">
                {response.citations.map((citation: RagCitation) => (
                  <li key={citation.chunk_id} className="search-result-card rag-citation-card">
                    <div className="search-result-meta">
                      <span className="rag-source-badge">{citation.source_id}</span>
                      <span>{citation.document_name}</span>
                      <span>
                        {citation.page_number != null
                          ? `Page ${citation.page_number}`
                          : "Page unknown"}
                      </span>
                      <span>Chunk {citation.chunk_index + 1}</span>
                      <span>
                        Similarity {(citation.similarity * 100).toFixed(1)}%
                      </span>
                    </div>
                    {citation.section_title && (
                      <p className="search-result-section">{citation.section_title}</p>
                    )}
                    <p>{citation.text}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
