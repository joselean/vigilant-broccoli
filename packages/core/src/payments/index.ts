import { config, isPlategaConfigured } from "../config";
import { cryptoBotPaymentProvider } from "./cryptobot";
import { manualPaymentProvider } from "./manual";
import { createPlategaProvider } from "./platega";
import type { PaymentMethodKind, PaymentProvider } from "./types";

/**
 * Platega — основной агрегатор для карт/СБП/крипты. Для крипты, если Platega
 * не настроена, используем CryptoBot как альтернативу. Если ничего не
 * настроено — оплата вручную по реквизитам с подтверждением админом.
 */
export function getPaymentProvider(method: PaymentMethodKind): PaymentProvider {
  if (isPlategaConfigured()) {
    return createPlategaProvider(method);
  }

  if (method === "crypto" && config.cryptoBotToken) {
    return cryptoBotPaymentProvider;
  }

  return manualPaymentProvider;
}

export * from "./types";
