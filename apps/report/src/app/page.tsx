import { loadBundle } from "@/lib/data";
import { Dashboard } from "@/components/Dashboard";

// El dataset se resuelve en el servidor (env var REPORT_DATA o demo). Nunca se expone
// la fuente ni credenciales al cliente; solo el JSON ya listo para graficar.
export const dynamic = "force-dynamic";

export default function Page() {
  const bundle = loadBundle();
  const globalDemo = !bundle.demoSections && bundle.overview?.CONS?.is_demo;
  return <Dashboard bundle={bundle} globalDemo={!!globalDemo} />;
}
