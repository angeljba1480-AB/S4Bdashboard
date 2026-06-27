"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";

/** Imagen servida por un endpoint protegido: descarga los bytes con el token
 * (un <img src> normal no manda Authorization) y los muestra como object URL.
 * Si no hay copia con token (o falla), cae al URL del proveedor (`fallbackUrl`). */
export function AuthImage({ id, alt, className, hasData = true, fallbackUrl = "" }:
  { id: string; alt: string; className?: string; hasData?: boolean; fallbackUrl?: string }) {
  const [src, setSrc] = useState<string>("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let url = "";
    let alive = true;
    if (!hasData) { setSrc(fallbackUrl); return; }
    api.imageBlob(id)
      .then((u) => { if (alive) { url = u; setSrc(u); } else { URL.revokeObjectURL(u); } })
      .catch(() => { if (alive) setSrc(fallbackUrl); });
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [id, hasData, fallbackUrl]);

  if (failed || (!src && !fallbackUrl)) {
    return <div className={`flex items-center justify-center bg-slate-100 text-xs text-slate-400 ${className || ""}`}>No se pudo cargar</div>;
  }
  if (!src) {
    return <div className={`animate-pulse bg-slate-100 ${className || ""}`} />;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} onError={() => setFailed(true)} />;
}
