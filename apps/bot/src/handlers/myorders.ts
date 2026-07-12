import { listUserOrders } from "@ultimahost/core";
import type { BotContext } from "../bot";
import { formatPrice, orderStatusLabel } from "../format";

export async function handleMyOrders(ctx: BotContext) {
  await ctx.answerCallbackQuery();
  const from = ctx.from;
  if (!from) return;

  const orders = await listUserOrders(BigInt(from.id));

  if (orders.length === 0) {
    await ctx.reply("У вас пока нет заказов.");
    return;
  }

  const lines = orders.map((order) => {
    const base = `#${order.id} — ${order.plan.name} — ${formatPrice(order.amountRub)} — ${orderStatusLabel(order.status)}`;
    return order.server?.ipv4 ? `${base}\nIP: ${order.server.ipv4}` : base;
  });

  await ctx.reply(lines.join("\n\n"));
}
