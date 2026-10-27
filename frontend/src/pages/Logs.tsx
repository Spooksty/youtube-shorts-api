import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../api";
import { Card, Field, PageHeader, ResultBadge, Table, inputCls } from "../components/ui";
import { LOG_RESULT, fmtDate } from "../format";
import type { LogRow } from "../types";

export default function Logs() {
  const [jobId, setJobId] = useState("");
  const [result, setResult] = useState("");

  const query = new URLSearchParams();
  if (jobId) query.set("job_id", jobId);
  if (result) query.set("result", result);
  const { data: logs } = useApi<LogRow[]>(`/logs?${query}`, 5000);

  return (
    <>
      <PageHeader title="Darbplūsmas žurnāls" sub="Katrs ģenerēšanas un publicēšanas solis ar ilgumu un rezultātu" />
      <Card>
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <Field label="Uzdevuma ID">
            <input className={inputCls} value={jobId} onChange={(e) => setJobId(e.target.value.replace(/\D/g, ""))} />
          </Field>
          <Field label="Rezultāts">
            <select className={inputCls} value={result} onChange={(e) => setResult(e.target.value)}>
              <option value="">Visi</option>
              {Object.entries(LOG_RESULT).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
            </select>
          </Field>
        </div>
        <Table head={["Laiks", "Uzdevums", "Kanāls", "Solis", "Rezultāts", "Ilgums", "Ziņojums"]} empty={logs?.length === 0}>
          {logs?.map((l) => (
            <tr key={l.id}>
              <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{fmtDate(l.started_at)}</td>
              <td className="px-3 py-1.5"><Link to={`/videos/${l.job_id}`} className="text-sky-700 hover:underline">#{l.job_id}</Link></td>
              <td className="whitespace-nowrap px-3 py-1.5">{l.channel}</td>
              <td className="whitespace-nowrap px-3 py-1.5">{l.step}</td>
              <td className="px-3 py-1.5"><ResultBadge result={l.result} /></td>
              <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{l.duration_ms} ms</td>
              <td className="px-3 py-1.5 text-slate-700">{l.message}</td>
            </tr>
          ))}
        </Table>
      </Card>
    </>
  );
}
