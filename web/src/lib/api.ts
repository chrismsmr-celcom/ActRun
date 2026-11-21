import { getActiveWorkspaceId, supabase } from "../auth";

const env = ((import.meta as any).env || {}) as Record<string, string | undefined>;
export const API_BASE: string = env.VITE_API_BASE_URL || env.VITE_API_URL || "";
export const REPO_URL = "https://github.com/chrismsmr-celcom/cerbere-cohort";
export const DOCS_URL: string = env.VITE_DOCS_URL || `${REPO_URL}/tree/main/docs`;
export const FEEDBACK_URL: string = env.VITE_FEEDBACK_URL || "";
export const PLANS_URL: string = env.VITE_PLANS_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) { super(message); this.status = status; }
}
export const isUnavailable = (error: unknown) => error instanceof ApiError && [404, 405, 501].includes(error.status);

/* Every request is timed so the Performance page can show real, client-measured latency. */
export type Sample = { path: string; ms: number; ok: boolean; at: number };
const samples: Sample[] = [];
const listeners = new Set<() => void>();
export const getSamples = () => samples;
export const subscribeSamples = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn); }; };
const normalize = (path: string) => path.split("?")[0]
  .replace(/\/branches\/[^/]+/, "/branches/:id")
  .replace(/\/leases\/.+/, "/leases/:key")
  .replace(/\/gateway\/agents\/[^/]+/, "/gateway/agents/:id");
function record(sample: Sample) {
  samples.push(sample);
  if (samples.length > 600) samples.splice(0, samples.length - 600);
  listeners.forEach((fn) => fn());
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(["/workspaces", "/onboarding"].includes(path) ? {} : (getActiveWorkspaceId() ? { "X-Organization-ID": getActiveWorkspaceId() } : {})),
    ...((init?.headers || {}) as Record<string, string>),
  };
  if (supabase) {
    const { data } = await supabase.auth.getSession();
    if (data.session?.access_token) headers.Authorization = `Bearer ${data.session.access_token}`;
  }
  if (!["/workspaces", "/onboarding"].includes(path) && !getActiveWorkspaceId() && supabase) {
    throw new ApiError("Select a workspace before using the Cohort runtime.", 400);
  }
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 15000);
  const started = performance.now();
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api${path}`, { ...init, headers, signal: controller.signal });
  } catch (err) {
    record({ path: normalize(path), ms: performance.now() - started, ok: false, at: Date.now() });
    throw new ApiError(err instanceof DOMException && err.name === "AbortError"
      ? "The API took too long to respond. It may be waking up — retry in a few seconds."
      : "Unable to reach the Cohort API.", 0);
  } finally {
    window.clearTimeout(timer);
  }
  record({ path: normalize(path), ms: performance.now() - started, ok: response.ok || response.status === 404, at: Date.now() });
  const body = await response.json().catch(() => ({}));
  if (response.status === 401 && supabase) {
    await supabase.auth.signOut();
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }
  if (!response.ok) {
    const detail = body?.detail;
    throw new ApiError(typeof detail === "string" ? detail : detail?.message || JSON.stringify(detail || body), response.status);
  }
  return body as T;
}
