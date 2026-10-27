import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { api, useApi } from "../api";
import { fmtDate } from "../format";
import type { Notification } from "../types";

const NAV = [
  { to: "/", label: "Sākums" },
  { to: "/videos", label: "Video" },
  { to: "/channels", label: "Kanāli" },
  { to: "/logs", label: "Žurnāls" },
  { to: "/stats", label: "Statistika" },
  { to: "/settings", label: "Budžets un kvota" },
  { to: "/admins", label: "Administratori" },
];

const LEVEL_DOT: Record<string, string> = {
  info: "bg-sky-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
};

function Notifications() {
  const [open, setOpen] = useState(false);
  const { data, reload } = useApi<Notification[]>("/notifications", 10000);
  const unread = data?.filter((n) => !n.is_read).length ?? 0;

  const markRead = async () => {
    await api("/notifications/read-all", "POST");
    reload();
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100"
      >
        Paziņojumi
        {unread > 0 && (
          <span className="ml-1.5 rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-semibold text-white">{unread}</span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-40 mt-2 w-80 max-w-[calc(100vw-2rem)] rounded-lg border border-slate-200 bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
            <span className="text-sm font-semibold">Paziņojumi</span>
            {unread > 0 && (
              <button onClick={markRead} className="text-xs text-slate-500 hover:text-slate-900">
                Atzīmēt kā lasītus
              </button>
            )}
          </div>
          <ul className="max-h-96 divide-y divide-slate-100 overflow-y-auto">
            {data?.length === 0 && <li className="p-4 text-center text-sm text-slate-400">Nav paziņojumu</li>}
            {data?.map((n) => (
              <li key={n.id} className={`flex gap-2 px-3 py-2 text-sm ${n.is_read ? "text-slate-500" : "text-slate-800"}`}>
                <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${LEVEL_DOT[n.level]}`} />
                <div className="min-w-0">
                  {n.job_id ? (
                    <Link to={`/videos/${n.job_id}`} onClick={() => setOpen(false)} className="hover:underline">
                      {n.message}
                    </Link>
                  ) : (
                    n.message
                  )}
                  <div className="text-xs text-slate-400">{fmtDate(n.created_at)}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function Layout({ username, onLogout }: { username: string; onLogout: () => void }) {
  const [menuOpen, setMenuOpen] = useState(false);

  const nav = (
    <nav className="flex flex-col gap-0.5">
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.to === "/"}
          onClick={() => setMenuOpen(false)}
          className={({ isActive }) =>
            `rounded-md px-3 py-2 text-sm ${isActive ? "bg-slate-800 font-medium text-white" : "text-slate-300 hover:bg-slate-800/60 hover:text-white"}`
          }
        >
          {n.label}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-slate-50 lg:pl-56">
      <aside className="fixed inset-y-0 left-0 hidden w-56 flex-col bg-slate-900 px-3 py-5 lg:flex">
        <Link to="/" className="mb-6 px-3 text-base font-semibold text-white">
          Shorts Studio
        </Link>
        {nav}
        <p className="mt-auto px-3 text-xs text-slate-500">
          Prototips · PIT 2026
          <span className="mt-0.5 block font-mono text-slate-600">v0.6.7</span>
        </p>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-slate-200 bg-white/90 px-4 backdrop-blur">
        <button className="rounded-md px-2 py-1 text-sm text-slate-700 hover:bg-slate-100 lg:hidden" onClick={() => setMenuOpen(!menuOpen)}>
          ☰ Izvēlne
        </button>
        <div className="ml-auto flex items-center gap-2">
          <Notifications />
          <span className="hidden text-sm text-slate-500 sm:inline">{username}</span>
          <button onClick={onLogout} className="rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100">
            Iziet
          </button>
        </div>
      </header>

      {menuOpen && <div className="border-b border-slate-800 bg-slate-900 p-3 lg:hidden">{nav}</div>}

      <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
