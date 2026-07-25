/**
 * Purpose: Shared HTTP client and TypeScript types for the FastAPI backend.
 * Interactions: Used by page.tsx, workspace.tsx, and document-library.tsx.
 * Calls /health, /documents, /agent/chat, and document processing endpoints.
 */
import type {
  ChatCitation,
  ChatMessageRecord,
  ChatSessionSummary,
  OperationalRecord,
  OperationalSourceBundle,
  ToolActivity as ChatToolActivity,
} from "@/lib/chat-types";
export type HealthResponse = {
  status: string;
  service: string;
  database: {
    connected: boolean;
    error: string | null;
  };
};

export type Document = {
  id: string;
  filename: string;
  original_filename: string;
  source_type: string;
  acquisition_mode: string;
  status: string;
  file_path: string;
  page_count: number | null;
  source_url: string | null;
  uploaded_at: string;
  retrieved_at: string | null;
  created_at: string;
  updated_at: string;
};

export type DocumentListResponse = {
  documents: Document[];
  total: number;
};

export type DocumentChunk = {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  page_number: number | null;
  section_title: string | null;
  token_count: number;
  created_at: string;
};

export type ChunkListResponse = {
  document_id: string;
  chunks: DocumentChunk[];
  total: number;
};

export type ProcessDocumentResponse = {
  document_id: string;
  status: string;
  page_count: number;
  chunk_count: number;
  message: string;
};

export type SearchResult = {
  chunk_id: string;
  document_id: string;
  document_name: string;
  chunk_index: number;
  text: string;
  page_number: number | null;
  section_title: string | null;
  similarity: number;
};

export type SearchResponse = {
  query: string;
  results: SearchResult[];
  total: number;
};

export type RagCitation = {
  source_id: string;
  chunk_id: string;
  document_id: string;
  document_name: string;
  chunk_index: number;
  text: string;
  page_number: number | null;
  section_title: string | null;
  similarity: number;
};

export type RagQueryResponse = {
  query: string;
  answer: string;
  citations: RagCitation[];
  insufficient_evidence: boolean;
  used_chunk_count: number;
};

export type ToolActivity = {
  tool_name: string;
  status: string;
  summary: string;
  error?: string | null;
};

export type OperationalRecordResponse = {
  record_id: string;
  title: string;
  summary: string;
  source_type: string;
  provider: string;
  source_url: string;
  retrieved_at: string;
  observed_at?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  location?: string | null;
  raw_text?: string | null;
  metadata?: Record<string, unknown>;
};

export type OperationalSourceBundleResponse = {
  provider: string;
  source_type: string;
  source_url: string;
  retrieved_at: string;
  records: OperationalRecordResponse[];
  pagination: Record<string, unknown>;
  is_live: boolean;
};

export type AgentChatResponse = {
  session_id?: string | null;
  message: string;
  answer: string;
  citations: RagCitation[];
  operational_sources: OperationalSourceBundleResponse[];
  insufficient_evidence: boolean;
  used_tools: string[];
  tool_activities: ToolActivity[];
  direct_answer: boolean;
  used_chunk_count: number;
};

export type ChatSessionSummaryResponse = {
  id: string;
  title: string | null;
  document_id: string | null;
  message_count: number;
  preview: string | null;
  created_at: string;
  updated_at: string;
};

export type ChatMessageRecordResponse = {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: RagCitation[];
  operational_sources: OperationalSourceBundleResponse[];
  tool_activities: ToolActivity[];
  used_tools: string[];
  direct_answer: boolean;
  insufficient_evidence: boolean;
  used_chunk_count: number;
  created_at: string;
};

export type ChatSessionDetailResponse = ChatSessionSummaryResponse & {
  messages: ChatMessageRecordResponse[];
};

export type ChatSessionListResponse = {
  sessions: ChatSessionSummaryResponse[];
  total: number;
};

export function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

