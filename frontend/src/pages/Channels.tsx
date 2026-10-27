import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApi } from "../api";
import ChannelForm from "../components/ChannelForm";
import { Badge, Button, Card, Modal, PageHeader, Table } from "../components/ui";
import { LANGUAGES } from "../format";
import type { Channel } from "../types";

export default function Channels() {
  const navigate = useNavigate();
  const { data: channels } = useApi<Channel[]>("/channels");
  const [adding, setAdding] = useState(false);

  return (
    <>
      <PageHeader
        title="Kanāli"
        sub="YouTube kanāli un to iestatījumi"
        actions={<Button onClick={() => setAdding(true)}>Pievienot kanālu</Button>}
      />
      <Card>
        <Table head={["Nosaukums", "Tēmu joma", "Valoda", "Auditorija", "YouTube", "Statuss", "Tēmas", "Publicēti", "Gaida"]}
               empty={channels?.length === 0}>
          {channels?.map((c) => (
            <tr key={c.id} onClick={() => navigate(`/channels/${c.id}`)} className="cursor-pointer hover:bg-slate-50">
              <td className="px-3 py-2 font-medium">{c.name}</td>
              <td className="px-3 py-2">{c.niche}</td>
              <td className="px-3 py-2">{LANGUAGES[c.language] ?? c.language}</td>
              <td className="px-3 py-2">{c.audience_age}</td>
              <td className="px-3 py-2">
                {c.linked
                  ? <Badge label="Sasaistīts" cls="bg-emerald-50 text-emerald-800 ring-emerald-300" />
                  : <Badge label="Nav sasaistīts" cls="bg-amber-50 text-amber-800 ring-amber-300" />}
              </td>
              <td className="px-3 py-2">
                {c.is_active
                  ? <Badge label="Aktīvs" cls="bg-emerald-50 text-emerald-800 ring-emerald-300" />
                  : <Badge label="Neaktīvs" cls="bg-zinc-100 text-zinc-600 ring-zinc-300" />}
              </td>
              <td className="px-3 py-2">{c.topic_count}</td>
              <td className="px-3 py-2">{c.published}</td>
              <td className="px-3 py-2">{c.pending}</td>
            </tr>
          ))}
        </Table>
      </Card>

      {adding && (
        <Modal title="Jauns kanāls" onClose={() => setAdding(false)} wide>
          <ChannelForm onCancel={() => setAdding(false)} onSaved={(c) => navigate(`/channels/${c.id}`, { state: { message: c.message } })} />
        </Modal>
      )}
    </>
  );
}
