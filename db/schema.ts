/**
 * Greenroom database schema.
 *
 * The data model is deliberately simple but realistic enough to support
 * the settlement workflows. Mariana (the booker at The Crescent) is the
 * primary user. Other personas (tour managers, agents, the GM) appear
 * in the data but don't have UI here.
 */

import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";

// -------- Users (operator accounts at the venue) --------

export const users = sqliteTable("users", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  email: text("email").notNull().unique(),
  role: text("role", {
    enum: ["booker", "gm", "production", "box_office"],
  }).notNull(),
  venueId: text("venue_id").notNull(),
});

// -------- Venues --------

export const venues = sqliteTable("venues", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  capacity: integer("capacity").notNull(),
  city: text("city").notNull(),
  state: text("state").notNull(),
});

// -------- Agencies & Agents --------

export const agencies = sqliteTable("agencies", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
});

export const agents = sqliteTable("agents", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  agencyId: text("agency_id").references(() => agencies.id),
  email: text("email").notNull(),
  phone: text("phone"),
  preferencesNotes: text("preferences_notes"),
});

// -------- Artists --------

export const artists = sqliteTable("artists", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  agentId: text("agent_id").references(() => agents.id),
  managerEmail: text("manager_email"),
  genre: text("genre"),
  priorShowCount: integer("prior_show_count").notNull().default(0),
});

// -------- Shows --------

export const shows = sqliteTable("shows", {
  id: text("id").primaryKey(),
  venueId: text("venue_id")
    .notNull()
    .references(() => venues.id),
  artistId: text("artist_id")
    .notNull()
    .references(() => artists.id),
  date: text("date").notNull(),
  status: text("status", {
    enum: ["booked", "advanced", "day_of", "settled", "closed"],
  })
    .notNull()
    .default("booked"),
  doorsTime: text("doors_time"),
  setTime: text("set_time"),
  openerArtistId: text("opener_artist_id").references(() => artists.id),
  roomConfig: text("room_config", { enum: ["standing", "seated", "mixed"] })
    .notNull()
    .default("standing"),
  internalNotes: text("internal_notes"),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
});

// -------- Deals --------

/**
 * One deal per show. The structure here is deliberately split:
 *
 *  - `dealType` and the structured fields (guarantee, percentage, etc.)
 *    are what the in-app settlement tool reads.
 *  - `dealNotesFreetext` is what Mariana actually trusts.
 *  - `bonusesJson` exists in the schema but the in-app tool doesn't read it.
 *    It's been there since 2023, originally added by a now-departed PM. About
 *    half the deals that have bonus structures fill it in; the other half
 *    leave it empty and put the bonuses in the prose only. That mismatch
 *    is one of the case-study seams.
 *
 * bonusesJson schema (when present):
 *   [
 *     { type: "gross_threshold", label: string, threshold: number, amount: number, stacks?: boolean },
 *     { type: "sellout", label: string, amount: number },
 *     { type: "attendance_threshold", label: string, threshold: number, amount: number },
 *     { type: "tier_ratchet", label: string, tiers: [{ from, to|null, percentage }] }
 *   ]
 */
export const deals = sqliteTable("deals", {
  id: text("id").primaryKey(),
  showId: text("show_id")
    .notNull()
    .unique()
    .references(() => shows.id),

  dealType: text("deal_type", {
    enum: ["flat", "percentage_of_gross", "percentage_of_net", "vs", "door"],
  }).notNull(),
  guaranteeAmount: real("guarantee_amount"),
  percentage: real("percentage"),
  percentageBasis: text("percentage_basis", { enum: ["gross", "net"] }),
  expenseCap: real("expense_cap"),
  hospitalityCap: real("hospitality_cap"),

  bonusesJson: text("bonuses_json"),
  dealNotesFreetext: text("deal_notes_freetext"),

  // -------- Slice 1 additions (deal capture & disambiguation) --------
  //
  // Optional paste of the agent's original deal email. When present, the LLM
  // extractor treats it as the primary source and flags any discrepancies
  // against `dealNotesFreetext`. When absent, the extractor falls back to
  // `dealNotesFreetext` alone with a lower confidence rating.
  agentEmailText: text("agent_email_text"),
  agentEmailReceivedAt: integer("agent_email_received_at", { mode: "timestamp" }),

  // Full LLM-extracted structured representation. JSON conforming to the
  // ExtractionOutput type below. Includes ratchets, walkout pots, planned
  // recoups, per-clause ambiguity scoring, source spans, and confidence.
  // Populated by lib/extraction.ts; reviewed by Mariana before downstream
  // consumers (pre-flight, settlement, agent confirmation) use it.
  extractedDealJson: text("extracted_deal_json"),

  // HITL gates. Two-layer review:
  //   1. Mariana reviews LLM extraction; marianaConfirmedAt is set on her sign-off.
  //   2. Agent reviews confirmation link; agentConfirmedAt is set on theirs.
  // Pre-flight signal (vi) fires when agentConfirmedAt is NULL within X days
  // of show.
  marianaConfirmedAt: integer("mariana_confirmed_at", { mode: "timestamp" }),
  agentConfirmedAt: integer("agent_confirmed_at", { mode: "timestamp" }),
  confirmedByAgentId: text("confirmed_by_agent_id"),

  createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
});

