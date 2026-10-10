"use client";

import { FormEvent, useMemo, useState } from "react";
import { createApi, errorMessage, Workspace } from "../lib/api";
import { Dashboard } from "../components/dashboard";

export default function Home() {
  const [session, setSession] = useState<{ key: string; workspace: Workspace } | null>(null);
  const api = useMemo(() => session ? createApi(session.key) : null, [session]);
  return <main>
    <header className="app-header">
      <div><p className="eyebrow">PYTHON SECURITY WORKSPACE</p><h1>SecureCode AI</h1></div>
      {session && <button className="secondary" onClick={() => setSession(null)}>Lock workspace</button>}
    </header>
    <p className="intro">Find risky code. Understand the evidence. Review a safer approach.</p>
    {session && api
      ? <Dashboard api={api} workspace={session.workspace} />
      : <AccessGate onUnlock={(key, workspace) => setSession({ key, workspace })} />}
    <footer>Bandit static analysis · Python source is never executed · Findings require developer review</footer>
  </main>;
}

function AccessGate({ onUnlock }: { onUnlock: (key: string, workspace: Workspace) => void }) {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function unlock(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError(null);
    try {
      const workspace = await createApi(key)<Workspace>("/workspace");
      onUnlock(key, workspace);
    } catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  return <section className="panel access" aria-labelledby="access-heading">
    <p className="eyebrow">PRIVATE BY DEFAULT</p>
    <h2 id="access-heading">Unlock your workspace</h2>
    <p>Use the API_KEY configured on your server. The key stays in this tab’s memory and is cleared when you lock or reload.</p>
    <form onSubmit={unlock}>
      <label htmlFor="access-key">Workspace access key</label>
      <input id="access-key" type="password" required minLength={32} autoComplete="off" value={key} onChange={event => setKey(event.target.value)} />
      <button disabled={busy}>{busy ? "Connecting…" : "Unlock workspace"}</button>
    </form>
    {error && <p className="error" role="alert">{error}</p>}
  </section>;
}
