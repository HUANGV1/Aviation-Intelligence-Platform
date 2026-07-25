"use client";

import { useEffect, useRef, useState } from "react";

import { cn } from "@/lib/utils";

type SidebarResizeHandleProps = {
  /** Which side of the panel this handle sits on. */
  edge: "left" | "right";
  /** Called with the pointer delta in CSS pixels (positive = wider for that edge). */
  onResize: (deltaX: number) => void;
  disabled?: boolean;
  label: string;
};

export function SidebarResizeHandle({
  edge,
  onResize,
  disabled = false,
  label,
}: SidebarResizeHandleProps) {
  const [dragging, setDragging] = useState(false);
  const lastXRef = useRef(0);
  const onResizeRef = useRef(onResize);

  useEffect(() => {
    onResizeRef.current = onResize;
  }, [onResize]);

  useEffect(() => {
    if (!dragging) return;

    function onPointerMove(event: PointerEvent) {
      const delta = event.clientX - lastXRef.current;
      lastXRef.current = event.clientX;
      // Right-edge handle: drag right widens. Left-edge handle: drag left widens.
      onResizeRef.current(edge === "right" ? delta : -delta);
    }

    function onPointerUp() {
      setDragging(false);
    }

    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", onPointerUp);
    window.addEventListener("pointercancel", onPointerUp);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", onPointerUp);
      window.removeEventListener("pointercancel", onPointerUp);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };
  }, [dragging, edge]);

  if (disabled) return null;

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={label}
      tabIndex={0}
      onPointerDown={(event) => {
        event.preventDefault();
        lastXRef.current = event.clientX;
        setDragging(true);
      }}
      onKeyDown={(event) => {
        const step = event.shiftKey ? 32 : 12;
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          onResize(edge === "right" ? -step : step);
        } else if (event.key === "ArrowRight") {
          event.preventDefault();
          onResize(edge === "right" ? step : -step);
        }
      }}
      className={cn(
        "absolute top-0 z-20 flex h-full w-3 -translate-x-1/2 cursor-col-resize items-stretch justify-center",
        edge === "right" ? "right-0 translate-x-1/2" : "left-0",
        "touch-none select-none",
      )}
    >
      <span
        className={cn(
          "my-auto h-10 w-px rounded-full transition-colors",
          dragging
            ? "bg-primary"
            : "bg-border group-hover/sidebar:bg-primary/50 hover:bg-primary/70",
        )}
      />
    </div>
  );
}
