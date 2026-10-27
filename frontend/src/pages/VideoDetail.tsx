import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, useApi } from "../api";
import { Alert, Button, Card, Field, PageHeader, ResultBadge, StatusBadge, Table, inputCls } from "../components/ui";
import { fmtDate, fmtEur, fmtTime, isBusy } from "../format";
import type { VideoDetail as Detail } from "../types";

const MEDIA_KIND: Record<string, string> = {
  audio: "Balss ieraksts",
  clip: "Video klips",
  image: "Attēls",
  subtitles: "Subtitri",
};

const STEPS = [
  "Budžeta pārbaude",
  "Tēmas izvēle",
  "Skripta ģenerēšana",
  "Balss ierakstīšana",
  "Materiālu iegūšana",
  "Montāža",
  "Tehniskā pārbaude",
];

function Progress({ job }: { job: Detail }) {
  const done = new Set(job.logs.filter((l) => l.result === "ok").map((l) => l.step));
  return (
    <ol className="space-y-2">
      {STEPS.map((s) => {
        const current = job.current_step === s;
        const ok = done.has(s) && !current;
        return (
          <li key={s} className="flex items-center gap-2 text-sm">
            <span className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
              ok ? "bg-emerald-500 text-white" : current ? "animate-pulse bg-sky-500 text-white" : "bg-slate-200 text-slate-500"}`}>
              {ok ? "✓" : ""}
            </span>
            <span className={ok ? "text-slate-700" : current ? "font-medium text-sky-800" : "text-slate-400"}>{s}</span>
          </li>
        );
      })}
    </ol>
  );
}

export default function VideoDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [poll, setPoll] = useState<number | undefined>(2000);
  const { data: job, error: loadError, reload } = useApi<Detail>(`/videos/${id}`, poll);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [tags, setTags] = useState("");
  const [loadedFor, setLoadedFor] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!job) return;
    setPoll(isBusy(job.status) || job.status === "approved" ? 2000 : undefined);
    if (job.video && loadedFor !== id) {
      setTitle(job.video.title);
      setDescription(job.video.description);
      setTags(job.video.tags.join(", "));
      setLoadedFor(id ?? null);
    }
  }, [job, id, loadedFor]);

  if (loadError) return <Alert>{loadError}</Alert>;
  if (!job) return null;

  const meta = () => ({ title, description, tags: tags.split(",").map((t) => t.trim()).filter(Boolean) });

  const run = async (fn: () => Promise<unknown>, success: string) => {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg({ kind: "success", text: success });
      setPoll(2000);
      reload();
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const reject = async (regenerate: boolean) => {
    setBusy(true);
    try {
      const res = await api<{ new_job_id: number | null }>(`/videos/${id}/reject`, "POST", { regenerate });
      if (res.new_job_id) navigate(`/videos/${res.new_job_id}`);
      else reload();
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const reviewable = job.status === "pending_review";
  const finalScript = job.scripts.find((s) => s.id === job.video?.script_id) ?? job.scripts[job.scripts.length - 1];

  return (
    <>
      <div className="mb-2 text-sm">
        <Link to="/videos" className="text-slate-500 hover:text-slate-900">← Video saraksts</Link>
      </div>
      <PageHeader
        title={job.video?.title ?? job.topic ?? `Uzdevums #${job.id}`}
        sub={`#${job.id} · ${job.channel} · izveidots ${fmtDate(job.created_at)}${job.manual ? " · manuāli" : " · pēc grafika"}`}
        actions={<StatusBadge status={job.status} />}
      />

      {job.status === "error" && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-md border border-red-200 bg-red-50 px-4 py-3">
          <span className="text-sm text-red-800">{job.error}</span>
          <Button variant="secondary" onClick={() => reject(true)} disabled={busy}>Ģenerēt no jauna</Button>
        </div>
      )}
      {job.status === "postponed" && (
        <div className="mb-4"><Alert kind="info">Uzdevums atlikts. Tas tiks atsākts automātiski, kad budžets būs pieejams.</Alert></div>
      )}

      <div className="grid gap-4 lg:grid-cols-[340px,1fr]">
        <div className="space-y-4">
          {job.video ? (
            <div className="overflow-hidden rounded-lg bg-black">
              <video src={job.video.url} controls className="aspect-[9/16] w-full" />
            </div>
          ) : (
            <Card title={isBusy(job.status) ? "Ģenerēšana" : "Soļi"}>
              <Progress job={job} />
            </Card>
          )}
          {job.video && (
            <Card title="Tehniskā pārbaude">
              <dl className="grid grid-cols-2 gap-y-1 text-sm">
                <dt className="text-slate-500">Izšķirtspēja</dt><dd>{job.video.width}×{job.video.height}</dd>
                <dt className="text-slate-500">Ilgums</dt><dd>{job.video.duration.toFixed(1)} s</dd>
                <dt className="text-slate-500">Audio</dt><dd>{job.video.has_audio ? "Ir" : "Nav"}</dd>
                <dt className="text-slate-500">Rezultāts</dt>
                <dd className={job.video.check_passed ? "text-emerald-700" : "text-red-700"}>
                  {job.video.check_passed ? "Izturēta" : "Neizturēta"}
                </dd>
              </dl>
            </Card>
          )}
          {job.publication && (
            <Card title="Publikācija">
              <dl className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm">
                <dt className="text-slate-500">YouTube ID</dt><dd className="font-mono">{job.publication.youtube_video_id}</dd>
                <dt className="text-slate-500">Publicēts</dt><dd>{fmtDate(job.publication.published_at)}</dd>
                <dt className="text-slate-500">Redzamība</dt><dd>{job.publication.privacy === "private" ? "Privāts (neauditēts projekts)" : job.publication.privacy}</dd>
                <dt className="text-slate-500">MI atzīme</dt><dd>{job.publication.ai_generated ? "Jā" : "Nē"}</dd>
              </dl>
            </Card>
          )}
        </div>

        <div className="space-y-4">
          {job.video && (
            <Card title="Metadati">
              <div className="space-y-3">
                <Field label="Virsraksts" hint={`${title.length} / 100`}>
                  <input className={inputCls} value={title} maxLength={100} onChange={(e) => setTitle(e.target.value)} disabled={!reviewable} />
                </Field>
                <Field label="Apraksts">
                  <textarea className={inputCls} rows={4} value={description} onChange={(e) => setDescription(e.target.value)} disabled={!reviewable} />
                </Field>
                <Field label="Tēmturi" hint="Atdalīti ar komatu">
                  <input className={inputCls} value={tags} onChange={(e) => setTags(e.target.value)} disabled={!reviewable} />
                </Field>
                {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
                {reviewable && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    <Button disabled={busy} onClick={() => run(() => api(`/videos/${id}/approve`, "POST", meta()), "Video apstiprināts un nodots publicēšanai")}>
                      Apstiprināt
                    </Button>
                    <Button variant="secondary" disabled={busy} onClick={() => run(() => api(`/videos/${id}/metadata`, "PUT", meta()), "Izmaiņas saglabātas")}>
                      Saglabāt izmaiņas
                    </Button>
                    <Button variant="danger" disabled={busy} onClick={() => reject(false)}>Noraidīt</Button>
                    <Button variant="ghost" disabled={busy} onClick={() => reject(true)}>Noraidīt un ģenerēt no jauna</Button>
                  </div>
                )}
                {job.status === "approved" && <p className="text-sm text-teal-700">Notiek publicēšana…</p>}
              </div>
            </Card>
          )}

          {finalScript && (
            <Card title="Skripts">
              <p className="whitespace-pre-line text-sm leading-relaxed text-slate-800">{finalScript.text}</p>
              {finalScript.keywords.length > 0 && (
                <p className="mt-3 text-xs text-slate-500">Vizuālie atslēgvārdi: {finalScript.keywords.join(", ")}</p>
              )}
              {job.scripts.length > 1 && (
                <div className="mt-3 border-t border-slate-100 pt-3">
                  <p className="mb-1 text-xs font-medium text-slate-500">Ģenerēšanas mēģinājumi</p>
                  <ul className="space-y-1 text-xs">
                    {job.scripts.map((s) => (
                      <li key={s.id} className={s.is_valid ? "text-emerald-700" : "text-amber-700"}>
                        #{s.attempt}: {s.is_valid ? "izturēja pārbaudi" : s.validation_message}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </Card>
          )}

          {job.media.length > 0 && (
            <Card title="Izmantotie materiāli">
              <Table head={["Veids", "Avots", "Atslēgvārds", "Autors", "Saite"]}>
                {job.media.map((m) => (
                  <tr key={m.id}>
                    <td className="px-3 py-1.5">{MEDIA_KIND[m.kind] ?? m.kind}</td>
                    <td className="px-3 py-1.5">{m.provider}</td>
                    <td className="px-3 py-1.5">{m.keyword ?? "—"}</td>
                    <td className="px-3 py-1.5">{m.author ?? "—"}</td>
                    <td className="px-3 py-1.5">
                      {m.source_url ? <a href={m.source_url} target="_blank" rel="noreferrer" className="text-sky-700 hover:underline">Atvērt</a> : "—"}
                    </td>
                  </tr>
                ))}
              </Table>
            </Card>
          )}

          {job.costs.length > 0 && (
            <Card title="Izmaksas" actions={<span className="text-sm font-semibold">{fmtEur(job.total_cost, 4)}</span>}>
              <Table head={["Serviss", "Operācija", "Vienības", "EUR"]}>
                {job.costs.map((c, i) => (
                  <tr key={i}>
                    <td className="px-3 py-1.5">{c.service}{c.simulated && <span className="ml-1 text-xs text-slate-400">(simulēts)</span>}</td>
                    <td className="px-3 py-1.5 text-slate-600">{c.operation}</td>
                    <td className="px-3 py-1.5">{c.units}</td>
                    <td className="px-3 py-1.5">{c.cost_eur.toFixed(4)}</td>
                  </tr>
                ))}
              </Table>
            </Card>
          )}

          <Card title="Žurnāls">
            <Table head={["Laiks", "Solis", "Rezultāts", "Ilgums", "Ziņojums"]} empty={job.logs.length === 0}>
              {job.logs.map((l) => (
                <tr key={l.id}>
                  <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{fmtTime(l.started_at)}</td>
                  <td className="whitespace-nowrap px-3 py-1.5">{l.step}</td>
                  <td className="px-3 py-1.5"><ResultBadge result={l.result} /></td>
                  <td className="whitespace-nowrap px-3 py-1.5 text-slate-500">{l.duration_ms} ms</td>
                  <td className="px-3 py-1.5 text-slate-700">{l.message}</td>
                </tr>
              ))}
            </Table>
          </Card>
        </div>
      </div>
    </>
  );
}
