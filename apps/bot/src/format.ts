import type { Plan } from "@ultimahost/db";

export function formatPrice(rub: number): string {
  return `${rub.toLocaleString("ru-RU")} ₽/мес`;
}

export function formatPlanSummary(plan: Plan): string {
  return `${plan.name} — ${plan.cpu} vCPU / ${plan.ramGb} GB RAM / ${plan.diskGb} GB NVMe — ${formatPrice(
    plan.priceRub,
  )}`;
}

export function formatPlanDetails(plan: Plan): string {
  return [
    `🖥 <b>${plan.name}</b>`,
    ``,
    `⚙️ CPU: ${plan.cpu} vCPU`,
    `🧠 RAM: ${plan.ramGb} GB`,
    `💾 Диск: ${plan.diskGb} GB NVMe`,
    `📍 Локация: ${plan.locationLabel}`,
    `💳 Цена: ${formatPrice(plan.priceRub)}`,
  ].join("\n");
}

export function orderStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    PENDING_PAYMENT: "⏳ Ожидает оплаты",
    PAID: "✅ Оплачен",
    PROVISIONING: "⚙️ Создаётся сервер",
    ACTIVE: "🟢 Активен",
    FAILED: "❌ Ошибка",
    CANCELLED: "🚫 Отменён",
  };
  return labels[status] ?? status;
}
