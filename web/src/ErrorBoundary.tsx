import { Component } from "react";
import type { ReactNode } from "react";

type State = { failed: boolean };

/** Last-resort guard: a render error must never leave beta testers on a blank page. */
export default class ErrorBoundary extends Component<{ children: ReactNode }, State> {
  state: State = { failed: false };
  static getDerivedStateFromError(): State { return { failed: true }; }
  componentDidCatch(error: unknown) { console.error("Cohort UI error", error); }
  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <main className="auth-page">
        <section className="auth-card">
          <div><h1>Something went wrong</h1><p>The dashboard hit an unexpected error. Your data is safe — reload to continue.</p></div>
          <button className="btn btn-primary btn-lg btn-block" onClick={() => window.location.reload()}>Reload dashboard</button>
        </section>
      </main>
    );
  }
}
