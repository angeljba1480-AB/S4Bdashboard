"use client";

import { api } from "@/lib/api";
import { Download, Plus, Server, TestTube, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

type Sftp = { id: string; name: string; host: string; port: number; username: string; auth_type: string; remote_path: string; area: string; category: string; created_at: string };

export function SftpPanel() {
  const [items, setItems] = useState<Sftp[]>([]);
  const [form, setForm] = useState({ name: "", host: "", port: 22, username: "", auth_type: "password", secret: "", remote_path: "", area: "", category: "" });
  const [msg, setMsg] = useState("");

  function load() { api.sftpSources().then(setItems).catch(() => {}); }
  useEffect(load, []);

  async function create() {
    if (!form.host.trim() || !form.username.trim() || !form.remote_path.trim() || !form.secret.trim()) {
      setMsg("host, usuario, ruta y credencial son obligatorios."); return;
    }
    try {
      await api.createSftp({ ...form, port: Number(form.port) || 22 });
      setForm({ name: "", host: "", port: 22, username: "", auth_type: "password", secret: "", remote_path: "", area: "", category: "" });
      setMsg("Conector creado."); load();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function test(s: Sftp) {
    setMsg(`Probando ${s.name}…`);
    try {
      const r = await api.testSftp(s.id);
      setMsg(`${s.name}: ${r.count} archivo(s) — ${r.files.slice(0, 5).map((f) => f.name).join(", ")}`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function importNow(s: Sftp) {
    setMsg(`Importando de ${s.name}…`);
    try {
      const r = await api.importSftp(s.id);
      setMsg(`${s.name}: ${r.imported} documento(s) importado(s) al RAG.`);
    } catch (e) { setMsg(e instanceof Error ? e.message : "Error"); }
  }

  async function remove(id: string) {
    if (!window.confirm("¿Eliminar el conector SFTP?")) return;
    await api.deleteSftp(id); load();
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <div className="mb-1 flex items-center gap-2">
        <Server className="h-5 w-5 text-violet-600" />
        <h2 className="font-semibold text-slate-800">Conector SFTP (sistemas legados)</h2>
      </div>
      <p className="mb-4 text-xs text-slate-500">
        Trae archivos (PDF, DOCX, CSV, TXT) de un servidor <b>SFTP</b> de solo lectura y los
        importa al repositorio + RAG (clasificados y cifrados). Apunta a un archivo o a un directorio.
      </p>

      <div className="mb-4 grid grid-cols-1 gap-2 rounded-xl border border-slate-100 bg-slate-50 p-3 sm:grid-cols-2">
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
          placeholder="Nombre (ej. ERP exports)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })}
          placeholder="Host (ej. sftp.acme.mx)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })}
          placeholder="Usuario" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })}
          placeholder="Puerto (22)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <select value={form.auth_type} onChange={(e) => setForm({ ...form, auth_type: e.target.value })}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
          <option value="password">Contraseña</option>
          <option value="key">Llave privada (PEM)</option>
        </select>
        <input value={form.remote_path} onChange={(e) => setForm({ ...form, remote_path: e.target.value })}
          placeholder="Ruta remota (archivo o carpeta)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
        <textarea value={form.secret} onChange={(e) => setForm({ ...form, secret: e.target.value })}
          placeholder={form.auth_type === "key" ? "Pega la llave privada PEM" : "Contraseña"} rows={form.auth_type === "key" ? 3 : 1}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm sm:col-span-2" />
        <button onClick={create} className="flex items-center justify-center gap-1.5 rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white sm:col-span-2">
          <Plus className="h-4 w-4" /> Crear conector
        </button>
      </div>
      {msg && <div className="mb-3 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">{msg}</div>}

      <div className="space-y-2">
        {items.length === 0 && <p className="text-xs text-slate-400">Aún no hay conectores SFTP.</p>}
        {items.map((s) => (
          <div key={s.id} className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm">
            <span className="min-w-0">
              <span className="font-medium text-slate-700">{s.name}</span>
              <span className="block truncate text-xs text-slate-400">{s.username}@{s.host}:{s.port} · {s.remote_path} · {s.auth_type}</span>
            </span>
            <span className="flex shrink-0 items-center gap-1.5">
              <button onClick={() => test(s)} title="Probar conexión" className="rounded-md border border-slate-300 p-1 text-slate-500"><TestTube className="h-3.5 w-3.5" /></button>
              <button onClick={() => importNow(s)} title="Importar al RAG" className="rounded-md bg-violet-600 p-1 text-white"><Download className="h-3.5 w-3.5" /></button>
              <button onClick={() => remove(s.id)} title="Eliminar" className="rounded-md border border-slate-300 p-1 text-red-500"><Trash2 className="h-3.5 w-3.5" /></button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
