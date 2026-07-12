import { config } from "../config";
import type { PaymentProvider, PaymentRequest, PaymentResult } from "./types";

/**
 * YooKassa (https://yookassa.ru) integration. Requires YOOKASSA_SHOP_ID and
 * YOOKASSA_SECRET_KEY. Fill in webhook handling in apps/web/app/api/payments/webhook
 * once real credentials are available.
 */
export const yookassaPaymentProvider: PaymentProvider = {
  name: "yookassa",
  async createPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!config.yookassaShopId || !config.yookassaSecretKey) {
      throw new Error("YooKassa is not configured: set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY");
    }

    const idempotenceKey = `order-${request.orderId}-${Date.now()}`;
    const res = await fetch("https://api.yookassa.ru/v3/payments", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotence-Key": idempotenceKey,
        Authorization: `Basic ${Buffer.from(
          `${config.yookassaShopId}:${config.yookassaSecretKey}`,
        ).toString("base64")}`,
      },
      body: JSON.stringify({
        amount: { value: request.amountRub.toFixed(2), currency: "RUB" },
        confirmation: { type: "redirect", return_url: process.env.PAYMENT_RETURN_URL ?? "" },
        capture: true,
        description: request.description,
        metadata: { orderId: request.orderId },
      }),
    });

    if (!res.ok) {
      throw new Error(`YooKassa error (${res.status}): ${await res.text()}`);
    }

    const data = (await res.json()) as { id: string; confirmation: { confirmation_url: string } };
    return {
      providerPaymentId: data.id,
      paymentUrl: data.confirmation.confirmation_url,
      instructions: null,
    };
  },
};
