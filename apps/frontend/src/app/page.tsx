/**
 * Purpose: Main workspace page — document library and cited Q&A chat console.
 * Interactions: Server component that fetches data via lib/api.ts and renders
 * Workspace for client-side document and chat interactions.
 */
import { Workspace } from "@/components/workspace";
import { fetchDocuments, fetchHealth } from "@/lib/api";

export default async function HomePage() {
  const [
    { data: health, error: healthError },
    { data: documents, error: documentsError },
  ] = await Promise.all([fetchHealth(), fetchDocuments()]);

  return (
    <Workspace
      initialDocuments={documents?.documents ?? []}
      initialHealth={health}
      healthError={healthError}
      documentsError={documentsError}
    />
  );
}
