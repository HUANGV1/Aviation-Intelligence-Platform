"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { History, Library, X } from "lucide-react";

import { ChatPanel } from "@/components/chat-panel";
import { ChatSessionSidebar } from "@/components/chat-session-sidebar";
import { ConsoleBackground } from "@/components/console-background";
import { DocumentLibrary } from "@/components/document-library";
import { SidebarResizeHandle } from "@/components/sidebar-resize-handle";
import { usePersistedWidth } from "@/hooks/use-persisted-width";
import type { ChatMessage, ChatSessionSummary } from "@/lib/chat-types";
import type { Document, HealthResponse } from "@/lib/api";
import {
  deleteChatSession,
  fetchChatSession,
  fetchDocuments,
  fetchChatSessions,
  resolveDocumentScope,
  sendAgentMessage,
  toChatCitation,
  toChatMessageRecord,
  toChatOperationalSource,
  toChatSessionSummary,
  toChatToolActivity,
  uploadDocument,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const COLLAPSED_SIDEBAR_WIDTH = 48;
const CHAT_SIDEBAR_DEFAULT = 280;
const DOC_SIDEBAR_DEFAULT = 340;
const SIDEBAR_MIN = 220;
const SIDEBAR_MAX = 520;

function uid() {
  return Math.random().toString(36).slice(2, 10);
}

function toUiMessage(
  record: ReturnType<typeof toChatMessageRecord>,
  scope?: { documentId: string | null; documentName: string | null },
): ChatMessage {
  const isUser = record.role === "user";
  return {
    id: record.id,
    role: isUser ? "user" : "assistant",
    content: record.content,
    sessionId: record.sessionId,
    scopedDocumentId: isUser ? (scope?.documentId ?? null) : null,
    scopedDocumentName: isUser ? (scope?.documentName ?? null) : null,
    citations: record.citations,
    operationalSources: record.operationalSources,
    createdAt: record.createdAt,
    insufficientEvidence: record.insufficientEvidence,
    toolActivities: record.toolActivities,
    directAnswer: record.directAnswer,
  };
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
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [documentLoadError, setDocumentLoadError] = useState(documentsError);
  const [sessionLoadError, setSessionLoadError] = useState<string | null>(null);
  const [chatSidebarOpen, setChatSidebarOpen] = useState(true);
  const [docSidebarOpen, setDocSidebarOpen] = useState(true);
  const [chatSidebarWidth, setChatSidebarWidth] = usePersistedWidth(
    "aip.chatSidebarWidth",
    {
      defaultWidth: CHAT_SIDEBAR_DEFAULT,
      minWidth: SIDEBAR_MIN,
      maxWidth: SIDEBAR_MAX,
    },
  );
  const [docSidebarWidth, setDocSidebarWidth] = usePersistedWidth(
    "aip.docSidebarWidth",
    {
      defaultWidth: DOC_SIDEBAR_DEFAULT,
      minWidth: SIDEBAR_MIN,
      maxWidth: SIDEBAR_MAX,
    },
  );
  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  const [mobileLibOpen, setMobileLibOpen] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    setSessionsError(null);
    const { data, error } = await fetchChatSessions();
    setSessionsLoading(false);

    if (error || !data) {
      setSessionsError(error ?? "Could not load chat sessions.");
      return;
    }

    setSessions(data.sessions.map(toChatSessionSummary));
  }, []);

  useEffect(() => {
    setDocuments(initialDocuments);
    if (initialDocuments.length > 0) {
      setDocumentLoadError(null);
    }
  }, [initialDocuments]);

  useEffect(() => {
    void loadSessions();
  }, [loadSessions]);

  const processedDocuments = useMemo(
    () => documents.filter((d) => d.status === "processed"),
    [documents],
  );

  const selectedDocument =
    selectedScopeId != null
      ? (documents.find((d) => d.id === selectedScopeId) ?? null)
      : null;

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [sessions, activeSessionId],
  );

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

  function handleSetDocumentScope(documentId: string | null) {
    setSelectedScopeId(documentId);
  }

  async function handleUpload(files: FileList) {
    setUploadError(null);
    const list = Array.from(files).filter(
      (f) =>
        f.type === "application/pdf" ||
        f.name.toLowerCase().endsWith(".pdf"),
    );

    if (list.length === 0) {
      setUploadError("Only PDF files are allowed.");
      return;
    }

    let uploaded = false;

    for (const file of list) {
      const { data, error } = await uploadDocument(file);
      if (error || !data) {
        setUploadError(error ?? "Upload failed.");
        continue;
      }
      uploaded = true;
      setDocuments((prev) => [
        data,
        ...prev.filter((item) => item.id !== data.id),
      ]);
    }

    if (uploaded) {
      const { data, error } = await fetchDocuments();
      if (data) {
        setDocuments(data.documents);
        setDocumentLoadError(null);
      } else if (error) {
        setUploadError(error);
        setDocumentLoadError(error);
      }
    }
  }

  function handleNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setSessionLoadError(null);
    setMobileChatOpen(false);
  }

  async function handleSelectSession(sessionId: string) {
    if (busy) return;

    setActiveSessionId(sessionId);
    setSessionLoadError(null);
    setMobileChatOpen(false);

    const { data, error } = await fetchChatSession(sessionId);
    if (error || !data) {
      setSessionLoadError(error ?? "Could not load chat session.");
      setMessages([]);
      return;
    }

    const sessionDocumentId = data.document_id ?? null;
    setSelectedScopeId(sessionDocumentId);

    const sessionDocumentName = sessionDocumentId
      ? (documents.find((doc) => doc.id === sessionDocumentId)?.original_filename ??
        "Selected document")
      : null;

    setMessages(
      data.messages.map((message) =>
        toUiMessage(toChatMessageRecord(message), {
          documentId: sessionDocumentId,
          documentName: sessionDocumentName,
        }),
      ),
    );
  }

  async function handleDeleteSession(sessionId: string) {
    const session = sessions.find((item) => item.id === sessionId);
    const label = session?.title ?? session?.preview ?? "this chat";
    const confirmed = window.confirm(`Delete "${label}"? This cannot be undone.`);
    if (!confirmed) return;

    const { error } = await deleteChatSession(sessionId);
    if (error) {
      setSessionsError(error);
      return;
    }

    setSessions((prev) => prev.filter((item) => item.id !== sessionId));
    if (activeSessionId === sessionId) {
      handleNewChat();
    }
  }

  async function handleSend(text: string) {
    if (busy) return;

    const scopedDocumentName = selectedDocument?.original_filename ?? null;
    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text,
      sessionId: activeSessionId,
      scopedDocumentId: selectedScopeId,
      scopedDocumentName,
      createdAt: new Date().toISOString(),
    };
    const pendingId = uid();
    const pendingMsg: ChatMessage = {
      id: pendingId,
      role: "assistant",
      content: "",
      sessionId: activeSessionId,
      scopedDocumentId: selectedScopeId,
      scopedDocumentName,
      createdAt: new Date().toISOString(),
      pending: true,
    };
    setMessages((prev) => [...prev, userMsg, pendingMsg]);
    setBusy(true);

    const { data, error } = await sendAgentMessage({
      message: text,
      ...(activeSessionId ? { session_id: activeSessionId } : {}),
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

    if (data.session_id) {
      setActiveSessionId(data.session_id);
    }

    setMessages((prev) =>
      prev.map((m) =>
        m.id === pendingId
          ? {
              ...m,
              pending: false,
              content: data.answer,
              sessionId: data.session_id ?? activeSessionId,
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

    await loadSessions();
  }

  const sessionTitle =
    activeSession?.title ??
    activeSession?.preview ??
    (activeSessionId ? "Active chat" : null);

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden">
      <ConsoleBackground />

      <div className="flex items-center justify-between border-b border-border bg-panel/60 px-4 py-1.5 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setMobileChatOpen(true)}
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground lg:hidden"
          >
            <History className="size-4" />
            <span className="mono-label">Chats</span>
          </button>
          <button
            type="button"
            onClick={() => setMobileLibOpen(true)}
            className="flex items-center gap-1.5 text-muted-foreground hover:text-foreground lg:hidden"
          >
            <Library className="size-4" />
            <span className="mono-label">Library</span>
          </button>
          <span className="mono-label hidden text-muted-foreground sm:inline">
            AVIATION INTELLIGENCE · AGENT CONSOLE v0.3
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

      <div className="grid min-h-0 flex-1 grid-cols-[auto_1fr_auto]">
        <div className="hidden min-h-0 lg:block">
          <div
            className="group/sidebar relative h-full"
            style={{
              width: chatSidebarOpen
                ? chatSidebarWidth
                : COLLAPSED_SIDEBAR_WIDTH,
            }}
          >
            <ChatSessionSidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              collapsed={!chatSidebarOpen}
              loading={sessionsLoading}
              error={sessionsError}
              onToggleCollapsed={() => setChatSidebarOpen((prev) => !prev)}
              onSelectSession={(sessionId) => {
                void handleSelectSession(sessionId);
              }}
              onNewChat={handleNewChat}
              onDeleteSession={(sessionId) => {
                void handleDeleteSession(sessionId);
              }}
            />
            <SidebarResizeHandle
              edge="right"
              disabled={!chatSidebarOpen}
              label="Resize chat sidebar"
              onResize={(delta) =>
                setChatSidebarWidth((prev) => prev + delta)
              }
            />
          </div>
        </div>

        <div className="min-h-0 min-w-0">
          {sessionLoadError && (
            <div className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-sm text-destructive">
              {sessionLoadError}
            </div>
          )}
          <ChatPanel
            messages={messages}
            busy={busy}
            selectedDocument={selectedDocument}
            processedDocuments={processedDocuments}
            sessionTitle={sessionTitle}
            onSend={handleSend}
            onNewChat={handleNewChat}
            onSetDocumentScope={handleSetDocumentScope}
          />
        </div>

        <div className="hidden min-h-0 lg:block">
          <div
            className="group/sidebar relative h-full"
            style={{
              width: docSidebarOpen
                ? docSidebarWidth
                : COLLAPSED_SIDEBAR_WIDTH,
            }}
          >
            <DocumentLibrary
              documents={documents}
              error={documentLoadError}
              uploadError={uploadError}
              collapsed={!docSidebarOpen}
              onToggleCollapsed={() => setDocSidebarOpen((prev) => !prev)}
              onUpload={handleUpload}
              onDocumentsChange={setDocuments}
            />
            <SidebarResizeHandle
              edge="left"
              disabled={!docSidebarOpen}
              label="Resize document library sidebar"
              onResize={(delta) =>
                setDocSidebarWidth((prev) => prev + delta)
              }
            />
          </div>
        </div>
      </div>

      {mobileChatOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            onClick={() => setMobileChatOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 flex w-[86%] max-w-sm flex-col bg-panel shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="mono-label text-muted-foreground">Chats</span>
              <button
                type="button"
                onClick={() => setMobileChatOpen(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close chats"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <ChatSessionSidebar
                sessions={sessions}
                activeSessionId={activeSessionId}
                collapsed={false}
                loading={sessionsLoading}
                error={sessionsError}
                onToggleCollapsed={() => setMobileChatOpen(false)}
                onSelectSession={(sessionId) => {
                  void handleSelectSession(sessionId);
                }}
                onNewChat={handleNewChat}
                onDeleteSession={(sessionId) => {
                  void handleDeleteSession(sessionId);
                }}
              />
            </div>
          </div>
        </div>
      )}

      {mobileLibOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            onClick={() => setMobileLibOpen(false)}
          />
          <div className="absolute inset-y-0 right-0 flex w-[86%] max-w-sm flex-col bg-panel shadow-2xl">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="mono-label text-muted-foreground">
                Document Library
              </span>
              <button
                type="button"
                onClick={() => setMobileLibOpen(false)}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close library"
              >
                <X className="size-4" />
              </button>
            </div>
            <div className="min-h-0 flex-1">
              <DocumentLibrary
                documents={documents}
                error={documentLoadError}
                uploadError={uploadError}
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
