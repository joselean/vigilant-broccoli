import { confirmOrderPayment } from "@ultimahost/core";
import { NextRequest, NextResponse } from "next/server";

// Webhook endpoint for hosted payment providers (YooKassa, CryptoBot, ...).
// TODO: once real provider credentials are configured, verify the request
// signature per provider docs before trusting the payload. Until then this
// endpoint is inert — orders placed via the bot are confirmed manually by an
// admin (see apps/bot/src/handlers/admin.ts).
export async function POST(req: NextRequest) {
  const provider = req.nextUrl.searchParams.get("provider");
  const body = await req.json().catch(() => null);

  const orderId = Number(body?.metadata?.orderId ?? body?.payload ?? body?.orderId);
  if (!orderId || Number.isNaN(orderId)) {
    return NextResponse.json({ error: "missing orderId" }, { status: 400 });
  }

  try {
    await confirmOrderPayment(orderId);
    return NextResponse.json({ ok: true, provider, orderId });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
