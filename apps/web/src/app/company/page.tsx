"use client";

import { PageHeader, Shell } from "@/components/Shell";
import { api } from "@/lib/api";
import type { CompanyArea, CompanyProfile, Me } from "@shared/types";
import { Building2, CheckCircle2, Plus, Save, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const SIZES = ["Micro (1-10)", "Pequeña (11-50)", "Mediana (51-250)", "Grande (250+)"];
const TONES = ["Formal", "Cercano", "Persuasivo", "Directo", "Institucional"];

export default function CompanyPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [p, setP] = useState<CompanyProfile | null>(null);
  const [tech, setTech] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const canEdit = me?.role === "admin" || me?.role === "super_admin";

  useEffect(() => {
    api.me().then(setMe).catch(() => {});
    api.companyProfile()
      .then((data) => {
        setP(data);
        setTech((data.tech_stack || []).join(", "));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Error"));
  }, []);

  function set<K extends keyof CompanyProfile>(key: K, value: CompanyProfile[K]) {
    setP((s) => (s ? { ...s, [key]: value } : s));
    setSaved(false);
  }

  function setArea(i: number, key: keyof CompanyArea, value: string) {
    setP((s) => {
      if (!s) return s;
      const areas = [...s.areas];
      areas[i] = { ...areas[i], [key]: value };
      return { ...s, areas };
    });
    setSaved(false);
  }
  function addArea() {
    setP((s) => (s ? { ...s, areas: [...s.areas, { name: "", responsible: "", email: "" }] } : s));
  }
  function removeArea(i: number) {
    setP((s) => (s ? { ...s, areas: s.areas.filter((_, j) => j !== i) } : s));
  }

  async function save() {
    if (!p) return;
    setBusy(true);
    setError("");
    try {
      const tech_stack = tech.split(",").map((t) => t.trim()).filter(Boolean);
      const completed = !!(p.industry && p.description && p.audience);
      const wasComplete = p.required_complete;
      const updated = await api.saveCompanyProfile({ ...p, tech_stack, completed });
      setP(updated);
      setTech((updated.tech_stack || []).join(", "));
      setSaved(true);
      // Onboarding recién completado → abrir el Mapa de Procesos (el hub) para arrancar.
      if (updated.required_complete && !wasComplete) {
        setTimeout(() => router.push("/procesos?onboarding=1"), 700);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "No se pudo guardar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell>
      <PageHeader
        title="Configuración de empresa"
        subtitle="Configura tu empresa una vez y todos los casos de uso quedan preconfigurados e integrados."
      />
      <div className="mx-auto max-w-3xl p-8">
        {error && <div className="mb-4 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}
        {!p ? (
          <div className="text-sm text-slate-400">Cargando…</div>
        ) : (
          <div className="space-y-6">
            {/* Progress */}
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-50">
                  <Building2 className="h-5 w-5 text-violet-600" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div className="font-semibold text-slate-800">{p.company_name || "Tu empresa"}</div>
                    <div className="text-sm font-semibold text-violet-600">{p.completion}%</div>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-100">
                    <div className="h-full rounded-full bg-violet-600 transition-all" style={{ width: `${p.completion}%` }} />
                  </div>
                </div>
              </div>
              {!canEdit && (
                <p className="mt-3 text-xs text-amber-600">
                  Solo un Admin de Empresa puede editar esta configuración. Estás en modo lectura.
                </p>
              )}
            </div>

            {/* Identity / context */}
            <Section title="Identidad y contexto">
              <Field label="Giro / sector">
                <input className={inp} disabled={!canEdit} value={p.industry}
                  placeholder="Ej. Retail, fintech, manufactura, salud"
                  onChange={(e) => set("industry", e.target.value)} />
              </Field>
              <Field label="Tamaño de la empresa">
                <select className={inp} disabled={!canEdit} value={p.company_size}
                  onChange={(e) => set("company_size", e.target.value)}>
                  <option value="">Selecciona…</option>
                  {SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </Field>
              <Field label="Tipo de organización">
                <select className={inp} disabled={!canEdit} value={p.org_type || "privada"}
                  onChange={(e) => set("org_type", e.target.value)}>
                  <option value="privada">Iniciativa privada (IP)</option>
                  <option value="gobierno">Gobierno / sector público</option>
                </select>
              </Field>
              {(p.org_type || "privada") !== "gobierno" && (
                <Field label="¿Participan en licitaciones o trámites de gobierno?">
                  <label className="flex items-center gap-2 text-sm text-slate-600">
                    <input type="checkbox" disabled={!canEdit} checked={!!p.gov_tramites}
                      onChange={(e) => set("gov_tramites", e.target.checked)} />
                    Mostrar los casos y trámites de gobierno (p. ej. licitaciones)
                  </label>
                </Field>
              )}
              <Field label="¿A qué se dedica la empresa?">
                <textarea className={inp} rows={3} disabled={!canEdit} value={p.description}
                  placeholder="Describe el negocio en 2-3 líneas"
                  onChange={(e) => set("description", e.target.value)} />
              </Field>
              <Field label="Clientes / mercado objetivo">
                <input className={inp} disabled={!canEdit} value={p.audience}
                  placeholder="¿A quién le venden?"
                  onChange={(e) => set("audience", e.target.value)} />
              </Field>
              <Field label="Propuesta de valor / diferenciadores">
                <textarea className={inp} rows={2} disabled={!canEdit} value={p.value_prop}
                  placeholder="¿Por qué te eligen?"
                  onChange={(e) => set("value_prop", e.target.value)} />
              </Field>
              <Field label="Objetivos del negocio">
                <input className={inp} disabled={!canEdit} value={p.goals}
                  placeholder="Ej. crecer ventas 30%, abrir 2 sucursales"
                  onChange={(e) => set("goals", e.target.value)} />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Tono de comunicación">
                  <select className={inp} disabled={!canEdit} value={p.tone}
                    onChange={(e) => set("tone", e.target.value)}>
                    <option value="">Selecciona…</option>
                    {TONES.map((t) => <option key={t} value={t}>{t}</option>)}
                  </select>
                </Field>
                <Field label="Sitio web">
                  <input className={inp} disabled={!canEdit} value={p.website}
                    placeholder="https://…" onChange={(e) => set("website", e.target.value)} />
                </Field>
              </div>
            </Section>

            {/* Areas / org chart */}
            <Section title="Áreas y responsables (organigrama)">
              <p className="-mt-1 mb-2 text-xs text-slate-500">
                Estas áreas aparecerán al correr casos de uso, para asignar responsable.
              </p>
              <div className="space-y-2">
                {p.areas.map((a, i) => (
                  <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] items-center gap-2">
                    <input className={inp} disabled={!canEdit} placeholder="Área (ej. Ventas)" value={a.name}
                      onChange={(e) => setArea(i, "name", e.target.value)} />
                    <input className={inp} disabled={!canEdit} placeholder="Responsable" value={a.responsible}
                      onChange={(e) => setArea(i, "responsible", e.target.value)} />
                    <input className={inp} disabled={!canEdit} placeholder="Correo" value={a.email}
                      onChange={(e) => setArea(i, "email", e.target.value)} />
                    {canEdit && (
                      <button onClick={() => removeArea(i)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-100 hover:text-red-500">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
              {canEdit && (
                <button onClick={addArea} className="mt-2 flex items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-700">
                  <Plus className="h-4 w-4" /> Agregar área
                </button>
              )}
            </Section>

            {/* Tech stack */}
            <Section title="Tecnología que usan">
              <Field label="Herramientas y sistemas (separados por coma)">
                <input className={inp} disabled={!canEdit} value={tech}
                  placeholder="Ej. HubSpot, SAP, Excel, WhatsApp, Shopify"
                  onChange={(e) => { setTech(e.target.value); setSaved(false); }} />
              </Field>
            </Section>

            <SupportSenderCard canEdit={canEdit} />

            {canEdit && (
              <div className="flex items-center gap-3">
                <button onClick={save} disabled={busy}
                  className="flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
                  <Save className="h-4 w-4" /> {busy ? "Guardando…" : "Guardar configuración"}
                </button>
                {saved && (
                  <span className="flex items-center gap-1 text-sm text-emerald-600">
                    <CheckCircle2 className="h-4 w-4" /> Guardado
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Shell>
  );
}

const inp =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm disabled:bg-slate-50 disabled:text-slate-500";

function SupportSenderCard({ canEdit }: { canEdit: boolean }) {
  const [data, setData] = useState<Awaited<ReturnType<typeof api.supportSender>> | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => { api.supportSender().then(setData).catch(() => {}); }, []);

  async function save() {
    if (!data) return;
    setBusy(true); setSaved(false); setMsg("");
    try {
      await api.setSupportSender({ account_id: data.account_id, from_addr: data.from_addr, from_name: data.from_name });
      setSaved(true);
    } catch (e) { setMsg(e instanceof Error ? e.message : "No se pudo guardar"); }
    finally { setBusy(false); }
  }
  if (!data) return null;
  return (
    <Section title="Remitente de soporte (correo saliente)">
      <p className="text-sm text-slate-500">
        Elige el buzón desde el que tu empresa envía correos de soporte (automatizaciones y acciones).
        Si lo dejas vacío, se usa la cuenta de quien ejecuta.
      </p>
      <Field label="Buzón de soporte">
        <select className={inp} disabled={!canEdit} value={data.account_id}
          onChange={(e) => { setData({ ...data, account_id: e.target.value }); setSaved(false); }}>
          <option value="">— Usar la cuenta del usuario —</option>
          {data.connections.map((c) => (
            <option key={c.id} value={c.id}>{c.email || c.id} ({c.provider})</option>
          ))}
        </select>
      </Field>
      {!data.connections.length && (
        <p className="text-xs text-amber-600">
          No hay cuentas conectadas. Conecta el buzón de soporte en <b>Integraciones</b> y aquí podrás elegirlo.
        </p>
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Nombre para mostrar (opcional)">
          <input className={inp} disabled={!canEdit} value={data.from_name}
            placeholder="Soporte · Empresa"
            onChange={(e) => { setData({ ...data, from_name: e.target.value }); setSaved(false); }} />
        </Field>
        <Field label="Alias From (opcional, requiere send-as verificado)">
          <input className={inp} disabled={!canEdit} value={data.from_addr}
            placeholder="soporte@empresa.com"
            onChange={(e) => { setData({ ...data, from_addr: e.target.value }); setSaved(false); }} />
        </Field>
      </div>
      {canEdit && (
        <div className="flex items-center gap-3">
          <button onClick={save} disabled={busy}
            className="flex items-center gap-2 rounded-lg border border-violet-300 px-4 py-2 text-sm font-semibold text-violet-700 hover:bg-violet-50 disabled:opacity-50">
            <Save className="h-4 w-4" /> {busy ? "Guardando…" : "Guardar remitente"}
          </button>
          {saved && <span className="flex items-center gap-1 text-sm text-emerald-600"><CheckCircle2 className="h-4 w-4" /> Guardado</span>}
          {msg && <span className="text-sm text-red-600">{msg}</span>}
        </div>
      )}
    </Section>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5">
      <h2 className="mb-3 font-semibold text-slate-800">{title}</h2>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1 block text-sm font-medium text-slate-700">{label}</label>
      {children}
    </div>
  );
}
