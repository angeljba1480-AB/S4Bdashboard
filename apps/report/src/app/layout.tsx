import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tablero Financiero · Silent4Business",
  description: "Reporte financiero (solo lectura) — acceso restringido.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen font-sans antialiased">{children}</body>
    </html>
  );
}
