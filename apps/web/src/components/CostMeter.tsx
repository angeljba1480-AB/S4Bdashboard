import { Coins } from "lucide-react";

export function CostMeter({ tokens, cost }: { tokens: number; cost: number }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-slate-600">
      <Coins className="h-3 w-3 text-amber-500" />
      {tokens.toLocaleString()} tok · ${cost.toFixed(5)}
    </span>
  );
}