export async function fetchHealth(): Promise<{
  data: HealthResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/health`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Backend responded with status ${response.status}`,
      };
    }

    const data = (await response.json()) as HealthResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function fetchDocuments(): Promise<{
  data: DocumentListResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/documents`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Failed to load documents (status ${response.status})`,
      };
    }

    const data = (await response.json()) as DocumentListResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function uploadDocument(file: File): Promise<{
  data: Document | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch(`${apiUrl}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      let errorMessage = `Upload failed (status ${response.status})`;

      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          errorMessage = payload.detail;
        } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
          const first = payload.detail[0] as { msg?: string };
          if (first.msg) {
            errorMessage = first.msg;
          }
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as Document;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function deleteDocument(documentId: string): Promise<{
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/documents/${documentId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      let errorMessage = `Delete failed (status ${response.status})`;

      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          errorMessage = payload.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { error: errorMessage };
    }

    return { error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { error: message };
  }
}

export function getDocumentFileUrl(documentId: string): string {
  return `${getApiUrl()}/documents/${documentId}/file`;
}

export async function processDocument(
  documentId: string,
  options: { signal?: AbortSignal } = {},
): Promise<{
  data: ProcessDocumentResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/documents/${documentId}/process`, {
      method: "POST",
      signal: options.signal,
    });

    if (!response.ok) {
      let errorMessage = `Processing failed (status ${response.status})`;

      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          errorMessage = payload.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as ProcessDocumentResponse;
    return { data, error: null };
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      return { data: null, error: "Processing cancelled." };
    }

    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function cancelDocumentProcessing(documentId: string): Promise<{
  data: Document | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/documents/${documentId}/cancel`, {
      method: "POST",
    });

    if (!response.ok) {
      let errorMessage = `Cancel failed (status ${response.status})`;

      try {
        const payload = (await response.json()) as { detail?: unknown };
        if (typeof payload.detail === "string") {
          errorMessage = payload.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as Document;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function fetchDocumentChunks(documentId: string): Promise<{
  data: ChunkListResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/documents/${documentId}/chunks`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Failed to load chunks (status ${response.status})`,
      };
    }

    const data = (await response.json()) as ChunkListResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function searchChunks(payload: {
  query: string;
  document_id?: string;
  top_k?: number;
}): Promise<{
  data: SearchResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/rag/search`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `Search failed (status ${response.status})`;

      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === "string") {
          errorMessage = body.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as SearchResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function queryRag(payload: {
  query: string;
  document_id?: string;
  top_k?: number;
}): Promise<{
  data: RagQueryResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/rag/query`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `Answer request failed (status ${response.status})`;

      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === "string") {
          errorMessage = body.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as RagQueryResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function sendAgentMessage(payload: {
  message: string;
  session_id?: string;
  document_id?: string;
  top_k?: number;
}): Promise<{
  data: AgentChatResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/agent/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let errorMessage = `Agent request failed (status ${response.status})`;

      try {
        const body = (await response.json()) as { detail?: unknown };
        if (typeof body.detail === "string") {
          errorMessage = body.detail;
        }
      } catch {
        // Keep the default error message.
      }

      return { data: null, error: errorMessage };
    }

    const data = (await response.json()) as AgentChatResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function fetchChatSessions(): Promise<{
  data: ChatSessionListResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/agent/sessions`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Failed to load chat sessions (status ${response.status})`,
      };
    }

    const data = (await response.json()) as ChatSessionListResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function fetchChatSession(sessionId: string): Promise<{
  data: ChatSessionDetailResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/agent/sessions/${sessionId}`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Failed to load chat session (status ${response.status})`,
      };
    }

    const data = (await response.json()) as ChatSessionDetailResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function createChatSession(payload: {
  title?: string;
  document_id?: string;
} = {}): Promise<{
  data: ChatSessionDetailResponse | null;
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/agent/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      return {
        data: null,
        error: `Failed to create chat session (status ${response.status})`,
      };
    }

    const data = (await response.json()) as ChatSessionDetailResponse;
    return { data, error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { data: null, error: message };
  }
}

export async function deleteChatSession(sessionId: string): Promise<{
  error: string | null;
}> {
  const apiUrl = getApiUrl();

  try {
    const response = await fetch(`${apiUrl}/agent/sessions/${sessionId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      return {
        error: `Failed to delete chat session (status ${response.status})`,
      };
    }

    return { error: null };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    return { error: message };
  }
}

export function toChatSessionSummary(
  session: ChatSessionSummaryResponse,
): ChatSessionSummary {
  return {
    id: session.id,
    title: session.title,
    documentId: session.document_id,
    messageCount: session.message_count,
    preview: session.preview,
    createdAt: session.created_at,
    updatedAt: session.updated_at,
  };
}

export function toChatMessageRecord(
  message: ChatMessageRecordResponse,
): ChatMessageRecord {
  return {
    id: message.id,
    sessionId: message.session_id,
    role: message.role,
    content: message.content,
    citations: message.citations.map(toChatCitation),
    operationalSources: message.operational_sources.map(toChatOperationalSource),
    createdAt: message.created_at,
    insufficientEvidence: message.insufficient_evidence,
    toolActivities: message.tool_activities.map(toChatToolActivity),
    directAnswer: message.direct_answer,
  };
}

export function formatTimestamp(value: string): string {
  // Fixed locale avoids SSR/client hydration mismatches (e.g. "p.m." vs "PM").
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function toChatCitation(citation: RagCitation): ChatCitation {
  return {
    id: citation.chunk_id,
    documentId: citation.document_id,
    documentName: citation.document_name,
    pageNumber: citation.page_number,
    snippet: citation.text,
    score: citation.similarity,
    sourceId: citation.source_id,
  };
}

export function toChatToolActivity(activity: ToolActivity): ChatToolActivity {
  return {
    toolName: activity.tool_name,
    status: activity.status,
    summary: activity.summary,
    error: activity.error ?? null,
  };
}

export function toChatOperationalRecord(
  record: OperationalRecordResponse,
): OperationalRecord {
  return {
    recordId: record.record_id,
    title: record.title,
    summary: record.summary,
    sourceType: record.source_type,
    provider: record.provider,
    sourceUrl: record.source_url,
    retrievedAt: record.retrieved_at,
    observedAt: record.observed_at ?? null,
    validFrom: record.valid_from ?? null,
    validTo: record.valid_to ?? null,
    location: record.location ?? null,
    rawText: record.raw_text ?? null,
  };
}

export function toChatOperationalSource(
  bundle: OperationalSourceBundleResponse,
): OperationalSourceBundle {
  return {
    provider: bundle.provider,
    sourceType: bundle.source_type,
    sourceUrl: bundle.source_url,
    retrievedAt: bundle.retrieved_at,
    records: bundle.records.map(toChatOperationalRecord),
    pagination: bundle.pagination,
    isLive: bundle.is_live,
  };
}

export function resolveDocumentScope(
  selectedDocumentId: string | null,
): { document_id?: string } {
  return selectedDocumentId ? { document_id: selectedDocumentId } : {};
}
