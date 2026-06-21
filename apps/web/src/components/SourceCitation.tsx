import type { Citation } from "@shared/types";
import { FileText } from "lucide-react";
import { SensitivityBadge } from "./PrivacyBadge";

export function SourceCitation({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;
  return (
    <div className="mt-3 space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">
        Fuentes ({citations.length})
      </div>
      {citations.map((c, i) => (
        <div key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs">
          <div className="mb-1 flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1 font-medium text-slate-700">
              <FileText className="h-3 w-3" /> {c.filename} · #{c.chunk_index}
            </span>
            <span className="flex items-center gap-2">
              <SensitivityBadge level={c.sensitivity} />
              <span className="text-slate-400">score {c.score.toFixed(3)}</span>
            </span>
          </div>
          <p className="line-clamp-2 text-slate-500">{c.text}</p>
        </div>
      ))}
    </div>
  );
}
