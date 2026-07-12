import { cancelOrder, confirmOrderPayment, config, getOrder } from "@ultimahost/core";
import type { BotContext } from "../bot";

function isAdmin(ctx: BotContext): boolean {
  const chatId = ctx.chat?.id ?? ctx.from?.id;
  return Boolean(config.adminChatId) && String(chatId) === config.adminChatId;
}

export async function handleAdminConfirm(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  if (!isAdmin(ctx)) {
    await ctx.reply("⛔ Недостаточно прав.");
    return;
  }

  const orderId = ctx.match?.[1];
  if (!orderId) return;

  await ctx.reply(`⚙️ Подтверждаем заказ #${orderId} и создаём сервер...`);

  try {
    const { order, server } = await confirmOrderPayment(Number(orderId));

    await ctx.api.sendMessage(
      order.user.telegramId ? Number(order.user.telegramId) : order.userId,
      [
        `🎉 Ваш сервер готов!`,
        ``,
        `IP-адрес: <code>${server.ipv4 ?? "—"}</code>`,
        `Пользователь: <code>root</code>`,
        `Пароль: <code>${server.rootPassword ?? "уточните у поддержки"}</code>`,
      ].join("\n"),
      { parse_mode: "HTML" },
    );

    await ctx.reply(`✅ Заказ #${orderId} подтверждён, сервер создан и данные отправлены клиенту.`);
  } catch (err) {
    await ctx.reply(`❌ Ошибка при создании сервера: ${err instanceof Error ? err.message : err}`);
  }
}

export async function handleAdminReject(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  if (!isAdmin(ctx)) {
    await ctx.reply("⛔ Недостаточно прав.");
    return;
  }

  const orderId = ctx.match?.[1];
  if (!orderId) return;

  const order = await getOrder(Number(orderId));
  await cancelOrder(Number(orderId), "Оплата не подтверждена администратором");

  if (order?.user.telegramId) {
    await ctx.api.sendMessage(
      Number(order.user.telegramId),
      `❌ Оплата заказа #${orderId} не подтверждена. Свяжитесь с поддержкой, если вы уже оплатили.`,
    );
  }

  await ctx.reply(`Заказ #${orderId} отклонён.`);
}
