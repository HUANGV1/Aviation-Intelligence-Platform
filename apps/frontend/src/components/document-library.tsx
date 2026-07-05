/**
 * Purpose: Displays the document library with view, delete, and inline PDF preview.
 * Interactions: Receives document data from page.tsx. Uses lib/api.ts for file URLs
 * and delete requests; removes deleted rows locally after successful deletion.
 */
"use client";

import { Fragment, useEffect, useState } from "react";

import type { Document } from "@/lib/api";
import {
  deleteDocument,
  formatTimestamp,
  getDocumentFileUrl,
} from "@/lib/api";

type DocumentLibraryProps = {
  documents: Document[];
  error: string | null;
};

type SelectedDocument = {
  id: string;
  original_filename: string;
};

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const className =
    normalized === "uploaded" || normalized === "processed"
      ? "badge healthy"
      : normalized === "processing"
        ? "badge loading"
        : normalized === "failed"
          ? "badge error"
          : "badge";

  return <span className={className}>{status}</span>;
}

export function DocumentLibrary({ documents, error }: DocumentLibraryProps) {
  const [libraryDocuments, setLibraryDocuments] = useState(documents);
  const [selected, setSelected] = useState<SelectedDocument | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const documentCount = libraryDocuments.length;

  useEffect(() => {
    setLibraryDocuments(documents);
  }, [documents]);

  async function handleDelete(document: Document) {
    const confirmed = window.confirm(
      `Delete "${document.original_filename}"? This cannot be undone.`,
    );
    if (!confirmed) {
      return;
    }

    setActionError(null);
    setDeletingId(document.id);

    const { error: deleteError } = await deleteDocument(document.id);

    setDeletingId(null);

    if (deleteError) {
      setActionError(deleteError);
      return;
    }

    if (selected?.id === document.id) {
      setSelected(null);
    }

    setLibraryDocuments((current) =>
      current.filter((item) => item.id !== document.id),
    );
  }

  if (error) {
    return (
      <>
        <div className="section-header">
          <h2>Document Library</h2>
          <span className="meta-text">0 documents</span>
        </div>
        <p className="error-text">Could not load documents: {error}</p>
      </>
    );
  }

  if (libraryDocuments.length === 0) {
    return (
      <>
        <div className="section-header">
          <h2>Document Library</h2>
          <span className="meta-text">0 documents</span>
        </div>
        <div className="empty-state">
          <p>No documents yet.</p>
          <p className="helper-text">
            Upload an aviation PDF to start building your document library.
          </p>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="section-header">
        <h2>Document Library</h2>
        <span className="meta-text">
          {documentCount} document{documentCount === 1 ? "" : "s"}
        </span>
      </div>

      {actionError && <p className="error-text">{actionError}</p>}

      <ul className="document-list">
        {libraryDocuments.map((document) => (
          <Fragment key={document.id}>
            <li
              className={`document-item${selected?.id === document.id ? " selected" : ""}`}
            >
              <div className="document-item-main">
                <h3>{document.original_filename}</h3>
                <p className="helper-text">
                  Uploaded {formatTimestamp(document.uploaded_at)}
                </p>
              </div>
              <div className="document-item-meta">
                <StatusBadge status={document.status} />
                <span className="meta-text">
                  {document.page_count != null
                    ? `${document.page_count} pages`
                    : "Page count pending"}
                </span>
                <div className="document-actions">
                  <button
                    type="button"
                    className="button secondary"
                    onClick={() =>
                      setSelected({
                        id: document.id,
                        original_filename: document.original_filename,
                      })
                    }
                  >
                    View
                  </button>
                  <button
                    type="button"
                    className="button danger"
                    disabled={deletingId === document.id}
                    onClick={() => handleDelete(document)}
                  >
                    {deletingId === document.id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            </li>

            {selected?.id === document.id && (
              <li className="pdf-viewer-item">
                <section className="pdf-viewer-panel">
                  <div className="pdf-viewer-header">
                    <div>
                      <h3>{selected.original_filename}</h3>
                      <p className="helper-text">Inline PDF preview</p>
                    </div>
                    <div className="document-actions">
                      <a
                        className="button secondary"
                        href={getDocumentFileUrl(selected.id)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        Open in new tab
                      </a>
                      <button
                        type="button"
                        className="button secondary"
                        onClick={() => setSelected(null)}
                      >
                        Close viewer
                      </button>
                    </div>
                  </div>
                  <iframe
                    className="pdf-viewer-frame"
                    src={getDocumentFileUrl(selected.id)}
                    title={`PDF preview: ${selected.original_filename}`}
                  />
                </section>
              </li>
            )}
          </Fragment>
        ))}
      </ul>
    </>
  );
}
