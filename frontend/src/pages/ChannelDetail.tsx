import { FormEvent, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { api, useApi } from "../api";
import ChannelForm from "../components/ChannelForm";
import GenerateModal from "../components/GenerateModal";
import { Alert, Badge, Button, Card, Field, Modal, PageHeader, Table, inputCls } from "../components/ui";
import { LANGUAGES } from "../format";
import type { Channel, Schedule, Template, Topic } from "../types";

function TopicsTab({ channelId }: { channelId: number }) {
  const { data: topics, reload } = useApi<Topic[]>(`/channels/${channelId}/topics`);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<Topic | null>(null);
  const [error, setError] = useState("");

  const add = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api(`/channels/${channelId}/topics`, "POST", { title, description });
      setTitle("");
      setDescription("");
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const save = async (t: Topic) => {
    try {
      await api(`/topics/${t.id}`, "PUT", t);
      setEditing(null);
      reload();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const remove = async (t: Topic) => {
    if (!confirm(`Dzēst tēmu "${t.title}"?`)) return;
    await api(`/topics/${t.id}`, "DELETE");
    reload();
  };

  return (
    <div className="space-y-4">
      <form onSubmit={add} className="grid gap-2 sm:grid-cols-[1fr,1fr,auto]">
        <input className={inputCls} placeholder="Jauna tēma, piem. Why the sky is blue" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className={inputCls} placeholder="Apraksts (pēc izvēles)" value={description} onChange={(e) => setDescription(e.target.value)} />
        <Button type="submit" disabled={!title.trim()}>Pievienot</Button>
      </form>
      {error && <Alert>{error}</Alert>}
      <Table head={["Tēma", "Apraksts", "Aktīva", ""]} empty={topics?.length === 0}>
        {topics?.map((t) =>
          editing?.id === t.id ? (
            <tr key={t.id} className="bg-slate-50">
              <td className="px-3 py-2"><input className={inputCls} value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} /></td>
              <td className="px-3 py-2"><input className={inputCls} value={editing.description} onChange={(e) => setEditing({ ...editing, description: e.target.value })} /></td>
              <td className="px-3 py-2">
                <input type="checkbox" checked={editing.is_active} onChange={(e) => setEditing({ ...editing, is_active: e.target.checked })} />
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Button onClick={() => save(editing)}>Saglabāt</Button>{" "}
                <Button variant="ghost" onClick={() => setEditing(null)}>Atcelt</Button>
              </td>
            </tr>
          ) : (
            <tr key={t.id}>
              <td className={`px-3 py-2 ${t.is_active ? "" : "text-slate-400 line-through"}`}>{t.title}</td>
              <td className="px-3 py-2 text-slate-500">{t.description || "—"}</td>
              <td className="px-3 py-2">
                <input type="checkbox" checked={t.is_active} onChange={() => save({ ...t, is_active: !t.is_active })} />
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-right">
                <Button variant="ghost" onClick={() => setEditing(t)}>Labot</Button>
                <Button variant="ghost" className="text-red-600" onClick={() => remove(t)}>Dzēst</Button>
              </td>
            </tr>
          ),
        )}
      </Table>
    </div>
  );
}

function TemplateModal({ channelId, template, onClose }: { channelId: number; template?: Template; onClose: () => void }) {
  const [name, setName] = useState(template?.name ?? "");
  const [body, setBody] = useState(template?.body ?? "");
  const [isActive, setIsActive] = useState(template?.is_active ?? true);
  const [error, setError] = useState("");

  const save = async () => {
    try {
      const payload = { name, body, is_active: isActive };
      if (template) await api(`/templates/${template.id}`, "PUT", payload);
      else await api(`/channels/${channelId}/templates`, "POST", payload);
      onClose();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Modal title={template ? "Labot veidni" : "Jauna promptu veidne"} onClose={onClose} wide>
      <div className="space-y-3">
        <Field label="Nosaukums"><input className={inputCls} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <Field label="Veidnes teksts" hint="Pieejamie mainīgie: {topic}, {audience_age}, {language}, {style}, {niche}">
          <textarea className={`${inputCls} font-mono`} rows={7} value={body} onChange={(e) => setBody(e.target.value)} />
        </Field>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isActive} onChange={(e) => setIsActive(e.target.checked)} /> Aktīva
        </label>
        {error && <Alert>{error}</Alert>}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>Atcelt</Button>
          <Button onClick={save}>Saglabāt</Button>
        </div>
      </div>
    </Modal>
  );
}

function TemplatesTab({ channelId }: { channelId: number }) {
  const { data: templates, reload } = useApi<Template[]>(`/channels/${channelId}/templates`);
  const [editing, setEditing] = useState<Template | "new" | null>(null);

  const remove = async (t: Template) => {
    if (!confirm(`Dzēst veidni "${t.name}"?`)) return;
    await api(`/templates/${t.id}`, "DELETE");
    reload();
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between">
        <p className="text-sm text-slate-500">Ģenerēšanai tiek izmantota jaunākā aktīvā veidne.</p>
        <Button onClick={() => setEditing("new")}>Jauna veidne</Button>
      </div>
      {templates?.length === 0 && <p className="text-sm text-slate-400">Nav veidņu, tiks izmantota noklusētā.</p>}
      {templates?.map((t) => (
        <div key={t.id} className="rounded-md border border-slate-200 p-3">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="font-medium">{t.name}</span>
            <span className="text-xs text-slate-400">v{t.version}</span>
            {!t.is_active && <Badge label="Neaktīva" cls="bg-zinc-100 text-zinc-600 ring-zinc-300" />}
            <div className="ml-auto">
              <Button variant="ghost" onClick={() => setEditing(t)}>Labot</Button>
              <Button variant="ghost" className="text-red-600" onClick={() => remove(t)}>Dzēst</Button>
            </div>
          </div>
          <pre className="whitespace-pre-wrap rounded bg-slate-50 p-2 font-mono text-xs text-slate-700">{t.body}</pre>
        </div>
      ))}
      {editing && (
        <TemplateModal
          channelId={channelId}
          template={editing === "new" ? undefined : editing}
          onClose={() => { setEditing(null); reload(); }}
        />
      )}
    </div>
  );
}

function ScheduleTab({ channel, onSaved }: { channel: Channel; onSaved: () => void }) {
  const initial = channel.schedule ?? { videos_per_day: 1, publish_times: ["18:00"], auto_publish: false };
  const [form, setForm] = useState<Schedule>(initial);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  const setTime = (i: number, v: string) => {
    const times = [...form.publish_times];
    times[i] = v;
    setForm({ ...form, publish_times: times });
  };

  const save = async () => {
    setMsg(null);
    try {
      const saved = await api<Schedule>(`/channels/${channel.id}/schedule`, "PUT", form);
      setForm(saved);
      setMsg({ kind: "success", text: "Grafiks saglabāts" });
      onSaved();
    } catch (err) {
      setMsg({ kind: "error", text: (err as Error).message });
    }
  };

  return (
    <div className="max-w-md space-y-4">
      <Field label="Video skaits dienā">
        <input type="number" min={1} max={10} className={inputCls} value={form.videos_per_day}
               onChange={(e) => setForm({ ...form, videos_per_day: Number(e.target.value) })} />
      </Field>
      <div>
        <span className="mb-1 block text-xs font-medium text-slate-600">Publicēšanas laiki</span>
        <div className="flex flex-wrap gap-2">
          {form.publish_times.map((t, i) => (
            <div key={i} className="flex items-center gap-1">
              <input type="time" className={`${inputCls} w-28`} value={t} onChange={(e) => setTime(i, e.target.value)} />
              <button className="px-1 text-slate-400 hover:text-red-600"
                      onClick={() => setForm({ ...form, publish_times: form.publish_times.filter((_, j) => j !== i) })}>✕</button>
            </div>
          ))}
          <Button variant="secondary" onClick={() => setForm({ ...form, publish_times: [...form.publish_times, "12:00"] })}>+ Laiks</Button>
        </div>
      </div>
      <label className="flex items-start gap-2 text-sm">
        <input type="checkbox" className="mt-0.5" checked={form.auto_publish} onChange={(e) => setForm({ ...form, auto_publish: e.target.checked })} />
        <span>
          Automātiskā publicēšana
          <span className="block text-xs text-slate-500">Ja izslēgta, katrs video gaida administratora apstiprinājumu.</span>
        </span>
      </label>
      {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
      <Button onClick={save}>Saglabāt grafiku</Button>
    </div>
  );
}

const TABS = [
  { key: "topics", label: "Tēmas" },
  { key: "templates", label: "Promptu veidnes" },
  { key: "schedule", label: "Publicēšanas grafiks" },
] as const;

export default function ChannelDetail() {
  const { id } = useParams();
  const location = useLocation();
  const { data: channel, error: loadError, reload, setData } = useApi<Channel>(`/channels/${id}`);
  const [tab, setTab] = useState<(typeof TABS)[number]["key"]>("topics");
  const [editing, setEditing] = useState(false);
  const [linking, setLinking] = useState(false);
  const [generate, setGenerate] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "info" | "success"; text: string } | null>(null);

  useEffect(() => {
    const m = (location.state as { message?: string } | null)?.message;
    if (m) setMsg({ kind: "info", text: m });
  }, [location.state]);

  if (loadError) return <Alert>{loadError}</Alert>;
  if (!channel) return null;

  const toggleActive = async () => {
    setMsg(null);
    try {
      setData(await api<Channel>(`/channels/${channel.id}/active`, "POST", { active: !channel.is_active }));
    } catch (err) {
      setMsg({ kind: "error", text: (err as Error).message });
    }
  };

  const link = async () => {
    setData(await api<Channel>(`/channels/${channel.id}/link`, "POST"));
    setLinking(false);
    setMsg({ kind: "success", text: "Kanāls sasaistīts ar YouTube. Tagad to var aktivizēt." });
  };

  return (
    <>
      <div className="mb-2 text-sm">
        <Link to="/channels" className="text-slate-500 hover:text-slate-900">← Kanāli</Link>
      </div>
      <PageHeader
        title={channel.name}
        sub={`${channel.niche} · ${LANGUAGES[channel.language] ?? channel.language} · ${channel.audience_age} gadi`}
        actions={
          <>
            <Button variant="secondary" onClick={() => setEditing(true)}>Rediģēt</Button>
            {!channel.linked && <Button variant="secondary" onClick={() => setLinking(true)}>Sasaistīt ar YouTube</Button>}
            <Button variant={channel.is_active ? "danger" : "secondary"} onClick={toggleActive}>
              {channel.is_active ? "Deaktivizēt" : "Aktivizēt"}
            </Button>
            <Button onClick={() => setGenerate(true)} disabled={!channel.is_active}>Ģenerēt video</Button>
          </>
        }
      />

      {msg && <div className="mb-4"><Alert kind={msg.kind}>{msg.text}</Alert></div>}

      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card><div className="text-xs text-slate-500">Statuss</div><div className="mt-1 font-medium">{channel.is_active ? "Aktīvs" : "Neaktīvs"}</div></Card>
        <Card><div className="text-xs text-slate-500">YouTube kanāla ID</div><div className="mt-1 truncate font-mono text-sm">{channel.youtube_channel_id ?? "Nav sasaistīts"}</div></Card>
        <Card><div className="text-xs text-slate-500">Balss ID</div><div className="mt-1 truncate font-mono text-sm">{channel.voice_id}</div></Card>
        <Card><div className="text-xs text-slate-500">Stils</div><div className="mt-1 text-sm">{channel.style || "—"}</div></Card>
      </div>

      <Card>
        <div className="-mx-4 -mt-4 mb-4 flex gap-1 overflow-x-auto border-b border-slate-100 px-4">
          {TABS.map((t) => (
            <button key={t.key} onClick={() => setTab(t.key)}
                    className={`whitespace-nowrap border-b-2 px-3 py-2.5 text-sm ${tab === t.key ? "border-slate-900 font-medium text-slate-900" : "border-transparent text-slate-500 hover:text-slate-800"}`}>
              {t.label}
            </button>
          ))}
        </div>
        {tab === "topics" && <TopicsTab channelId={channel.id} />}
        {tab === "templates" && <TemplatesTab channelId={channel.id} />}
        {tab === "schedule" && <ScheduleTab channel={channel} onSaved={reload} />}
      </Card>

      {editing && (
        <Modal title="Rediģēt kanālu" onClose={() => setEditing(false)} wide>
          <ChannelForm channel={channel} onCancel={() => setEditing(false)} onSaved={(c) => { setData(c); setEditing(false); }} />
        </Modal>
      )}

      {linking && (
        <Modal title="Sasaistīt ar YouTube" onClose={() => setLinking(false)}>
          <div className="space-y-3 text-sm">
            <p>Reālajā sistēmā šeit notiek pāradresācija uz Google OAuth piekrišanas lapu, kur administrators piešķir tiesības augšupielādēt video.</p>
            <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
              <div className="font-medium">Shorts Studio vēlas piekļūt jūsu YouTube kontam</div>
              <ul className="mt-1 list-inside list-disc text-slate-600">
                <li>Augšupielādēt video (youtube.upload)</li>
              </ul>
            </div>
            <p className="text-xs text-slate-500">Prototipā piekrišana tiek simulēta.</p>
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setLinking(false)}>Atcelt</Button>
              <Button onClick={link}>Atļaut</Button>
            </div>
          </div>
        </Modal>
      )}

      {generate && <GenerateModal channelId={channel.id} onClose={() => setGenerate(false)} />}
    </>
  );
}
