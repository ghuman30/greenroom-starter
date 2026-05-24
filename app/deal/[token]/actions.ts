"use server";

/**
 * Server actions for the agent confirmation surface at /deal/[token].
 *
 *   recordResponse(token, fieldPath, action, details)
 *   confirmAll(token)
 *
 * Token is verified inside each action; if it's invalid we return a
 * typed error so the UI can show a clean message.
 *
 * Input validation:
 *   - fieldPath is whitelisted against FIELD_PATH_RE to prevent audit
 *     log poisoning from arbitrary client strings.
 *   - details payload is bounded (custom_reading / comment clamped to
 *     CUSTOM_TEXT_MAX before stringify).
 *   - id generation uses crypto.randomUUID() to avoid same-ms PK collisions.
 */

import { randomUUID } from "node:crypto";
import { revalidatePath } from "next/cache";
import { eq } from "drizzle-orm";
import { db } from "@/db";
import { deals, dealAgentResponses } from "@/db/schema";
import { resolveToken } from "@/lib/dealTokens";

export type AgentActionResult =
  | { ok: true }
  | { ok: false; error: string };

/**
 * Discriminated union of valid `details` payloads for recordResponse.
 * Anything else is rejected at the boundary.
 */
type ResponseDetails =
  | { reading_index: number }
  | { custom_reading: string }
  | { comment: string }
  | Record<string, never>; // empty object is allowed (e.g. plain confirm)

interface RecordResponseInput {
  token: string;
  fieldPath: string;
  action: "confirmed" | "flagged" | "reading_chosen";
  details?: ResponseDetails;
}

const FIELD_PATH_RE =
  /^(deal_kind|guarantee_amount|percentage|expense_cap|hospitality_cap|bonus_\d+|ratchet_\d+|walkout_\d+|recoup_\d+|ambiguity_\d+|discrepancy_\d+|all)$/;
const CUSTOM_TEXT_MAX = 2000;
const VALID_ACTIONS = new Set(["confirmed", "flagged", "reading_chosen"]);

function sanitizeDetails(details: ResponseDetails | undefined): string | null {
  if (!details) return null;
  const out: Record<string, unknown> = {};
  if ("reading_index" in details && typeof details.reading_index === "number") {
    out.reading_index = details.reading_index;
  }
  if ("custom_reading" in details && typeof details.custom_reading === "string") {
    out.custom_reading = details.custom_reading.slice(0, CUSTOM_TEXT_MAX);
  }
  if ("comment" in details && typeof details.comment === "string") {
    out.comment = details.comment.slice(0, CUSTOM_TEXT_MAX);
  }
  return Object.keys(out).length === 0 ? null : JSON.stringify(out);
}

export async function recordResponse(
  input: RecordResponseInput,
): Promise<AgentActionResult> {
  if (!FIELD_PATH_RE.test(input.fieldPath)) {
    return { ok: false, error: "invalid field" };
  }
  if (!VALID_ACTIONS.has(input.action)) {
    return { ok: false, error: "invalid action" };
  }

  const t = await resolveToken(input.token);
  if (!t.ok) return { ok: false, error: `Link is ${t.reason}` };

  await db.insert(dealAgentResponses).values({
    id: randomUUID(),
    dealId: t.token.dealId,
    tokenUsed: input.token,
    fieldPath: input.fieldPath,
    action: input.action,
    detailsJson: sanitizeDetails(input.details),
    respondedAt: new Date(),
  });

  revalidatePath(`/deal/${input.token}`);
  return { ok: true };
}

/**
 * Single "confirm everything" action. Records one `resp_*_all` row plus
 * sets deals.agentConfirmedAt. Short-circuits if already confirmed (so
 * accidental double-clicks don't pollute the audit log).
 */
export async function confirmAll(token: string): Promise<AgentActionResult> {
  const t = await resolveToken(token);
  if (!t.ok) return { ok: false, error: `Link is ${t.reason}` };

  // Look up the deal once: we need showId for revalidation AND we need
  // to check existing agentConfirmedAt before re-confirming.
  const [deal] = await db
    .select({ id: deals.id, showId: deals.showId, agentConfirmedAt: deals.agentConfirmedAt })
    .from(deals)
    .where(eq(deals.id, t.token.dealId))
    .limit(1);

  if (!deal) return { ok: false, error: "Deal not found" };

  if (deal.agentConfirmedAt) {
    // Idempotent: already confirmed; don't double-write.
    return { ok: true };
  }

  const now = new Date();
  await db.insert(dealAgentResponses).values({
    id: randomUUID(),
    dealId: deal.id,
    tokenUsed: token,
    fieldPath: "all",
    action: "confirmed",
    detailsJson: null,
    respondedAt: now,
  });

  await db
    .update(deals)
    .set({ agentConfirmedAt: now })
    .where(eq(deals.id, deal.id));

  revalidatePath(`/deal/${token}`);
  // Mariana's UI lives at /shows/{showId}/deal — NOT /shows/{dealId}/deal.
  // Look up showId from the deal row above (revalidation needs the route's
  // dynamic segment, which is the show id).
  revalidatePath(`/shows/${deal.showId}/deal`);
  return { ok: true };
}
