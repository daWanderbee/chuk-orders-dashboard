import { NextResponse } from "next/server";
import { setOrderStatus } from "@/lib/woocommerce";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function PUT(req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const wcId = parseInt(id, 10);
  if (!Number.isFinite(wcId)) {
    return NextResponse.json({ ok: false, error: "bad id" }, { status: 400 });
  }
  let status = "";
  try {
    const body = await req.json();
    status = String(body?.status ?? "");
  } catch {
    /* empty */
  }
  if (status !== "completed" && status !== "processing") {
    return NextResponse.json({ ok: false, error: "bad status" }, { status: 400 });
  }
  const ok = await setOrderStatus(wcId, status);
  return NextResponse.json({ ok }, { status: ok ? 200 : 502 });
}
