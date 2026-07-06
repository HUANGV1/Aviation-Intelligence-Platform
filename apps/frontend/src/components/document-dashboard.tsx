/**
 * Purpose: Shared client state for upload, library, and semantic search panels.
 * Interactions: Receives the server-loaded document list from page.tsx and keeps
 * all document-aware widgets in sync after uploads, deletes, processing, or cancel.
 */
"use client";

import { useEffect, useState } from "react";

import { CitedAnswer } from "@/components/cited-answer";
import { DocumentLibrary } from "@/components/document-library";
import { DocumentUpload } from "@/components/document-upload";
import type { Document } from "@/lib/api";

type DocumentDashboardProps = {
  initialDocuments: Document[];
  documentsError: string | null;
};

export function DocumentDashboard({
  initialDocuments,
  documentsError,
}: DocumentDashboardProps) {
  const [documents, setDocuments] = useState(initialDocuments);

  useEffect(() => {
    setDocuments(initialDocuments);
  }, [initialDocuments]);

  function handleUploaded(document: Document) {
    setDocuments((current) => [
      document,
      ...current.filter((item) => item.id !== document.id),
    ]);
  }

  return (
    <>
      <section className="card">
        <h2>Upload Document</h2>
        <p className="helper-text">
          PDF only. Files are stored locally and indexed in Supabase metadata.
        </p>
        <DocumentUpload onUploaded={handleUploaded} />
      </section>

      <section className="card">
        <DocumentLibrary
          documents={documents}
          error={documentsError}
          onDocumentsChange={setDocuments}
        />
      </section>

      <section className="card">
        <CitedAnswer documents={documents} />
      </section>
    </>
  );
}
