import { NextResponse } from "next/server";
import { setOrderStatus, setDispatchFrom } from "@/lib/woocommerce";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function PUT(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const wcId = parseInt(id, 10);
  if (!Number.isFinite(wcId)) {
    return NextResponse.json({ ok: false, error: "bad id" }, { status: 400 });
  }

  let body: { status?: unknown; dispatchFrom?: unknown } = {};
  try {
    body = await req.json();
  } catch {
    /* empty */
  }

  // status flip (✓ Done tick)
  if (body.status !== undefined) {
    const status = String(body.status);
    if (status !== "completed" && status !== "processing") {
      return NextResponse.json({ ok: false, error: "bad status" }, { status: 400 });
    }
    const ok = await setOrderStatus(wcId, status);
    return NextResponse.json({ ok }, { status: ok ? 200 : 502 });
  }

  // dispatch-from / ship-to text
  if (body.dispatchFrom !== undefined) {
    const ok = await setDispatchFrom(wcId, String(body.dispatchFrom));
    return NextResponse.json({ ok }, { status: ok ? 200 : 502 });
  }

  return NextResponse.json({ ok: false, error: "nothing to update" }, { status: 400 });
}
