/**
 * Purpose: Shared HTTP client and TypeScript types for the FastAPI backend.
 * Interactions: Used by page.tsx and document-upload.tsx. Calls /health,
 * /documents, and /documents/upload using NEXT_PUBLIC_API_URL from .env.local.
 */
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

export function getDocumentFileUrl(documentId: string): string {
  return `${getApiUrl()}/documents/${documentId}/file`;
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

export function formatTimestamp(value: string): string {
  // Fixed locale avoids SSR/client hydration mismatches (e.g. "p.m." vs "PM").
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
