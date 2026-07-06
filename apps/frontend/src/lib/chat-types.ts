export interface ChatCitation {
  id: string;
  documentId: string;
  documentName: string;
  pageNumber: number | null;
  snippet: string;
  score: number;
  sourceId: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  scopedDocumentId: string | null;
  citations?: ChatCitation[];
  createdAt: string;
  pending?: boolean;
  insufficientEvidence?: boolean;
}
