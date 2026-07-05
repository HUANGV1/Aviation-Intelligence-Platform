/**
 * Purpose: Main dashboard page — system health, PDF upload, and document library.
 * Interactions: Server component that fetches data via lib/api.ts and renders
 * DocumentUpload (client) and DocumentLibrary. Entry point at http://localhost:3000.
 */
import { DocumentLibrary } from "@/components/document-library";
import { DocumentUpload } from "@/components/document-upload";
import { fetchDocuments, fetchHealth } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  const className =
    normalized === "healthy"
      ? "badge healthy"
      : normalized === "loading"
        ? "badge loading"
        : "badge degraded";

  return <span className={className}>{status}</span>;
}

export default async function HomePage() {
  const [{ data: health, error: healthError }, { data: documents, error: documentsError }] =
    await Promise.all([fetchHealth(), fetchDocuments()]);

  return (
    <main>
      <h1>Aviation Intelligence Platform</h1>
      <p className="subtitle">
        Upload aviation PDFs and manage your document library.
      </p>

      <div className="page-grid">
        <section className="card compact-card">
          <h2>System Status</h2>

          {healthError && (
            <p className="error-text">Could not reach backend: {healthError}</p>
          )}

          {health && (
            <>
              <div className="status-row">
                <span className="label">Backend</span>
                <StatusBadge status={health.status} />
              </div>
              <div className="status-row">
                <span className="label">Database</span>
                <StatusBadge
                  status={health.database.connected ? "healthy" : "degraded"}
                />
              </div>
              {health.database.error && (
                <p className="error-text">{health.database.error}</p>
              )}
            </>
          )}

          {!health && !healthError && <StatusBadge status="loading" />}
        </section>

        <section className="card">
          <h2>Upload Document</h2>
          <p className="helper-text">
            PDF only. Files are stored locally and indexed in Supabase metadata.
          </p>
          <DocumentUpload />
        </section>

        <section className="card">
          <DocumentLibrary
            documents={documents?.documents ?? []}
            error={documentsError}
          />
        </section>
      </div>
    </main>
  );
}
