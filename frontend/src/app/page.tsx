"use client";

import { FormEvent, useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  backend: { status: string };
  database: { status: string; detail?: string };
};

type UploadResponse = {
  scan_id: number;
  status: string;
  filename: string;
  total_findings: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        return response.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError("Choose a Python file before uploading.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${apiUrl}/api/scans`, { method: "POST", body: formData });
      const payload = await response.json() as UploadResponse & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? `Upload failed with status ${response.status}`);
      setUploadResult(payload);
    } catch (requestError) {
      setUploadError(requestError instanceof Error ? requestError.message : "The upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <main>
      <p className="eyebrow">LOCAL SECURITY WORKSPACE</p>
      <h1>SecureCode AI</h1>
      <p className="intro">A verified foundation for deterministic source-code security analysis.</p>
      <section aria-label="System health" className="health-grid">
        <HealthCard label="Backend API" status={health?.backend.status} />
        <HealthCard label="PostgreSQL" status={health?.database.status} />
      </section>
      <p className="overall" role="status">
        {error ? `Unable to reach the backend: ${error}` : health ? `System status: ${health.status}` : "Checking services..."}
      </p>
      <section className="upload-panel" aria-labelledby="upload-heading">
        <p className="eyebrow">NEXT PIPELINE STEP</p>
        <h2 id="upload-heading">Upload Python source</h2>
        <form onSubmit={handleUpload}>
          <label className="file-picker">
            <span>{selectedFile?.name ?? "Choose a .py file"}</span>
            <input
              type="file"
              accept=".py"
              onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <button type="submit" disabled={uploading || !selectedFile}>
            {uploading ? "Uploading..." : "Upload"}
          </button>
        </form>
        {uploadError && <p className="form-message error" role="alert">{uploadError}</p>}
        {uploadResult && (
          <dl className="upload-result" aria-label="Upload result">
            <div><dt>Scan ID</dt><dd>{uploadResult.scan_id}</dd></div>
            <div><dt>Status</dt><dd>{uploadResult.status}</dd></div>
            <div><dt>Filename</dt><dd>{uploadResult.filename}</dd></div>
            <div><dt>Findings</dt><dd>{uploadResult.total_findings}</dd></div>
          </dl>
        )}
      </section>
    </main>
  );
}

function HealthCard({ label, status }: { label: string; status?: string }) {
  const isReady = status === "ok";
  return (
    <article className="health-card">
      <span className={`status-dot ${isReady ? "ready" : "pending"}`} aria-hidden="true" />
      <div><p className="card-label">{label}</p><strong>{status ?? "checking"}</strong></div>
    </article>
  );
}
