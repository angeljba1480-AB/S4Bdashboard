"use client";

import { api } from "@/lib/api";
import { FolderKanban } from "lucide-react";
import { useState } from "react";

type Site = { id: string; name: string; web_url: string };
type Item = { id: string; name: string; is_folder: boolean; size: number };

/** Explorador SharePoint tipo Drive: busca sitios → navega carpetas → importa
 * archivos al repositorio + RAG, con la cuenta Microsoft conectada. */
export function SharepointBrowser({ area, category }: { area?: string; category?: string }) {
  const [open, setOpen] = useState(false);
  const [sites, setSites] = useState<Site[]>([]);
  const [site, setSite] = useState<Site | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [stack, setStack] = useState<{ id: string; name: string }[]>([]);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  async function loadSites() {
    setBusy(true); setMsg("");
    try { setSites((await api.sharepointSites(query)).sites); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function openSite(s: Site) {
    setSite(s); setStack([]); setBusy(true); setMsg("");
    try { setItems((await api.sharepointBrowse(s.id, "")).files); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function openFolder(it: Item) {
    if (!site) return;
    setBusy(true); setMsg("");
    try { setItems((await api.sharepointBrowse(site.id, it.id)).files); setStack((s) => [...s, { id: it.id, name: it.name }]); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function goCrumb(i: number) {
    if (!site) return;
    const folder = i < 0 ? "" : stack[i].id;
    setBusy(true);
    try { setItems((await api.sharepointBrowse(site.id, folder)).files); setStack((s) => s.slice(0, i + 1)); }
    catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
    finally { setBusy(false); }
  }
  async function importItem(it: Item) {
    if (!site) return;
    setMsg(`Importando ${it.name}…`);
    try { const r = await api.sharepointImportItem({ site: site.id, item_id: it.id, name: it.name, area, category }); setMsg(`✓ Importado: ${r.filename}`); }
    catch (e) { setMsg(e instanceof Error ? `✗ ${e.message}` : "Error"); }
  }

  return (
    <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-4">
      <button onClick={() => { setOpen((v) => !v); if (!open && !sites.length) loadSites(); }}
        className="flex w-full items-center justify-between text-sm font-semibold text-slate-800">
        <span className="flex items-center gap-2"><FolderKanban className="h-4 w-4 text-violet-600" /> Importar de SharePoint</span>
        <span className="text-xs text-slate-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-slate-400">Se importa con el área/categoría de arriba. Requiere tu cuenta Microsoft conectada.</p>
          {!site ? (
            <>
              <div className="flex gap-2">
                <input value={query} onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") loadSites(); }}
                  placeholder="Buscar sitio…" className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm" />
                <button onClick={loadSites} disabled={busy} className="rounded-lg bg-slate-900 px-3 text-sm font-semibold text-white disabled:opacity-50">Buscar</button>
              </div>
              {msg && <div className="text-xs text-slate-500">{msg}</div>}
              <div className="max-h-64 space-y-1 overflow-auto">
                {sites.map((s) => (
                  <button key={s.id} onClick={() => openSite(s)} className="block w-full truncate rounded-lg border border-slate-100 px-2 py-1.5 text-left text-sm text-slate-600 hover:text-violet-700">
                    🏢 {s.name}
                  </button>
                ))}
                {!busy && sites.length === 0 && <p className="text-xs text-slate-400">Sin sitios. Busca por nombre.</p>}
              </div>
            </>
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-1 text-xs text-slate-500">
                <button onClick={() => { setSite(null); setItems([]); setStack([]); }} className="rounded px-1 hover:text-violet-700">Sitios</button>
                <span className="text-slate-300">/</span>
                <button onClick={() => goCrumb(-1)} className="max-w-[140px] truncate rounded px-1 hover:text-violet-700">{site.name}</button>
                {stack.map((c, i) => (
                  <span key={c.id} className="flex items-center gap-1">
                    <span className="text-slate-300">/</span>
                    <button onClick={() => goCrumb(i)} className="max-w-[120px] truncate rounded px-1 hover:text-violet-700">{c.name}</button>
                  </span>
                ))}
              </div>
              {msg && <div className="text-xs text-slate-500">{msg}</div>}
              <div className="max-h-64 space-y-1 overflow-auto">
                {items.map((it) => (
                  <div key={it.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-2 py-1.5 text-sm">
                    {it.is_folder ? (
                      <button onClick={() => openFolder(it)} disabled={busy} className="flex min-w-0 items-center gap-1 truncate text-left text-slate-600 hover:text-violet-700">📁 <span className="truncate">{it.name}</span></button>
                    ) : (
                      <span className="truncate text-slate-600">📄 {it.name}</span>
                    )}
                    {!it.is_folder && (
                      <button onClick={() => importItem(it)} className="shrink-0 rounded-md bg-violet-600 px-2 py-1 text-xs font-semibold text-white">Importar</button>
                    )}
                  </div>
                ))}
                {!busy && items.length === 0 && <p className="text-xs text-slate-400">Carpeta vacía.</p>}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
