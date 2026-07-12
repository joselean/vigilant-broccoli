export type PaymentMethodKind = "card" | "sbp" | "crypto";

export interface PaymentRequest {
  orderId: number;
  amountRub: number;
  description: string;
}

export interface PaymentResult {
  providerPaymentId: string;
  /** URL to redirect the user to for hosted checkout, or null for manual/off-platform payment. */
  paymentUrl: string | null;
  /** Instructions to show the user when there is no hosted checkout (e.g. bank transfer, crypto wallet). */
  instructions: string | null;
}

export interface PaymentProvider {
  name: string;
  createPayment(request: PaymentRequest): Promise<PaymentResult>;
}
