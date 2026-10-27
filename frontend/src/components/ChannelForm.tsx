import { FormEvent, useState } from "react";
import { api, useApi } from "../api";
import type { Channel } from "../types";
import { Alert, Button, Field, inputCls } from "./ui";

type FormData = Pick<Channel, "name" | "niche" | "audience_age" | "language" | "voice_id" | "style">;

const EMPTY: FormData = { name: "", niche: "", audience_age: "", language: "en", voice_id: "", style: "" };

export default function ChannelForm({ channel, onSaved, onCancel }: {
  channel?: Channel;
  onSaved: (c: Channel & { message?: string }) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<FormData>(channel ? { ...channel } : EMPTY);
  const [error, setError] = useState("");
  const { data: voices } = useApi<{ id: string; name: string }[]>("/voices");

  const set = (key: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm({ ...form, [key]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const saved = channel
        ? await api<Channel>(`/channels/${channel.id}`, "PUT", form)
        : await api<Channel>("/channels", "POST", form);
      onSaved(saved);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Nosaukums *"><input className={inputCls} value={form.name} onChange={set("name")} /></Field>
        <Field label="Tēmu joma *"><input className={inputCls} value={form.niche} onChange={set("niche")} placeholder="piem. Kosmoss" /></Field>
        <Field label="Mērķauditorijas vecums *"><input className={inputCls} value={form.audience_age} onChange={set("audience_age")} placeholder="18-34" /></Field>
        <Field label="Valoda *">
          <select className={inputCls} value={form.language} onChange={set("language")}>
            <option value="en">Angļu</option>
            <option value="lv">Latviešu</option>
          </select>
        </Field>
        <Field label="Balss *" hint="ElevenLabs balss">
          {voices?.length ? (
            <select className={inputCls} value={form.voice_id} onChange={set("voice_id")}>
              <option value="">Izvēlies balsi</option>
              {!voices.some((v) => v.id === form.voice_id) && form.voice_id && (
                <option value={form.voice_id}>{form.voice_id} (nav pieejama)</option>
              )}
              {voices.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
            </select>
          ) : (
            <input className={inputCls} value={form.voice_id} onChange={set("voice_id")} />
          )}
        </Field>
        <Field label="Stils"><input className={inputCls} value={form.style} onChange={set("style")} placeholder="enerģisks, humoristisks" /></Field>
      </div>
      {error && <Alert>{error}</Alert>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="secondary" onClick={onCancel}>Atcelt</Button>
        <Button type="submit">Saglabāt</Button>
      </div>
    </form>
  );
}
