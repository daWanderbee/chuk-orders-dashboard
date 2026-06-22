"use client";

import { useMemo, useState } from "react";
import type { Palette } from "@/lib/theme";
import { STATUS_COLOR } from "@/lib/theme";
import type { OrderRow, StatusGroup } from "@/lib/types";
import { KpiCard } from "./KpiCard";

const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "2-digit",
    hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

const GROUPS: ("All" | StatusGroup)[] = ["All", "Processing", "Completed", "Failed/Cancelled"];

export function OrdersSection({
  p, sectionDf, keyName, onChanged,
}: {
  p: Palette;
  sectionDf: OrderRow[];
  keyName: string;
  onChanged: () => void;
}) {
  const [grp, setGrp] = useState<"All" | StatusGroup>("All");
  const [search, setSearch] = useState("");
  const [stateSel, setStateSel] = useState("All");
  const [showContact, setShowContact] = useState(false);
  const [pending, setPending] = useState<Set<number>>(new Set());
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [savingMeta, setSavingMeta] = useState<Set<number>>(new Set());
  const [savedFlash, setSavedFlash] = useState<Set<number>>(new Set());
  const [invoicing, setInvoicing] = useState<Set<number>>(new Set());

  const view = useMemo(
    () => (grp === "All" ? sectionDf : sectionDf.filter((o) => o.statusGrp === grp)),
    [sectionDf, grp],
  );

  const stateOptions = useMemo(
    () => ["All", ...[...new Set(view.map((o) => o.state).filter(Boolean))].sort()],
    [view],
  );

  const disp = useMemo(() => {
    let d = view;
    if (search) {
      const q = search.toLowerCase();
      d = d.filter(
        (o) =>
          o.customer.toLowerCase().includes(q) ||
          o.city.toLowerCase().includes(q) ||
          o.products.toLowerCase().includes(q) ||
          o.order.toLowerCase().includes(q),
      );
    }
    if (stateSel !== "All") d = d.filter((o) => o.state === stateSel);
    return d;
  }, [view, search, stateSel]);

  const revenue = view.reduce((s, o) => s + o.total, 0);
  const avg = view.length ? revenue / view.length : 0;

  if (sectionDf.length === 0) {
    return (
      <div className="rounded-xl px-4 py-6 text-center" style={{ color: p.muted, background: p.card_bg }}>
        No orders in this group. 🍃
      </div>
    );
  }

  async function toggleDone(o: OrderRow, done: boolean) {
    setPending((s) => new Set(s).add(o.wcId));
    const status = done ? "completed" : "processing";
    const res = await fetch(`/api/orders/${o.wcId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    setPending((s) => {
      const n = new Set(s);
      n.delete(o.wcId);
      return n;
    });
    if (res.ok) {
      onChanged(); // refetch in parent
    } else {
      alert(`Failed to update order ${o.order}.`);
    }
  }

  function setDraft(wcId: number, val: string) {
    setDrafts((d) => ({ ...d, [wcId]: val }));
  }

  async function saveDispatch(o: OrderRow) {
    const text = drafts[o.wcId] ?? o.dispatchFrom;
    setSavingMeta((s) => new Set(s).add(o.wcId));
    const res = await fetch(`/api/orders/${o.wcId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dispatchFrom: text }),
    });
    setSavingMeta((s) => {
      const n = new Set(s); n.delete(o.wcId); return n;
    });
    if (res.ok) {
      setSavedFlash((s) => new Set(s).add(o.wcId));
      setTimeout(() => setSavedFlash((s) => {
        const n = new Set(s); n.delete(o.wcId); return n;
      }), 1800);
      // Refresh so the saved value is canonical and the invoice picks it up.
      onChanged();
    } else {
      alert(`Failed to save dispatch text for ${o.order}.`);
    }
  }

  async function downloadInvoice(o: OrderRow) {
    setInvoicing((s) => new Set(s).add(o.wcId));
    try {
      const res = await fetch(`/api/invoice/${o.wcId}`, { cache: "no-store" });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        alert(j.error || `Invoice download failed for ${o.order}.`);
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `chuk_invoice_${o.wcId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setInvoicing((s) => { const n = new Set(s); n.delete(o.wcId); return n; });
    }
  }

  function downloadCsv() {
    const cols = ["order", "date", "status", "type", "customer", "email", "phone",
      "city", "state", "products", "total", "payment", "dispatchFrom"] as const;
    const head = cols.join(",");
    const esc = (v: string) => `"${String(v).replace(/"/g, '""')}"`;
    const lines = view.map((o) => cols.map((c) => esc(String(o[c]))).join(","));
    const csv = [head, ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
    a.href = url;
    a.download = `chuk_${keyName}_${stamp}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const contactCols = showContact;
  const pillBase = "rounded-full px-4 py-1.5 text-sm font-semibold transition";

  return (
    <div className="flex flex-col gap-4">
      {/* group segmented filter */}
      <div className="flex flex-wrap gap-1.5">
        {GROUPS.map((g) => {
          const active = g === grp;
          return (
            <button
              key={g}
              onClick={() => setGrp(g)}
              className={pillBase}
              style={{
                background: active ? "#942A45" : p.tab_bg,
                color: active ? "#fff" : p.tab_text,
              }}
            >
              {g}
            </button>
          );
        })}
      </div>

      {/* mini KPIs */}
      <div className="grid grid-cols-3 gap-3">
        <KpiCard p={p} value={view.length} label="Orders" />
        <KpiCard p={p} value={inr(revenue)} label="Revenue" />
        <KpiCard p={p} value={inr(avg)} label="Avg Order" />
      </div>

      {/* filters */}
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search order / customer / city / product…"
        className="rounded-xl px-4 py-2 outline-none"
        style={{ background: p.card_bg, color: p.text, border: `1px solid ${p.card_border}` }}
      />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-center">
        <select
          value={stateSel}
          onChange={(e) => setStateSel(e.target.value)}
          className="rounded-xl px-3 py-2 outline-none"
          style={{ background: p.card_bg, color: p.text, border: `1px solid ${p.card_border}` }}
        >
          {stateOptions.map((s) => (
            <option key={s} value={s}>{s === "All" ? "All states" : s}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm" style={{ color: p.text }}>
          <input type="checkbox" checked={showContact} onChange={(e) => setShowContact(e.target.checked)} />
          Show email & phone
        </label>
      </div>

      {/* table */}
      <div
        className="tbl-scroll overflow-auto rounded-[15px]"
        style={{ border: `1px solid ${p.df_border}`, maxHeight: 460 }}
      >
        <table className="w-full text-sm border-collapse" style={{ color: p.table_text }}>
          <thead className="sticky top-0" style={{ background: p.tab_bg }}>
            <tr>
              {["✓ Done", "Order", "Date", "Status", "Customer",
                ...(contactCols ? ["Email", "Phone"] : []),
                "City", "State", "Products", "Total", "Payment",
                "Dispatch from", "Invoice"].map((h) => (
                <th key={h} className="text-left px-3 py-2 whitespace-nowrap font-semibold"
                    style={{ color: p.tab_text }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {disp.map((o) => (
              <tr key={o.wcId} style={{ borderTop: `1px solid ${p.df_border}` }}>
                <td className="px-3 py-2">
                  <input
                    type="checkbox"
                    checked={o.status === "completed"}
                    disabled={pending.has(o.wcId)}
                    onChange={(e) => toggleDone(o, e.target.checked)}
                    title="Tick = mark completed · untick = back to processing"
                  />
                </td>
                <td className="px-3 py-2 whitespace-nowrap font-medium">{o.order}</td>
                <td className="px-3 py-2 whitespace-nowrap">{fmtDate(o.date)}</td>
                <td className="px-3 py-2 whitespace-nowrap font-semibold"
                    style={{ color: STATUS_COLOR[o.status] ?? p.muted }}>
                  {o.status}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">{o.customer}</td>
                {contactCols && <td className="px-3 py-2 whitespace-nowrap">{o.email}</td>}
                {contactCols && <td className="px-3 py-2 whitespace-nowrap">{o.phone}</td>}
                <td className="px-3 py-2 whitespace-nowrap">{o.city}</td>
                <td className="px-3 py-2 whitespace-nowrap">{o.state}</td>
                <td className="px-3 py-2 max-w-[280px] truncate" title={o.products}>{o.products}</td>
                <td className="px-3 py-2 whitespace-nowrap">{inr(o.total)}</td>
                <td className="px-3 py-2 whitespace-nowrap">{o.payment}</td>
                <td className="px-3 py-2 align-top">
                  <div className="flex items-start gap-1.5">
                    <textarea
                      value={drafts[o.wcId] ?? o.dispatchFrom}
                      onChange={(e) => setDraft(o.wcId, e.target.value)}
                      onKeyDown={(e) => {
                        // Ctrl/Cmd+Enter saves; plain Enter inserts a newline
                        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                          e.preventDefault();
                          saveDispatch(o);
                        }
                      }}
                      rows={3}
                      placeholder={"Ship-to / dispatch address…\n(Ctrl+Enter to save)"}
                      className="rounded-md px-2 py-1 text-sm outline-none w-[220px] resize-y leading-snug"
                      style={{ background: p.app_bg, color: p.text, border: `1px solid ${p.df_border}` }}
                    />
                    {(() => {
                      const dirty = (drafts[o.wcId] ?? o.dispatchFrom) !== o.dispatchFrom;
                      const saving = savingMeta.has(o.wcId);
                      const saved = savedFlash.has(o.wcId);
                      return (
                        <button
                          onClick={() => saveDispatch(o)}
                          disabled={!dirty || saving}
                          className="rounded-md px-2 py-1 text-xs font-semibold disabled:opacity-40"
                          style={{ background: p.btn_bg, color: p.btn_text }}
                          title="Save dispatch address to the order (Ctrl+Enter)"
                        >
                          {saving ? "…" : saved ? "✓" : "Save"}
                        </button>
                      );
                    })()}
                  </div>
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <button
                    onClick={() => downloadInvoice(o)}
                    disabled={invoicing.has(o.wcId)}
                    className="rounded-full px-3 py-1 text-xs font-bold disabled:opacity-50"
                    style={{ background: p.tab_bg, color: p.tab_text, border: `1px solid ${p.df_border}` }}
                    title="Download the latest invoice PDF"
                  >
                    {invoicing.has(o.wcId) ? "…" : "Invoice ⬇"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="text-xs" style={{ color: p.muted }}>
          Showing {disp.length} of {view.length} orders · tick ✓ Done to complete an order
        </span>
        <button
          onClick={downloadCsv}
          className="rounded-full px-5 py-1.5 font-bold text-sm"
          style={{ background: p.btn_bg, color: p.btn_text }}
        >
          Download CSV
        </button>
      </div>
    </div>
  );
}
