"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUp, Radio, Sparkles, X } from "lucide-react";

import type { Document } from "@/lib/api";
import type { ChatMessage } from "@/lib/chat-types";
import { SOURCE_META, normalizeSourceType } from "@/lib/source-meta";
import { cn } from "@/lib/utils";
import { ChatMessageRow } from "./chat-message";

const SCOPED_SUGGESTIONS = [
  "What were the contributing factors in this report?",
  "Summarize the safety recommendations.",
  "Which conditions affected the approach?",
];

interface ChatPanelProps {
  messages: ChatMessage[];
  busy: boolean;
  selectedDocument: Document | null;
  processedCount: number;
  onSend: (text: string) => void;
  onClearConversation: () => void;
  onRemoveDoc: () => void;
}

export function ChatPanel({
  messages,
  busy,
  selectedDocument,
  processedCount,
  onSend,
  onClearConversation,
  onRemoveDoc,
}: ChatPanelProps) {
  const [value, setValue] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const canSend =
    value.trim().length > 0 && !busy && processedCount > 0;

  function submit() {
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  }

  const scopeMeta = selectedDocument
    ? SOURCE_META[normalizeSourceType(selectedDocument.source_type)]
    : null;

  return (
    <section className="flex h-full min-h-0 flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-panel/40 px-4 py-3 backdrop-blur-sm">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-md border border-primary/40 bg-primary/10 text-primary">
            <Radio className="size-4" />
          </span>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-foreground">
              Aviation Intelligence Platform
            </h1>
            <p className="mono-label text-muted-foreground">
              Document Q&amp;A Console
            </p>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={onClearConversation}
            className="mono-label text-muted-foreground transition-colors hover:text-foreground"
          >
            Clear conversation
          </button>
        )}
      </header>

      <div className="flex min-h-[42px] flex-wrap items-center gap-2 border-b border-border px-4 py-2">
        <span className="mono-label text-muted-foreground">Scope</span>
        {selectedDocument ? (
          <span className="flex items-center gap-1.5 rounded border border-primary/40 bg-primary/10 py-0.5 pl-1.5 pr-1 text-xs">
            {scopeMeta && (
              <span className={cn("mono-label", scopeMeta.tone)}>
                {scopeMeta.code}
              </span>
            )}
            <span className="max-w-[200px] truncate text-foreground">
              {selectedDocument.original_filename}
            </span>
            <button
              type="button"
              onClick={onRemoveDoc}
              className="text-muted-foreground hover:text-destructive"
              aria-label={`Remove ${selectedDocument.original_filename} from scope`}
            >
              <X className="size-3" />
            </button>
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">
            {processedCount > 0
              ? "All processed documents — select one in the library to narrow scope"
              : "Upload and process a PDF to start asking questions"}
          </span>
        )}
      </div>

      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center gap-6 px-6 text-center">
            <div className="relative">
              <span className="flex size-14 items-center justify-center rounded-xl border border-primary/40 bg-primary/10 text-primary">
                <Sparkles className="size-6" />
              </span>
            </div>
            <div className="space-y-2">
              <h2 className="text-balance text-xl font-semibold tracking-tight text-foreground">
                Ask questions grounded in your documents
              </h2>
              <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
                Every answer is generated only from retrieved source excerpts and
                returns page-level citations you can inspect.
              </p>
            </div>
            {/* {processedCount > 0 ? (
              <div className="grid w-full gap-2">
                {SCOPED_SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => onSend(s)}
                    disabled={busy}
                    className="group flex items-center justify-between rounded-md border border-border bg-card/40 px-3.5 py-2.5 text-left text-sm text-foreground transition-colors hover:border-primary/50 hover:bg-card disabled:opacity-50"
                  >
                    <span>{s}</span>
                    <ArrowUp className="size-3.5 rotate-45 text-muted-foreground transition-colors group-hover:text-primary" />
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No processed documents yet. Upload a PDF and run Process in the
                library.
              </p>
            )} */}
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6 md:px-6">
            {messages.map((m) => (
              <ChatMessageRow key={m.id} message={m} />
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-border bg-panel/40 px-4 py-3 backdrop-blur-sm">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-lg border border-border bg-background px-3 py-2 focus-within:border-primary/60">
            <textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing &&
                  e.keyCode !== 229
                ) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={1}
              placeholder={
                processedCount === 0
                  ? "Process a document first…"
                  : selectedDocument
                    ? `Ask about ${selectedDocument.original_filename}…`
                    : "Ask about your documents…"
              }
              disabled={processedCount === 0}
              className="max-h-40 min-h-[36px] w-full resize-none bg-transparent py-1.5 text-sm leading-relaxed outline-none placeholder:text-muted-foreground disabled:opacity-50"
            />
            <button
              type="button"
              onClick={submit}
              disabled={!canSend}
              className={cn(
                "flex size-8 shrink-0 items-center justify-center rounded-md transition-colors",
                canSend
                  ? "bg-primary text-primary-foreground hover:opacity-90"
                  : "bg-muted text-muted-foreground",
              )}
              aria-label="Send message"
            >
              <ArrowUp className="size-4" />
            </button>
          </div>
          <p className="mt-1.5 px-1 mono-label text-muted-foreground">
            {selectedDocument
              ? "1 document in scope · answers cite sources"
              : processedCount > 0
                ? `${processedCount} processed · all in scope`
                : "No processed documents"}{" "}
            · enter to send · shift+enter for newline
          </p>
        </div>
      </div>
    </section>
  );
}
