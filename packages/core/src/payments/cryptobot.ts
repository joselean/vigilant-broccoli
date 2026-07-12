import { config } from "../config";
import type { PaymentProvider, PaymentRequest, PaymentResult } from "./types";

/**
 * @CryptoBot (https://help.crypt.bot/crypto-pay-api) integration.
 * Requires CRYPTOBOT_TOKEN. Fill in webhook handling in apps/web/app/api/payments/webhook
 * once real credentials are available.
 */
export const cryptoBotPaymentProvider: PaymentProvider = {
  name: "cryptobot",
  async createPayment(request: PaymentRequest): Promise<PaymentResult> {
    if (!config.cryptoBotToken) {
      throw new Error("CryptoBot is not configured: set CRYPTOBOT_TOKEN");
    }

    const res = await fetch("https://pay.crypt.bot/api/createInvoice", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Crypto-Pay-API-Token": config.cryptoBotToken,
      },
      body: JSON.stringify({
        currency_type: "fiat",
        fiat: "RUB",
        amount: request.amountRub.toString(),
        description: request.description,
        payload: String(request.orderId),
      }),
    });

    if (!res.ok) {
      throw new Error(`CryptoBot error (${res.status}): ${await res.text()}`);
    }

    const data = (await res.json()) as {
      result: { invoice_id: number; pay_url: string };
    };
    return {
      providerPaymentId: String(data.result.invoice_id),
      paymentUrl: data.result.pay_url,
      instructions: null,
    };
  },
};
