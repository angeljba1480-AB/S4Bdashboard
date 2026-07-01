/**
 * Auth del reporte público: gate por contraseña compartida, validada en el servidor
 * (Edge Middleware). La contraseña NUNCA llega al navegador; solo viaja una cookie
 * firmada con HMAC-SHA256 sobre un secreto de servidor. Usa Web Crypto para ser
 * compatible con el runtime Edge de Vercel (no `crypto` de Node).
 */

export const COOKIE_NAME = "report_auth";
const SESSION_TTL_SECONDS = 60 * 60 * 12; // 12 h

function b64url(bytes: Uint8Array): string {
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function b64urlToBytes(s: string): Uint8Array {
  const pad = s.length % 4 === 0 ? "" : "=".repeat(4 - (s.length % 4));
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/") + pad);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

function secret(): string {
  return process.env.REPORT_SECRET || process.env.REPORT_PASSWORD || "dev-insecure-secret";
}

async function hmac(message: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret()),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(message));
  return new Uint8Array(sig);
}

function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a[i] ^ b[i];
  return diff === 0;
}

/** Firma un token `exp.<sig>` para meterlo en la cookie httpOnly. */
export async function issueToken(): Promise<string> {
  const exp = Math.floor(Date.now() / 1000) + SESSION_TTL_SECONDS;
  const payload = String(exp);
  const sig = b64url(await hmac(payload));
  return `${payload}.${sig}`;
}

/** Verifica el token de la cookie (firma válida + no expirado). */
export async function verifyToken(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  const dot = token.indexOf(".");
  if (dot < 0) return false;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const exp = Number(payload);
  if (!Number.isFinite(exp) || exp * 1000 < Date.now()) return false;
  const expected = await hmac(payload);
  let given: Uint8Array;
  try {
    given = b64urlToBytes(sig);
  } catch {
    return false;
  }
  return timingSafeEqual(expected, given);
}

/** Compara la contraseña enviada con la configurada (constante en tiempo). */
export async function passwordMatches(input: string): Promise<boolean> {
  const expected = process.env.REPORT_PASSWORD || "";
  if (!expected) return false;
  // Comparación por HMAC para no filtrar longitud/contenido por tiempo.
  const a = await hmac(input);
  const b = await hmac(expected);
  return timingSafeEqual(a, b);
}

export const SESSION_MAX_AGE = SESSION_TTL_SECONDS;
