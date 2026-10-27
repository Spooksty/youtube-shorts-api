import { useNavigate } from "react-router-dom";
import { fmtDate, fmtDuration } from "../format";
import type { JobRow } from "../types";
import { StatusBadge, Table } from "./ui";

export default function JobTable({ jobs, compact }: { jobs: JobRow[]; compact?: boolean }) {
  const navigate = useNavigate();
  const head = compact
    ? ["#", "Kanāls", "Tēma", "Statuss", "Izveidots"]
    : ["#", "Kanāls", "Tēma / virsraksts", "Statuss", "Solis / kļūda", "Ilgums", "Izveidots"];

  return (
    <Table head={head} empty={jobs.length === 0}>
      {jobs.map((j) => (
        <tr key={j.id} onClick={() => navigate(`/videos/${j.id}`)} className="cursor-pointer hover:bg-slate-50">
          <td className="px-3 py-2 text-slate-400">{j.id}</td>
          <td className="whitespace-nowrap px-3 py-2">{j.channel}</td>
          <td className="max-w-xs px-3 py-2">
            <div className="truncate">{j.title ?? j.topic ?? <span className="text-slate-400">Tēma vēl nav izvēlēta</span>}</div>
            {!compact && j.title && j.topic && <div className="truncate text-xs text-slate-400">{j.topic}</div>}
          </td>
          <td className="px-3 py-2"><StatusBadge status={j.status} /></td>
          {!compact && (
            <>
              <td className="max-w-[16rem] px-3 py-2 text-xs text-slate-500">
                <div className="truncate">{j.error ?? j.current_step ?? ""}</div>
              </td>
              <td className="whitespace-nowrap px-3 py-2 text-slate-600">{fmtDuration(j.duration)}</td>
            </>
          )}
          <td className="whitespace-nowrap px-3 py-2 text-slate-500">{fmtDate(j.created_at)}</td>
        </tr>
      ))}
    </Table>
  );
}
