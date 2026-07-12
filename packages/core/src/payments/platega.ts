import { config, isPlategaConfigured } from "../config";
import type { PaymentMethodKind, PaymentProvider, PaymentRequest, PaymentResult } from "./types";

// Platega.io — платёжный агрегатор (карты, СБП, криптовалюта) с хостед-чекаутом.
// Собрано по https://docs.platega.io/ (создание платежа: POST /transaction/process,
// заголовки X-MerchantId/X-Secret) — при интеграции с боевым мерчантом сверьтесь
// с актуальной документацией в личном кабинете Platega, т.к. эндпоинты у таких
// агрегаторов иногда меняются.
const PAYMENT_METHOD_CODES: Record<PaymentMethodKind, number> = {
  sbp: 2, // SbpQr
  card: 10, // CardsRub
  crypto: 13, // Cryptocurrency
};

interface PlategaCreateTransactionResponse {
  transactionId: string;
  redirect: string;
  status: string;
  expiresIn?: string;
}

export function createPlategaProvider(method: PaymentMethodKind): PaymentProvider {
  return {
    name: `platega:${method}`,
    async createPayment(request: PaymentRequest): Promise<PaymentResult> {
      if (!isPlategaConfigured()) {
        throw new Error("Platega is not configured: set PLATEGA_MERCHANT_ID and PLATEGA_SECRET");
      }

      const res = await fetch(`${config.plategaBaseUrl}/transaction/process`, {
        method: "POST",
        headers: {
          "X-MerchantId": config.plategaMerchantId,
          "X-Secret": config.plategaSecret,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          paymentMethod: PAYMENT_METHOD_CODES[method],
          paymentDetails: { amount: request.amountRub, currency: "RUB" },
          description: request.description,
          // Платега ожидает поле "return" (не "returnUrl") для ссылки успеха.
          return: config.paymentReturnUrl || undefined,
          failedUrl: config.paymentReturnUrl || undefined,
          payload: String(request.orderId),
        }),
      });

      if (!res.ok) {
        throw new Error(`Platega error (${res.status}): ${await res.text()}`);
      }

      const data = (await res.json()) as PlategaCreateTransactionResponse;

      return {
        providerPaymentId: data.transactionId,
        paymentUrl: data.redirect,
        instructions: null,
      };
    },
  };
}
