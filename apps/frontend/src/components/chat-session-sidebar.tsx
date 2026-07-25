"use client";

import { ChevronLeft, ChevronRight, MessageSquarePlus, Trash2 } from "lucide-react";

import type { ChatSessionSummary } from "@/lib/chat-types";
import { formatRelativeDate } from "@/lib/format";
import { cn } from "@/lib/utils";

type ChatSessionSidebarProps = {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  collapsed: boolean;
  loading?: boolean;
  error?: string | null;
  onToggleCollapsed: () => void;
  onSelectSession: (sessionId: string) => void;
  onNewChat: () => void;
  onDeleteSession: (sessionId: string) => void;
};

function sessionLabel(session: ChatSessionSummary): string {
  if (session.title?.trim()) {
    return session.title.trim();
  }
  if (session.preview?.trim()) {
    return session.preview.trim();
  }
  return "New chat";
}

export function ChatSessionSidebar({
  sessions,
  activeSessionId,
  collapsed,
  loading = false,
  error = null,
  onToggleCollapsed,
  onSelectSession,
  onNewChat,
  onDeleteSession,
}: ChatSessionSidebarProps) {
  if (collapsed) {
    return (
      <aside className="flex h-full min-h-0 w-12 flex-col border-r border-border bg-panel/70 backdrop-blur-sm">
        <div className="flex flex-col items-center gap-2 border-b border-border px-2 py-3">
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="flex size-8 items-center justify-center rounded-md border border-border text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            aria-label="Expand chat sessions"
          >
            <ChevronRight className="size-4" />
          </button>
          <button
            type="button"
            onClick={onNewChat}
            className="flex size-8 items-center justify-center rounded-md border border-primary/40 bg-primary/10 text-primary transition-colors hover:bg-primary/15"
            aria-label="New chat"
          >
            <MessageSquarePlus className="size-4" />
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="flex h-full min-h-0 w-full flex-col border-r border-border bg-panel/70 backdrop-blur-sm">
      <div className="flex items-center justify-between border-b border-border px-3 py-3">
        <div>
          <span className="mono-label text-muted-foreground">Chats</span>
          <p className="mt-1 text-xs text-muted-foreground">
            {sessions.length} saved
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onNewChat}
            className="flex size-8 items-center justify-center rounded-md border border-primary/40 bg-primary/10 text-primary transition-colors hover:bg-primary/15"
            aria-label="New chat"
            title="New chat"
          >
            <MessageSquarePlus className="size-4" />
          </button>
          <button
            type="button"
            onClick={onToggleCollapsed}
            className="flex size-8 items-center justify-center rounded-md border border-border text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            aria-label="Collapse chat sessions"
          >
            <ChevronLeft className="size-4" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-2 py-2">
        {loading ? (
          <p className="px-2 py-6 text-center text-sm text-muted-foreground">
            Loading chats…
          </p>
        ) : error ? (
          <p className="px-2 py-6 text-center text-sm text-destructive">{error}</p>
        ) : sessions.length === 0 ? (
          <div className="px-2 py-8 text-center">
            <p className="text-sm text-muted-foreground">No chats yet.</p>
            <button
              type="button"
              onClick={onNewChat}
              className="mt-3 text-sm text-primary hover:underline"
            >
              Start a new chat
            </button>
          </div>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {sessions.map((session) => {
              const active = session.id === activeSessionId;
              return (
                <li key={session.id}>
                  <div
                    className={cn(
                      "group rounded-md border transition-colors",
                      active
                        ? "border-primary/60 bg-primary/10"
                        : "border-border bg-card/30 hover:bg-card/60",
                    )}
                  >
                    <button
                      type="button"
                      onClick={() => onSelectSession(session.id)}
                      className="w-full px-3 py-2.5 text-left"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-foreground">
                            {sessionLabel(session)}
                          </p>
                          {session.preview && (
                            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
                              {session.preview}
                            </p>
                          )}
                          <p className="mt-1 mono-label text-muted-foreground">
                            {session.messageCount} msgs ·{" "}
                            {formatRelativeDate(session.updatedAt)}
                          </p>
                        </div>
                      </div>
                    </button>
                    <div className="flex justify-end border-t border-border/60 px-2 py-1 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100">
                      <button
                        type="button"
                        onClick={() => onDeleteSession(session.id)}
                        className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs text-destructive hover:bg-destructive/10"
                      >
                        <Trash2 className="size-3" />
                        Delete
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
