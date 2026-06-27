"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function GlobalSearch() {
  const router = useRouter();
  const [q, setQ] = useState("");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (q.trim().length < 2) return;
    router.push(`/search?q=${encodeURIComponent(q.trim())}`);
  }

  return (
    <form onSubmit={submit} className="fixed right-16 top-3 z-50 hidden sm:block">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar…"
          className="w-44 rounded-full border border-slate-200 bg-white py-1.5 pl-8 pr-3 text-sm shadow-sm focus:w-60 focus:outline-none focus:ring-2 focus:ring-violet-200" />
      </div>
    </form>
  );
}
