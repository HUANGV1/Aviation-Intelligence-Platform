/**
 * Purpose: Semantic search UI for querying embedded document chunks.
 * Interactions: Uses lib/api.ts to call POST /rag/search and displays source snippets.
 */
"use client";

import { useEffect, useMemo, useState } from "react";

import type { Document, SearchResult } from "@/lib/api";
import { searchChunks } from "@/lib/api";

type SemanticSearchProps = {
  documents: Document[];
};

export function SemanticSearch({ documents }: SemanticSearchProps) {
  const processedDocuments = useMemo(
    () => documents.filter((document) => document.status === "processed"),
    [documents],
  );

  const [query, setQuery] = useState("");
  const [documentId, setDocumentId] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [resultQuery, setResultQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    if (
      documentId &&
      !processedDocuments.some((document) => document.id === documentId)
    ) {
      setDocumentId("");
    }
  }, [documentId, processedDocuments]);

  async function handleSearch(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      setError("Enter a search query.");
      return;
    }

    setLoading(true);
    setError(null);

    const { data, error: searchError } = await searchChunks({
      query: trimmedQuery,
      document_id: documentId || undefined,
    });

    setLoading(false);
    setHasSearched(true);

    if (searchError || !data) {
      setResults([]);
      setResultQuery("");
      setError(searchError ?? "Search failed.");
      return;
    }

    setResults(data.results);
    setResultQuery(data.query);
  }

  return (
    <section className="search-panel">
      <div className="section-header">
        <h2>Semantic Search</h2>
        <span className="meta-text">
          Available: {processedDocuments.length} processed document
          {processedDocuments.length === 1 ? "" : "s"}
        </span>
      </div>

      <p className="helper-text">
        Search processed aviation PDFs using natural language. Results include
        source snippets with document name and page number when available.
      </p>

      <form className="search-form" onSubmit={handleSearch}>
        <label className="field-label" htmlFor="search-query">
          Query
        </label>
        <input
          id="search-query"
          className="text-input"
          type="text"
          value={query}
          placeholder="What operational risks are mentioned?"
          onChange={(event) => setQuery(event.target.value)}
        />

        <label className="field-label" htmlFor="search-document">
          Document scope
        </label>
        <select
          id="search-document"
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
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      {hasSearched && !error && results.length === 0 && (
        <div className="empty-state search-empty-state">
          <p>No matching chunks found.</p>
          <p className="helper-text">
            Try a broader question or process another aviation PDF first.
          </p>
        </div>
      )}

      {results.length > 0 && (
        <div className="search-results">
          <p className="helper-text">
            Showing {results.length} result{results.length === 1 ? "" : "s"} for
            &quot;{resultQuery}&quot;
          </p>
          <ul className="search-results-list">
            {results.map((result) => (
              <li key={result.chunk_id} className="search-result-card">
                <div className="search-result-meta">
                  <span>{result.document_name}</span>
                  <span>
                    {result.page_number != null
                      ? `Page ${result.page_number}`
                      : "Page unknown"}
                  </span>
                  <span>Chunk {result.chunk_index + 1}</span>
                  <span>Similarity {(result.similarity * 100).toFixed(1)}%</span>
                </div>
                {result.section_title && (
                  <p className="search-result-section">{result.section_title}</p>
                )}
                <p>{result.text}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
