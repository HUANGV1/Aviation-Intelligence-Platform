export type SourceType =
  | "NTSB"
  | "FAA"
  | "WEATHER"
  | "SOP"
  | "OTHER";

export const SOURCE_META: Record<
  SourceType,
  { label: string; code: string; tone: string }
> = {
  NTSB: { label: "Accident Report", code: "NTSB", tone: "text-destructive" },
  FAA: { label: "FAA Advisory", code: "FAA", tone: "text-primary" },
  WEATHER: { label: "Weather / METAR", code: "WX", tone: "text-accent" },
  SOP: { label: "Standard Ops", code: "SOP", tone: "text-muted-foreground" },
  OTHER: { label: "Document", code: "DOC", tone: "text-muted-foreground" },
};

export function normalizeSourceType(value: string): SourceType {
  const upper = value.toUpperCase();
  if (upper in SOURCE_META) {
    return upper as SourceType;
  }
  return "OTHER";
}
