"use client";

import { api } from "@/lib/api";
import { useEffect, useState } from "react";

/** Imagen servida por un endpoint protegido: descarga los bytes con el token
 * (un <img src> normal no manda Authorization) y los muestra como object URL. */
export function AuthImage({ id, alt, className }: { id: string; alt: string; className?: string }) {
  const [src, setSrc] = useState<string>("");
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let url = "";
    let alive = true;
    api.imageBlob(id)
      .then((u) => { if (alive) { url = u; setSrc(u); } else { URL.revokeObjectURL(u); } })
      .catch(() => alive && setFailed(true));
    return () => { alive = false; if (url) URL.revokeObjectURL(url); };
  }, [id]);

  if (failed) {
    return <div className={`flex items-center justify-center bg-slate-100 text-xs text-slate-400 ${className || ""}`}>No se pudo cargar</div>;
  }
  if (!src) {
    return <div className={`animate-pulse bg-slate-100 ${className || ""}`} />;
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} />;
}
