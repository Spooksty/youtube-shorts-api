import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, useApi } from "../api";
import type { Channel, JobRow, Topic } from "../types";
import { Alert, Button, Field, Modal, inputCls } from "./ui";

export default function GenerateModal({ onClose, channelId }: { onClose: () => void; channelId?: number }) {
  const navigate = useNavigate();
  const { data: channels } = useApi<Channel[]>("/channels");
  const [channel, setChannel] = useState<number | "">(channelId ?? "");
  const [topic, setTopic] = useState<number | "">("");
  const { data: topics } = useApi<Topic[]>(channel ? `/channels/${channel}/topics` : null);
  const [error, setError] = useState("");

  const active = channels?.filter((c) => c.is_active) ?? [];

  const submit = async () => {
    setError("");
    try {
      const job = await api<JobRow>("/jobs", "POST", { channel_id: channel, topic_id: topic || null });
      navigate(`/videos/${job.id}`);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Modal title="Ģenerēt video" onClose={onClose}>
      <div className="space-y-3">
        <Field label="Kanāls">
          <select className={inputCls} value={channel} onChange={(e) => { setChannel(Number(e.target.value) || ""); setTopic(""); }}>
            <option value="">Izvēlies kanālu</option>
            {active.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Tēma" hint="Ja tēma netiek norādīta, sistēma izvēlas tēmu, kas nav izmantota pēdējās 30 publikācijās.">
          <select className={inputCls} value={topic} onChange={(e) => setTopic(Number(e.target.value) || "")} disabled={!channel}>
            <option value="">Automātiski</option>
            {topics?.filter((t) => t.is_active).map((t) => (
              <option key={t.id} value={t.id}>{t.title}</option>
            ))}
          </select>
        </Field>
        {error && <Alert>{error}</Alert>}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>Atcelt</Button>
          <Button onClick={submit} disabled={!channel}>Sākt ģenerēšanu</Button>
        </div>
      </div>
    </Modal>
  );
}
