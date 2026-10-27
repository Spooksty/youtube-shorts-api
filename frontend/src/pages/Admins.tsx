import { FormEvent, useState } from "react";
import { api, useApi } from "../api";
import { Alert, Badge, Button, Card, Field, PageHeader, Table, inputCls } from "../components/ui";
import { fmtDate } from "../format";

interface Admin {
  id: number;
  username: string;
  email: string;
  last_login: string | null;
  locked: boolean;
}

export default function Admins() {
  const { data: admins, reload } = useApi<Admin[]>("/admins");
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    try {
      await api("/admins", "POST", form);
      setForm({ username: "", email: "", password: "" });
      setMsg({ kind: "success", text: "Konts izveidots" });
      reload();
    } catch (err) {
      setMsg({ kind: "error", text: (err as Error).message });
    }
  };

  return (
    <>
      <PageHeader title="Administratori" sub="Jaunu kontu var izveidot tikai esošs administrators" />
      <div className="grid gap-4 lg:grid-cols-[1fr,320px]">
        <Card>
          <Table head={["Lietotājvārds", "E-pasts", "Pēdējā pieteikšanās", "Statuss"]} empty={admins?.length === 0}>
            {admins?.map((a) => (
              <tr key={a.id}>
                <td className="px-3 py-2 font-medium">{a.username}</td>
                <td className="px-3 py-2">{a.email}</td>
                <td className="px-3 py-2 text-slate-500">{fmtDate(a.last_login)}</td>
                <td className="px-3 py-2">
                  {a.locked
                    ? <Badge label="Bloķēts" cls="bg-red-50 text-red-800 ring-red-300" />
                    : <Badge label="Aktīvs" cls="bg-emerald-50 text-emerald-800 ring-emerald-300" />}
                </td>
              </tr>
            ))}
          </Table>
        </Card>
        <Card title="Jauns administrators">
          <form onSubmit={submit} className="space-y-3">
            <Field label="Lietotājvārds"><input className={inputCls} value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></Field>
            <Field label="E-pasts"><input type="email" className={inputCls} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Parole" hint="Vismaz 8 rakstzīmes"><input type="password" className={inputCls} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
            <Button type="submit" className="w-full">Izveidot kontu</Button>
          </form>
        </Card>
      </div>
    </>
  );
}
