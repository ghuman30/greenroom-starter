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
 * Submit the agent's review. Two distinct outcomes:
 *
 *   1. NO flagged items → "fully confirmed" — sets agentConfirmedAt,
 *      pre-flight signal (vi) stops firing, deal is considered agreed.
 *
 *   2. ANY flagged items → "reviewed with flags" — does NOT set
 *      agentConfirmedAt. The agent reviewed, but raised objections.
 *      Pre-flight keeps firing signal (vi) so Mariana knows the deal
 *      isn't yet agreed. The flagged items are visible to Mariana via
 *      the AgentResponseSection on her review page.
 *
 * Idempotent: short-circuits if a "submitted" summary row already
 * exists. The summary row's `action` field encodes the outcome
 * ('confirmed' for clean, 'flagged' for reviewed-with-flags).
 */
export async function confirmAll(token: string): Promise<AgentActionResult> {
  const t = await resolveToken(token);
  if (!t.ok) return { ok: false, error: `Link is ${t.reason}` };

  const [deal] = await db
    .select({
      id: deals.id,
      showId: deals.showId,
      agentConfirmedAt: deals.agentConfirmedAt,
    })
    .from(deals)
    .where(eq(deals.id, t.token.dealId))
    .limit(1);

  if (!deal) return { ok: false, error: "Deal not found" };

  // Count actual flags from per-item responses for THIS deal.
  // `fieldPath != 'all'` excludes the aggregate row itself.
  const responses = await db
    .select({
      action: dealAgentResponses.action,
      fieldPath: dealAgentResponses.fieldPath,
    })
    .from(dealAgentResponses)
    .where(eq(dealAgentResponses.dealId, deal.id));

  const flaggedCount = responses.filter(
    (r) => r.action === "flagged" && r.fieldPath !== "all",
  ).length;

  const alreadySubmitted = responses.some((r) => r.fieldPath === "all");
  if (alreadySubmitted) {
    // Idempotent: already submitted. Don't double-write.
    return { ok: true };
  }

  const now = new Date();

  // Aggregate row encodes outcome in `action`.
  await db.insert(dealAgentResponses).values({
    id: randomUUID(),
    dealId: deal.id,
    tokenUsed: token,
    fieldPath: "all",
    action: flaggedCount > 0 ? "flagged" : "confirmed",
    detailsJson: flaggedCount > 0 ? JSON.stringify({ flagged_count: flaggedCount }) : null,
    respondedAt: now,
  });

  // Only set agentConfirmedAt if the agent actually agreed to everything.
  // Otherwise the deal is "reviewed but not confirmed" — pre-flight
  // signal (vi) keeps firing.
  if (flaggedCount === 0) {
    await db
      .update(deals)
      .set({ agentConfirmedAt: now })
      .where(eq(deals.id, deal.id));
  }

  revalidatePath(`/deal/${token}`);
  revalidatePath(`/shows/${deal.showId}/deal`);
  return { ok: true };
}
