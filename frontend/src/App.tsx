import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { api } from "./api";
import Layout from "./components/Layout";
import Admins from "./pages/Admins";
import ChannelDetail from "./pages/ChannelDetail";
import Channels from "./pages/Channels";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import Settings from "./pages/Settings";
import Stats from "./pages/Stats";
import VideoDetail from "./pages/VideoDetail";
import Videos from "./pages/Videos";

interface User {
  id: number;
  username: string;
}

export default function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined);

  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => setUser(null));
    const onUnauthorized = () => setUser(null);
    window.addEventListener("unauthorized", onUnauthorized);
    return () => window.removeEventListener("unauthorized", onUnauthorized);
  }, []);

  if (user === undefined) return null;
  if (user === null) return <Login onLogin={setUser} />;

  const logout = async () => {
    await api("/auth/logout", "POST");
    setUser(null);
  };

  return (
    <Routes>
      <Route element={<Layout username={user.username} onLogout={logout} />}>
        <Route index element={<Dashboard />} />
        <Route path="videos" element={<Videos />} />
        <Route path="videos/:id" element={<VideoDetail />} />
        <Route path="channels" element={<Channels />} />
        <Route path="channels/:id" element={<ChannelDetail />} />
        <Route path="logs" element={<Logs />} />
        <Route path="stats" element={<Stats />} />
        <Route path="settings" element={<Settings />} />
        <Route path="admins" element={<Admins />} />
        <Route path="*" element={<p className="text-slate-500">Lapa nav atrasta.</p>} />
      </Route>
    </Routes>
  );
}
