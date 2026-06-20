import { NextResponse } from "next/server";
import { wpFetch } from "@/lib/wp-session";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

const WP_BASE = (process.env.WP_BASE || "https://chuk.in").replace(/\/$/, "");

// Builds the APIFW invoice URL. order_id is a urlencoded JSON array of ids,
// e.g. %5B12345%5D for order 12345 (confirmed from class-apifw-front-end.php:
// json_decode(stripslashes(urldecode($_GET['order_id'])))).
function invoiceUrl(wcId: number): string {
  const enc = encodeURIComponent(JSON.stringify([wcId]));
  return `${WP_BASE}/?apifw_document=true&order_id=${enc}&type=invoice&action=download`;
}

export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const wcId = parseInt(id, 10);
  if (!Number.isFinite(wcId)) {
    return NextResponse.json({ error: "bad id" }, { status: 400 });
  }

  // The APIFW endpoint requires a logged-in WP session (manage_woocommerce).
  // wpFetch logs in with WP_LOGIN_USER / WP_LOGIN_PASS and reuses the cookie.
  const result = await wpFetch(invoiceUrl(wcId));
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: result.status });
  }

  return new NextResponse(result.body, {
    status: 200,
    headers: {
      "Content-Type": result.contentType || "application/pdf",
      "Content-Disposition": `attachment; filename="chuk_invoice_${wcId}.pdf"`,
      "Cache-Control": "no-store",
    },
  });
}
