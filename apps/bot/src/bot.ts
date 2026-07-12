import { Bot, Context } from "grammy";
import { handleAdminConfirm, handleAdminReject } from "./handlers/admin";
import { handleMyOrders } from "./handlers/myorders";
import { handleBuyPlan, handleCancelOrder, handleMarkPaid } from "./handlers/order";
import { handleShowTariffs, handleShowPlanDetails } from "./handlers/tariffs";
import { handleStart, handleSupport, mainMenuKeyboard } from "./handlers/start";

export type BotContext = Context;

export function createBot(token: string): Bot<BotContext> {
  const bot = new Bot<BotContext>(token);

  bot.command("start", handleStart);
  bot.command("menu", (ctx) => ctx.reply("Главное меню:", { reply_markup: mainMenuKeyboard() }));

  bot.callbackQuery("menu:tariffs", handleShowTariffs);
  bot.callbackQuery("menu:orders", handleMyOrders);
  bot.callbackQuery("menu:support", handleSupport);

  bot.callbackQuery(/^plan:(.+)$/, handleShowPlanDetails);
  bot.callbackQuery(/^buy:(.+)$/, handleBuyPlan);
  bot.callbackQuery(/^paid:(\d+)$/, handleMarkPaid);
  bot.callbackQuery(/^cancel:(\d+)$/, handleCancelOrder);
  bot.callbackQuery(/^admin_confirm:(\d+)$/, handleAdminConfirm);
  bot.callbackQuery(/^admin_reject:(\d+)$/, handleAdminReject);

  bot.catch((err) => {
    console.error("Bot error:", err.error);
  });

  return bot;
}
