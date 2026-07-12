import { prisma } from "@ultimahost/db";
import { NextResponse } from "next/server";

export async function GET() {
  const plans = await prisma.plan.findMany({ where: { isActive: true }, orderBy: { sortOrder: "asc" } });
  return NextResponse.json(plans);
}
