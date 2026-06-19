import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

// Proxies the WooCommerce PDF-invoice plugin so the access key stays server-side.
// Set INVOICE_URL_TEMPLATE to the plugin's download URL with {id} where the
// order id goes, e.g.:
//   https://chuk.in/?page=wpo_wcpdf&action=generate_wpo_wcpdf&document_type=invoice&order_ids={id}&access_key=XXXX
// Re-fetched live on every request, so a download after editing the dispatch
// text regenerates with the new value (plugin reads current order meta).
export async function GET(_req: Request, ctx: { params: Promise<{ id: string }> }) {
  const { id } = await ctx.params;
  const wcId = parseInt(id, 10);
  if (!Number.isFinite(wcId)) {
    return NextResponse.json({ error: "bad id" }, { status: 400 });
  }

  const template = process.env.INVOICE_URL_TEMPLATE;
  if (!template) {
    return NextResponse.json(
      { error: "INVOICE_URL_TEMPLATE env var not set" },
      { status: 503 },
    );
  }

  const url = template.includes("{id}")
    ? template.replace(/\{id\}/g, String(wcId))
    : `${template}${template.includes("?") ? "&" : "?"}order_ids=${wcId}`;

  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), 50_000);
  try {
    const upstream = await fetch(url, { signal: ctrl.signal, cache: "no-store" });
    if (!upstream.ok) {
      return NextResponse.json(
        { error: `invoice source returned ${upstream.status}` },
        { status: 502 },
      );
    }
    const buf = await upstream.arrayBuffer();
    const ct = upstream.headers.get("content-type") || "application/pdf";
    return new NextResponse(buf, {
      status: 200,
      headers: {
        "Content-Type": ct,
        "Content-Disposition": `attachment; filename="chuk_invoice_${wcId}.pdf"`,
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json({ error: "invoice fetch failed" }, { status: 502 });
  } finally {
    clearTimeout(t);
  }
}
