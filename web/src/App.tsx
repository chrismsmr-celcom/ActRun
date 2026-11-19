import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import CohortDashboard from "./CohortDashboard";
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
  if (!authEnvironmentPresent && !apiConfigured) return <CohortDashboard />;
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
        <form onSubmit={sendMagicLink} className="auth-form">
          <label className="form-label">Work email
            <input type="email" required autoComplete="email" autoFocus value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@company.com" />
          </label>
          <button className="button-primary auth-button" disabled={busy || !email.trim()}>{busy ? "Please wait…" : sent ? "Resend sign-in link" : "Email me a sign-in link"}</button>
          <div className="auth-divider"><span>or</span></div>
          <button type="button" className="button-secondary auth-button" disabled={busy} onClick={() => void signInWithGoogle()}>Continue with Google</button>
        </form>
      </AuthScreen>
    );
  }
  return <CohortDashboard userEmail={session.user.email ?? undefined} onSignOut={() => void supabase?.auth.signOut()} />;
}

function AuthScreen({ title, subtitle, message, children }: { title: string; subtitle?: string; message?: { text: string; tone: "info" | "error" } | null; children?: ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-card">
        <div className="auth-brand"><img src={cohortLogo} alt="" width={30} height={30} /><strong>cohort</strong><span className="beta-tag">BETA</span></div>
        <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
        {children}
        {message && <p role={message.tone === "error" ? "alert" : "status"} className={`auth-message ${message.tone}`}>{message.text}</p>}
      </section>
      <small className="auth-footer">Cohort by Cerbere · Coordination for AI agents</small>
    </main>
  );
}
