import { FormEvent, useEffect, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import type { Session } from "@supabase/supabase-js";
import CohortDashboard from "./CohortDashboard";
import { authConfigured, authEnvironmentPresent, supabase } from "./auth";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const apiConfigured = Boolean((import.meta as any).env?.VITE_API_BASE_URL || (import.meta as any).env?.VITE_API_URL);

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, next) => setSession(next));
    return () => data.subscription.unsubscribe();
  }, []);

  // Local development remains passwordless. A remotely configured API must
  // never silently fall back to an unauthenticated dashboard.
  if (!authEnvironmentPresent && !apiConfigured) return <CohortDashboard />;
  if (!authConfigured || !supabase) {
    return <AuthScreen message="Set VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY and VITE_COHORT_ORGANIZATION_ID in the frontend environment." />;
  }
  if (!session) {
    async function sendMagicLink(event: FormEvent) {
      event.preventDefault();
      if (!supabase) return;
      setBusy(true); setMessage("");
      const { error } = await supabase.auth.signInWithOtp({
        email: email.trim(),
        options: { emailRedirectTo: window.location.origin },
      });
      setMessage(error ? error.message : "Check your email for the secure sign-in link.");
      setBusy(false);
    }
    async function signInWithGoogle() {
      if (!supabase) return;
      setBusy(true); setMessage("");
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: window.location.origin },
      });
      if (error) setMessage(error.message);
      setBusy(false);
    }
    return (
      <AuthScreen message={message}>
        <form onSubmit={sendMagicLink} style={{ display: "grid", gap: 12, width: "100%" }}>
          <label style={{ display: "grid", gap: 6, textAlign: "left", fontSize: 13 }}>
            Email address
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com" style={inputStyle} />
          </label>
          <button disabled={busy} style={buttonStyle}>{busy ? "Please wait…" : "Send magic link"}</button>
          <button type="button" disabled={busy} onClick={() => void signInWithGoogle()}
            style={{ ...buttonStyle, background: "#fff", color: "#202124", border: "1px solid #d0d5dd" }}>
            Continue with Google
          </button>
        </form>
      </AuthScreen>
    );
  }
  return (
    <>
      <button onClick={() => void supabase.auth.signOut()} style={signOutStyle}>Sign out</button>
      <CohortDashboard />
    </>
  );
}

function AuthScreen({ message, children }: { message: string; children?: ReactNode }) {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#f5f6f8", padding: 24 }}>
      <section style={{ width: "100%", maxWidth: 380, padding: 32, borderRadius: 16, background: "#fff", boxShadow: "0 12px 40px rgba(16,24,40,.08)", display: "grid", gap: 18 }}>
        <div><div style={{ fontSize: 11, letterSpacing: 2, color: "#667085", fontWeight: 700 }}>COHORT</div><h1 style={{ margin: "8px 0", fontSize: 26, color: "#101828" }}>Sign in to your workspace</h1><p style={{ margin: 0, color: "#667085", fontSize: 14 }}>Use your organization account to access shared agent coordination.</p></div>
        {children}
        {message && <p role="status" style={{ margin: 0, color: "#475467", fontSize: 13 }}>{message}</p>}
      </section>
    </main>
  );
}

const inputStyle: CSSProperties = { padding: "12px 13px", border: "1px solid #d0d5dd", borderRadius: 8, fontSize: 14 };
const buttonStyle: React.CSSProperties = { padding: "12px 14px", border: 0, borderRadius: 8, background: "#161b26", color: "#fff", fontWeight: 600, cursor: "pointer" };
const signOutStyle: React.CSSProperties = { position: "fixed", top: 12, right: 16, zIndex: 1000, padding: "8px 12px", border: "1px solid #d0d5dd", borderRadius: 8, background: "#fff", cursor: "pointer" };
