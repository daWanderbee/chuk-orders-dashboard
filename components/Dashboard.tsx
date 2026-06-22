"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { palette, type ThemeMode } from "@/lib/theme";
import type { OrderRow } from "@/lib/types";
import { CHUK_LOGO } from "@/app/assets/logo";
import { KpiCard } from "./KpiCard";
import { OrdersSection } from "./OrdersSection";
import { Charts } from "./Charts";
import { InstallButton } from "./InstallButton";

const FAILED = new Set(["cancelled", "failed", "refunded"]);
const inr = (n: number) => "₹" + Math.round(n).toLocaleString("en-IN");
const DAY_OPTIONS = [7, 14, 30, 60, 90, 180, 365];

export function Dashboard() {
  const router = useRouter();
  const [mode, setMode] = useState<ThemeMode>("dark");
  const [days, setDays] = useState(30);
  const [hideTests, setHideTests] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [tab, setTab] = useState<"web" | "sample">("web");

  const [raw, setRaw] = useState<OrderRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lastRefresh, setLastRefresh] = useState<number>(Date.now());
  const reqId = useRef(0);

  const p = palette(mode);

  const load = useCallback(async (d: number) => {
    const id = ++reqId.current;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`/api/orders?days=${d}&_=${Date.now()}`, { cache: "no-store" });
      const json = await res.json();
      if (id !== reqId.current) return; // stale response
      if (!res.ok) {
        setError(json?.error || "The store API may have timed out.");
        setRaw([]);
      } else {
        setRaw(json.orders as OrderRow[]);
        setLastRefresh(Date.now());
      }
    } catch {
      if (id === reqId.current) {
        setError("Network error.");
        setRaw([]);
      }
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }, []);

  useEffect(() => { load(days); }, [days, load]);

  // auto-refresh every 3 min
  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(() => load(days), 180_000);
    return () => clearInterval(t);
  }, [autoRefresh, days, load]);

  // ── derive views ─────────────────────────────────────────────────────────
  const testN = useMemo(() => (raw ?? []).filter((o) => o.isTest).length, [raw]);
  const df = useMemo(
    () => (hideTests ? (raw ?? []).filter((o) => !o.isTest) : (raw ?? [])),
    [raw, hideTests],
  );
  const dfRev = useMemo(() => df.filter((o) => !FAILED.has(o.status)), [df]);

  const totalRev = dfRev.reduce((s, o) => s + o.total, 0);
  const processingN = df.filter((o) => o.statusGrp === "Processing").length;
  const failedN = df.filter((o) => o.statusGrp === "Failed/Cancelled").length;
  const websiteN = df.filter((o) => o.type === "Website Order").length;
  const sampleN = df.filter((o) => o.type === "Sample Kit").length;

  async function logout() {
    await fetch("/api/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  // ── splash on first load ───────────────────────────────────────────────────
  if (loading && raw === null) {
    return (
      <div className="splash">
        <img className="splash-logo" src={CHUK_LOGO} alt="CHUK" />
        <div className="splash-ring" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex" style={{ background: p.app_bg, color: p.text }}>
      {/* sidebar */}
      <aside
        className="hidden md:flex flex-col gap-5 w-64 shrink-0 p-5 sticky top-0 h-screen overflow-auto"
        style={{ background: p.sidebar_bg, borderRight: `1px solid ${p.card_border}` }}
      >
        <div>
          <h3 className="font-bold mb-2">Appearance</h3>
          <div className="flex gap-1.5">
            {(["Dark", "Light"] as const).map((m) => {
              const active = mode === m.toLowerCase();
              return (
                <button
                  key={m}
                  onClick={() => setMode(m.toLowerCase() as ThemeMode)}
                  className="rounded-full px-4 py-1.5 text-sm font-semibold"
                  style={{
                    background: active ? "#942A45" : p.tab_bg,
                    color: active ? "#fff" : p.tab_text,
                  }}
                >
                  {m}
                </button>
              );
            })}
          </div>
        </div>

        <hr style={{ borderColor: p.card_border }} />

        <div>
          <h3 className="font-bold mb-2">Filters</h3>
          <label className="text-sm" style={{ color: p.lbl }}>Date range</label>
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="w-full rounded-xl px-3 py-2 mt-1 outline-none"
            style={{ background: p.card_bg, color: p.text, border: `1px solid ${p.card_border}` }}
          >
            {DAY_OPTIONS.map((d) => (
              <option key={d} value={d}>Last {d} days</option>
            ))}
          </select>
        </div>

        <hr style={{ borderColor: p.card_border }} />

        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={hideTests} onChange={(e) => setHideTests(e.target.checked)} />
          Hide test orders (&lt;₹100 / “test”)
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
          Auto-refresh (3 min)
        </label>

        <button
          onClick={() => load(days)}
          className="rounded-full px-5 py-1.5 font-bold text-sm"
          style={{ background: p.btn_bg, color: p.btn_text }}
        >
          {loading ? "Refreshing…" : "Refresh now"}
        </button>
        <span className="text-xs" style={{ color: p.muted }}>
          Updated: {new Date(lastRefresh).toLocaleTimeString("en-GB")}
        </span>

        <div className="mt-auto flex flex-col gap-3">
          <InstallButton p={p} />
          <button onClick={logout} className="text-xs underline self-start" style={{ color: p.muted }}>
            Log out
          </button>
        </div>
      </aside>

      {/* main */}
      <main className="flex-1 min-w-0 px-4 md:px-8 py-8 max-w-[1240px] mx-auto w-full">
        {/* mobile controls */}
        <div className="md:hidden flex flex-wrap gap-2 items-center mb-5">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-xl px-3 py-2 outline-none text-sm"
            style={{ background: p.card_bg, color: p.text, border: `1px solid ${p.card_border}` }}
          >
            {DAY_OPTIONS.map((d) => <option key={d} value={d}>Last {d} days</option>)}
          </select>
          <button
            onClick={() => setMode(mode === "dark" ? "light" : "dark")}
            className="rounded-full px-4 py-1.5 text-sm font-semibold"
            style={{ background: p.tab_bg, color: p.tab_text }}
          >
            {mode === "dark" ? "☀ Light" : "🌙 Dark"}
          </button>
          <button
            onClick={() => load(days)}
            className="rounded-full px-4 py-1.5 text-sm font-bold"
            style={{ background: p.btn_bg, color: p.btn_text }}
          >
            ↻
          </button>
          <InstallButton p={p} />
        </div>

        {/* hero */}
        <div className="flex flex-col items-start pb-4 mb-3" style={{ borderBottom: `1px solid ${p.card_border}` }}>
          <img
            src={CHUK_LOGO}
            alt="CHUK"
            style={{
              height: 52, objectFit: "contain", marginBottom: ".6rem",
              background: p.logo_bg, padding: p.logo_pad, borderRadius: 10,
            }}
          />
          <div className="text-[1.1rem] font-bold">Orders Dashboard</div>
          <p className="text-sm mt-0.5" style={{ color: p.muted }}>
            chuk.in · last {days} days · <b style={{ color: p.val }}>{df.length} orders</b>
            {hideTests && testN ? ` · ${testN} test hidden` : ""}
          </p>
        </div>

        {error && (
          <div className="rounded-xl px-4 py-3 my-4 text-sm"
               style={{ background: p.card_bg, border: `1px solid ${p.card_border}`, color: "#F46C62" }}>
            No orders found — {error}{" "}
            <button onClick={() => load(days)} className="underline font-semibold">Retry</button>
          </div>
        )}

        {df.length > 0 && (
          <>
            {/* overall KPIs */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-5">
              <KpiCard p={p} value={df.length} label="Total Orders" />
              <KpiCard p={p} value={inr(totalRev)} label="Revenue (excl. failed)" />
              <KpiCard p={p} value={websiteN} label="Website Orders" />
              <KpiCard p={p} value={sampleN} label="Sample Kits" />
              <KpiCard p={p} value={processingN} label="Processing" />
              <KpiCard p={p} value={failedN} label="Failed/Cancelled" />
            </div>

            <hr className="my-7" style={{ borderColor: p.card_border }} />

            {/* orders */}
            <h2 className="text-xl font-bold mb-3">Orders</h2>
            <div className="flex gap-1.5 mb-4">
              {([["web", `Website Orders (${websiteN})`], ["sample", `Sample Kits (${sampleN})`]] as const).map(
                ([k, label]) => {
                  const active = tab === k;
                  return (
                    <button
                      key={k}
                      onClick={() => setTab(k)}
                      className="rounded-full px-5 py-1.5 text-sm font-semibold"
                      style={{
                        background: active ? "#942A45" : p.tab_bg,
                        color: active ? "#fff" : p.tab_text,
                      }}
                    >
                      {label}
                    </button>
                  );
                },
              )}
            </div>

            {tab === "web" ? (
              <OrdersSection p={p} keyName="web" onChanged={() => load(days)}
                             sectionDf={df.filter((o) => o.type === "Website Order")} />
            ) : (
              <OrdersSection p={p} keyName="sample" onChanged={() => load(days)}
                             sectionDf={df.filter((o) => o.type === "Sample Kit")} />
            )}

            <hr className="my-7" style={{ borderColor: p.card_border }} />

            {/* analytics */}
            <h2 className="text-xl font-bold mb-3">Analytics</h2>
            <Charts p={p} df={df} dfRev={dfRev} />
          </>
        )}
      </main>
    </div>
  );
}
