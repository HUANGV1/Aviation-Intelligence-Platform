"use client";

import { useState } from "react";
import { ChevronRight, Cloud, FileText, Quote, Radio, Wrench } from "lucide-react";

import { formatTime } from "@/lib/format";
import type { ChatMessage, OperationalSourceBundle, ToolActivity } from "@/lib/chat-types";
import { cn } from "@/lib/utils";

function ToolActivityList({ activities }: { activities: ToolActivity[] }) {
  if (!activities.length) return null;

  return (
    <div className="mb-3 flex flex-wrap gap-2">
      {activities.map((activity) => (
        <span
          key={`${activity.toolName}-${activity.summary}`}
          className={cn(
            "inline-flex items-center gap-1.5 rounded border px-2 py-1 text-xs",
            activity.status === "success"
              ? "border-accent/40 bg-accent/10 text-accent"
              : "border-destructive/40 bg-destructive/10 text-destructive",
          )}
        >
          <Wrench className="size-3" />
          <span className="mono-label">{activity.toolName}</span>
          <span className="text-foreground/80">{activity.summary}</span>
        </span>
      ))}
    </div>
  );
}

function OperationalSourceList({
  sources,
}: {
  sources: OperationalSourceBundle[];
}) {
  const [open, setOpen] = useState(true);
  if (!sources.length) return null;

  return (
    <div className="mt-3 rounded-md border border-border bg-background/60">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-3 py-2"
      >
        <span className="flex items-center gap-2">
          <Cloud className="size-3 text-accent" />
          <span className="mono-label text-muted-foreground">
            live operational sources
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
        <div className="flex flex-col gap-3 border-t border-border px-3 py-3">
          {sources.map((source) => (
            <div key={`${source.provider}-${source.sourceType}-${source.retrievedAt}`}>
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="mono-label rounded bg-accent/15 px-1.5 py-0.5 text-accent">
                  {source.sourceType}
                </span>
                <span className="text-muted-foreground">{source.provider}</span>
                <span className="mono-label text-muted-foreground">
                  retrieved {formatTime(source.retrievedAt)}
                </span>
                {!source.isLive && (
                  <span className="mono-label text-destructive">not live</span>
                )}
              </div>
              {source.records.length === 0 ? (
                <p className="mt-2 text-xs text-muted-foreground">
                  No matching live records were returned.
                </p>
              ) : (
                <ul className="mt-2 flex flex-col gap-2">
                  {source.records.map((record, index) => (
                    <li
                      key={`${record.recordId}-${index}`}
                      className="rounded border border-border/70 bg-card/40 px-3 py-2"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-xs font-medium text-foreground">
                          {record.title}
                        </span>
                        {record.location && (
                          <span className="mono-label text-muted-foreground">
                            {record.location}
                          </span>
                        )}
                      </div>
                      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                        {record.summary}
                      </p>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

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
          {message.directAnswer && (
            <span className="mono-label text-muted-foreground">direct answer</span>
          )}
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
              thinking
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
            {message.toolActivities && (
              <ToolActivityList activities={message.toolActivities} />
            )}
            {message.content}
            {message.operationalSources && (
              <OperationalSourceList sources={message.operationalSources} />
            )}
            {message.citations && <CitationList citations={message.citations} />}
          </div>
        )}
      </div>
    </div>
  );
}
