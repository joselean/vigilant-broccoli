import { prisma } from "@ultimahost/db";
import { hetznerClient } from "./hetzner";
import { getPaymentProvider } from "./payments";

export interface CreateOrderInput {
  telegramId: bigint;
  username?: string | null;
  firstName?: string | null;
  planSlug: string;
}

export async function findOrCreateUser(input: {
  telegramId: bigint;
  username?: string | null;
  firstName?: string | null;
}) {
  return prisma.user.upsert({
    where: { telegramId: input.telegramId },
    update: { username: input.username ?? undefined, firstName: input.firstName ?? undefined },
    create: {
      telegramId: input.telegramId,
      username: input.username ?? null,
      firstName: input.firstName ?? null,
    },
  });
}

export async function listActivePlans() {
  return prisma.plan.findMany({ where: { isActive: true }, orderBy: { sortOrder: "asc" } });
}

export async function createOrder(input: CreateOrderInput) {
  const plan = await prisma.plan.findUnique({ where: { slug: input.planSlug } });
  if (!plan || !plan.isActive) {
    throw new Error(`Unknown or inactive plan: ${input.planSlug}`);
  }

  const user = await findOrCreateUser(input);

  const order = await prisma.order.create({
    data: {
      userId: user.id,
      planId: plan.id,
      amountRub: plan.priceRub,
      status: "PENDING_PAYMENT",
    },
  });

  const paymentProvider = getPaymentProvider();
  const payment = await paymentProvider.createPayment({
    orderId: order.id,
    amountRub: plan.priceRub,
    description: `UltimaHost — тариф ${plan.name} (заказ #${order.id})`,
  });

  const updatedOrder = await prisma.order.update({
    where: { id: order.id },
    data: {
      paymentProvider: paymentProvider.name,
      paymentId: payment.providerPaymentId,
    },
  });

  return { order: updatedOrder, plan, payment };
}

export async function listUserOrders(telegramId: bigint) {
  const user = await prisma.user.findUnique({ where: { telegramId } });
  if (!user) return [];
  return prisma.order.findMany({
    where: { userId: user.id },
    include: { plan: true, server: true },
    orderBy: { createdAt: "desc" },
  });
}

export async function getOrder(orderId: number) {
  return prisma.order.findUnique({
    where: { id: orderId },
    include: { plan: true, user: true, server: true },
  });
}

/** Marks an order as paid and kicks off Hetzner server provisioning. */
export async function confirmOrderPayment(orderId: number) {
  const order = await prisma.order.update({
    where: { id: orderId },
    data: { status: "PAID" },
    include: { plan: true, user: true },
  });

  return provisionServer(order.id);
}

export async function provisionServer(orderId: number) {
  const order = await prisma.order.update({
    where: { id: orderId },
    data: { status: "PROVISIONING" },
    include: { plan: true, user: true },
  });

  try {
    const result = await hetznerClient.createServer({
      name: `ultimahost-${order.id}`,
      serverType: order.plan.hetznerServerType,
      location: order.plan.hetznerLocation,
      image: order.plan.hetznerImage,
    });

    const server = await prisma.server.create({
      data: {
        orderId: order.id,
        hetznerServerId: result.hetznerServerId,
        ipv4: result.ipv4,
        ipv6: result.ipv6,
        rootPassword: result.rootPassword,
        status: "active",
      },
    });

    await prisma.order.update({ where: { id: order.id }, data: { status: "ACTIVE" } });

    return { order, server };
  } catch (err) {
    await prisma.order.update({
      where: { id: order.id },
      data: { status: "FAILED", failureReason: err instanceof Error ? err.message : String(err) },
    });
    throw err;
  }
}

export async function cancelOrder(orderId: number, reason: string) {
  return prisma.order.update({
    where: { id: orderId },
    data: { status: "CANCELLED", failureReason: reason },
  });
}
