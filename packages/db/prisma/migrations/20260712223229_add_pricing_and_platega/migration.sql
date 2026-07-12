/*
  Warnings:

  - Added the required column `costEur` to the `Plan` table without a default value. This is not possible if the table is not empty.

*/
-- AlterTable
-- Default 0 only backfills existing rows so this migration is non-destructive;
-- re-run `pnpm db:seed` afterwards to set real costEur values.
ALTER TABLE "Plan" ADD COLUMN     "costEur" DOUBLE PRECISION NOT NULL DEFAULT 0;
ALTER TABLE "Plan" ALTER COLUMN "costEur" DROP DEFAULT;

-- CreateTable
CREATE TABLE "ExchangeRate" (
    "id" SERIAL NOT NULL,
    "base" TEXT NOT NULL,
    "quote" TEXT NOT NULL,
    "rate" DOUBLE PRECISION NOT NULL,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "ExchangeRate_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "ExchangeRate_base_quote_key" ON "ExchangeRate"("base", "quote");
