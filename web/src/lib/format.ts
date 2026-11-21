export const short = (value?: string | null) => (value ? `${value.slice(0, 7)}…${value.slice(-4)}` : "—");
export const timeAgo = (value: string | number) => {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
};
export const clock = (value: string | number) => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
export const ms = (value: number | null | undefined) => (value == null || Number.isNaN(value) ? "—" : value >= 1000 ? `${(value / 1000).toFixed(2)} s` : `${Math.round(value)} ms`);
export const pct = (value: number | null | undefined) => (value == null || Number.isNaN(value) ? "—" : `${(value * 100).toFixed(value < 0.1 ? 1 : 0)}%`);
export const percentile = (values: number[], p: number) => {
  if (!values.length) return NaN;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.min(sorted.length - 1, Math.floor((p / 100) * sorted.length))];
};
export const countdown = (expiresAtSeconds: number, now: number) => {
  const left = Math.max(0, Math.round(expiresAtSeconds - now / 1000));
  return left >= 60 ? `${Math.floor(left / 60)}m ${String(left % 60).padStart(2, "0")}s` : `${left}s`;
};
export const eventTone = (action: string): "danger" | "success" | "neutral" =>
  /conflict|abort|reject|denied/.test(action) ? "danger" : /commit|resolve|merge/.test(action) ? "success" : "neutral";
export const download = (name: string, text: string, type = "application/x-ndjson") => {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
};
