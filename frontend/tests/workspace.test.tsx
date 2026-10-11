import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test, vi } from "vitest";
import Home from "../src/app/page";

const key = "test-workspace-key-not-for-use-123456";
const scan = { id: 7, name: "example.py", status: "completed", scanner_names: ["bandit"],
  created_at: "2026-01-01T00:00:00Z", total_findings: 1, critical_count: 0, high_count: 0,
  medium_count: 1, low_count: 0, info_count: 0, failure_reason: null };
const finding = { id: 12, rule_id: "B307", title: "Use of eval", file_path: "example.py",
  line_number: 1, code_snippet: 'eval("<script>alert(1)</script>")', severity: "MEDIUM", confidence: "HIGH",
  analysis_available: true, remediation_guidance: "Use a parser.", cwe_id: "CWE-94", cwe_name: "Code injection" };
const savedAnalysis = { finding_summary: "Saved guidance", root_cause: "Dynamic evaluation", security_impact: "Code injection",
  false_positive_assessment: "Review input", remediation: "Use json.loads", provider: "mock", fixed_code: null, diff: null };

function mockApi(overrides: Record<string, unknown> = {}) {
  const calls: string[] = [];
  const fetch = vi.fn(async (input: string, init?: RequestInit) => {
    expect(new Headers(init?.headers).get("Authorization")).toBe(`Bearer ${key}`);
    const url = new URL(input); const method = init?.method ?? "GET";
    const route = `${method} ${url.pathname}${url.search}`; calls.push(route);
    const responses: Record<string, unknown> = {
      "GET /api/workspace": { max_upload_size_bytes: 5242880, analysis_provider: "mock", remote_analysis: false },
      "GET /api/scans?offset=0&limit=10": { items: [scan], total: 1, offset: 0, limit: 10 },
      "GET /api/scans/7": scan,
      "GET /api/scans/7/findings?limit=20&offset=0": [finding],
      "GET /api/scans/7/findings?limit=20&offset=0&severity=HIGH": [],
      "GET /api/findings/12/analysis": savedAnalysis,
      "POST /api/scans": { scan_id: 7 },
      ...overrides,
    };
    if (route === "DELETE /api/scans/7") return new Response(null, { status: 204 });
    if (!(route in responses)) throw new Error(`Unexpected API call: ${route}`);
    if (responses[route] instanceof Response) return responses[route];
    return Response.json(responses[route]);
  });
  vi.stubGlobal("fetch", fetch);
  return calls;
}

async function unlock() {
  const user = userEvent.setup();
  render(<Home />);
  await user.type(screen.getByLabelText("Workspace access key"), key);
  await user.click(screen.getByRole("button", { name: "Unlock workspace" }));
  await screen.findByRole("heading", { name: "Scan history" });
  return user;
}

test("reopens persisted findings, renders code as text, and reads saved guidance without regenerating", async () => {
  const calls = mockApi(); const user = await unlock();
  await user.click(await screen.findByRole("button", { name: /example.py completed/ }));
  await screen.findByRole("heading", { name: "Use of eval" });
  expect(screen.getByLabelText("Source snippet")).toHaveTextContent("<script>");
  expect(document.querySelector("script")).toBeNull();
  await user.click(screen.getByRole("button", { name: "View saved analysis" }));
  expect(await screen.findByText("Saved guidance")).toBeInTheDocument();
  expect(calls).toContain("GET /api/findings/12/analysis");
  expect(calls).not.toContain("POST /api/findings/12/analysis");
  await user.click(screen.getByRole("button", { name: "Lock workspace" }));
  expect(screen.getByLabelText("Workspace access key")).toHaveValue("");
  expect(localStorage.length).toBe(0);
});

test("upload selects real result; filtering and confirmed deletion use the API", async () => {
  const calls = mockApi(); const user = await unlock();
  await user.upload(screen.getByLabelText("Python source file"), new File(["eval(input())"], "example.py", { type: "text/x-python" }));
  await user.click(screen.getByRole("button", { name: "Run security scan" }));
  await screen.findByRole("heading", { name: "Use of eval" });
  expect(calls).toContain("POST /api/scans");
  await user.selectOptions(screen.getByLabelText("Filter severity"), "HIGH");
  expect(await screen.findByText("No matching findings")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Delete scan" }));
  expect(calls).not.toContain("DELETE /api/scans/7");
  await user.click(screen.getByRole("button", { name: "Confirm delete" }));
  expect(await screen.findByRole("heading", { name: "Ready to review" })).toBeInTheDocument();
  expect(calls).toContain("DELETE /api/scans/7");
});

test("failed scans cannot be presented as clean", async () => {
  mockApi({ "GET /api/scans/7": { ...scan, status: "failed", failure_reason: "Python syntax error" },
    "GET /api/scans/7/findings?limit=20&offset=0": [] });
  const user = await unlock();
  await user.click(await screen.findByRole("button", { name: /example.py completed/ }));
  expect(await screen.findByRole("alert")).toHaveTextContent("No clean-code conclusion");
  expect(screen.queryByText("No findings reported")).not.toBeInTheDocument();
});

test("pagination reaches findings beyond the first 20", async () => {
  mockApi({ "GET /api/scans/7": { ...scan, total_findings: 21, medium_count: 21 },
    "GET /api/scans/7/findings?limit=20&offset=20": [{ ...finding, id: 40, title: "Last finding" }] });
  const user = await unlock();
  await user.click(await screen.findByRole("button", { name: /example.py completed/ }));
  await screen.findByRole("heading", { name: "Use of eval" });
  const results = screen.getByRole("region", { name: "Scan results" });
  await user.click(within(results).getByRole("button", { name: "Next" }));
  expect(await screen.findByRole("heading", { name: "Last finding" })).toBeInTheDocument();
});

test("failed requests show an error and can be retried", async () => {
  mockApi({ "GET /api/scans?offset=0&limit=10": new Response("offline", { status: 503 }) });
  const user = await unlock();
  expect(await screen.findByRole("alert")).toHaveTextContent("Request failed (503)");
  mockApi();
  await waitFor(() => expect(screen.getByRole("button", { name: "Refresh" })).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "Refresh" }));
  expect(await screen.findByRole("button", { name: /example.py completed/ })).toBeInTheDocument();
});

test("remote failure fallback is identified as local guidance", async () => {
  mockApi({
    "GET /api/findings/12/analysis": {
      finding_summary: "Fallback guidance", root_cause: "Provider unavailable", security_impact: "Review required",
      false_positive_assessment: "Verify manually", remediation: "Use a safe parser", fixed_code: null,
      diff: null, confidence: 0, provider: "mock-fallback", model: null,
    },
  });
  const user = await unlock();
  await user.click(await screen.findByRole("button", { name: /example.py completed/ }));
  await user.click(screen.getByRole("button", { name: "View saved analysis" }));
  expect(await screen.findByText("LOCAL FALLBACK GUIDANCE · REMOTE AI UNAVAILABLE")).toBeInTheDocument();
});
