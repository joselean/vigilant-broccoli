import type { Metadata } from "next";
import { prisma } from "@ultimahost/db";
import { Footer } from "../../components/Footer";
import { Header } from "../../components/Header";
import { PlanCard } from "../../components/PlanCard";

export const metadata: Metadata = {
  title: "Тарифы VDS — ULTIMA HOST",
};

export const revalidate = 60;

export default async function TariffsPage() {
  const plans = await prisma.plan.findMany({ where: { isActive: true }, orderBy: { sortOrder: "asc" } });

  return (
    <>
      <Header />
      <main className="mx-auto max-w-6xl px-6 py-16">
        <h1 className="text-3xl font-semibold">Тарифы VDS</h1>
        <p className="mt-2 text-white/60">
          Все серверы на базе Hetzner Cloud с NVMe-дисками и защитой от DDoS. Оформление заказа и оплата — в Telegram-боте.
        </p>
        <div className="mt-10 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {plans.map((plan, i) => (
            <PlanCard key={plan.id} plan={plan} featured={i === 1} />
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
