import { listActivePlans } from "@ultimahost/core";
import { prisma } from "@ultimahost/db";
import { InlineKeyboard } from "grammy";
import type { BotContext } from "../bot";
import { formatPlanDetails, formatPlanSummary } from "../format";

export async function handleShowTariffs(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const plans = await listActivePlans();

  if (plans.length === 0) {
    await ctx.reply("Тарифы временно недоступны, загляните позже.");
    return;
  }

  const keyboard = new InlineKeyboard();
  for (const plan of plans) {
    keyboard.text(formatPlanSummary(plan), `plan:${plan.slug}`).row();
  }

  await ctx.reply("Выберите тариф:", { reply_markup: keyboard });
}

export async function handleShowPlanDetails(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const slug = ctx.match?.[1];
  if (!slug) return;

  const plan = await prisma.plan.findUnique({ where: { slug } });
  if (!plan) {
    await ctx.reply("Тариф не найден.");
    return;
  }

  const keyboard = new InlineKeyboard().text("✅ Заказать", `pay:${plan.slug}`);
  await ctx.reply(formatPlanDetails(plan), { parse_mode: "HTML", reply_markup: keyboard });
}
