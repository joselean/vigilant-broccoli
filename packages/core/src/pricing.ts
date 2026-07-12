import { prisma } from "@ultimahost/db";

// Наценка ресейла поверх себестоимости Hetzner.
export const RESALE_MARKUP = 0.3;
// Наценка на биржевой курс валюты (закладываем в курс продажи, а не только в цену).
export const EXCHANGE_MARKUP = 0.05;

const EUR = "EUR";
const RUB = "RUB";

// Курс ЦБ РФ, публичное зеркало без ключа. Меняйте на другой источник
// (например, биржевой курс Мосбиржи) через EXCHANGE_RATE_SOURCE_URL при необходимости.
const EXCHANGE_RATE_SOURCE_URL =
  process.env.EXCHANGE_RATE_SOURCE_URL ?? "https://www.cbr-xml-daily.ru/daily_json.js";

interface CbrDailyResponse {
  Valute: Record<string, { Value: number; Nominal: number }>;
}

export async function fetchMarketEurRubRate(): Promise<number> {
  const res = await fetch(EXCHANGE_RATE_SOURCE_URL);
  if (!res.ok) {
    throw new Error(`Exchange rate source error (${res.status})`);
  }
  const data = (await res.json()) as CbrDailyResponse;
  const eur = data.Valute?.EUR;
  if (!eur) {
    throw new Error("EUR rate missing in exchange rate source response");
  }
  return eur.Value / eur.Nominal;
}

/** Курс, по которому реально считаем цены: биржевой курс + 5%. */
export function applyExchangeMarkup(marketRate: number): number {
  return marketRate * (1 + EXCHANGE_MARKUP);
}

/** Себестоимость Hetzner (EUR) -> цена продажи (RUB), округлённая вверх до 10 ₽. */
export function computeSellPriceRub(costEur: number, marketRate: number): number {
  const sellRate = applyExchangeMarkup(marketRate);
  const priceRub = costEur * sellRate * (1 + RESALE_MARKUP);
  return Math.ceil(priceRub / 10) * 10;
}

export async function getCachedEurRubRate(): Promise<number> {
  const cached = await prisma.exchangeRate.findUnique({
    where: { base_quote: { base: EUR, quote: RUB } },
  });
  if (cached) return cached.rate;
  return fetchMarketEurRubRate();
}

/** Обновляет курс валюты и пересчитывает priceRub всех тарифов. Дёргать по расписанию. */
export async function refreshExchangeRateAndPrices(): Promise<{ rate: number; updatedPlans: number }> {
  const rate = await fetchMarketEurRubRate();

  await prisma.exchangeRate.upsert({
    where: { base_quote: { base: EUR, quote: RUB } },
    update: { rate },
    create: { base: EUR, quote: RUB, rate },
  });

  const plans = await prisma.plan.findMany();
  for (const plan of plans) {
    const priceRub = computeSellPriceRub(plan.costEur, rate);
    if (priceRub !== plan.priceRub) {
      await prisma.plan.update({ where: { id: plan.id }, data: { priceRub } });
    }
  }

  return { rate, updatedPlans: plans.length };
}
