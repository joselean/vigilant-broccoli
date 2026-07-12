import { cancelOrder, config, createOrder } from "@ultimahost/core";
import type { PaymentMethodKind } from "@ultimahost/core";
import { InlineKeyboard } from "grammy";
import type { BotContext } from "../bot";
import { formatPrice } from "../format";

const PAYMENT_METHOD_LABELS: Record<PaymentMethodKind, string> = {
  card: "💳 Банковской картой",
  sbp: "📱 Через СБП",
  crypto: "🪙 Криптовалютой",
};

export async function handleChoosePaymentMethod(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const slug = ctx.match?.[1];
  if (!slug) return;

  const keyboard = new InlineKeyboard()
    .text(PAYMENT_METHOD_LABELS.card, `buy:${slug}:card`)
    .row()
    .text(PAYMENT_METHOD_LABELS.sbp, `buy:${slug}:sbp`)
    .row()
    .text(PAYMENT_METHOD_LABELS.crypto, `buy:${slug}:crypto`)
    .row()
    .text("« Назад", `plan:${slug}`);

  await ctx.reply("Выберите способ оплаты:", { reply_markup: keyboard });
}

export async function handleBuyPlan(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const slug = ctx.match?.[1];
  const method = ctx.match?.[2] as PaymentMethodKind | undefined;
  const from = ctx.from;
  if (!slug || !method || !from) return;

  await ctx.reply("⏳ Оформляем заказ...");

  try {
    const { order, plan, payment } = await createOrder({
      telegramId: BigInt(from.id),
      username: from.username ?? null,
      firstName: from.first_name ?? null,
      planSlug: slug,
      paymentMethod: method,
    });

    const lines = [
      `🧾 Заказ #${order.id} создан.`,
      `Тариф: <b>${plan.name}</b>`,
      `Способ оплаты: ${PAYMENT_METHOD_LABELS[method]}`,
      `Сумма: <b>${formatPrice(order.amountRub)}</b>`,
    ];

    const keyboard = new InlineKeyboard();

    if (payment.paymentUrl) {
      lines.push("", "Нажмите кнопку ниже, чтобы оплатить:");
      keyboard.url("💳 Оплатить", payment.paymentUrl);
    } else if (payment.instructions) {
      lines.push("", payment.instructions);
      keyboard.text("✅ Я оплатил", `paid:${order.id}`).row();
    }

    keyboard.text("❌ Отменить", `cancel:${order.id}`);

    await ctx.reply(lines.join("\n"), { parse_mode: "HTML", reply_markup: keyboard });
  } catch (err) {
    await ctx.reply(`Не удалось создать заказ: ${err instanceof Error ? err.message : err}`);
  }
}

export async function handleMarkPaid(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const orderId = ctx.match?.[1];
  const from = ctx.from;
  if (!orderId || !from) return;

  await ctx.reply("✅ Спасибо! Проверяем оплату — обычно это занимает до 15 минут. Мы пришлём данные сервера сюда.");

  if (config.adminChatId) {
    const keyboard = new InlineKeyboard()
      .text("✅ Подтвердить оплату", `admin_confirm:${orderId}`)
      .text("❌ Отклонить", `admin_reject:${orderId}`);

    await ctx.api.sendMessage(
      config.adminChatId,
      `Заказ #${orderId} — пользователь @${from.username ?? from.id} сообщил об оплате.`,
      { reply_markup: keyboard },
    );
  }
}

export async function handleCancelOrder(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const orderId = ctx.match?.[1];
  if (!orderId) return;

  await cancelOrder(Number(orderId), "Отменён пользователем");
  await ctx.reply(`Заказ #${orderId} отменён.`);
}
