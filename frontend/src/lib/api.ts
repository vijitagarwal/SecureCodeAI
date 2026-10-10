export type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type Scan = {
  id: number; name: string; status: "queued" | "running" | "completed" | "failed";
  created_at: string; completed_at: string | null; scanner_names: string[];
  total_findings: number; critical_count: number; high_count: number;
  medium_count: number; low_count: number; info_count: number; failure_reason: string | null;
};
export type ScanPage = { items: Scan[]; total: number; offset: number; limit: number };
export type Workspace = { max_upload_size_bytes: number; analysis_provider: string; remote_analysis: boolean };
export type Finding = {
  id: number; rule_id: string; title: string; description: string; severity: Severity;
  confidence: string; file_path: string; line_number: number | null; code_snippet: string | null;
  cwe_id: string | null; cwe_name: string | null; owasp_category: string | null;
  remediation_guidance: string; analysis_available: boolean;
};
export type Analysis = {
  finding_summary: string; root_cause: string; security_impact: string;
  false_positive_assessment: string; remediation: string; fixed_code: string | null;
  diff: string | null; confidence: number; provider?: string; model?: string | null;
};

const baseUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function createApi(key: string) {
  return async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const timeout = new AbortController();
    const timer = setTimeout(() => timeout.abort(), 65000);
    try {
      const headers = new Headers(options.headers);
      headers.set("Authorization", `Bearer ${key}`);
      const response = await fetch(`${baseUrl}/api${path}`, {
        ...options, headers, cache: "no-store",
        signal: options.signal ? AbortSignal.any([options.signal, timeout.signal]) : timeout.signal,
      });
      if (response.status === 204) return undefined as T;
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = payload && typeof payload === "object" && "detail" in payload ? payload.detail : null;
        throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status}). Please try again.`);
      }
      if (payload === null) throw new Error("The API returned an invalid response.");
      return payload as T;
    } catch (error) {
      if (timeout.signal.aborted) throw new Error("Request timed out. Refresh scan history before retrying an upload.");
      if (error instanceof TypeError) throw new Error("Cannot reach the API. Check that the backend is running, then retry.");
      throw error;
    } finally {
      clearTimeout(timer);
    }
  };
}

export type Api = ReturnType<typeof createApi>;
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "The request failed. Please try again.";
}
export function formatDate(value: string): string {
  // Older SQLite records have no offset; stored timestamps are UTC.
  return new Date(/[zZ]|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`).toLocaleString();
}
