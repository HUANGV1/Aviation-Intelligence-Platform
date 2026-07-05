type HealthResponse = {
  status: string;
  service: string;
  database: {
    connected: boolean;
    error: string | null;
  };
};

async function fetchHealth(): Promise<{
  data: HealthResponse | null;
  error: string | null;
}> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
  const { data, error } = await fetchHealth();

  return (
    <main>
      <h1>Aviation Intelligence Platform</h1>
      <p className="subtitle">
        Phase 1 foundation — frontend connected to backend health check.
      </p>

      <section className="card">
        <h2>System Status</h2>

        {error && (
          <p className="error-text">
            Could not reach backend: {error}
          </p>
        )}

        {data && (
          <>
            <div className="status-row">
              <span className="label">Backend</span>
              <StatusBadge status={data.status} />
            </div>
            <div className="status-row">
              <span className="label">Service</span>
              <span>{data.service}</span>
            </div>
            <div className="status-row">
              <span className="label">Database</span>
              <StatusBadge
                status={data.database.connected ? "healthy" : "degraded"}
              />
            </div>
            {data.database.error && (
              <p className="error-text">{data.database.error}</p>
            )}
            <pre>{JSON.stringify(data, null, 2)}</pre>
          </>
        )}

        {!data && !error && (
          <StatusBadge status="loading" />
        )}
      </section>
    </main>
  );
}
