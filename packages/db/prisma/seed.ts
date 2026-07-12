import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// Себестоимость — актуальная цена соответствующего server_type в Hetzner Cloud
// Console (см. console.hetzner.cloud/pricing) в EUR/мес. Сверьте перед запуском
// в продакшене и поправьте при изменении прайса Hetzner.
const plans = [
  {
    slug: "start",
    name: "Start",
    cpu: 2,
    ramGb: 4,
    diskGb: 40,
    costEur: 3.79,
    locationLabel: "Германия, Нюрнберг",
    hetznerServerType: "cx22",
    hetznerLocation: "nbg1",
    sortOrder: 1,
  },
  {
    slug: "optimal",
    name: "Optimal",
    cpu: 4,
    ramGb: 8,
    diskGb: 80,
    costEur: 6.30,
    locationLabel: "Германия, Нюрнберг",
    hetznerServerType: "cx32",
    hetznerLocation: "nbg1",
    sortOrder: 2,
  },
  {
    slug: "power",
    name: "Power",
    cpu: 8,
    ramGb: 16,
    diskGb: 160,
    costEur: 11.90,
    locationLabel: "Финляндия, Хельсинки",
    hetznerServerType: "cx42",
    hetznerLocation: "hel1",
    sortOrder: 3,
  },
  {
    slug: "ultra",
    name: "Ultra",
    cpu: 16,
    ramGb: 32,
    diskGb: 320,
    costEur: 22.90,
    locationLabel: "США, Эшберн",
    hetznerServerType: "cx52",
    hetznerLocation: "ash",
    sortOrder: 4,
  },
];

// Только для первого сидирования, пока не запущен price:refresh с живым курсом.
// Формула должна совпадать с packages/core/src/pricing.ts.
const FALLBACK_EUR_RUB_RATE = 100;
const EXCHANGE_MARKUP = 0.05;
const RESALE_MARKUP = 0.3;

function estimatePriceRub(costEur: number): number {
  const rate = FALLBACK_EUR_RUB_RATE * (1 + EXCHANGE_MARKUP);
  return Math.ceil((costEur * rate * (1 + RESALE_MARKUP)) / 10) * 10;
}

async function main() {
  for (const plan of plans) {
    const data = { ...plan, priceRub: estimatePriceRub(plan.costEur) };
    await prisma.plan.upsert({
      where: { slug: plan.slug },
      update: data,
      create: data,
    });
  }
  console.log(`Seeded ${plans.length} plans with estimated prices.`);
  console.log("Запустите `pnpm price:refresh`, чтобы подставить актуальный биржевой курс EUR/RUB.");
}

main()
  .catch((err) => {
    console.error(err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
