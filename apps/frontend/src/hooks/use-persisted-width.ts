"use client";

import { useCallback, useEffect, useState } from "react";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

export function usePersistedWidth(
  storageKey: string,
  {
    defaultWidth,
    minWidth,
    maxWidth,
  }: {
    defaultWidth: number;
    minWidth: number;
    maxWidth: number;
  },
) {
  const [width, setWidthState] = useState(defaultWidth);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = Number(raw);
      if (Number.isFinite(parsed)) {
        setWidthState(clamp(parsed, minWidth, maxWidth));
      }
    } catch {
      // Ignore storage failures (private mode, etc.).
    }
  }, [storageKey, minWidth, maxWidth]);

  const setWidth = useCallback(
    (next: number | ((prev: number) => number)) => {
      setWidthState((prev) => {
        const resolved = typeof next === "function" ? next(prev) : next;
        const clamped = clamp(resolved, minWidth, maxWidth);
        try {
          window.localStorage.setItem(storageKey, String(clamped));
        } catch {
          // Ignore storage failures.
        }
        return clamped;
      });
    },
    [storageKey, minWidth, maxWidth],
  );

  return [width, setWidth] as const;
}
