import { useEffect, useState } from "react";
import { api, useApi } from "../api";
import { Alert, Button, Card, Field, PageHeader, ProgressBar, inputCls } from "../components/ui";
import { fmtEur } from "../format";
import type { Budget, Providers } from "../types";

interface SettingsData {
  monthly_budget_eur: number;
  youtube_daily_quota: number;
  youtube_upload_units: number;
  scheduler_enabled: boolean;
  budget: Budget;
  quota_used_today: number;
  providers: Providers;
}

export default function Settings() {
  const { data, setData } = useApi<SettingsData>("/settings");
  const [budget, setBudget] = useState("");
  const [quota, setQuota] = useState("");
  const [scheduler, setScheduler] = useState(false);
  const [msg, setMsg] = useState<{ kind: "error" | "success"; text: string } | null>(null);

  useEffect(() => {
    if (data) {
      setBudget(String(data.monthly_budget_eur));
      setQuota(String(data.youtube_daily_quota));
      setScheduler(data.scheduler_enabled);
    }
  }, [data]);

  if (!data) return null;

  const save = async () => {
    setMsg(null);
    try {
      setData(await api<SettingsData>("/settings", "PUT", {
        monthly_budget_eur: Number(budget),
        youtube_daily_quota: Number(quota),
        scheduler_enabled: scheduler,
      }));
      setMsg({ kind: "success", text: "Iestatījumi saglabāti" });
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    }
  };

  const uploadsLeft = Math.max(0, Math.floor((data.youtube_daily_quota - data.quota_used_today) / data.youtube_upload_units));

  return (
    <>
      <PageHeader title="Budžets un kvota" sub="API izmaksu ierobežojumi un YouTube Data API kvota" />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Ierobežojumi">
          <div className="space-y-4">
            <Field label="Mēneša API budžets (EUR)" hint="Sasniedzot 80 %, tiek nosūtīts brīdinājums. Sasniedzot limitu, jauni uzdevumi tiek atlikti.">
              <input type="number" min={0} step="0.01" className={inputCls} value={budget} onChange={(e) => setBudget(e.target.value)} />
            </Field>
            <Field label="YouTube augšupielāžu limits dienā" hint="videos.insert kvota no Google Cloud Console (noklusēti 100 dienā).">
              <input type="number" min={1} className={inputCls} value={quota} onChange={(e) => setQuota(e.target.value)} />
            </Field>
            <label className="flex items-start gap-2 text-sm">
              <input type="checkbox" className="mt-0.5" checked={scheduler} onChange={(e) => setScheduler(e.target.checked)} />
              <span>
                Automātiskā ģenerēšana pēc grafika
                <span className="block text-xs text-slate-500">Ja izslēgta, video tiek ģenerēti tikai manuāli. Ieslēdzot tiek tērēti API līdzekļi.</span>
              </span>
            </label>
            {msg && <Alert kind={msg.kind}>{msg.text}</Alert>}
            <Button onClick={save}>Saglabāt</Button>
          </div>
        </Card>

        <div className="space-y-4">
          <Card title="Šī mēneša izlietojums">
            <div className="mb-2 flex items-baseline justify-between text-sm">
              <span className="font-semibold">{fmtEur(data.budget.spent, 4)}</span>
              <span className="text-slate-500">{data.budget.pct}% no {fmtEur(data.budget.limit)}</span>
            </div>
            <ProgressBar pct={data.budget.pct} />
          </Card>
          <Card title="YouTube augšupielādes šodien">
            <div className="mb-2 flex items-baseline justify-between text-sm">
              <span className="font-semibold">{data.quota_used_today}</span>
              <span className="text-slate-500">no {data.youtube_daily_quota}</span>
            </div>
            <ProgressBar pct={(data.quota_used_today / data.youtube_daily_quota) * 100} />
            <p className="mt-2 text-xs text-slate-500">Šodien vēl iespējamas {uploadsLeft} augšupielādes.</p>
          </Card>
          <Card title="Aktīvie adapteri">
            <p className="mb-2 text-xs text-slate-500">Reālie servisi tiek izmantoti, ja .env failā norādīta API atslēga.</p>
            <dl className="grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm">
              <dt className="text-slate-500">Skripts</dt><dd>{data.providers.llm}</dd>
              <dt className="text-slate-500">Balss</dt><dd>{data.providers.tts}</dd>
              <dt className="text-slate-500">Materiāli</dt><dd>{data.providers.media}</dd>
              <dt className="text-slate-500">Publicēšana</dt><dd>{data.providers.platform}</dd>
            </dl>
          </Card>
        </div>
      </div>
    </>
  );
}
