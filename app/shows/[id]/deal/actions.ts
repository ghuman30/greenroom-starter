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
import { eq } from "drizzle-orm";
import { db } from "@/db";
import { deals } from "@/db/schema";
import { parseBonuses } from "@/lib/dealMath";
import {
  extractDeal,
  persistExtraction,
  ExtractionError,
} from "@/lib/extraction";

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
 * Reset BOTH Mariana's and the agent's confirmation. Used when Mariana
 * wants to re-review (any change she makes invalidates the agent's prior
 * signoff, since the agent confirmed a specific structured deal).
 */
export async function resetReview(
  dealId: string,
  showId: string,
): Promise<ActionResult> {
  await db
    .update(deals)
    .set({ marianaConfirmedAt: null, agentConfirmedAt: null })
    .where(eq(deals.id, dealId));
  revalidatePath(`/shows/${showId}/deal`);
  return { ok: true };
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
