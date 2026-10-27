import { useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useApi } from "../api";
import { Alert, Card, Field, PageHeader, Table, inputCls } from "../components/ui";
import { fmtEur } from "../format";

// Demo data until the daily YouTube stats fetch is connected to a real channel
const DEMO_CHANNELS = [
  { name: "Wild Facts Daily", color: "#2a78d6", base: 1800, growth: 60 },
  { name: "Space in 30s", color: "#eb6834", base: 900, growth: 45 },
  { name: "Vēstures mīklas", color: "#1baf7a", base: 300, growth: 15 },
];

function seeded(seed: number) {
  let s = seed;
  return () => {
    s = (s * 9301 + 49297) % 233280;
    return s / 233280;
  };
}

function demoSeries(days: number) {
  const rand = seeded(days);
  const today = new Date();
  return Array.from({ length: days }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (days - 1 - i));
    const row: Record<string, string | number> = {
      day: d.toLocaleDateString("lv-LV", { day: "2-digit", month: "2-digit" }),
    };
    for (const c of DEMO_CHANNELS) {
      row[c.name] = Math.round(c.base + c.growth * i + (rand() - 0.5) * c.base * 0.6);
    }
    return row;
  });
}

interface CostReport {
  by_service: { service: string; requests: number; cost_eur: number }[];
  by_channel: { channel: string; jobs: number; cost_eur: number }[];
}

const axis = { fontSize: 12, fill: "#64748b" };

export default function Stats() {
  const [days, setDays] = useState(30);
  const series = useMemo(() => demoSeries(days), [days]);
  const { data: costs } = useApi<CostReport>(`/reports/costs?days=${days}`);

  const totals = DEMO_CHANNELS.map((c) => {
    const views = series.reduce((s, r) => s + (r[c.name] as number), 0);
    return { ...c, views, likes: Math.round(views * 0.045), comments: Math.round(views * 0.004), videos: Math.round(days * (c.base > 1000 ? 2.6 : 1.4)) };
  });
  const sum = (k: "views" | "likes" | "comments" | "videos") => totals.reduce((s, t) => s + t[k], 0);

  return (
    <>
      <PageHeader
        title="Statistika un izmaksas"
        sub="Publicēto video rezultāti un API izmaksas pa kanāliem"
        actions={
          <Field label="Periods">
            <select className={inputCls} value={days} onChange={(e) => setDays(Number(e.target.value))}>
              <option value={7}>Pēdējās 7 dienas</option>
              <option value={30}>Pēdējās 30 dienas</option>
              <option value={90}>Pēdējās 90 dienas</option>
            </select>
          </Field>
        }
      />

      <div className="mb-4">
        <Alert kind="info">Skatījumu statistika prototipā ir demonstrācijas dati. Izmaksu tabulas zemāk tiek nolasītas no datubāzes.</Alert>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ["Publicēti video", sum("videos")],
          ["Skatījumi", sum("views")],
          ["Patīk", sum("likes")],
          ["Komentāri", sum("comments")],
        ].map(([label, value]) => (
          <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
            <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
            <div className="mt-1 text-2xl font-semibold">{Number(value).toLocaleString("lv-LV")}</div>
          </div>
        ))}
      </div>

      <Card title="Skatījumi dienā" className="mb-4">
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
              <CartesianGrid stroke="#e2e8f0" vertical={false} />
              <XAxis dataKey="day" tick={axis} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} minTickGap={24} />
              <YAxis tick={axis} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
              <Legend wrapperStyle={{ fontSize: 12 }} iconType="plainline"
                      formatter={(v: string) => <span className="text-slate-600">{v}</span>} />
              {DEMO_CHANNELS.map((c) => (
                <Line key={c.name} type="monotone" dataKey={c.name} stroke={c.color} strokeWidth={2} dot={false}
                      activeDot={{ r: 4 }} isAnimationActive={false} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Pa kanāliem" className="mb-4">
        <Table head={["Kanāls", "Video", "Skatījumi", "Patīk", "Komentāri", "Vid. skatījumi uz video"]}>
          {totals.map((t) => (
            <tr key={t.name}>
              <td className="px-3 py-2">
                <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: t.color }} />
                {t.name}
              </td>
              <td className="px-3 py-2">{t.videos}</td>
              <td className="px-3 py-2">{t.views.toLocaleString("lv-LV")}</td>
              <td className="px-3 py-2">{t.likes.toLocaleString("lv-LV")}</td>
              <td className="px-3 py-2">{t.comments.toLocaleString("lv-LV")}</td>
              <td className="px-3 py-2">{Math.round(t.views / t.videos).toLocaleString("lv-LV")}</td>
            </tr>
          ))}
        </Table>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="API izmaksas pa servisiem">
          {costs && costs.by_service.length > 0 ? (
            <>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={costs.by_service} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
                    <CartesianGrid stroke="#e2e8f0" vertical={false} />
                    <XAxis dataKey="service" tick={axis} tickLine={false} axisLine={{ stroke: "#cbd5e1" }} />
                    <YAxis tick={axis} tickLine={false} axisLine={false} />
                    <Tooltip formatter={(v: number) => fmtEur(v, 4)} contentStyle={{ fontSize: 12, borderRadius: 6 }} cursor={{ fill: "#f1f5f9" }} />
                    <Bar dataKey="cost_eur" name="Izmaksas" fill="#2a78d6" radius={[4, 4, 0, 0]} maxBarSize={48}
                         isAnimationActive={false} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <Table head={["Serviss", "Pieprasījumi", "Izmaksas"]}>
                {costs.by_service.map((s) => (
                  <tr key={s.service}>
                    <td className="px-3 py-1.5">{s.service}</td>
                    <td className="px-3 py-1.5">{s.requests}</td>
                    <td className="px-3 py-1.5">{fmtEur(s.cost_eur, 4)}</td>
                  </tr>
                ))}
              </Table>
            </>
          ) : (
            <p className="text-sm text-slate-400">Šajā periodā nav izmaksu ierakstu.</p>
          )}
        </Card>

        <Card title="API izmaksas pa kanāliem">
          <Table head={["Kanāls", "Uzdevumi", "Izmaksas", "Uz uzdevumu"]} empty={!costs?.by_channel.length}>
            {costs?.by_channel.map((c) => (
              <tr key={c.channel}>
                <td className="px-3 py-1.5">{c.channel}</td>
                <td className="px-3 py-1.5">{c.jobs}</td>
                <td className="px-3 py-1.5">{fmtEur(c.cost_eur, 4)}</td>
                <td className="px-3 py-1.5">{fmtEur(c.jobs ? c.cost_eur / c.jobs : 0, 4)}</td>
              </tr>
            ))}
          </Table>
        </Card>
      </div>
    </>
  );
}
