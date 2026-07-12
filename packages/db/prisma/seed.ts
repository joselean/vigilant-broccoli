import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

const plans = [
  {
    slug: "start",
    name: "Start",
    cpu: 2,
    ramGb: 4,
    diskGb: 40,
    priceRub: 590,
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
    priceRub: 1190,
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
    priceRub: 2390,
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
    priceRub: 4590,
    locationLabel: "США, Эшберн",
    hetznerServerType: "cx52",
    hetznerLocation: "ash",
    sortOrder: 4,
  },
];

async function main() {
  for (const plan of plans) {
    await prisma.plan.upsert({
      where: { slug: plan.slug },
      update: plan,
      create: plan,
    });
  }
  console.log(`Seeded ${plans.length} plans`);
}

main()
  .catch((err) => {
    console.error(err);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
