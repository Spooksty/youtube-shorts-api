import { FormEvent, useState } from "react";
import { api } from "../api";
import { Alert, Button, Field, inputCls } from "../components/ui";

export default function Login({ onLogin }: { onLogin: (u: { id: number; username: string }) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onLogin(await api("/auth/login", "POST", { username, password }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-lg font-semibold">Shorts Studio</h1>
        <p className="mb-5 text-sm text-slate-500">Administratora panelis</p>
        <div className="space-y-3">
          <Field label="Lietotājvārds">
            <input className={inputCls} value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </Field>
          <Field label="Parole">
            <input type="password" className={inputCls} value={password} onChange={(e) => setPassword(e.target.value)} required />
          </Field>
          {error && <Alert>{error}</Alert>}
          <Button type="submit" className="w-full" disabled={busy}>
            {busy ? "Notiek pieslēgšanās..." : "Pieslēgties"}
          </Button>
        </div>
        <p className="mt-4 text-xs text-slate-400">Jaunu kontu var izveidot tikai esošs administrators.</p>
      </form>
    </div>
  );
}
