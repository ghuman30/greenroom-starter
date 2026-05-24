/**
 * Deal confirmation tokens for the agent-facing /deal/[token] surface.
 *
 * Mariana mints a token (Server Action) and shares the URL out-of-band.
 * Agent opens the link, the server resolves the token to a deal + grants
 * read-confirm access. Token is opaque; no signing key needed.
 *
 * Lifecycle:
 *   - mintToken(dealId, ttlDays)        - create a fresh token
 *   - resolveToken(token)               - validate + return DealId (or
 *                                          a typed reason if invalid)
 *   - revokeToken(token)                - set revokedAt; future resolves
 *                                          return REVOKED
 */

import { and, desc, eq, gt, isNull } from "drizzle-orm";
import { db } from "@/db";
import {
  dealConfirmationTokens,
  type DealConfirmationToken,
} from "@/db/schema";

const DEFAULT_TTL_DAYS = 30;
const TOKEN_BYTES = 24; // 32 chars base64url -> 192 bits of entropy

export type TokenResolution =
  | { ok: true; token: DealConfirmationToken }
  | { ok: false; reason: "not_found" | "expired" | "revoked" };

/**
 * Mint a fresh token for a deal. Returns the URL-safe token string. The
 * caller (Server Action) is responsible for constructing the full URL
 * and presenting it.
 */
export async function mintToken(
  dealId: string,
  opts: { ttlDays?: number; label?: string } = {},
): Promise<string> {
  const token = generateUrlSafeToken();
  const now = new Date();
  const ttl = opts.ttlDays ?? DEFAULT_TTL_DAYS;
  const expiresAt = new Date(now.getTime() + ttl * 86_400_000);

  await db.insert(dealConfirmationTokens).values({
    token,
    dealId,
    createdAt: now,
    expiresAt,
    label: opts.label ?? null,
  });

  return token;
}

/**
 * Resolve a token to its row, validating presence + expiry + revocation.
 * Returns a discriminated result so callers branch cleanly on failure
 * (page can render different UI for each invalid state).
 *
 * Timing-attack note: the lookup is `eq(token, ?)` against the PK column.
 * It's a B-tree probe whose cost is constant in tree height — there's no
 * exploitable timing differential for guessing tokens. The 192-bit
 * entropy of `generateUrlSafeToken` is the actual defence.
 */
export async function resolveToken(token: string): Promise<TokenResolution> {
  const [row] = await db
    .select()
    .from(dealConfirmationTokens)
    .where(eq(dealConfirmationTokens.token, token))
    .limit(1);

  if (!row) return { ok: false, reason: "not_found" };
  if (row.revokedAt) return { ok: false, reason: "revoked" };
  if (row.expiresAt.getTime() < Date.now())
    return { ok: false, reason: "expired" };

  return { ok: true, token: row };
}

/**
 * Revoke a token immediately. Idempotent — re-revoking is a no-op.
 */
export async function revokeToken(token: string): Promise<void> {
  await db
    .update(dealConfirmationTokens)
    .set({ revokedAt: new Date() })
    .where(eq(dealConfirmationTokens.token, token));
}

/**
 * Look up the most recent active token for a deal (used by Mariana's
 * surface to show "the link is already minted" rather than minting a
 * new one on every click). Returns null if no live token exists.
 */
export async function findActiveTokenForDeal(
  dealId: string,
): Promise<DealConfirmationToken | null> {
  const [row] = await db
    .select()
    .from(dealConfirmationTokens)
    .where(
      and(
        eq(dealConfirmationTokens.dealId, dealId),
        isNull(dealConfirmationTokens.revokedAt),
        gt(dealConfirmationTokens.expiresAt, new Date()),
      ),
    )
    .orderBy(desc(dealConfirmationTokens.createdAt))
    .limit(1);
  return row ?? null;
}

// --------------------- Internal -----------------------------------------

/** Generate a URL-safe random token using the Web Crypto API. */
function generateUrlSafeToken(): string {
  const bytes = new Uint8Array(TOKEN_BYTES);
  crypto.getRandomValues(bytes);
  // base64url: replace +,/ with -,_, strip padding
  return Buffer.from(bytes)
    .toString("base64")
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}
