import type { Plan } from "@ultimahost/db";

const TELEGRAM_BOT_URL = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL || "https://t.me/ultimahost_bot";

export function PlanCard({ plan, featured = false }: { plan: Plan; featured?: boolean }) {
  return (
    <div
      className={`flex flex-col rounded-2xl border p-6 ${
        featured ? "border-white/40 bg-white/[0.04] shadow-glow" : "border-white/10 bg-white/[0.02]"
      }`}
    >
      <h3 className="text-lg font-semibold">{plan.name}</h3>
      <p className="mt-1 text-sm text-white/50">{plan.locationLabel}</p>

      <div className="mt-6 text-3xl font-semibold">
        {plan.priceRub.toLocaleString("ru-RU")} ₽
        <span className="text-base font-normal text-white/50">/мес</span>
      </div>

      <ul className="mt-6 flex-1 space-y-2 text-sm text-white/70">
        <li>⚙️ {plan.cpu} vCPU</li>
        <li>🧠 {plan.ramGb} GB RAM</li>
        <li>💾 {plan.diskGb} GB NVMe</li>
        <li>⚡ Автоматическое развёртывание</li>
      </ul>

      <a
        href={TELEGRAM_BOT_URL}
        target="_blank"
        rel="noreferrer"
        className={`mt-6 rounded-lg px-4 py-2.5 text-center text-sm font-medium transition ${
          featured
            ? "bg-white text-black hover:bg-white/90"
            : "border border-white/20 hover:border-white/50 hover:shadow-glow"
        }`}
      >
        Заказать в Telegram
      </a>
    </div>
  );
}
