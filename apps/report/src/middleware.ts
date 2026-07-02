import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";
import { COOKIE_NAME, verifyToken } from "@/lib/auth";

/**
 * Compuerta global: todo requiere sesión válida salvo /login y las rutas de API de
 * auth. La contraseña se valida server-side en /api/login; aquí solo se comprueba la
 * cookie firmada.
 */
export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const ok = await verifyToken(req.cookies.get(COOKIE_NAME)?.value);
  if (ok) {
    // Ya autenticado: no tiene caso ver /login.
    if (pathname === "/login") {
      return NextResponse.redirect(new URL("/", req.url));
    }
    return NextResponse.next();
  }
  if (pathname === "/login") return NextResponse.next();
  const url = new URL("/login", req.url);
  if (pathname !== "/") url.searchParams.set("next", pathname);
  return NextResponse.redirect(url);
}

export const config = {
  // Protege todo menos assets estáticos y las rutas de API de login/logout.
  matcher: ["/((?!api/login|api/logout|_next/static|_next/image|favicon.ico).*)"],
};
