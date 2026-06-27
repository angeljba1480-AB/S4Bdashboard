/** Convierte el markdown que devuelven los modelos en texto limpio para mostrar/narrar.
 *  Quita asteriscos (**negritas**, *itálicas*), almohadillas (#), backticks de código,
 *  y normaliza viñetas (-, *, +) a "• ". No depende de librerías. */
export function cleanMarkdown(input: string): string {
  if (!input) return input;
  let t = input;
  // Bloques de código ``` ``` y código en línea `code` → contenido sin backticks.
  t = t.replace(/```[a-zA-Z0-9]*\n?/g, "").replace(/```/g, "");
  t = t.replace(/`([^`]+)`/g, "$1");
  // Negritas/itálicas (negritas antes que itálicas).
  t = t.replace(/\*\*([^*]+)\*\*/g, "$1").replace(/__([^_]+)__/g, "$1");
  t = t.replace(/\*([^*]+)\*/g, "$1").replace(/(^|[\s(])_([^_]+)_/g, "$1$2");
  // Encabezados (#, ##, …) y citas (>).
  t = t.replace(/^\s{0,3}#{1,6}\s+/gm, "");
  t = t.replace(/^\s{0,3}>\s?/gm, "");
  // Viñetas -, *, + al inicio de línea → "• ".
  t = t.replace(/^\s*[-*+]\s+/gm, "• ");
  // Enlaces [texto](url) → texto (url).
  t = t.replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");
  // Separadores --- y líneas en blanco de más.
  t = t.replace(/^\s*([-*_]\s*){3,}$/gm, "");
  t = t.replace(/\n{3,}/g, "\n\n");
  return t.trim();
}
