import { NextResponse } from "next/server";
import { fetchOrders } from "@/lib/woocommerce";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
// Allow the WooCommerce pagination to run; Vercel Pro/Hobby cap applies.
export const maxDuration = 60;

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const daysBack = Math.min(365, Math.max(1, parseInt(searchParams.get("days") || "30", 10) || 30));
  try {
    const orders = await fetchOrders(daysBack);
    return NextResponse.json(
      { orders, fetchedAt: Date.now() },
      // Edge/CDN cache for 60s, matching the old @st.cache_data(ttl=60).
      { headers: { "Cache-Control": "s-maxage=60, stale-while-revalidate=30" } },
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json({ orders: [], error: msg }, { status: 502 });
  }
}