// -------- Deal versions (amendment tracking) --------

/**
 * Every change to a deal (structured or prose) creates a new version row.
 * The deal-level fields hold the CURRENT version; deal_versions is the
 * append-only history.
 *
 * Default behavior: when a version is created, agentReconfirmRequired = true
 * and the parent deal's agentConfirmedAt is cleared. The agent must confirm
 * the new version via the shareable link before downstream consumers use it.
 *
 * Memo-flagged open product question: should every amendment require
 * agent re-confirmation, or only material ones (changes to guarantee,
 * percentage, caps above $X)? Currently every change requires
 * re-confirmation; a future config could relax this.
 */
export const dealVersions = sqliteTable("deal_versions", {
  id: text("id").primaryKey(),
  dealId: text("deal_id")
    .notNull()
    .references(() => deals.id),
  versionNumber: integer("version_number").notNull(),
  changedAt: integer("changed_at", { mode: "timestamp" }).notNull(),
  changedByUserId: text("changed_by_user_id").references(() => users.id),
  changeReason: text("change_reason"),
  previousValueJson: text("previous_value_json"),
  newValueJson: text("new_value_json"),
  agentReconfirmRequired: integer("agent_reconfirm_required", { mode: "boolean" })
    .notNull()
    .default(true),
  agentReconfirmedAt: integer("agent_reconfirmed_at", { mode: "timestamp" }),
});

// -------- Deal confirmation tokens (T3) --------

/**
 * Stateful access tokens for the agent-facing confirmation page at
 * /deal/[token]. The agent doesn't have a Greenroom account; Mariana
 * shares the URL out-of-band (email, text). Token grants read access to
 * the deal + permission to confirm/flag items.
 *
 * Why stateful (vs signed JWT): no signing-secret management; trivial
 * revocation by setting revokedAt; easy to inspect in dev for debugging.
 */
export const dealConfirmationTokens = sqliteTable("deal_confirmation_tokens", {
  token: text("token").primaryKey(),
  dealId: text("deal_id")
    .notNull()
    .references(() => deals.id),
  createdAt: integer("created_at", { mode: "timestamp" }).notNull(),
  expiresAt: integer("expires_at", { mode: "timestamp" }).notNull(),
  revokedAt: integer("revoked_at", { mode: "timestamp" }),
  // Optional descriptive label so Mariana sees "Confirmed by Daniel via
  // link 'WME-Mar-14'" rather than a random string.
  label: text("label"),
});

// -------- Deal agent responses (T3) --------

/**
 * Per-item agent actions on the confirmation page. One row per
 * confirm/flag/reading-choice event.
 *
 * fieldPath identifies what was acted on:
 *   "guarantee_amount", "percentage", "expense_cap", "hospitality_cap"
 *   "bonus_<index>", "ratchet_<index>", "walkout_pot_<index>"
 *   "ambiguity_<index>", "discrepancy_<index>"
 *   "all" — single "confirm everything" action covers the happy path
 *
 * action: what the agent did
 *   "confirmed"    - looks right, agent agrees with our reading
 *   "flagged"      - looks wrong, see details_json for their note
 *   "reading_chosen" - for ambiguity flags, picked one of the readings;
 *                      reading_index in details_json
 *
 * details_json: structured payload, optional. Examples:
 *   { reading_index: 0 }
 *   { custom_reading: "Actually neither — see explanation" }
 *   { comment: "I never agreed to a $500 hosp cap" }
 */
export const dealAgentResponses = sqliteTable("deal_agent_responses", {
  id: text("id").primaryKey(),
  dealId: text("deal_id")
    .notNull()
    .references(() => deals.id),
  tokenUsed: text("token_used"), // for audit; not enforced FK
  fieldPath: text("field_path").notNull(),
  action: text("action", {
    enum: ["confirmed", "flagged", "reading_chosen"],
  }).notNull(),
  detailsJson: text("details_json"),
  respondedAt: integer("responded_at", { mode: "timestamp" }).notNull(),
});

// -------- Ticket sales --------

