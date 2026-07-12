import { config } from "../config";
import { cryptoBotPaymentProvider } from "./cryptobot";
import { manualPaymentProvider } from "./manual";
import type { PaymentProvider } from "./types";
import { yookassaPaymentProvider } from "./yookassa";

const providers: Record<string, PaymentProvider> = {
  manual: manualPaymentProvider,
  yookassa: yookassaPaymentProvider,
  cryptobot: cryptoBotPaymentProvider,
};

export function getPaymentProvider(): PaymentProvider {
  return providers[config.paymentProvider] ?? manualPaymentProvider;
}

export * from "./types";
