/**
 * Purpose: Document library sidebar with upload, scope selection, and management.
 * Interactions: Uses lib/api.ts for upload, process, delete, chunks, and file URLs.
 */
"use client";

import { Fragment, useRef, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import {
  Check,
  FileText,
  Loader2,
  Plus,
  Search,
  TriangleAlert,
  X,
} from "lucide-react";

import type { Document, DocumentChunk } from "@/lib/api";
import {
  cancelDocumentProcessing,
  deleteDocument,
  fetchDocumentChunks,
  getDocumentFileUrl,
  processDocument,
} from "@/lib/api";
import { formatRelativeDate } from "@/lib/format";
import { SOURCE_META, normalizeSourceType } from "@/lib/source-meta";
import { cn } from "@/lib/utils";

type DocumentLibraryProps = {
  documents: Document[];
  error: string | null;
  uploadError: string | null;
  selectedScopeId: string | null;
  onToggleScopeSelect: (id: string) => void;
  onUpload: (files: FileList) => void;
  onDocumentsChange: Dispatch<SetStateAction<Document[]>>;
};

function StatusDot({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  if (normalized === "processed")
    return (
      <span className="flex items-center gap-1.5 mono-label text-[var(--color-chart-3)]">
        <span className="size-1.5 rounded-full bg-[var(--color-chart-3)]" />
        Indexed
      </span>
    );
  if (normalized === "processing")
    return (
      <span className="flex items-center gap-1.5 mono-label text-accent">
        <Loader2 className="size-2.5 animate-spin" />
        Indexing
      </span>
    );
  if (normalized === "failed")
    return (
      <span className="flex items-center gap-1.5 mono-label text-destructive">
        <TriangleAlert className="size-2.5" />
        Failed
      </span>
    );
  if (normalized === "cancelled")
    return (
      <span className="flex items-center gap-1.5 mono-label text-muted-foreground">
        Cancelled
      </span>
    );
  return (
    <span className="flex items-center gap-1.5 mono-label text-muted-foreground">
      <span className="size-1.5 rounded-full bg-muted-foreground animate-blink" />
      Queued
    </span>
  );
}

function canProcess(status: string): boolean {
  const normalized = status.toLowerCase();
  return (
    normalized === "uploaded" ||
    normalized === "failed" ||
    normalized === "cancelled"
  );
}

export function DocumentLibrary({
  documents,
  error,
  uploadError,
  selectedScopeId,
  onToggleScopeSelect,
  onUpload,
  onDocumentsChange,
}: DocumentLibraryProps) {
  const [query, setQuery] = useState("");
  const [dragging, setDragging] = useState(false);
  const [viewingId, setViewingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [cancellingId, setCancellingId] = useState<string | null>(null);
  const [inspectingId, setInspectingId] = useState<string | null>(null);
  const [chunksPreview, setChunksPreview] = useState<DocumentChunk[]>([]);
  const [chunksTotal, setChunksTotal] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const processControllerRef = useRef<AbortController | null>(null);

  const filtered = documents.filter((d) =>
    (d.original_filename + d.source_type)
      .toLowerCase()
      .includes(query.toLowerCase()),
  );
  const indexed = documents.filter((d) => d.status === "processed").length;

  function updateDocumentInList(updated: Partial<Document> & { id: string }) {
    onDocumentsChange((current) =>
      current.map((item) =>
        item.id === updated.id ? { ...item, ...updated } : item,
      ),
    );
  }

  async function handleDelete(document: Document) {
    const confirmed = window.confirm(
      `Delete "${document.original_filename}"? This cannot be undone.`,
    );
    if (!confirmed) return;

    setActionError(null);
    setDeletingId(document.id);

    const { error: deleteError } = await deleteDocument(document.id);
    setDeletingId(null);

    if (deleteError) {
      setActionError(deleteError);
      return;
    }

    if (viewingId === document.id) setViewingId(null);
    if (expandedId === document.id) setExpandedId(null);
    if (inspectingId === document.id) {
      setInspectingId(null);
      setChunksPreview([]);
      setChunksTotal(0);
    }

    onDocumentsChange((current) =>
      current.filter((item) => item.id !== document.id),
    );
  }

  async function handleProcess(document: Document) {
    const controller = new AbortController();
    setActionError(null);
    setProcessingId(document.id);
    setCancellingId(null);
    processControllerRef.current = controller;
    updateDocumentInList({ id: document.id, status: "processing" });

    const { data, error: processError } = await processDocument(document.id, {
      signal: controller.signal,
    });

    setProcessingId(null);
    if (processControllerRef.current === controller) {
      processControllerRef.current = null;
    }

    if (processError || !data) {
      updateDocumentInList({
        id: document.id,
        status: controller.signal.aborted ? "cancelled" : "failed",
      });
      if (controller.signal.aborted) return;
      setActionError(processError ?? "Processing failed.");
      return;
    }

    updateDocumentInList({
      id: document.id,
      status: data.status,
      page_count: data.page_count,
    });
  }

  async function handleCancelProcess(document: Document) {
    setActionError(null);
    setCancellingId(document.id);

    const { data, error: cancelError } = await cancelDocumentProcessing(
      document.id,
    );
    processControllerRef.current?.abort();
    setCancellingId(null);

    if (cancelError || !data) {
      setActionError(cancelError ?? "Could not cancel processing.");
      return;
    }

    updateDocumentInList(data);
  }

  async function handleInspectChunks(document: Document) {
    setActionError(null);
    setInspectingId(document.id);
    setExpandedId(document.id);

    const { data, error: chunksError } = await fetchDocumentChunks(document.id);

    if (chunksError || !data) {
      setInspectingId(null);
      setActionError(chunksError ?? "Could not load chunks.");
      return;
    }

    setChunksPreview(data.chunks.slice(0, 5));
    setChunksTotal(data.total);
  }

  return (
    <aside className="flex h-full min-h-0 flex-col border-r border-border bg-panel/60 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="mono-label text-muted-foreground">Library</span>
          <span className="mono-label text-primary">
            / {documents.length} DOCS
          </span>
        </div>
        <span className="mono-label text-muted-foreground">{indexed} indexed</span>
      </div>

      <div className="px-3 pt-3">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            if (e.dataTransfer.files.length) onUpload(e.dataTransfer.files);
          }}
          className={cn(
            "group flex w-full flex-col items-center gap-1.5 rounded-md border border-dashed border-border px-4 py-5 text-center transition-colors",
            dragging
              ? "border-primary bg-primary/10"
              : "hover:border-primary/60 hover:bg-primary/5",
          )}
        >
          <span className="flex size-8 items-center justify-center rounded-full border border-border bg-background text-primary transition-transform group-hover:scale-110">
            <Plus className="size-4" />
          </span>
          <span className="text-sm font-medium text-foreground">
            Upload document
          </span>
          <span className="mono-label text-muted-foreground">
            PDF · drop or browse
          </span>
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) onUpload(e.target.files);
            e.target.value = "";
          }}
        />
        {(uploadError || actionError) && (
          <p className="mt-2 text-xs text-destructive">
            {uploadError ?? actionError}
          </p>
        )}
      </div>

      <div className="px-3 py-3">
        <div className="flex items-center gap-2 rounded-md border border-border bg-background px-2.5 py-1.5 focus-within:border-primary/60">
          <Search className="size-3.5 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter library"
            className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery("")}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 pb-4">
        {error ? (
          <p className="px-3 py-8 text-center text-sm text-destructive">
            Could not load documents: {error}
          </p>
        ) : filtered.length === 0 ? (
          <p className="px-3 py-8 text-center text-sm text-muted-foreground">
            {documents.length === 0
              ? "No documents yet. Upload an aviation PDF to get started."
              : "No documents match."}
          </p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {filtered.map((doc) => {
              const selected = selectedScopeId === doc.id;
              const meta = SOURCE_META[normalizeSourceType(doc.source_type)];
              const selectable = doc.status === "processed";
              const isExpanded = expandedId === doc.id;

              return (
                <Fragment key={doc.id}>
                  <li>
                    <div
                      className={cn(
                        "group relative w-full rounded-md border text-left transition-colors",
                        selected
                          ? "border-primary/70 bg-primary/10"
                          : "border-border bg-card/40 hover:bg-card",
                      )}
                    >
                      {selected && (
                        <span className="absolute inset-y-0 left-0 w-0.5 rounded-full bg-primary" />
                      )}
                      <button
                        type="button"
                        disabled={!selectable}
                        onClick={() => onToggleScopeSelect(doc.id)}
                        className={cn(
                          "w-full px-3 py-2.5 text-left",
                          !selectable && "cursor-not-allowed opacity-60",
                        )}
                      >
                        <div className="flex items-start gap-2.5">
                          <span
                            className={cn(
                              "mt-0.5 flex size-7 shrink-0 items-center justify-center rounded border border-border bg-background",
                              meta.tone,
                            )}
                          >
                            <FileText className="size-3.5" />
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex items-center gap-2">
                              <span className={cn("mono-label", meta.tone)}>
                                {meta.code}
                              </span>
                              <StatusDot status={doc.status} />
                            </div>
                            <p className="mt-1 truncate text-sm font-medium text-foreground">
                              {doc.original_filename}
                            </p>
                            <p className="mt-0.5 mono-label text-muted-foreground">
                              {doc.page_count != null
                                ? `${doc.page_count}p`
                                : "—"}{" "}
                              · {formatRelativeDate(doc.uploaded_at)}
                            </p>
                          </div>
                          <span
                            className={cn(
                              "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-[4px] border transition-colors",
                              selected
                                ? "border-primary bg-primary text-primary-foreground"
                                : "border-border text-transparent group-hover:border-primary/50",
                            )}
                          >
                            <Check className="size-3" />
                          </span>
                        </div>
                      </button>

                      <div className="flex flex-wrap gap-1 border-t border-border/60 px-2 py-1.5">
                        {canProcess(doc.status) && (
                          <button
                            type="button"
                            disabled={processingId === doc.id}
                            onClick={() => handleProcess(doc)}
                            className="mono-label rounded px-1.5 py-0.5 text-primary hover:bg-primary/10 disabled:opacity-50"
                          >
                            {processingId === doc.id ? "Processing…" : "Process"}
                          </button>
                        )}
                        {doc.status === "processing" && (
                          <button
                            type="button"
                            disabled={cancellingId === doc.id}
                            onClick={() => handleCancelProcess(doc)}
                            className="mono-label rounded px-1.5 py-0.5 text-destructive hover:bg-destructive/10 disabled:opacity-50"
                          >
                            {cancellingId === doc.id ? "Cancelling…" : "Cancel"}
                          </button>
                        )}
                        {doc.status === "processed" && (
                          <button
                            type="button"
                            disabled={inspectingId === doc.id}
                            onClick={() => handleInspectChunks(doc)}
                            className="mono-label rounded px-1.5 py-0.5 text-accent hover:bg-accent/10 disabled:opacity-50"
                          >
                            {inspectingId === doc.id ? "Loading…" : "Chunks"}
                          </button>
                        )}
                        <button
                          type="button"
                          onClick={() => {
                            setViewingId(viewingId === doc.id ? null : doc.id);
                            setExpandedId(viewingId === doc.id ? null : doc.id);
                          }}
                          className="mono-label rounded px-1.5 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
                        >
                          {viewingId === doc.id ? "Hide PDF" : "View PDF"}
                        </button>
                        <button
                          type="button"
                          disabled={deletingId === doc.id}
                          onClick={() => handleDelete(doc)}
                          className="mono-label rounded px-1.5 py-0.5 text-destructive hover:bg-destructive/10 disabled:opacity-50"
                        >
                          {deletingId === doc.id ? "Deleting…" : "Delete"}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            setExpandedId(isExpanded ? null : doc.id)
                          }
                          className="mono-label ml-auto rounded px-1.5 py-0.5 text-muted-foreground hover:text-foreground"
                        >
                          {isExpanded ? "Collapse" : "Expand"}
                        </button>
                      </div>
                    </div>
                  </li>

                  {isExpanded && viewingId === doc.id && (
                    <li className="rounded-md border border-border bg-background/60 p-2">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="mono-label text-muted-foreground">
                          PDF preview
                        </span>
                        <a
                          href={getDocumentFileUrl(doc.id)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mono-label text-accent hover:underline"
                        >
                          Open tab
                        </a>
                      </div>
                      <iframe
                        className="h-48 w-full rounded border border-border bg-background"
                        src={getDocumentFileUrl(doc.id)}
                        title={`PDF preview: ${doc.original_filename}`}
                      />
                    </li>
                  )}

                  {isExpanded &&
                    inspectingId === doc.id &&
                    chunksPreview.length > 0 && (
                      <li className="rounded-md border border-border bg-background/60 p-2">
                        <p className="mb-2 mono-label text-muted-foreground">
                          Chunks · {chunksPreview.length} of {chunksTotal}
                        </p>
                        <ul className="flex flex-col gap-2">
                          {chunksPreview.map((chunk) => (
                            <li
                              key={chunk.id}
                              className="rounded border border-border/60 bg-card/40 p-2 text-xs"
                            >
                              <div className="mb-1 flex gap-2 mono-label text-muted-foreground">
                                <span>Chunk {chunk.chunk_index + 1}</span>
                                <span>
                                  {chunk.page_number != null
                                    ? `p.${chunk.page_number}`
                                    : "p.?"}
                                </span>
                                <span>{chunk.token_count} tok</span>
                              </div>
                              <p className="leading-relaxed text-foreground">
                                {chunk.text}
                              </p>
                            </li>
                          ))}
                        </ul>
                      </li>
                    )}
                </Fragment>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
