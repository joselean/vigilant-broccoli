import { cancelOrder, confirmOrderPayment, config } from "@ultimahost/core";
import { NextRequest, NextResponse } from "next/server";

// Platega присылает статус транзакции сюда после оплаты. Аутентификация —
// теми же заголовками X-MerchantId/X-Secret, что и в запросе на создание
// платежа. Сверьте формат payload с актуальной документацией Platega перед
// продакшеном — у платёжных агрегаторов это иногда меняется.
export async function POST(req: NextRequest) {
  const merchantId = req.headers.get("x-merchantid");
  const secret = req.headers.get("x-secret");

  if (!config.plategaMerchantId || merchantId !== config.plategaMerchantId || secret !== config.plategaSecret) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const body = await req.json().catch(() => null);
  const orderId = Number(body?.payload ?? body?.Payload);
  const status = String(body?.status ?? body?.Status ?? "").toUpperCase();

  if (!orderId || Number.isNaN(orderId)) {
    return NextResponse.json({ error: "missing payload/orderId" }, { status: 400 });
  }

  try {
    if (status === "CONFIRMED") {
      await confirmOrderPayment(orderId);
    } else if (status === "CANCELED" || status === "CANCELLED") {
      await cancelOrder(orderId, "Platega: платёж отменён/не прошёл");
    }
    return NextResponse.json({ ok: true });
  } catch (err) {
    return NextResponse.json({ error: err instanceof Error ? err.message : String(err) }, { status: 500 });
  }
}
