import { refreshExchangeRateAndPrices } from "@ultimahost/core";
import { createBot } from "./bot";

const token = process.env.BOT_TOKEN;
if (!token) {
  throw new Error("BOT_TOKEN is not set");
}

const PRICE_REFRESH_INTERVAL_MS = 6 * 60 * 60 * 1000;

function refreshPrices() {
  refreshExchangeRateAndPrices()
    .then(({ rate, updatedPlans }) => {
      console.log(`Курс EUR/RUB обновлён: ${rate.toFixed(2)}, тарифов пересчитано: ${updatedPlans}`);
    })
    .catch((err) => {
      console.error("Не удалось обновить курс/цены:", err);
    });
}

refreshPrices();
setInterval(refreshPrices, PRICE_REFRESH_INTERVAL_MS);

const bot = createBot(token);

bot.start({
  onStart: (info) => console.log(`UltimaHost bot started as @${info.username}`),
});
