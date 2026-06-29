"use client";

import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, PieChart, Pie, Cell, LabelList,
} from "recharts";
import type { Palette } from "@/lib/theme";
import { GROUP_COLOR } from "@/lib/theme";
import type { OrderRow } from "@/lib/types";

const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

function ChartCard({ p, title, height, children }: {
  p: Palette; title: string; height: number; children: React.ReactElement;
}) {
  return (
    <div
      className="rounded-[15px] p-3"
      style={{ background: p.card_bg, border: `1px solid ${p.card_border}` }}
    >
      <div className="text-sm font-bold mb-2" style={{ color: p.chart_title }}>
        {title}
      </div>
      <ResponsiveContainer width="100%" height={height}>
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export function Charts({ p, df, dfRev }: { p: Palette; df: OrderRow[]; dfRev: OrderRow[] }) {
  const tick = { fill: p.chart_font, fontSize: 11 };
  const grid = p.grid;

  // Orders per day, stacked by status group
  const dayMap = new Map<string, Record<string, number>>();
  for (const o of df) {
    const day = o.date.slice(0, 10);
    const row = dayMap.get(day) ?? {};
    row[o.statusGrp] = (row[o.statusGrp] ?? 0) + 1;
    dayMap.set(day, row);
  }
  const groups = ["Processing", "Completed", "Failed/Cancelled", "Other"];
  const daily = [...dayMap.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([day, counts]) => ({ day: day.slice(5), ...counts }));

  // Status group pie
  const grpCounts = new Map<string, number>();
  for (const o of df) grpCounts.set(o.statusGrp, (grpCounts.get(o.statusGrp) ?? 0) + 1);
  const pie = [...grpCounts.entries()].map(([name, value]) => ({ name, value }));

  // Revenue by type (processing + completed only)
  const typeMap = new Map<string, { revenue: number; orders: number }>();
  for (const o of dfRev) {
    const t = typeMap.get(o.type) ?? { revenue: 0, orders: 0 };
    t.revenue += o.total; t.orders += 1; typeMap.set(o.type, t);
  }
  const byType = [...typeMap.entries()].map(([type, v]) => ({ type, ...v }));
  const TYPE_COLOR: Record<string, string> = { "Sample Kit": "#33A8C3", "Website Order": "#F3B343" };

  // Top states by revenue (excl. failed)
  const stateMap = new Map<string, number>();
  for (const o of dfRev) stateMap.set(o.state, (stateMap.get(o.state) ?? 0) + o.total);
  const states = [...stateMap.entries()]
    .map(([state, total]) => ({ state, total }))
    .sort((a, b) => b.total - a.total)
    .slice(0, 12);

  // Top cities by order count
  const cityMap = new Map<string, number>();
  for (const o of df) cityMap.set(o.city, (cityMap.get(o.city) ?? 0) + 1);
  const cities = [...cityMap.entries()]
    .map(([city, orders]) => ({ city, orders }))
    .sort((a, b) => b.orders - a.orders)
    .slice(0, 10);

  // Payment methods
  const payMap = new Map<string, number>();
  for (const o of df) payMap.set(o.payment, (payMap.get(o.payment) ?? 0) + 1);
  const pays = [...payMap.entries()]
    .map(([payment, orders]) => ({ payment, orders }))
    .sort((a, b) => b.orders - a.orders);

  return (
    <div className="flex flex-col gap-4">
      <ChartCard p={p} title="Orders per Day" height={260}>
        <BarChart data={daily} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid stroke={grid} vertical={false} />
          <XAxis dataKey="day" tick={tick} axisLine={{ stroke: p.axis }} tickLine={false} />
          <YAxis tick={tick} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle(p)} />
          <Legend wrapperStyle={{ fontSize: 11, color: p.muted }} />
          {groups.map((g) => (
            <Bar key={g} dataKey={g} stackId="s" fill={GROUP_COLOR[g]} />
          ))}
        </BarChart>
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard p={p} title="Processing vs Failed/Cancelled" height={260}>
          <PieChart>
            <Pie data={pie} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85}
                 paddingAngle={2}>
              {pie.map((e) => (
                <Cell key={e.name} fill={GROUP_COLOR[e.name] ?? "#CDB096"} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle(p)} />
            <Legend wrapperStyle={{ fontSize: 10, color: p.muted }} />
          </PieChart>
        </ChartCard>

        <ChartCard p={p} title="Revenue by Type (₹, processing + completed)" height={260}>
          <BarChart data={byType} margin={{ top: 16, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="type" tick={tick} axisLine={{ stroke: p.axis }} tickLine={false} />
            <YAxis tick={tick} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle(p)} formatter={(v: number) => inr(v)} />
            <Bar dataKey="revenue" radius={[6, 6, 0, 0]}>
              {byType.map((e) => (
                <Cell key={e.type} fill={TYPE_COLOR[e.type] ?? "#F3B343"} />
              ))}
              <LabelList dataKey="orders" position="top" formatter={(v: number) => `${v} orders`}
                         style={{ fill: p.chart_font, fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ChartCard>
      </div>

      <ChartCard p={p} title="Top States by Revenue (₹, processing + completed)" height={320}>
        <BarChart data={states} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
          <CartesianGrid stroke={grid} horizontal={false} />
          <XAxis type="number" tick={tick} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="state" tick={tick} width={110} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={tooltipStyle(p)} formatter={(v: number) => inr(v)} />
          <Bar dataKey="total" fill="#F46C62" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ChartCard>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ChartCard p={p} title="Top Cities" height={300}>
          <BarChart data={cities} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
            <CartesianGrid stroke={grid} horizontal={false} />
            <XAxis type="number" tick={tick} axisLine={false} tickLine={false} />
            <YAxis type="category" dataKey="city" tick={tick} width={90} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle(p)} />
            <Bar dataKey="orders" fill="#33A8C3" radius={[0, 6, 6, 0]} />
          </BarChart>
        </ChartCard>

        <ChartCard p={p} title="Payment Method" height={300}>
          <BarChart data={pays} margin={{ top: 16, right: 8, left: -8, bottom: 0 }}>
            <CartesianGrid stroke={grid} vertical={false} />
            <XAxis dataKey="payment" tick={tick} axisLine={{ stroke: p.axis }} tickLine={false} />
            <YAxis tick={tick} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle(p)} />
            <Bar dataKey="orders" fill="#F3B343" radius={[6, 6, 0, 0]}>
              <LabelList dataKey="orders" position="top" style={{ fill: p.chart_font, fontSize: 11 }} />
            </Bar>
          </BarChart>
        </ChartCard>
      </div>
    </div>
  );
}

function tooltipStyle(p: Palette): React.CSSProperties {
  return {
    background: p.card_bg,
    border: `1px solid ${p.card_border}`,
    borderRadius: 10,
    color: p.text,
    fontSize: 12,
  };
}
