import { FormEvent, useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { request } from "@/lib/api";

interface TokenResponse { access_token: string }

export function LoginPanel({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const [registering, setRegistering] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await request<TokenResponse>(registering ? "auth/register" : "auth/login", undefined, { email, password });
      onAuthenticated(result.access_token);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return <main className="login-screen">
    <div className="login-mark"><ShieldCheck size={20} /> TRINETRA <span>INTELLIGENCE ANALYSIS</span></div>
    <div className="login-panel">
      <div className="eyebrow">SECURE WORKSPACE ACCESS</div>
      <h1>{registering ? "Create analyst account" : "Sign in to workspace"}</h1>
      <p>Access source records, evidence lineage, and operational status from the connected backend.</p>
      <form onSubmit={submit}>
        <label>Email address<input type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} required /></label>
        <label>Password<input type="password" autoComplete={registering ? "new-password" : "current-password"} minLength={8} value={password} onChange={event => setPassword(event.target.value)} required /></label>
        {error && <div className="form-error" role="alert">{error}</div>}
        <button className="primary-button" disabled={busy}>{busy ? "Connecting…" : registering ? "Create account" : "Sign in"}<ArrowRight size={15} /></button>
      </form>
      <button className="text-button" onClick={() => { setRegistering(!registering); setError(""); }}>
        {registering ? "Already have an account? Sign in" : "Need an account? Register"}
      </button>
    </div>
    <div className="login-footer">EVIDENCE-CENTRIC OSINT ANALYSIS PLATFORM <span>AUTHORIZED USERS ONLY</span></div>
  </main>;
}
