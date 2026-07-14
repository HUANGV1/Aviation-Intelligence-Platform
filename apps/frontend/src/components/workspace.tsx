"use client";

import { useEffect, useMemo, useState } from "react";
import { Library, X } from "lucide-react";

import { ChatPanel } from "@/components/chat-panel";
import { ConsoleBackground } from "@/components/console-background";
import { DocumentLibrary } from "@/components/document-library";
import type { ChatMessage } from "@/lib/chat-types";
import type { Document, HealthResponse } from "@/lib/api";
import {
  resolveDocumentScope,
  sendAgentMessage,
  toChatCitation,
  toChatOperationalSource,
  toChatToolActivity,
  uploadDocument,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

type WorkspaceProps = {
  initialDocuments: Document[];
  initialHealth: HealthResponse | null;
  healthError: string | null;
  documentsError: string | null;
};

export function Workspace({
  initialDocuments,
  initialHealth,
  healthError,
  documentsError,
}: WorkspaceProps) {
  const [documents, setDocuments] = useState(initialDocuments);
  const [selectedScopeId, setSelectedScopeId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [libOpen, setLibOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  const processedDocuments = useMemo(
    () => documents.filter((d) => d.status === "processed"),
    [documents],
  );

  const selectedDocument =
    selectedScopeId != null
      ? (documents.find((d) => d.id === selectedScopeId) ?? null)
      : null;

  useEffect(() => {
    if (
      selectedScopeId &&
      !processedDocuments.some((d) => d.id === selectedScopeId)
    ) {
      setSelectedScopeId(null);
    }
  }, [selectedScopeId, processedDocuments]);

  const isHealthy =
    initialHealth?.status?.toLowerCase() === "healthy" &&
    initialHealth.database.connected;

  function toggleScopeSelect(id: string) {
    setSelectedScopeId((prev) => (prev === id ? null : id));
  }

  async function handleUpload(files: FileList) {
    setUploadError(null);
    const list = Array.from(files).filter(
      (f) =>
        f.type === "application/pdf" ||
        f.name.toLowerCase().endsWith(".pdf"),
    );

    for (const file of list) {
      const { data, error } = await uploadDocument(file);
      if (error || !data) {
        setUploadError(error ?? "Upload failed.");
        continue;
      }
      setDocuments((prev) => [
        data,
        ...prev.filter((item) => item.id !== data.id),
      ]);
    }
  }

  async function handleSend(text: string) {
    if (busy) return;

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text,
      scopedDocumentId: selectedScopeId,
      createdAt: new Date().toISOString(),
    };
    const pendingId = uid();
    const pendingMsg: ChatMessage = {
      id: pendingId,
      role: "assistant",
      content: "",
      scopedDocumentId: selectedScopeId,
      createdAt: new Date().toISOString(),
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setBusy(true);

    const { data, error } = await sendAgentMessage({
      message: text,
      ...resolveDocumentScope(selectedScopeId),
    });

    setBusy(false);

    if (error || !data) {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === pendingId
            ? {
                ...m,
                pending: false,
                content:
                  error ??
                  "The agent service is unavailable. Confirm the backend is running.",
              }
            : m,
        ),
      );
      return;
    }

    setMessages((prev) =>
      prev.map((m) =>
        m.id === pendingId
          ? {
              ...m,
              pending: false,
              content: data.answer,
              citations: data.citations.map(toChatCitation),
              operationalSources: data.operational_sources.map(
                toChatOperationalSource,
              ),
              insufficientEvidence: data.insufficient_evidence,
              toolActivities: data.tool_activities.map(toChatToolActivity),
              directAnswer: data.direct_answer,
            }
          : m,
      ),
    );
  }

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden">
      <ConsoleBackground />

      <div className="flex items-center justify-between border-b border-border bg-panel/60 px-4 py-1.5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setLibOpen(true)}
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground md:hidden"
          >
            <Library className="size-4" />
            <span className="mono-label">Library</span>
          </button>
          <span className="mono-label hidden text-muted-foreground sm:inline">
            AVIATION INTELLIGENCE · AGENT CONSOLE v0.2
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="mono-label text-muted-foreground">
            SES.{new Date().getFullYear()}
          </span>
          <span className="flex items-center gap-1.5">
            <span
              className={cn(
                "size-1.5 rounded-full",
                isHealthy
                  ? "bg-[var(--color-chart-3)]"
                  : "bg-primary animate-beacon",
              )}
            />
            <span className="mono-label text-muted-foreground">
              {healthError
                ? "Backend unreachable"
                : isHealthy
                  ? "Live backend"
                  : "Degraded"}
            </span>
          </span>
        </div>
      </div>

      <div className="grid min-h-0 flex-1 md:grid-cols-[320px_1fr] lg:grid-cols-[360px_1fr]">
        <div className="hidden min-h-0 md:block">
          <DocumentLibrary
            documents={documents}
            error={documentsError}
            uploadError={uploadError}
            selectedScopeId={selectedScopeId}
            onToggleScopeSelect={toggleScopeSelect}
            onUpload={handleUpload}
            onDocumentsChange={setDocuments}
          />
        </div>

        <div className="min-h-0">
          <ChatPanel
            messages={messages}
            busy={busy}
            selectedDocument={selectedDocument}
            processedCount={processedDocuments.length}
            onSend={handleSend}
            onClearConversation={() => setMessages([])}
            onRemoveDoc={() => setSelectedScopeId(null)}
          />
        </div>
      </div>

      {libOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            onClick={() => setLibOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[86%] max-w-sm flex-col bg-panel shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="mono-label text-muted-foreground">
                Document Library
              </span>
              <button
                type="button"
                onClick={() => setLibOpen(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close library"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <DocumentLibrary
                documents={documents}
                error={documentsError}
                uploadError={uploadError}
                selectedScopeId={selectedScopeId}
                onToggleScopeSelect={(id) => {
                  toggleScopeSelect(id);
                }}
                onUpload={handleUpload}
                onDocumentsChange={setDocuments}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
