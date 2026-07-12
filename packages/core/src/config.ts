export const config = {
  hetznerApiToken: process.env.HETZNER_API_TOKEN ?? "",
  hetznerSshKeyId: process.env.HETZNER_SSH_KEY_ID ?? "",
  yookassaShopId: process.env.YOOKASSA_SHOP_ID ?? "",
  yookassaSecretKey: process.env.YOOKASSA_SECRET_KEY ?? "",
  cryptoBotToken: process.env.CRYPTOBOT_TOKEN ?? "",
  plategaMerchantId: process.env.PLATEGA_MERCHANT_ID ?? "",
  plategaSecret: process.env.PLATEGA_SECRET ?? "",
  plategaBaseUrl: process.env.PLATEGA_BASE_URL ?? "https://api.platega.io",
  paymentReturnUrl: process.env.PAYMENT_RETURN_URL ?? "",
  adminChatId: process.env.ADMIN_CHAT_ID ?? "",
  manualPaymentInstructions:
    process.env.MANUAL_PAYMENT_INSTRUCTIONS ??
    "Переведите сумму заказа на карту 0000 0000 0000 0000 или на кошелёк USDT (TRC20): TXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX, затем нажмите «Я оплатил».",
} as const;

export function isHetznerConfigured(): boolean {
  return config.hetznerApiToken.length > 0;
}

export function isPlategaConfigured(): boolean {
  return config.plategaMerchantId.length > 0 && config.plategaSecret.length > 0;
}
