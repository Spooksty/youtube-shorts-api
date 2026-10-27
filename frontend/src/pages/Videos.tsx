import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useApi } from "../api";
import GenerateModal from "../components/GenerateModal";
import JobTable from "../components/JobTable";
import { Button, Card, Field, PageHeader, inputCls } from "../components/ui";
import { STATUS, isBusy } from "../format";
import type { Channel, JobRow, JobStatus } from "../types";

export default function Videos() {
  const [params, setParams] = useSearchParams();
  const [generate, setGenerate] = useState(false);
  const { data: channels } = useApi<Channel[]>("/channels");

  const query = new URLSearchParams();
  for (const key of ["channel_id", "status", "date_from", "date_to"]) {
    const v = params.get(key);
    if (v) query.set(key, v);
  }
  const { data: jobs } = useApi<JobRow[]>(`/videos?${query}`, 3000);

  const setFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const busy = jobs?.filter((j) => isBusy(j.status)).length ?? 0;

  return (
    <>
      <PageHeader
        title="Video"
        sub={busy ? `${busy} uzdevumi rindā vai izpildē` : "Visi ģenerēšanas uzdevumi un video"}
        actions={<Button onClick={() => setGenerate(true)}>Ģenerēt video</Button>}
      />

      <Card>
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-5">
          <Field label="Kanāls">
            <select className={inputCls} value={params.get("channel_id") ?? ""} onChange={(e) => setFilter("channel_id", e.target.value)}>
              <option value="">Visi</option>
              {channels?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </Field>
          <Field label="Statuss">
            <select className={inputCls} value={params.get("status") ?? ""} onChange={(e) => setFilter("status", e.target.value)}>
              <option value="">Visi</option>
              {(Object.keys(STATUS) as JobStatus[]).map((s) => <option key={s} value={s}>{STATUS[s].label}</option>)}
            </select>
          </Field>
          <Field label="No">
            <input type="date" className={inputCls} value={params.get("date_from") ?? ""} onChange={(e) => setFilter("date_from", e.target.value)} />
          </Field>
          <Field label="Līdz">
            <input type="date" className={inputCls} value={params.get("date_to") ?? ""} onChange={(e) => setFilter("date_to", e.target.value)} />
          </Field>
          <div className="flex items-end">
            <Button variant="ghost" onClick={() => setParams({}, { replace: true })}>Notīrīt filtrus</Button>
          </div>
        </div>
        {jobs && <JobTable jobs={jobs} />}
      </Card>

      {generate && <GenerateModal onClose={() => setGenerate(false)} />}
    </>
  );
}
