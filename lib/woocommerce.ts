// Server-only WooCommerce client. Ports fetch_orders() / set_order_status()
// from chuk_orders_dashboard.py. Credentials come from env vars and never
// reach the browser.
import "server-only";
import type { OrderRow, StatusGroup } from "@/lib/types";

const WC_BASE = "https://chuk.in/wp-json/wc/v3";

const WC_FIELDS = [
  "id", "number", "status", "date_created",
  "billing", "shipping", "line_items",
  "total", "total_tax", "shipping_total",
  "payment_method_title", "meta_data",
].join(",");

// Custom order meta holding the free-text dispatch-from / ship-to note.
export const DISPATCH_META_KEY = "_chuk_dispatch_from";

export const STATE_MAP: Record<string, string> = {
  AP: "Andhra Pradesh", AR: "Arunachal Pradesh", AS: "Assam", BR: "Bihar",
  CT: "Chhattisgarh", GA: "Goa", GJ: "Gujarat", HR: "Haryana", HP: "Himachal Pradesh",
  JH: "Jharkhand", KA: "Karnataka", KL: "Kerala", MP: "Madhya Pradesh", MH: "Maharashtra",
  MN: "Manipur", ML: "Meghalaya", MZ: "Mizoram", NL: "Nagaland", OD: "Odisha",
  PB: "Punjab", RJ: "Rajasthan", SK: "Sikkim", TN: "Tamil Nadu", TS: "Telangana",
  TR: "Tripura", UP: "Uttar Pradesh", UK: "Uttarakhand", WB: "West Bengal",
  AN: "Andaman & Nicobar", CH: "Chandigarh", DN: "Dadra & Nagar Haveli", DD: "Daman & Diu",
  DL: "Delhi", JK: "Jammu & Kashmir", LA: "Ladakh", LD: "Lakshadweep", PY: "Puducherry",
};

const PROCESSING_STATUSES = new Set(["pending", "processing", "on-hold"]);
const FAILED_STATUSES = new Set(["cancelled", "failed", "refunded"]);
export const FAILED_STATUS_LIST = ["cancelled", "failed", "refunded"];

const TEST_MIN_TOTAL = 100.0; // orders below this (₹) treated as test orders

export function statusGroup(s: string): StatusGroup {
  if (PROCESSING_STATUSES.has(s)) return "Processing";
  if (FAILED_STATUSES.has(s)) return "Failed/Cancelled";
  if (s === "completed") return "Completed";
  return "Other";
}

type WcLineItem = { name: string; quantity: number };
type WcBilling = {
  first_name?: string; last_name?: string; email?: string;
  phone?: string; city?: string; state?: string;
};
type WcMeta = { id?: number; key: string; value: unknown };
type WcOrder = {
  id: number; number: string | number; status: string; date_created: string;
  billing: WcBilling; shipping?: WcBilling; line_items?: WcLineItem[];
  total?: string | number; payment_method_title?: string;
  meta_data?: WcMeta[];
};

function authHeader(): string {
  const user = process.env.WC_USER;
  const key = process.env.WC_APP_KEY;
  if (!user || !key) {
    throw new Error("WC_USER / WC_APP_KEY env vars not set");
  }
  return "Basic " + Buffer.from(`${user}:${key}`).toString("base64");
}

const TIMEOUT_MS = 45000;

async function getJson(url: string, signal: AbortSignal): Promise<{ data: WcOrder[]; totalPages: number }> {
  const r = await fetch(url, {
    headers: { Authorization: authHeader(), "Cache-Control": "no-cache" },
    signal,
    cache: "no-store",
  });
  if (!r.ok) throw new Error(`WC API ${r.status}`);
  const data = (await r.json()) as WcOrder[];
  const totalPages = parseInt(r.headers.get("X-WP-TotalPages") || "1", 10);
  return { data, totalPages };
}

export async function fetchOrders(daysBack: number): Promise<OrderRow[]> {
  const after = new Date(Date.now() - daysBack * 86400_000)
    .toISOString().slice(0, 10) + "T00:00:00";

  const all: WcOrder[] = [];
  for (let page = 1; page <= 20; page++) {
    // _cb busts chuk.in's LiteSpeed server-side REST cache so new/updated
    // orders show up; dropped on the final retry to accept a stale copy.
    const params = new URLSearchParams({
      per_page: "50", orderby: "date", order: "desc",
      after, _fields: WC_FIELDS, _cb: String(Date.now()), page: String(page),
    });
    const url = `${WC_BASE}/orders?${params.toString()}`;

    let batch: WcOrder[] | null = null;
    let totalPages = 1;
    for (let attempt = 0; attempt < 3; attempt++) {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
      try {
        const res = await getJson(url, ctrl.signal);
        batch = res.data;
        totalPages = res.totalPages;
        break;
      } catch (e) {
        if (attempt === 2) throw e;
        await new Promise((r) => setTimeout(r, 1000 * (attempt + 1)));
      } finally {
        clearTimeout(t);
      }
    }
    if (!batch || batch.length === 0) break;
    all.push(...batch);
    if (page >= totalPages || batch.length < 50) break;
  }

  return all.map(toRow);
}

function toRow(o: WcOrder): OrderRow {
  const items = o.line_items ?? [];
  const isSample = items.length > 0 && items.every((i) => i.name.toLowerCase().includes("sample kit"));
  const products = items.map((i) => `${i.name} ×${i.quantity}`).join("; ");
  const b = o.billing ?? {};
  const customer = `${b.first_name ?? ""} ${b.last_name ?? ""}`.trim();
  const email = b.email ?? "";
  const total = Number(o.total ?? 0) || 0;
  const blob = `${customer} ${email} ${products}`.toLowerCase();
  const isTest = total < TEST_MIN_TOTAL || blob.includes("test");
  const stateCode = b.state ?? "";
  const city = (b.city ?? "").replace(/\w\S*/g, (w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase());
  const dispatchMeta = (o.meta_data ?? []).find((m) => m.key === DISPATCH_META_KEY);
  const dispatchFrom = dispatchMeta?.value == null ? "" : String(dispatchMeta.value);

  return {
    order: "#" + String(o.number),
    date: o.date_created,
    status: o.status,
    statusGrp: statusGroup(o.status),
    type: isSample ? "Sample Kit" : "Website Order",
    isTest,
    customer,
    email,
    phone: b.phone ?? "",
    city,
    state: STATE_MAP[stateCode] ?? stateCode,
    stateCode,
    products,
    total,
    payment: o.payment_method_title ?? "",
    wcId: o.id,
    dispatchFrom,
  };
}

async function putOrder(wcId: number, body: Record<string, unknown>): Promise<boolean> {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(`${WC_BASE}/orders/${wcId}`, {
      method: "PUT",
      headers: { Authorization: authHeader(), "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal: ctrl.signal,
      cache: "no-store",
    });
    return r.status === 200;
  } catch {
    return false;
  } finally {
    clearTimeout(t);
  }
}

export function setOrderStatus(wcId: number, status: string): Promise<boolean> {
  return putOrder(wcId, { status });
}

export function setDispatchFrom(wcId: number, text: string): Promise<boolean> {
  return putOrder(wcId, { meta_data: [{ key: DISPATCH_META_KEY, value: text }] });
}
