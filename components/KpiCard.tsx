import type { Palette } from "@/lib/theme";

export function KpiCard({ p, value, label }: { p: Palette; value: React.ReactNode; label: string }) {
  return (
    <div
      className="rounded-[15px] px-5 py-4 text-left h-full"
      style={{ background: p.card_bg, border: `1px solid ${p.card_border}` }}
    >
      <div className="text-[0.8rem] font-medium" style={{ color: p.lbl }}>
        {label}
      </div>
      <div className="text-[1.9rem] font-bold leading-tight mt-0.5" style={{ color: p.val }}>
        {value}
      </div>
    </div>
  );
}
