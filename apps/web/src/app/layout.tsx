import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Private AI Platform — México",
  description: "Private AI Gateway + Vertical Agents. AI empresarial sin perder control de tus datos.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
