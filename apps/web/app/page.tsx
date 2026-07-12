import { prisma } from "@ultimahost/db";
import { Features } from "../components/Features";
import { Footer } from "../components/Footer";
import { Header } from "../components/Header";
import { Hero } from "../components/Hero";
import { PlanCard } from "../components/PlanCard";

export const revalidate = 60;

async function getPlans() {
  return prisma.plan.findMany({ where: { isActive: true }, orderBy: { sortOrder: "asc" } });
}

export default async function HomePage() {
  const plans = await getPlans();

  return (
    <>
      <Header />
      <main>
        <Hero />
        <Features />

        <section id="tariffs" className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-2xl font-semibold md:text-3xl">Тарифы</h2>
          <p className="mt-2 text-white/60">VDS на базе Hetzner Cloud — оплата и выдача доступа через Telegram-бота.</p>
          <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {plans.map((plan, i) => (
              <PlanCard key={plan.id} plan={plan} featured={i === 1} />
            ))}
          </div>
        </section>

        <section id="faq" className="mx-auto max-w-6xl px-6 py-20">
          <h2 className="text-2xl font-semibold md:text-3xl">Частые вопросы</h2>
          <div className="mt-10 space-y-6">
            <div>
              <h3 className="font-medium">Как быстро создаётся сервер?</h3>
              <p className="mt-1 text-sm text-white/60">
                Сразу после подтверждения оплаты — сервер создаётся автоматически, данные для доступа приходят в Telegram.
              </p>
            </div>
            <div>
              <h3 className="font-medium">Как оплатить?</h3>
              <p className="mt-1 text-sm text-white/60">
                Выберите тариф в Telegram-боте — бот покажет доступные способы оплаты для выбранного тарифа.
              </p>
            </div>
            <div>
              <h3 className="font-medium">Можно сменить тариф позже?</h3>
              <p className="mt-1 text-sm text-white/60">Да, напишите в поддержку — поможем с миграцией на другой тариф.</p>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
