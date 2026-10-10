"use client";

import { useState } from "react";
import { Analysis, Api, errorMessage, Finding, Workspace } from "../lib/api";

export function FindingCard({ finding, api, workspace }: { finding: Finding; api: Api; workspace: Workspace }) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function loadAnalysis() {
    setBusy(true); setError(null);
    try {
      setAnalysis(await api<Analysis>(`/findings/${finding.id}/analysis`, { method: finding.analysis_available ? "GET" : "POST" }));
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <article className="panel finding-card">
    <div className="section-heading"><span className={`severity severity-${finding.severity.toLowerCase()}`}>{finding.severity}</span>
      <span className="muted">{finding.rule_id} · {finding.confidence} confidence</span></div>
    <h3>{finding.title}</h3>
    <p className="location">{finding.file_path}:{finding.line_number ?? "?"}</p>
    <dl className="classification">
      <div><dt>CWE</dt><dd>{finding.cwe_id ? `${finding.cwe_id} · ${finding.cwe_name}` : "Unmapped — manual review"}</dd></div>
      <div><dt>OWASP 2021</dt><dd>{finding.owasp_category ?? "Unmapped — manual review"}</dd></div>
    </dl>
    {finding.code_snippet && <pre aria-label="Source snippet"><code>{finding.code_snippet}</code></pre>}
    <p><strong>Remediation guidance:</strong> {finding.remediation_guidance}</p>
    {!analysis && <>
      {workspace.remote_analysis && !finding.analysis_available && <p className="muted">Generating analysis sends this finding and snippet to {workspace.analysis_provider}.</p>}
      <button className="secondary" onClick={loadAnalysis} disabled={busy}>
        {busy ? "Loading analysis…" : finding.analysis_available ? "View saved analysis" : workspace.remote_analysis ? `Analyze with ${workspace.analysis_provider}` : "Generate local guidance"}
      </button>
    </>}
    {error && <p className="error" role="alert">{error}</p>}
    {analysis && <section className="analysis" aria-label="Security analysis">
      <p className="eyebrow">{(analysis.provider ?? workspace.analysis_provider) === "mock" ? "LOCAL RULE-BASED GUIDANCE · NO LLM" : `AI ANALYSIS · ${analysis.provider ?? workspace.analysis_provider}${analysis.model ? ` / ${analysis.model}` : ""}`}</p>
      <h4>{analysis.finding_summary}</h4>
      <p><strong>Root cause:</strong> {analysis.root_cause}</p>
      <p><strong>Security impact:</strong> {analysis.security_impact}</p>
      <p><strong>False-positive review:</strong> {analysis.false_positive_assessment}</p>
      <p><strong>Recommended remediation:</strong> {analysis.remediation}</p>
      {analysis.fixed_code && <><h4>Proposed code</h4><pre><code>{analysis.fixed_code}</code></pre></>}
      {analysis.diff && <><h4>Proposed diff</h4><pre><code>{analysis.diff}</code></pre></>}
      <p className="muted">Review and test proposed changes in your project before applying them.</p>
    </section>}
  </article>;
}
