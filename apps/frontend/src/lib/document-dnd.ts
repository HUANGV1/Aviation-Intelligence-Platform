/** Drag-and-drop MIME type for scoping a library document into chat. */
export const DOCUMENT_SCOPE_MIME = "application/x-aip-document-id";

export function setDocumentDragData(
  dataTransfer: DataTransfer,
  documentId: string,
) {
  dataTransfer.setData(DOCUMENT_SCOPE_MIME, documentId);
  dataTransfer.effectAllowed = "copy";
}

export function getDocumentDragId(dataTransfer: DataTransfer): string | null {
  const id = dataTransfer.getData(DOCUMENT_SCOPE_MIME);
  return id.trim() || null;
}

export function isDocumentDrag(dataTransfer: DataTransfer): boolean {
  return Array.from(dataTransfer.types).includes(DOCUMENT_SCOPE_MIME);
}
