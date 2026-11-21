import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import Dashboard from "./Dashboard";
import "./styles/app.css";
import cohortLogo from "./cohortLogo";
import { authConfigured, authEnvironmentPresent, supabase } from "./auth";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [message, setMessage] = useState<{ text: string; tone: "info" | "error" } | null>(null);
  const apiConfigured = Boolean((import.meta as any).env?.VITE_API_BASE_URL || (import.meta as any).env?.VITE_API_URL);

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => { setSession(data.session); setReady(true); });
    const { data } = supabase.auth.onAuthStateChange((_event, next) => { setSession(next); setReady(true); });
    return () => data.subscription.unsubscribe();
  }, []);

  // Local development remains passwordless. A remotely configured API must
  // never silently fall back to an unauthenticated dashboard.
  if (!authEnvironmentPresent && !apiConfigured) return <Dashboard />;
  if (!authConfigured || !supabase) {
    return <AuthScreen title="Configuration required" message={{ tone: "error", text: "Set VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY and VITE_COHORT_ORGANIZATION_ID in the frontend environment, then redeploy." }} />;
  }
  if (!ready) return <AuthScreen title="Loading your workspace…" />;
  if (!session) {
    async function sendMagicLink(event: FormEvent) {
      event.preventDefault();
      if (!supabase) return;
      setBusy(true); setMessage(null);
      const { error } = await supabase.auth.signInWithOtp({ email: email.trim(), options: { emailRedirectTo: window.location.origin } });
      if (error) setMessage({ tone: "error", text: error.message });
      else { setSent(true); setMessage({ tone: "info", text: `We sent a sign-in link to ${email.trim()}. It expires shortly — check your spam folder if it does not arrive.` }); }
      setBusy(false);
    }
    async function signInWithGoogle() {
      if (!supabase) return;
      setBusy(true); setMessage(null);
      const { error } = await supabase.auth.signInWithOAuth({ provider: "google", options: { redirectTo: window.location.origin } });
      if (error) { setMessage({ tone: "error", text: error.message }); setBusy(false); }
    }
    return (
      <AuthScreen title="Sign in to Cohort" subtitle="Private beta. Access is limited to invited members of your organization." message={message}>
        <form onSubmit={sendMagicLink} className="stack">
          <label className="field">Work email
            <input type="email" required autoComplete="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
          </label>
          <button className="btn btn-primary btn-lg btn-block" disabled={busy || !email.trim()}>{busy ? "Please wait…" : sent ? "Resend sign-in link" : "Email me a sign-in link"}</button>
          <div className="divider"><span>or</span></div>
          <button type="button" className="btn btn-secondary btn-lg btn-block" disabled={busy} onClick={() => void signInWithGoogle()}>Continue with Google</button>
        </form>
      </AuthScreen>
    );
  }
  return <Dashboard userEmail={session.user.email ?? undefined} onSignOut={() => void supabase?.auth.signOut()} />;
}

function AuthScreen({ title, subtitle, message, children }: { title: string; subtitle?: string; message?: { text: string; tone: "info" | "error" } | null; children?: ReactNode }) {
  return (
    <main className="auth-page">
      <div className="app-bg" aria-hidden /><div className="bg-noise" aria-hidden />
      <section className="auth-card">
        <div className="row"><img src={cohortLogo} alt="" width={32} height={32} /><strong style={{ fontSize: 18, color: "var(--ink)" }}>Cohort</strong><span className="tag-beta">Beta</span></div>
        <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
        {children}
        {message && <p role={message.tone === "error" ? "alert" : "status"} className={`notice ${message.tone === "error" ? "err" : ""}`}>{message.text}</p>}
      </section>
      <small className="muted" style={{ position: "relative", zIndex: 1 }}>Cohort by Cerbère · Coordination for AI agents</small>
    </main>
  );
}
