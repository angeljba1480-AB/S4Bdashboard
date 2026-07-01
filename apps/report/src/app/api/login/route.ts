import { NextResponse } from "next/server";
import { COOKIE_NAME, SESSION_MAX_AGE, issueToken, passwordMatches } from "@/lib/auth";

export const runtime = "edge";

export async function POST(req: Request) {
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
    return NextResponse.json({ ok: false, error: "Contraseña incorrecta" }, { status: 401 });
  }

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
