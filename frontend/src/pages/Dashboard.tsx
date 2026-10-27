import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../api";
import GenerateModal from "../components/GenerateModal";
import JobTable from "../components/JobTable";
import { Button, Card, PageHeader, ProgressBar } from "../components/ui";
import { fmtDate, fmtEur } from "../format";
import type { Budget, JobRow, Notification, Providers } from "../types";

interface DashboardData {
  published_today: number;
  pending_review: number;
  errors_24h: number;
  in_progress: number;
  budget: Budget;
  quota: { used: number; limit: number };
  recent_jobs: JobRow[];
  notifications: Notification[];
  providers: Providers;
}

function Stat({ label, value, to, tone }: { label: string; value: number | string; to?: string; tone?: string }) {
  const body = (
    <div className="rounded-lg border border-slate-200 bg-white p-4 transition hover:border-slate-300">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${tone ?? "text-slate-900"}`}>{value}</div>
    </div>
  );
  return to ? <Link to={to}>{body}</Link> : body;
}

export default function Dashboard() {
  const { data } = useApi<DashboardData>("/dashboard", 5000);
  const [generate, setGenerate] = useState(false);

  if (!data) return null;
  const quotaPct = (data.quota.used / data.quota.limit) * 100;

  return (
    <>
      <PageHeader
        title="Sākums"
        sub="Sistēmas darbības kopsavilkums"
        actions={<Button onClick={() => setGenerate(true)}>Ģenerēt video</Button>}
      />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Šodien publicēti" value={data.published_today} to="/videos?status=published" />
        <Stat label="Gaida apstiprinājumu" value={data.pending_review} to="/videos?status=pending_review"
              tone={data.pending_review ? "text-violet-700" : undefined} />
        <Stat label="Kļūdas (24 h)" value={data.errors_24h} to="/videos?status=error"
              tone={data.errors_24h ? "text-red-700" : undefined} />
        <Stat label="Rindā / izpildē" value={data.in_progress} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card title="Pēdējie uzdevumi" className="lg:col-span-2" actions={<Link to="/videos" className="text-xs text-slate-500 hover:text-slate-900">Visi video →</Link>}>
          <JobTable jobs={data.recent_jobs} compact />
        </Card>

        <div className="space-y-4">
          <Card title="Mēneša API budžets">
            <div className="mb-2 flex items-baseline justify-between text-sm">
              <span className="font-semibold">{fmtEur(data.budget.spent)}</span>
              <span className="text-slate-500">no {fmtEur(data.budget.limit)}</span>
            </div>
            <ProgressBar pct={data.budget.pct} />
            <div className="mt-4 mb-2 flex items-baseline justify-between text-sm">
              <span className="text-slate-600">YouTube augšupielādes šodien</span>
              <span className="text-slate-500">{data.quota.used} / {data.quota.limit}</span>
            </div>
            <ProgressBar pct={quotaPct} />
          </Card>

          <Card title="Paziņojumi">
            {data.notifications.length === 0 && <p className="text-sm text-slate-400">Nav paziņojumu</p>}
            <ul className="space-y-2">
              {data.notifications.map((n) => (
                <li key={n.id} className="text-sm">
                  <span className={n.level === "error" ? "text-red-700" : n.level === "warning" ? "text-amber-700" : "text-slate-700"}>
                    {n.message}
                  </span>
                  <span className="ml-2 text-xs text-slate-400">{fmtDate(n.created_at)}</span>
                </li>
              ))}
            </ul>
          </Card>

          <Card title="Ārējie servisi">
            <dl className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm">
              <dt className="text-slate-500">Teksts</dt><dd>{data.providers.llm}</dd>
              <dt className="text-slate-500">Balss</dt><dd>{data.providers.tts}</dd>
              <dt className="text-slate-500">Materiāli</dt><dd>{data.providers.media}</dd>
              <dt className="text-slate-500">Publicēšana</dt><dd>{data.providers.platform}</dd>
            </dl>
          </Card>
        </div>
      </div>

      {generate && <GenerateModal onClose={() => setGenerate(false)} />}
    </>
  );
}
