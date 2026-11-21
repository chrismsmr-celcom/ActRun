import { useCallback, useEffect, useRef, useState } from "react";
import { api, isUnavailable } from "./api";
import type { Branch, Data, EventItem, Health, Lease, Overview, Settings, StateSnapshot } from "./types";

const empty: Data = {
  overview: null, branches: [], state: { head: "", parent: null, items: [] }, events: [], leases: [], settings: null, health: null,
  connected: false, loaded: false, error: "", lastUpdated: null,
};

/** Polls the Cohort API every 5 s (paused while the tab is hidden). Never fabricates data. */
export function useCohort() {
  const [data, setData] = useState<Data>(empty);
  const inFlight = useRef(false);
  const refresh = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const [overview, branches, state, events, leases, settings, health] = await Promise.all([
        api<Overview>("/overview"), api<{ items: Branch[] }>("/branches"), api<StateSnapshot>("/state"),
        api<{ items: EventItem[] }>("/events?limit=300"), api<{ items: Lease[] }>("/leases"), api<Settings>("/settings"),
        api<Health>("/health").catch(() => null),
      ]);
      setData({ overview, branches: branches.items, state, events: events.items, leases: leases.items, settings, health, connected: true, loaded: true, error: "", lastUpdated: Date.now() });
    } catch (err) {
      setData((prev) => ({ ...prev, connected: false, loaded: true, error: err instanceof Error ? err.message : "Unable to reach Cohort API" }));
    } finally {
      inFlight.current = false;
    }
  }, []);
  useEffect(() => {
    void refresh();
    const tick = () => { if (!document.hidden) void refresh(); };
    const id = window.setInterval(tick, 5000);
    document.addEventListener("visibilitychange", tick);
    return () => { window.clearInterval(id); document.removeEventListener("visibilitychange", tick); };
  }, [refresh]);
  return { data, refresh };
}

export type Optional<T> = { status: "loading" | "ready" | "unavailable" | "error"; data: T | null; error: string; reload: () => void };

/** For endpoints that may not exist yet: a 404/405/501 becomes status "unavailable" (no polling, no fake data). */
export function useOptional<T>(path: string | null, intervalMs = 0): Optional<T> {
  const [state, setState] = useState<{ status: Optional<T>["status"]; data: T | null; error: string }>({ status: "loading", data: null, error: "" });
  const [nonce, setNonce] = useState(0);
  useEffect(() => {
    if (!path) return;
    let active = true;
    let timer = 0;
    setState((prev) => (prev.status === "ready" ? prev : { status: "loading", data: null, error: "" }));
    const load = async () => {
      try {
        const data = await api<T>(path);
        if (active) setState({ status: "ready", data, error: "" });
        if (active && intervalMs) timer = window.setTimeout(load, intervalMs);
      } catch (err) {
        if (!active) return;
        if (isUnavailable(err)) setState({ status: "unavailable", data: null, error: "" });
        else {
          setState((prev) => ({ status: "error", data: prev.data, error: err instanceof Error ? err.message : "Request failed" }));
          if (intervalMs) timer = window.setTimeout(load, intervalMs * 2);
        }
      }
    };
    void load();
    return () => { active = false; window.clearTimeout(timer); };
  }, [path, intervalMs, nonce]);
  return { ...state, reload: () => setNonce((n) => n + 1) };
}
