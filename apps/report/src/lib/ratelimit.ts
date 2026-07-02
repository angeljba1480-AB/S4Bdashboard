/**
 * Rate-limit best-effort para el gate de contraseña (anti-fuerza-bruta).
 *
 * Ventana deslizante por IP en memoria del isolate. Limitación conocida: el runtime
 * Edge no comparte memoria entre isolates/regiones, así que esto frena ráfagas desde
 * una misma IP en un isolate caliente, no un ataque distribuido. Es una barrera
 * razonable para una contraseña compartida; para algo más fuerte, usar Vercel KV/
 * Upstash. Ver backlog.
 */
const WINDOW_MS = 5 * 60 * 1000; // 5 min
const MAX_ATTEMPTS = 10; // intentos por ventana por IP

type Bucket = { count: number; resetAt: number };
const buckets = new Map<string, Bucket>();

export function clientIp(req: Request): string {
  const xff = req.headers.get("x-forwarded-for") || "";
  return xff.split(",")[0].trim() || req.headers.get("x-real-ip") || "unknown";
}

/** Registra un intento fallido y devuelve si la IP quedó bloqueada + segundos restantes. */
export function tooManyAttempts(ip: string, now: number): { limited: boolean; retryAfter: number } {
  const b = buckets.get(ip);
  if (!b || now >= b.resetAt) {
    buckets.set(ip, { count: 1, resetAt: now + WINDOW_MS });
    return { limited: false, retryAfter: 0 };
  }
  b.count += 1;
  if (b.count > MAX_ATTEMPTS) {
    return { limited: true, retryAfter: Math.ceil((b.resetAt - now) / 1000) };
  }
  return { limited: false, retryAfter: 0 };
}

/** Login correcto: limpia el contador de esa IP. */
export function resetAttempts(ip: string): void {
  buckets.delete(ip);
}

/** Solo lectura: ¿la IP ya está bloqueada ahora mismo? (sin incrementar). */
export function isBlocked(ip: string, now: number): { limited: boolean; retryAfter: number } {
  const b = buckets.get(ip);
  if (b && now < b.resetAt && b.count > MAX_ATTEMPTS) {
    return { limited: true, retryAfter: Math.ceil((b.resetAt - now) / 1000) };
  }
  return { limited: false, retryAfter: 0 };
}
