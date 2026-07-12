import { refreshExchangeRateAndPrices } from "../pricing";

refreshExchangeRateAndPrices()
  .then(({ rate, updatedPlans }) => {
    console.log(`EUR/RUB: ${rate.toFixed(2)} (к этому курсу применяется наценка +5% и наценка ресейла +30%)`);
    console.log(`Обновлено тарифов: ${updatedPlans}`);
    process.exit(0);
  })
  .catch((err) => {
    console.error("Не удалось обновить курс и цены:", err);
    process.exit(1);
  });
