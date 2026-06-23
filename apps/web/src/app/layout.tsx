import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MaestroAI — Agentes y casos para LATAM",
  description: "MaestroAI: agentes y casos de uso por país, con IA privada y control de tus datos.",
  manifest: "/manifest.webmanifest",
  applicationName: "MaestroAI",
  appleWebApp: { capable: true, statusBarStyle: "default", title: "MaestroAI" },
};

export const viewport = { themeColor: "#7c3aed" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
