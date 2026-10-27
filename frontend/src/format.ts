import type { JobStatus } from "./types";

export const STATUS: Record<JobStatus, { label: string; cls: string }> = {
  waiting: { label: "Gaida", cls: "bg-slate-100 text-slate-700 ring-slate-300" },
  postponed: { label: "Atlikts", cls: "bg-amber-50 text-amber-800 ring-amber-300" },
  running: { label: "Izpildē", cls: "bg-sky-50 text-sky-800 ring-sky-300" },
  pending_review: { label: "Gaida apstiprinājumu", cls: "bg-violet-50 text-violet-800 ring-violet-300" },
  approved: { label: "Apstiprināts", cls: "bg-teal-50 text-teal-800 ring-teal-300" },
  rejected: { label: "Noraidīts", cls: "bg-zinc-100 text-zinc-600 ring-zinc-300" },
  published: { label: "Publicēts", cls: "bg-emerald-50 text-emerald-800 ring-emerald-300" },
  error: { label: "Kļūda", cls: "bg-red-50 text-red-800 ring-red-300" },
};

export const LOG_RESULT: Record<string, { label: string; cls: string }> = {
  ok: { label: "OK", cls: "bg-emerald-50 text-emerald-800 ring-emerald-300" },
  warn: { label: "Brīdinājums", cls: "bg-amber-50 text-amber-800 ring-amber-300" },
  retry: { label: "Atkārtojums", cls: "bg-sky-50 text-sky-800 ring-sky-300" },
  error: { label: "Kļūda", cls: "bg-red-50 text-red-800 ring-red-300" },
  info: { label: "Info", cls: "bg-slate-100 text-slate-700 ring-slate-300" },
};

export const LANGUAGES: Record<string, string> = { en: "Angļu", lv: "Latviešu" };

export function fmtDate(iso: string | null | undefined) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("lv-LV", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString("lv-LV", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function fmtEur(v: number, digits = 2) {
  return v.toLocaleString("lv-LV", { minimumFractionDigits: digits, maximumFractionDigits: digits }) + " €";
}

export function fmtDuration(sec: number | null) {
  if (sec == null) return "—";
  return `${sec.toFixed(1)} s`;
}

export const isBusy = (s: JobStatus) => s === "waiting" || s === "running";
