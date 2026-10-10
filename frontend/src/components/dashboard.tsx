"use client";

import { FormEvent, useRef, useState } from "react";
import { Api, errorMessage, formatDate, ScanPage, Workspace } from "../lib/api";
import { ScanResults } from "./scan-results";
import { Pagination } from "./pagination";
import { useRequest } from "../lib/use-request";

export function Dashboard({ api, workspace }: { api: Api; workspace: Workspace }) {
  const [selected, setSelected] = useState<number | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [offset, setOffset] = useState(0);
  return <>
    <UploadPanel api={api} workspace={workspace} onCreated={id => {
      setSelected(id); setOffset(0); setRefresh(value => value + 1);
    }} />
    <div className="workspace-grid">
      <History api={api} selected={selected} onSelect={setSelected} refresh={refresh} offset={offset} onPage={setOffset} />
      {selected !== null
        ? <ScanResults key={selected} api={api} scanId={selected} workspace={workspace} onDeleted={() => {
          setSelected(null); setOffset(0); setRefresh(value => value + 1);
        }} />
        : <section className="panel empty" aria-label="Scan results"><h2>Ready to review</h2><p>Run a scan or choose one from your history to explore its findings.</p></section>}
    </div>
  </>;
}

function UploadPanel({ api, workspace, onCreated }: { api: Api; workspace: Workspace; onCreated: (id: number) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const input = useRef<HTMLInputElement>(null);
  async function upload(event: FormEvent) {
    event.preventDefault(); setError(null);
    if (!file) { setError("Choose a Python file first."); return; }
    if (!/\.py$/i.test(file.name)) { setError("Only Python (.py) files are supported."); return; }
    if (file.size === 0 || file.size > workspace.max_upload_size_bytes) { setError("Choose a non-empty file within the upload limit."); return; }
    setBusy(true);
    const body = new FormData(); body.append("file", file);
    try {
      const result = await api<{ scan_id: number }>("/scans", { method: "POST", body });
      onCreated(result.scan_id); setFile(null);
      if (input.current) input.current.value = "";
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <section className="panel upload-panel" aria-labelledby="upload-heading">
    <div><p className="eyebrow">NEW SCAN</p><h2 id="upload-heading">Inspect Python source</h2>
      <p className="muted">One .py file · Up to {(workspace.max_upload_size_bytes / 1024 / 1024).toFixed(1)} MB · Temporary source removed after scanning</p></div>
    <form onSubmit={upload}>
      <label htmlFor="source-file" className="sr-only">Python source file</label>
      <input ref={input} id="source-file" type="file" accept=".py" disabled={busy} onChange={event => setFile(event.target.files?.[0] ?? null)} />
      <button disabled={busy || !file}>{busy ? "Scanning…" : "Run security scan"}</button>
    </form>
    {busy && <p role="status">Analyzing with Bandit. This can take up to 30 seconds.</p>}
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}

function History({ api, selected, onSelect, refresh, offset, onPage }: {
  api: Api; selected: number | null; onSelect: (id: number) => void;
  refresh: number; offset: number; onPage: (offset: number) => void;
}) {
  const [retry, setRetry] = useState(0);
  const { data: page, busy, error } = useRequest<ScanPage>(api, `/scans?offset=${offset}&limit=10`, `${refresh}:${retry}`);
  return <aside className="panel history" aria-labelledby="history-heading">
    <div className="section-heading"><h2 id="history-heading">Scan history</h2><button className="secondary small" disabled={busy} onClick={() => setRetry(value => value + 1)}>Refresh</button></div>
    {busy && <p role="status">Loading history…</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {!busy && !error && page && <>
      {page.total === 0 && <p className="muted">Your first scan will appear here.</p>}
      <ul className="history-list">{page.items.map(scan => <li key={scan.id}>
        <button aria-label={`${scan.name} ${scan.status}, scan ${scan.id}`} className={`history-item ${scan.id === selected ? "selected" : ""}`} onClick={() => onSelect(scan.id)} aria-current={scan.id === selected ? "true" : undefined}>
          <strong>{scan.name}</strong><span className={`scan-status status-${scan.status}`}>{scan.status}</span>
          <span>{scan.total_findings} findings · #{scan.id}</span><time dateTime={scan.created_at}>{formatDate(scan.created_at)}</time>
        </button>
      </li>)}</ul>
      <Pagination offset={offset} limit={10} total={page.total} onPage={onPage} />
    </>}
  </aside>;
}
