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

type Finding = {
  id: number;
  rule_id: string;
  title: string;
  description: string;
  severity: string;
  confidence: string;
  file_path: string;
  line_number: number | null;
  code_snippet: string | null;
  cwe_id: string | null;
  cwe_name: string | null;
  owasp_category: string | null;
  remediation_guidance: string;
  analysis_available: boolean;
};

type Analysis = {
  finding_summary: string;
  root_cause: string;
  security_impact: string;
  false_positive_assessment: string;
  remediation: string;
  fixed_code: string | null;
  diff: string | null;
  confidence: number;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsLoading, setFindingsLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const [analysis, setAnalysis] = useState<Record<number, Analysis>>({});
  const [analysisLoading, setAnalysisLoading] = useState<number | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${apiUrl}/api/health`)
      .then((response) => {
        if (!response.ok) throw new Error(`Backend returned ${response.status}`);
        return response.json() as Promise<HealthResponse>;
      })
      .then(setHealth)
      .catch((requestError: Error) => setError(requestError.message));
  }, []);

  async function requestAnalysis(findingId: number) {
    setAnalysisLoading(findingId);
    setAnalysisError(null);
    try {
      const response = await fetch(`${apiUrl}/api/findings/${findingId}/analysis`, { method: "POST" });
      const payload = await response.json() as Analysis & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? `Analysis failed (${response.status})`);
      setAnalysis((current) => ({ ...current, [findingId]: payload }));
    } catch (requestError) {
      setAnalysisError(requestError instanceof Error ? requestError.message : "Analysis failed.");
    } finally {
      setAnalysisLoading(null);
    }
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedFile) {
      setUploadError("Choose a Python file before uploading.");
      return;
    }

    setUploading(true);
    setUploadError(null);
    setUploadResult(null);
    setFindings([]);
    setAnalysis({});
    setAnalysisError(null);
    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${apiUrl}/api/scans`, { method: "POST", body: formData });
      const payload = await response.json() as UploadResponse & { detail?: string };
      if (!response.ok) throw new Error(payload.detail ?? `Upload failed with status ${response.status}`);
      setUploadResult(payload);
      setFindingsLoading(true);
      const findingsResponse = await fetch(`${apiUrl}/api/scans/${payload.scan_id}/findings`);
      const findingsPayload = await findingsResponse.json() as Finding[] & { detail?: string };
      if (!findingsResponse.ok) {
        throw new Error(findingsPayload.detail ?? `Findings could not be loaded (${findingsResponse.status})`);
      }

      setFindings(findingsPayload);
    } catch (requestError) {
      setUploadError(requestError instanceof Error ? requestError.message : "The upload failed.");
    } finally {
      setUploading(false);
      setFindingsLoading(false);
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
      {uploadResult && (
        <section className="findings-panel" aria-labelledby="findings-heading">
          <div className="findings-header">
            <div>
              <p className="eyebrow">STATIC ANALYSIS RESULTS</p>
              <h2 id="findings-heading">Security findings</h2>
            </div>
            <label className="filter-label">
              Severity
              <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
                <option value="ALL">All severities</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </label>
          </div>
          {findingsLoading && <p className="form-message" role="status">Loading findings...</p>}
          {!findingsLoading && findings.length === 0 && (
            <p className="empty-state" role="status">No security findings were reported for this file.</p>
          )}
          <div className="finding-list">
            {findings
              .filter((finding) => severityFilter === "ALL" || finding.severity === severityFilter)
              .map((finding) => (
                <article className="finding-card" key={finding.id}>
                  <div className="finding-card-header">
                    <span className={`severity severity-${finding.severity.toLowerCase()}`}>{finding.severity}</span>
                    <span className="finding-location">{finding.file_path}:{finding.line_number ?? "?"}</span>
                  </div>
                  <h3>{finding.title}</h3>
                  <p>{finding.description}</p>
                  <p className="finding-meta">{finding.rule_id} · {finding.confidence} confidence</p>
                  <dl className="classification">
                    <div><dt>CWE</dt><dd>{finding.cwe_id ? `${finding.cwe_id} · ${finding.cwe_name}` : "Unmapped"}</dd></div>
                    <div><dt>OWASP</dt><dd>{finding.owasp_category ?? "Unmapped"}</dd></div>
                  </dl>
                  <p className="remediation-guidance"><strong>Guidance:</strong> {finding.remediation_guidance}</p>
                  {finding.code_snippet && <pre><code>{finding.code_snippet}</code></pre>}
                  <button
                    className="analysis-button"
                    type="button"
                    onClick={() => requestAnalysis(finding.id)}
                    disabled={analysisLoading === finding.id}
                  >
                    {analysisLoading === finding.id ? "Analyzing..." : analysis[finding.id] ? "Re-run AI analysis" : "Analyze with SecureCode AI"}
                  </button>
                  {analysisError && analysisLoading === null && <p className="form-message error" role="alert">{analysisError}</p>}
                  {analysis[finding.id] && (
                    <div className="analysis-card" aria-label="AI security analysis">
                      <p className="analysis-label">AI ANALYSIS · {Math.round(analysis[finding.id].confidence * 100)}% confidence</p>
                      <h4>{analysis[finding.id].finding_summary}</h4>
                      <p><strong>Root cause:</strong> {analysis[finding.id].root_cause}</p>
                      <p><strong>Security impact:</strong> {analysis[finding.id].security_impact}</p>
                      <p><strong>False-positive review:</strong> {analysis[finding.id].false_positive_assessment}</p>
                      <p><strong>Recommended remediation:</strong> {analysis[finding.id].remediation}</p>
                      {analysis[finding.id].diff && <pre><code>{analysis[finding.id].diff}</code></pre>}
                    </div>
                  )}
                </article>
              ))}
          </div>
        </section>
      )}
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
