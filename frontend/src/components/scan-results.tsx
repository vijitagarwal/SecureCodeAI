"use client";

import { useState } from "react";
import { Api, errorMessage, Finding, formatDate, Scan, Severity, Workspace } from "../lib/api";
import { FindingCard } from "./finding-card";
import { Pagination } from "./pagination";
import { useRequest } from "../lib/use-request";

const severities: Severity[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"];
function countFor(scan: Scan, severity: Severity | "ALL") {
  const counts = { ALL: scan.total_findings, CRITICAL: scan.critical_count, HIGH: scan.high_count, MEDIUM: scan.medium_count, LOW: scan.low_count, INFO: scan.info_count };
  return counts[severity];
}

export function ScanResults({ api, scanId, workspace, onDeleted }: { api: Api; scanId: number; workspace: Workspace; onDeleted: () => void }) {
  const [severity, setSeverity] = useState<Severity | "ALL">("ALL");
  const [offset, setOffset] = useState(0);
  const [actionError, setActionError] = useState<string | null>(null);
  const [action, setAction] = useState<string | null>(null);
  const [retry, setRetry] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const scanRequest = useRequest<Scan>(api, `/scans/${scanId}`, retry);
  const findingsRequest = useRequest<Finding[]>(api, `/scans/${scanId}/findings?limit=20&offset=${offset}${severity === "ALL" ? "" : `&severity=${severity}`}`, retry);
  const scan = scanRequest.data;
  const findings = findingsRequest.data ?? [];
  const busy = scanRequest.busy || findingsRequest.busy;
  const error = scanRequest.error ?? findingsRequest.error;

  async function exportReport() {
    setAction("export"); setActionError(null);
    try {
      const report = await api<unknown>(`/scans/${scanId}/report`);
      const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }));
      const anchor = document.createElement("a"); anchor.href = url; anchor.download = `securecode-scan-${scanId}.json`;
      anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) { setActionError(errorMessage(error)); }
    finally { setAction(null); }
  }
  async function removeScan() {
    setAction("delete"); setActionError(null);
    try { await api(`/scans/${scanId}`, { method: "DELETE" }); onDeleted(); }
    catch (error) { setActionError(errorMessage(error)); }
    finally { setAction(null); }
  }
  return <section className="results" aria-label="Scan results" aria-busy={busy}>
    <div className="panel">
      <div className="section-heading"><div><p className="eyebrow">SCAN #{scanId}</p><h2>{scan?.name ?? "Security findings"}</h2></div>
        <button className="secondary small" disabled={busy} onClick={() => setRetry(value => value + 1)}>Reload results</button></div>
      {busy && <p role="status">Loading results…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {scan && <>
        <p className="muted"><span className={`scan-status status-${scan.status}`}>{scan.status}</span> · {formatDate(scan.created_at)} · {scan.scanner_names.join(", ")}</p>
        {scan.status === "failed" && <p className="error" role="alert">{scan.failure_reason ?? "This scan failed."} No clean-code conclusion is available.</p>}
        {(scan.status === "queued" || scan.status === "running") && <p role="status">Scan in progress. Reload results to check its status.</p>}
        {scan.status === "completed" && <>
          <div className="severity-counts">{severities.map(value => <div key={value}><strong>{countFor(scan, value)}</strong><span className={`severity severity-${value.toLowerCase()}`}>{value}</span></div>)}</div>
          <label className="filter">Filter severity <select value={severity} onChange={event => { setSeverity(event.target.value as Severity | "ALL"); setOffset(0); }}>
            <option value="ALL">All severities ({scan.total_findings})</option>
            {severities.map(value => <option key={value} value={value}>{value} ({countFor(scan, value)})</option>)}
          </select></label>
        </>}
        {(scan.status === "completed" || scan.status === "failed") && <div className="actions">
          <button className="secondary" disabled={action !== null} onClick={exportReport}>{action === "export" ? "Exporting…" : "Export JSON report"}</button>
          <button className="danger secondary" disabled={action !== null} onClick={() => setConfirmDelete(true)}>Delete scan</button>
        </div>}
        {confirmDelete && <div className="delete-confirm" role="group" aria-label="Confirm deletion">
          <p>Delete this scan, all its source snippets, and saved analyses?</p>
          <div className="actions"><button className="danger" disabled={action !== null} onClick={removeScan}>Confirm delete</button><button className="secondary" disabled={action !== null} onClick={() => setConfirmDelete(false)}>Keep scan</button></div>
        </div>}
        {actionError && <p className="error" role="alert">{actionError}</p>}
      </>}
    </div>
    {!busy && !error && scan?.status === "completed" && <>
      {findings.length === 0 && <div className="panel empty" role="status"><h3>{scan.total_findings === 0 ? "No findings reported" : "No matching findings"}</h3>
        <p>{scan.total_findings === 0 ? "Bandit found no supported security patterns. This is not a guarantee that the code is secure." : "Choose another severity to review the remaining findings."}</p></div>}
      {findings.map(finding => <FindingCard key={finding.id} finding={finding} api={api} workspace={workspace} />)}
      <Pagination offset={offset} limit={20} total={countFor(scan, severity)} onPage={setOffset} />
    </>}
  </section>;
}
