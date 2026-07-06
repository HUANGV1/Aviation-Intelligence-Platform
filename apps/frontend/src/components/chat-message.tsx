"use client";

import { useState } from "react";
import { ChevronRight, FileText, Quote, Radio } from "lucide-react";

import { formatTime } from "@/lib/format";
import type { ChatMessage } from "@/lib/chat-types";
import { cn } from "@/lib/utils";

function CitationList({
  citations,
}: {
  citations: NonNullable<ChatMessage["citations"]>;
}) {
  const [open, setOpen] = useState(true);
  if (!citations.length) return null;
  return (
    <div className="mt-3 rounded-md border border-border bg-background/60">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between px-3 py-2"
      >
        <span className="flex items-center gap-2">
          <Quote className="size-3 text-accent" />
          <span className="mono-label text-muted-foreground">
            {citations.length} sources
          </span>
        </span>
        <ChevronRight
          className={cn(
            "size-3.5 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
      </button>
      {open && (
        <ul className="flex flex-col gap-px border-t border-border">
          {citations.map((c) => (
            <li
              key={c.id}
              className="group px-3 py-2.5 transition-colors hover:bg-accent/5"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="flex min-w-0 items-center gap-1.5">
                  <FileText className="size-3 shrink-0 text-accent" />
                  <span className="truncate text-xs font-medium text-foreground">
                    {c.documentName}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-2">
                  <span className="mono-label text-muted-foreground">
                    {c.sourceId}
                  </span>
                  {c.pageNumber != null && (
                    <span className="mono-label text-muted-foreground">
                      p.{c.pageNumber}
                    </span>
                  )}
                  <span className="mono-label rounded bg-accent/15 px-1.5 py-0.5 text-accent">
                    {(c.score * 100).toFixed(0)}%
                  </span>
                </span>
              </div>
              <p className="mt-1.5 border-l-2 border-accent/40 pl-2.5 text-xs leading-relaxed text-muted-foreground">
                {c.snippet}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ChatMessageRow({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex animate-fade-rise justify-end">
        <div className="max-w-[85%]">
          <div className="mb-1 flex items-center justify-end gap-2">
            <span className="mono-label text-muted-foreground">
              {formatTime(message.createdAt)}
            </span>
            <span className="mono-label text-primary">You</span>
          </div>
          <div className="rounded-md rounded-tr-none border border-primary/40 bg-primary/10 px-3.5 py-2.5 text-sm leading-relaxed text-foreground">
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex animate-fade-rise gap-3">
      <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md border border-primary/40 bg-primary/10 text-primary">
        <Radio className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="mb-1 flex items-center gap-2">
          <span className="mono-label text-primary">AIP</span>
          {message.insufficientEvidence && (
            <span className="mono-label text-destructive">
              insufficient evidence
            </span>
          )}
          {!message.pending && (
            <span className="mono-label text-muted-foreground">
              {formatTime(message.createdAt)}
            </span>
          )}
        </div>
        {message.pending ? (
          <div className="flex items-center gap-1.5 py-1">
            <span className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.2s]" />
            <span className="size-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.1s]" />
            <span className="size-1.5 animate-bounce rounded-full bg-primary" />
            <span className="mono-label ml-1 text-muted-foreground">
              retrieving
            </span>
          </div>
        ) : (
          <div
            className={cn(
              "rounded-md rounded-tl-none border px-3.5 py-3 text-sm leading-relaxed text-foreground",
              message.insufficientEvidence
                ? "border-destructive/40 bg-destructive/5"
                : "border-border bg-card/60",
            )}
          >
            {message.content}
            {message.citations && <CitationList citations={message.citations} />}
          </div>
        )}
      </div>
    </div>
  );
}