export const ticketSales = sqliteTable("ticket_sales", {
  id: text("id").primaryKey(),
  showId: text("show_id")
    .notNull()
    .references(() => shows.id),
  qty: integer("qty").notNull(),
  gross: real("gross").notNull(),
  fees: real("fees").notNull(),
  capturedAt: integer("captured_at", { mode: "timestamp" }).notNull(),
});

// -------- Comps --------

/**
 * Comp tickets given away. A real source of dispute — agents sometimes argue
 * that certain comps "should have counted toward the gross" the artist's % is
 * calculated against. Most comps don't count, but the rules vary by category
 * and sometimes by deal.
 *
 * Stored as one row per category per show (aggregated count, not per-ticket).
 */
export const comps = sqliteTable("comps", {
  id: text("id").primaryKey(),
  showId: text("show_id")
    .notNull()
    .references(() => shows.id),
  category: text("category", {
    enum: [
      "artist_gl", // artist guest list
      "label", // label/management
      "press", // journalists, photographers
      "venue_staff", // venue staff and friends
      "sponsor", // sponsor reps
      "promo", // radio giveaways, 2-for-1s
      "other",
    ],
  }).notNull(),
  count: integer("count").notNull(),
  faceValue: real("face_value").notNull(),
  // Whether these comps count toward gross box office for settlement purposes.
  // Most categories don't, but the rules are inconsistent across deals.
  countsTowardGross: integer("counts_toward_gross", { mode: "boolean" })
    .notNull()
    .default(false),
  notes: text("notes"),
});

// -------- Expenses --------

export const expenses = sqliteTable("expenses", {
  id: text("id").primaryKey(),
  showId: text("show_id")
    .notNull()
    .references(() => shows.id),
  category: text("category", {
    enum: [
      "production",
      "sound",
      "lights",
      "hospitality",
      "marketing",
      "backline",
      "security",
      "other",
    ],
  }).notNull(),
  amount: real("amount").notNull(),
  description: text("description"),
  approved: integer("approved", { mode: "boolean" }).notNull().default(true),
  absorbedByVenue: integer("absorbed_by_venue", { mode: "boolean" })
    .notNull()
    .default(false),
  enteredByUserId: text("entered_by_user_id").references(() => users.id),
  enteredAt: integer("entered_at", { mode: "timestamp" }).notNull(),
});

// -------- Settlements --------

/**
 * The post-show financial reconciliation. One per show.
 *
 * Settlement is a multi-party state machine: the venue calculates a number,
 * sends it to the artist's tour manager / agent for review, they sign or
 * dispute, revisions happen, eventually a final number is agreed and money
 * moves.
 *
 * Stage timestamps below capture each transition. `status` is the current
 * stage. Most past shows are `paid`; recent ones are still in-flight.
 *
 * recoupsJson schema (when present):
 *   [
 *     { id, category: "marketing"|"hospitality_overage"|"production_overage"|"prior_advance"|"damages"|"other",
 *       label: string, amount: number, status: "agreed"|"disputed"|"withdrawn" }
 *   ]
 *
 * Recoups are venue costs that come "off the top" before artist payment.
 * They differ from regular expenses in two ways:
 *   1. They're disputed more often — the deal email language about recoups
 *      is frequently ambiguous (see the Coastal Spell dispute).
 *   2. They have their own lifecycle independent of the rest of the
 *      settlement — a recoup can be disputed even after the rest of the
 *      math is signed.
 */
export const settlements = sqliteTable("settlements", {
  id: text("id").primaryKey(),
  showId: text("show_id")
    .notNull()
    .unique()
    .references(() => shows.id),

  status: text("status", {
    enum: [
      "draft", // booker is still doing math
      "submitted", // sent to artist team
      "in_review", // artist team has opened it
      "signed", // both parties agree
      "disputed", // line items contested
      "revised", // venue sent a revision after dispute
      "finalized", // signed after revision
      "paid", // money has moved
      "voided", // show cancelled or settlement scrapped
    ],
  })
    .notNull()
    .default("draft"),

  // Stage timestamps
  draftedAt: integer("drafted_at", { mode: "timestamp" }),
  submittedAt: integer("submitted_at", { mode: "timestamp" }),
  reviewStartedAt: integer("review_started_at", { mode: "timestamp" }),
  signedAt: integer("signed_at", { mode: "timestamp" }),
  disputedAt: integer("disputed_at", { mode: "timestamp" }),
  revisedAt: integer("revised_at", { mode: "timestamp" }),
  finalizedAt: integer("finalized_at", { mode: "timestamp" }),
  paidAt: integer("paid_at", { mode: "timestamp" }),

  completedAt: integer("completed_at", { mode: "timestamp" }),
  completedByUserId: text("completed_by_user_id").references(() => users.id),

  grossBoxOffice: real("gross_box_office"),
  netBoxOffice: real("net_box_office"),
  totalExpenses: real("total_expenses"),
  totalToArtist: real("total_to_artist"),

  calculationJson: text("calculation_json"),
  recoupsJson: text("recoups_json"),

  signoffText: text("signoff_text"),
  notes: text("notes"),
});

