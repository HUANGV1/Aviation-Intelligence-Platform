"use client";

import { useEffect, useRef, useState, type DragEvent } from "react";
import {
  ArrowUp,
  FilePlus2,
  MessageSquarePlus,
  Radio,
  Sparkles,
  X,
} from "lucide-react";

import type { Document } from "@/lib/api";
import type { ChatMessage } from "@/lib/chat-types";
import {
  getDocumentDragId,
  isDocumentDrag,
} from "@/lib/document-dnd";
import { SOURCE_META, normalizeSourceType } from "@/lib/source-meta";
import { cn } from "@/lib/utils";
import { ChatMessageRow } from "./chat-message";

interface ChatPanelProps {
  messages: ChatMessage[];
  busy: boolean;
  selectedDocument: Document | null;
  processedDocuments: Document[];
  sessionTitle?: string | null;
  onSend: (text: string) => void;
  onNewChat: () => void;
  onSetDocumentScope: (documentId: string | null) => void;
}

export function ChatPanel({
  messages,
  busy,
  selectedDocument,
  processedDocuments,
  sessionTitle = null,
  onSend,
  onNewChat,
  onSetDocumentScope,
}: ChatPanelProps) {
  const [value, setValue] = useState("");
  const [draggingDoc, setDraggingDoc] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const dragDepthRef = useRef(0);
  const pickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  useEffect(() => {
    if (!pickerOpen) return;

    function handlePointerDown(event: MouseEvent) {
      if (
        pickerRef.current &&
        !pickerRef.current.contains(event.target as Node)
      ) {
        setPickerOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [pickerOpen]);

  const canSend = value.trim().length > 0 && !busy;
  const processedCount = processedDocuments.length;

  function submit() {
    if (!canSend) return;
    onSend(value.trim());
    setValue("");
  }

  function handleDragEnter(event: DragEvent) {
    if (!isDocumentDrag(event.dataTransfer)) return;
    event.preventDefault();
    dragDepthRef.current += 1;
    setDraggingDoc(true);
  }

  function handleDragOver(event: DragEvent) {
    if (!isDocumentDrag(event.dataTransfer)) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  }

  function handleDragLeave(event: DragEvent) {
    if (!isDocumentDrag(event.dataTransfer)) return;
    event.preventDefault();
    dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
    if (dragDepthRef.current === 0) {
      setDraggingDoc(false);
    }
  }

  function handleDrop(event: DragEvent) {
    if (!isDocumentDrag(event.dataTransfer)) return;
    event.preventDefault();
    dragDepthRef.current = 0;
    setDraggingDoc(false);

    const documentId = getDocumentDragId(event.dataTransfer);
    if (!documentId) return;
    if (!processedDocuments.some((doc) => doc.id === documentId)) return;
    onSetDocumentScope(documentId);
  }

  const scopeMeta = selectedDocument
    ? SOURCE_META[normalizeSourceType(selectedDocument.source_type)]
    : null;

  return (
    <section
      className={cn(
        "relative flex h-full min-h-0 flex-col",
        draggingDoc && "ring-2 ring-inset ring-primary/50",
      )}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {draggingDoc && (
        <div className="pointer-events-none absolute inset-0 z-20 flex items-center justify-center bg-background/70 backdrop-blur-[1px]">
          <div className="rounded-md border border-primary/50 bg-primary/10 px-4 py-3 text-center">
            <p className="text-sm font-medium text-foreground">
              Drop to attach document to chat
            </p>
            <p className="mt-1 mono-label text-muted-foreground">
              Limits document search to this file
            </p>
          </div>
        </div>
      )}

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
              {sessionTitle ? sessionTitle : "Agent Console"}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onNewChat}
          className="inline-flex items-center gap-1.5 rounded-md border border-primary/40 bg-primary/10 px-2.5 py-1.5 text-xs font-medium text-primary transition-colors hover:bg-primary/15"
        >
          <MessageSquarePlus className="size-3.5" />
          New chat
        </button>
      </header>

      <div className="flex min-h-[42px] flex-wrap items-center gap-2 border-b border-border px-4 py-2">
        <span className="mono-label text-muted-foreground">Attached</span>
        {selectedDocument ? (
          <span className="flex items-center gap-1.5 rounded border border-primary/40 bg-primary/10 py-0.5 pl-1.5 pr-1 text-xs">
            {scopeMeta && (
              <span className={cn("mono-label", scopeMeta.tone)}>
                {scopeMeta.code}
              </span>
            )}
            <span className="max-w-[220px] truncate text-foreground">
              {selectedDocument.original_filename}
            </span>
            <button
              type="button"
              onClick={() => onSetDocumentScope(null)}
              className="text-muted-foreground hover:text-destructive"
              aria-label={`Detach ${selectedDocument.original_filename}`}
            >
              <X className="size-3" />
            </button>
          </span>
        ) : (
          <span className="text-xs text-muted-foreground">
            {processedCount > 0
              ? "None — drag an indexed PDF here or add one"
              : "None — index a PDF in the library first"}
          </span>
        )}

        <div ref={pickerRef} className="relative ml-auto">
          <button
            type="button"
            disabled={processedCount === 0}
            onClick={() => setPickerOpen((open) => !open)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs transition-colors",
              processedCount === 0
                ? "cursor-not-allowed border-border text-muted-foreground opacity-50"
                : "border-primary/40 bg-primary/10 text-primary hover:bg-primary/15",
            )}
            aria-expanded={pickerOpen}
            aria-haspopup="listbox"
          >
            <FilePlus2 className="size-3.5" />
            Add document
          </button>
          {pickerOpen && (
            <ul
              role="listbox"
              className="absolute right-0 z-30 mt-1 max-h-56 w-72 overflow-y-auto rounded-md border border-border bg-panel py-1 shadow-lg"
            >
              {processedDocuments.map((doc) => {
                const meta = SOURCE_META[normalizeSourceType(doc.source_type)];
                const active = selectedDocument?.id === doc.id;
                return (
                  <li key={doc.id}>
                    <button
                      type="button"
                      role="option"
                      aria-selected={active}
                      onClick={() => {
                        onSetDocumentScope(doc.id);
                        setPickerOpen(false);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-primary/10",
                        active && "bg-primary/10",
                      )}
                    >
                      <span className={cn("mono-label shrink-0", meta.tone)}>
                        {meta.code}
                      </span>
                      <span className="truncate text-foreground">
                        {doc.original_filename}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
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
                Chat with the aviation intelligence agent
              </h2>
              <p className="text-pretty text-sm leading-relaxed text-muted-foreground">
                {selectedDocument
                  ? `Document search is limited to ${selectedDocument.original_filename}. Remove the attachment above to search all indexed documents.`
                  : processedCount > 0
                    ? "Drag an indexed PDF from the library into this chat, or use Add document, to limit retrieval to one file."
                    : "Ask general aviation questions, or upload and process a PDF in the library for cited document answers."}
              </p>
            </div>
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
                selectedDocument
                  ? `Ask about ${selectedDocument.original_filename}…`
                  : "Ask the aviation intelligence agent…"
              }
              disabled={busy}
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
              ? "retrieval limited to attached document"
              : processedCount > 0
                ? `retrieval across ${processedCount} indexed documents`
                : "no indexed documents"}{" "}
            · enter to send · shift+enter for newline
          </p>
        </div>
      </div>
    </section>
  );
}
