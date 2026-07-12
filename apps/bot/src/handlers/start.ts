import { InlineKeyboard } from "grammy";
import type { BotContext } from "../bot";

export function mainMenuKeyboard(): InlineKeyboard {
  return new InlineKeyboard()
    .text("🖥 Тарифы", "menu:tariffs")
    .row()
    .text("📦 Мои заказы", "menu:orders")
    .row()
    .text("💬 Поддержка", "menu:support");
}

const WELCOME_TEXT = [
  "👋 Добро пожаловать в <b>ULTIMA HOST</b>!",
  "",
  "Надёжные VDS-серверы на базе Hetzner Cloud:",
  "⚡ NVMe скорость",
  "🛡 Защита от DDoS",
  "🌐 Серверы по всему миру",
  "",
  "Выберите тариф — сервер будет создан автоматически сразу после оплаты.",
].join("\n");

export async function handleStart(ctx: BotContext) {
  await ctx.reply(WELCOME_TEXT, { parse_mode: "HTML", reply_markup: mainMenuKeyboard() });
}

export async function handleSupport(ctx: BotContext) {
  const supportUsername = process.env.SUPPORT_USERNAME ?? "ultimahost_support";
  await ctx.answerCallbackQuery();
  await ctx.reply(`По всем вопросам пишите: @${supportUsername}`);
}