// -------- Type exports for convenience --------

export type User = typeof users.$inferSelect;
export type Venue = typeof venues.$inferSelect;
export type Agency = typeof agencies.$inferSelect;
export type Agent = typeof agents.$inferSelect;
export type Artist = typeof artists.$inferSelect;
export type Show = typeof shows.$inferSelect;
export type Deal = typeof deals.$inferSelect;
export type DealVersion = typeof dealVersions.$inferSelect;
export type DealConfirmationToken = typeof dealConfirmationTokens.$inferSelect;
export type DealAgentResponse = typeof dealAgentResponses.$inferSelect;
export type TicketSale = typeof ticketSales.$inferSelect;
export type Comp = typeof comps.$inferSelect;
export type Expense = typeof expenses.$inferSelect;
export type Settlement = typeof settlements.$inferSelect;

// -------- Decoded JSON helpers --------

export type Bonus =
  | {
      type: "gross_threshold";
      label: string;
      threshold: number;
      amount: number;
      stacks?: boolean;
    }
  | { type: "sellout"; label: string; amount: number }
  | {
      type: "attendance_threshold";
      label: string;
      threshold: number;
      amount: number;
    }
  | {
      type: "tier_ratchet";
      label: string;
      tiers: { from: number; to: number | null; percentage: number }[];
    };

export type Recoup = {
  id: string;
  category:
    | "marketing"
    | "hospitality_overage"
    | "production_overage"
    | "prior_advance"
    | "damages"
    | "other";
  label: string;
  amount: number;
  status: "agreed" | "disputed" | "withdrawn";
};

export type SettlementStage = Settlement["status"];

// -------- LLM extraction output types (Slice 1) --------

/**
 * Structured deal representation produced by the LLM extractor.
 * The full ExtractionOutput is stored as JSON in deals.extractedDealJson.
 */

export type TierRatchet = {
  trigger: "attendance_pct" | "gross";
  from_pct: number;
  to_pct: number;
  threshold: number;
};

export type WalkoutPot = {
  percent: number;
  threshold: number;
  basis: "gross" | "net";
};

export type PlannedRecoup = {
  category:
    | "marketing"
    | "hospitality_overage"
    | "production_overage"
    | "prior_advance"
    | "damages";
  amount: number;
  /** "outside_cap" = comes off gross before % applied. "inside_cap" = counts toward expense cap.
   *  "unspecified" = source didn't say — needs ambiguity flag. */
  basis: "gross" | "net" | "outside_cap" | "inside_cap" | "unspecified";
  description: string;
};

export type ExtractedDeal = {
  deal_kind: "flat" | "percentage_of_gross" | "percentage_of_net" | "vs" | "door";
  guarantee_amount: number | null;
  percentage: number | null;
  percentage_basis: "gross" | "net" | null;
  expense_cap: number | null;
  hospitality_cap: number | null;
  bonuses: Bonus[];
  ratchets: TierRatchet[];
  walkout_pots: WalkoutPot[];
  planned_recoups: PlannedRecoup[];
};

export type AmbiguityFlag = {
  /** Verbatim quote from the source. */
  clause: string;
  source: "email" | "notes";
  severity: "low" | "medium" | "high";
  readings: {
    interpretation: string;
    implied_payout_change_usd: number | null;
    implied_payout_change_pct: number | null;
  }[];
};

export type Discrepancy = {
  field: string;
  email_says: string;
  notes_says: string;
  severity: "low" | "medium" | "high";
};

export type LowConfidenceField = {
  field: string;
  reason: string;
};

/**
 * Full LLM extraction output. Stored verbatim as JSON in
 * deals.extractedDealJson. Read by:
 *   - Mariana's review UI (per-field display + source spans)
 *   - Agent confirmation surface (plain-English restatement)
 *   - Pre-flight signals (ambiguity, structure, planned recoups)
 */
export type ExtractionOutput = {
  extracted: ExtractedDeal;
  source_spans: Record<string, string>;
  confidence_per_field: Record<string, number>;
  ambiguity_flags: AmbiguityFlag[];
  discrepancies: Discrepancy[];
  low_confidence: LowConfidenceField[];
  /**
   * Metadata for the extraction run itself. Optional because:
   *  - The LLM may or may not include these in its JSON output.
   *  - lib/extraction.ts fills them in at the boundary if missing.
   * Callers that need them guaranteed should null-check or read them
   * from the ExtractionMetadata returned by extractDeal().
   */
  model?: string;
  generated_at?: string;
  source?: "email" | "notes" | "both";
};
