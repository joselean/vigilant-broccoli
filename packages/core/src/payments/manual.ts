import { config } from "../config";
import type { PaymentProvider, PaymentRequest, PaymentResult } from "./types";

/**
 * No hosted checkout configured yet: shows the customer transfer instructions
 * and the order is confirmed manually by an admin (see admin handlers in the bot).
 */
export const manualPaymentProvider: PaymentProvider = {
  name: "manual",
  async createPayment(request: PaymentRequest): Promise<PaymentResult> {
    return {
      providerPaymentId: `manual-${request.orderId}`,
      paymentUrl: null,
      instructions: config.manualPaymentInstructions,
    };
  },
};
