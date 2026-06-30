"use client";

import { api } from "@/lib/api";
import { Bell, Check } from "lucide-react";
import { useEffect, useState } from "react";

type Ntf = { id: string; title: string; body: string; level: string; read: boolean; created_at: string };

export function NotificationBell() {
  const [count, setCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Ntf[]>([]);

  function refreshCount() { api.unreadCount().then((r) => setCount(r.count)).catch(() => {}); }
  useEffect(() => {
    refreshCount();
    const t = setInterval(refreshCount, 30000);
    return () => clearInterval(t);
  }, []);

  function toggle() {
    const next = !open;
    setOpen(next);
    if (next) api.notifications().then(setItems).catch(() => {});
  }
  async function markRead(id: string) {
    await api.markNotificationRead(id);
    setItems((x) => x.map((i) => (i.id === id ? { ...i, read: true } : i)));
    refreshCount();
  }
  async function markAll() {
    await api.markAllNotificationsRead();
    setItems((x) => x.map((i) => ({ ...i, read: true })));
    refreshCount();
  }

  return (
    <div className="fixed right-4 top-3 z-50">
      <button onClick={toggle} aria-label="Notificaciones"
        className="relative rounded-full border border-slate-200 bg-white p-2 shadow-sm hover:bg-slate-50">
        <Bell className="h-4 w-4 text-slate-600" />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-bold text-white">
            {count > 9 ? "9+" : count}
          </span>
        )}
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-50 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-100 px-3 py-2">
              <span className="text-sm font-semibold text-slate-800">Notificaciones</span>
              <button onClick={markAll} className="text-xs font-semibold text-violet-600 hover:text-violet-800">Marcar todo leído</button>
            </div>
            <div className="max-h-96 overflow-auto">
              {items.length === 0 && <p className="px-3 py-6 text-center text-xs text-slate-400">Sin notificaciones.</p>}
              {items.map((n) => (
                <div key={n.id} className={`border-b border-slate-50 px-3 py-2 text-sm ${n.read ? "opacity-60" : "bg-violet-50/40"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <span className={`font-medium ${n.level === "error" ? "text-red-600" : n.level === "warn" ? "text-amber-600" : "text-slate-700"}`}>{n.title}</span>
                    {!n.read && (
                      <button onClick={() => markRead(n.id)} title="Marcar leído" className="shrink-0 text-slate-400 hover:text-slate-600">
                        <Check className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                  {n.body && <p className="mt-0.5 max-h-60 overflow-y-auto whitespace-pre-wrap text-xs text-slate-500">{n.body}</p>}
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
