export interface ChatCitation {
  id: string;
  documentId: string;
  documentName: string;
  pageNumber: number | null;
  snippet: string;
  score: number;
  sourceId: string;
}

export interface ToolActivity {
  toolName: string;
  status: string;
  summary: string;
  error?: string | null;
}

export interface OperationalRecord {
  recordId: string;
  title: string;
  summary: string;
  sourceType: string;
  provider: string;
  sourceUrl: string;
  retrievedAt: string;
  observedAt?: string | null;
  validFrom?: string | null;
  validTo?: string | null;
  location?: string | null;
  rawText?: string | null;
}

export interface OperationalSourceBundle {
  provider: string;
  sourceType: string;
  sourceUrl: string;
  retrievedAt: string;
  records: OperationalRecord[];
  pagination: Record<string, unknown>;
  isLive: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sessionId?: string | null;
  scopedDocumentId: string | null;
  citations?: ChatCitation[];
  operationalSources?: OperationalSourceBundle[];
  createdAt: string;
  pending?: boolean;
  insufficientEvidence?: boolean;
  toolActivities?: ToolActivity[];
  directAnswer?: boolean;
}

export interface ChatSessionSummary {
  id: string;
  title: string | null;
  documentId: string | null;
  messageCount: number;
  preview: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ChatSessionDetail extends ChatSessionSummary {
  messages: ChatMessageRecord[];
}

export interface ChatMessageRecord {
  id: string;
  sessionId: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: ChatCitation[];
  operationalSources?: OperationalSourceBundle[];
  createdAt: string;
  pending?: boolean;
  insufficientEvidence?: boolean;
  toolActivities?: ToolActivity[];
  directAnswer?: boolean;
}
