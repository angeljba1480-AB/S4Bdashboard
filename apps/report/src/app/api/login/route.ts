import { NextResponse } from "next/server";
import { COOKIE_NAME, SESSION_MAX_AGE, issueToken, passwordMatches } from "@/lib/auth";
import { clientIp, isBlocked, resetAttempts, tooManyAttempts } from "@/lib/ratelimit";

export const runtime = "edge";

export async function POST(req: Request) {
  const now = Date.now();
  const ip = clientIp(req);

  // Anti-fuerza-bruta: si la IP ya excedió el límite, rechazar sin validar.
  const blocked = isBlocked(ip, now);
  if (blocked.limited) {
    return NextResponse.json(
      { ok: false, error: "Demasiados intentos. Espera unos minutos." },
      { status: 429, headers: { "Retry-After": String(blocked.retryAfter) } },
    );
  }

  let password = "";
  const ctype = req.headers.get("content-type") || "";
  try {
    if (ctype.includes("application/json")) {
      password = String((await req.json())?.password || "");
    } else {
      password = String((await req.formData()).get("password") || "");
    }
  } catch {
    password = "";
  }

  if (!(await passwordMatches(password))) {
    const rl = tooManyAttempts(ip, now);
    const status = rl.limited ? 429 : 401;
    const error = rl.limited ? "Demasiados intentos. Espera unos minutos." : "Contraseña incorrecta";
    const headers = rl.limited ? { "Retry-After": String(rl.retryAfter) } : undefined;
    return NextResponse.json({ ok: false, error }, { status, headers });
  }

  resetAttempts(ip); // login correcto: limpia el contador

  const token = await issueToken();
  const res = NextResponse.json({ ok: true });
  res.cookies.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
  });
  return res;
}
