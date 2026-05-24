"use server";

/**
 * Server actions for the Mariana review surface.
 *
 *   triggerExtraction(dealId)   - calls extractDeal + persistExtraction
 *   confirmExtraction(dealId)   - marks marianaConfirmedAt
 *   resetReview(dealId)         - clears BOTH mariana + agent confirmations
 *                                  (Mariana editing invalidates agent's signoff)
 *   updateEmailText(dealId, text) - update optional agent email paste
 *
 * Note on auth: this is Mariana's own data and not multi-tenant in the
 * current product, so we don't gate by user. dealId/showId come from the
 * client; Drizzle parameter binding handles injection. In a multi-venue
 * future we'd derive showId from dealId on the server rather than trusting
 * the pair from the client.
 */

import { revalidatePath } from "next/cache";
import { headers } from "next/headers";
import { and, eq, isNull } from "drizzle-orm";
import { db } from "@/db";
import {
  deals,
  dealAgentResponses,
  dealConfirmationTokens,
} from "@/db/schema";
import { parseBonuses } from "@/lib/dealMath";
import {
  extractDeal,
  persistExtraction,
  ExtractionError,
} from "@/lib/extraction";
import { mintToken, findActiveTokenForDeal } from "@/lib/dealTokens";

export type ActionResult =
  | { ok: true }
  | { ok: false; error: string };

export async function triggerExtraction(
  dealId: string,
  showId: string,
): Promise<ActionResult> {
  const [deal] = await db
    .select()
    .from(deals)
    .where(eq(deals.id, dealId))
    .limit(1);

  if (!deal) {
    return { ok: false, error: "Deal not found" };
  }

  try {
    // parseBonuses (from lib/dealMath) gracefully returns [] on malformed
    // JSON; using it instead of raw JSON.parse mirrors lib/queries.ts and
    // avoids a SyntaxError throw on the ~half of deals with inconsistent
    // bonuses_json (per db/schema.ts:97-99).
    const result = await extractDeal({
      emailText: deal.agentEmailText,
      notesText: deal.dealNotesFreetext ?? "",
      structuredFieldsContext: {
        deal_type: deal.dealType,
        guarantee_amount: deal.guaranteeAmount,
        percentage: deal.percentage,
        percentage_basis: deal.percentageBasis,
        expense_cap: deal.expenseCap,
        hospitality_cap: deal.hospitalityCap,
        bonuses_json: parseBonuses(deal),
      },
    });
    await persistExtraction(dealId, result);
    revalidatePath(`/shows/${showId}/deal`);
    return { ok: true };
  } catch (err) {
    if (err instanceof ExtractionError) {
      // Log full error server-side; return a short tag to the client.
      console.error("[extraction] failed", {
        reason: err.reason,
        model: err.model,
        cause: err.cause,
      });
      return {
        ok: false,
        error: `${err.reason}: ${err.message}`,
      };
    }
    console.error("[extraction] unknown error", err);
    return { ok: false, error: String(err).slice(0, 200) };
  }
}

export async function confirmExtraction(
  dealId: string,
  showId: string,
): Promise<ActionResult> {
  await db
    .update(deals)
    .set({ marianaConfirmedAt: new Date() })
    .where(eq(deals.id, dealId));
  revalidatePath(`/shows/${showId}/deal`);
  return { ok: true };
}

/**
 * Reset the entire review loop for a deal. Mariana clicks this when she
 * wants to revise the extraction — any prior agent feedback is about an
 * older state of the deal and shouldn't carry forward.
 *
 * Atomic clear of all three sources of prior-review state:
 *   1. `dealAgentResponses` rows — old per-item confirmations/flags
 *      would otherwise show up on the next agent's view AND on
 *      Mariana's AgentResponseSection, even though they're stale.
 *   2. Active `dealConfirmationTokens` — any link Mariana previously
 *      shared still works otherwise, and the agent would land on a
 *      page pre-rendered with their old responses. Revoking forces a
 *      fresh link share after Mariana re-confirms.
 *   3. `marianaConfirmedAt` + `agentConfirmedAt` timestamps — the
 *      whole HITL state machine resets.
 *
 * This is the "I'm starting this loop over" gesture.
 */
export async function resetReview(
  dealId: string,
  showId: string,
): Promise<ActionResult> {
  const now = new Date();
  // Delete per-item responses for THIS deal only.
  await db.delete(dealAgentResponses).where(eq(dealAgentResponses.dealId, dealId));
  // Revoke any currently-active tokens — sets revokedAt, doesn't delete.
  // The token URL becomes invalid; resolveToken returns reason='revoked'.
  await db
    .update(dealConfirmationTokens)
    .set({ revokedAt: now })
    .where(
      and(
        eq(dealConfirmationTokens.dealId, dealId),
        isNull(dealConfirmationTokens.revokedAt),
      ),
    );
  // Clear both confirmation timestamps.
  await db
    .update(deals)
    .set({ marianaConfirmedAt: null, agentConfirmedAt: null })
    .where(eq(deals.id, dealId));
  revalidatePath(`/shows/${showId}/deal`);
  return { ok: true };
}

/**
 * Get-or-mint the shareable agent confirmation link. Idempotent: returns
 * the active token if one exists, mints a fresh one otherwise. Returns
 * the absolute URL so the caller can copy-to-clipboard.
 */
export async function getAgentLink(
  dealId: string,
): Promise<
  { ok: true; url: string; minted: boolean } | { ok: false; error: string }
> {
  try {
    const existing = await findActiveTokenForDeal(dealId);
    const token = existing?.token ?? (await mintToken(dealId));
    // Derive base URL from the current request — works locally and in
    // deployed previews. Falls back to APP_BASE_URL env if headers
    // aren't available (e.g., direct server invocation).
    const h = await headers();
    const host = h.get("x-forwarded-host") ?? h.get("host");
    const proto = h.get("x-forwarded-proto") ?? "http";
    const base = host
      ? `${proto}://${host}`
      : process.env.APP_BASE_URL ?? "http://localhost:3000";
    return { ok: true, url: `${base}/deal/${token}`, minted: !existing };
  } catch (err) {
    return { ok: false, error: String(err).slice(0, 200) };
  }
}

export async function updateEmailText(
  dealId: string,
  showId: string,
  emailText: string,
): Promise<ActionResult> {
  await db
    .update(deals)
    .set({
      agentEmailText: emailText.trim() || null,
      agentEmailReceivedAt: emailText.trim() ? new Date() : null,
      // Email change clears extraction + confirmations so they re-validate
      extractedDealJson: null,
      marianaConfirmedAt: null,
      agentConfirmedAt: null,
    })
    .where(eq(deals.id, dealId));
  revalidatePath(`/shows/${showId}/deal`);
  return { ok: true };
}
