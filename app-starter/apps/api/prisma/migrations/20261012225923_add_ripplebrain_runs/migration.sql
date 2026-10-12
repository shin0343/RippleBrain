-- CreateEnum
CREATE TYPE "RippleBrainRunKind" AS ENUM ('ANALYZE', 'APPROVE', 'REJECT');

-- CreateTable
CREATE TABLE "ripplebrain_runs" (
    "id" TEXT NOT NULL,
    "organization_id" TEXT NOT NULL,
    "actor_id" TEXT NOT NULL,
    "kind" "RippleBrainRunKind" NOT NULL,
    "analysis_id" TEXT,
    "summary" TEXT,
    "createdAt" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ripplebrain_runs_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "ripplebrain_runs_organization_id_idx" ON "ripplebrain_runs"("organization_id");

-- CreateIndex
CREATE INDEX "ripplebrain_runs_actor_id_idx" ON "ripplebrain_runs"("actor_id");

-- AddForeignKey
ALTER TABLE "ripplebrain_runs" ADD CONSTRAINT "ripplebrain_runs_organization_id_fkey" FOREIGN KEY ("organization_id") REFERENCES "organizations"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "ripplebrain_runs" ADD CONSTRAINT "ripplebrain_runs_actor_id_fkey" FOREIGN KEY ("actor_id") REFERENCES "users"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
