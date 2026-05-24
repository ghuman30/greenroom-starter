/**
 * Pre-flight signal computation (T4 / slice 3).
 *
 * Pure functions that take a deal + its context and emit a list of
 * risk signals. Mirrors the Wednesday-honest signal set from the Q11
 * backtest (notes/queries/q11_backtest_corrected.py) but with one
 * material upgrade in production: signal (i) reads the LLM-extracted
 * ambiguity_flags from deals.extracted_deal_json instead of doing
 * regex on prose. The LLM's semantic reading is the lift the case
 * promises (target: 17% -> 40%+ recall on signal i).
 *
 * Signal set (locked after Q12 + Q13):
 *   (i)       Ambiguous prose                 [LLM in prod, regex in backtest]
 *   (ii.pred) Recoup risk from history        [SQL — prior settlements]
 *   (iii.pred) Hospitality overrun history    [SQL — prior settlements]
 *   (iv)      Ignored structure (ratchet/walkout)
 *   (v)       Prior open-loop notes
 *   (vi)      Deal not agent-confirmed         [reads deals.agentConfirmedAt]
 *   (vii)     Agent severity modifier         [scales other signals up/down]
 *   (ix)      New-to-venue agent              [informational badge]
 *
 *   (viii) was dropped after Q13 stress-test (precision 4.9%, lift 1.0x).
 */

import type {
  Deal,
  ExtractionOutput,
  Agent,
} from "@/db/schema";
import { getExtraction } from "./extraction";

// --------------------- Public types -----------------------------------------

export type SignalId =
  | "i_ambiguous"
  | "ii_recoup_history"
  | "iii_hosp_history"
  | "iv_structure"
  | "v_open_loop"
  | "vi_not_confirmed"
  | "ix_new_agent";

export type SignalSeverity = "low" | "medium" | "high";

export interface SignalResult {
  id: SignalId;
  severity: SignalSeverity;
  /** One-line summary for the UI badge. */
  label: string;
  /** Longer explanation, shown when the row is expanded. */
  detail: string;
}

/** Context the signal functions need beyond the deal itself. */
export interface SignalContext {
  /** Prior settlements for the same artist OR agent OR agency, in the
   *  18 months before this show's date. */
  priorSettlements: PriorSettlement[];
  /** Agent record (preferences_notes used for severity modifier + new-agent flag). */
  agent: Pick<Agent, "name" | "preferencesNotes"> | null;
  /** Show date for relative timing. */
  showDate: string; // YYYY-MM-DD
  /** Days from "today" to show date. Negative = past. */
  daysUntilShow: number;
}

export interface PriorSettlement {
  showId: string;
  date: string;
  status: string;
  recoupsJson: string | null;
  notes: string | null;
  hospitalityCap: number | null;
  hospitalityActual: number; // sum of hospitality expenses for that show
}

// --------------------- Severity weights --------------------------------------

const SEVERITY_WEIGHTS: Record<SignalSeverity, number> = {
  low: 1,
  medium: 2,
  high: 3,
};

export function severityWeight(s: SignalSeverity): number {
  return SEVERITY_WEIGHTS[s];
}

// --------------------- Agent severity modifier (vii) -------------------------

/**
 * Agent-level context reads from preferences_notes. We classify the
 * agent's posture as "elevated risk" (escalates other signal severities)
 * or "low risk" (de-escalates). Defaults to "neutral" when notes are
 * absent or noncommittal.
 */
type AgentPosture = "elevated" | "neutral" | "low";

function classifyAgentPosture(prefs: string | null | undefined): AgentPosture {
  if (!prefs) return "neutral";
  const lower = prefs.toLowerCase();
  // Tom Neary, Daniel Hwang
  if (
    /pushes? back hard|tends? to ambiguity|annoying|template he wants|pet peeve/.test(
      lower,
    )
  ) {
    return "elevated";
  }
  // Danny Ortiz, Sarah Kim
  if (
    /easygoing|quick to sign|trusts mariana|one of the easier|reads.*fairly/.test(
      lower,
    )
  ) {
    return "low";
  }
  return "neutral";
}

function adjustSeverity(
  base: SignalSeverity,
  posture: AgentPosture,
): SignalSeverity {
  if (posture === "neutral") return base;
  const order: SignalSeverity[] = ["low", "medium", "high"];
  const idx = order.indexOf(base);
  if (posture === "elevated") return order[Math.min(idx + 1, order.length - 1)];
  return order[Math.max(idx - 1, 0)];
}

// --------------------- Signal implementations -------------------------------

/**
 * Signal (i) — Ambiguous prose. Reads LLM-extracted ambiguity_flags.
 * Severity is the max severity across all flags (high if any flag is
 * high, etc.). Returns null if no flags.
 */
export function signal_i_ambiguous(
  extraction: ExtractionOutput | null,
): SignalResult | null {
  if (!extraction) return null;
  const flags = extraction.ambiguity_flags ?? [];
  if (flags.length === 0) return null;

  const order: SignalSeverity[] = ["low", "medium", "high"];
  let max: SignalSeverity = "low";
  for (const f of flags) {
    if (order.indexOf(f.severity) > order.indexOf(max)) max = f.severity;
  }

  const exemplar = flags[0];
  const truncated =
    exemplar.clause.length > 80
      ? exemplar.clause.slice(0, 77) + "…"
      : exemplar.clause;

  return {
    id: "i_ambiguous",
    severity: max,
    label: `${flags.length} ambiguous clause${flags.length === 1 ? "" : "s"}`,
    detail: `LLM flagged: "${truncated}" with ${exemplar.readings?.length ?? 0} possible readings.`,
  };
}

/**
 * Signal (ii.pred) — Recoup risk from history. Fires when this deal's
 * prose is silent on recoups AND the same agent/artist has historically
 * had recoups at >=40% of past shows.
 */
export function signal_ii_recoup_history(
  deal: Pick<Deal, "dealNotesFreetext">,
  ctx: SignalContext,
): SignalResult | null {
  const notes = (deal.dealNotesFreetext ?? "").toLowerCase();
  // Tightened from the original wide list (which suppressed the signal
  // on routine words like "rider", "production", "advance"). We only
  // skip when the prose actually addresses recoupable spend or a
  // recoup mechanism explicitly.
  const RECOUP_PHRASES = [
    "recoup",
    "marketing recoup",
    "ad spend",
    "spotify ad",
    "instagram boost",
    "marketing pass-through",
    "promo recoup",
    "prior advance",
  ];
  if (RECOUP_PHRASES.some((w) => notes.includes(w))) return null;

  // Count prior settlements with non-empty recoups_json
  const total = ctx.priorSettlements.length;
  if (total < 3) return null;

  const withRecoups = ctx.priorSettlements.filter(
    (s) =>
      s.recoupsJson &&
      s.recoupsJson !== "" &&
      s.recoupsJson !== "[]",
  ).length;

  const rate = withRecoups / total;
  if (rate < 0.4) return null;

  return {
    id: "ii_recoup_history",
    severity: rate >= 0.6 ? "high" : "medium",
    label: `Recoup risk · ${withRecoups}/${total} prior shows`,
    detail: `Deal email mentions no recoup, but ${withRecoups} of last ${total} shows with this artist/agent had a recoup at settlement (${Math.round(
      rate * 100,
    )}%). Confirm with the agent before show.`,
  };
}

/**
 * Signal (iii.pred) — Hospitality overrun history. Fires when this deal
 * has a hospitality_cap AND the artist/agent has historically overrun
 * caps on >=50% of past shows.
 */
export function signal_iii_hosp_history(
  deal: Pick<Deal, "hospitalityCap">,
  ctx: SignalContext,
): SignalResult | null {
  if (deal.hospitalityCap == null) return null;

  const eligible = ctx.priorSettlements.filter(
    (s) => s.hospitalityCap != null,
  );
  if (eligible.length < 2) return null;

  const overruns = eligible.filter(
    (s) => s.hospitalityActual > (s.hospitalityCap ?? 0) * 1.1,
  ).length;
  const rate = overruns / eligible.length;
  if (rate < 0.5) return null;

  return {
    id: "iii_hosp_history",
    severity: rate >= 0.75 ? "high" : "medium",
    label: `Hosp overrun risk · ${overruns}/${eligible.length} prior shows`,
    detail: `${overruns} of last ${eligible.length} shows with this artist/agent overran their hospitality cap. This show has cap $${deal.hospitalityCap.toFixed(
      0,
    )}.`,
  };
}

/**
 * Signal (iv) — Ignored structure. Fires when the deal has a tier
 * ratchet, walkout pot, or escalator that the in-app settlement
 * engine can't handle. Reads structured (bonuses_json) AND prose.
 */
export function signal_iv_structure(
  deal: Pick<Deal, "bonusesJson" | "dealNotesFreetext">,
): SignalResult | null {
  // Check bonuses_json for tier_ratchet (dealMath.ts:243 ignores these)
  if (deal.bonusesJson) {
    try {
      const parsed = JSON.parse(deal.bonusesJson);
      if (Array.isArray(parsed)) {
        for (const b of parsed) {
          if (b && typeof b === "object" && b.type === "tier_ratchet") {
            return {
              id: "iv_structure",
              severity: "high",
              label: "Tier ratchet — engine ignores",
              detail:
                "Deal has a tier_ratchet bonus structure. The in-app settlement engine throws this away (lib/dealMath.ts:243). Settle manually or pre-confirm the ratcheted percentage with the agent.",
            };
          }
        }
      }
    } catch {
      // ignore malformed
    }
  }
  // Check prose for walkout / ratchet / escalator
  const notes = (deal.dealNotesFreetext ?? "").toLowerCase();
  if (/walkout/.test(notes)) {
    return {
      id: "iv_structure",
      severity: "medium",
      label: "Walkout pot in prose",
      detail:
        "Deal mentions a walkout pot, which the schema doesn't represent. Settlement will need manual math.",
    };
  }
  if (/ratchet|escalator|escalates/.test(notes)) {
    return {
      id: "iv_structure",
      severity: "medium",
      label: "Ratchet / escalator in prose",
      detail:
        "Deal has a tier ratchet or escalator in prose. Verify the structured fields capture it.",
    };
  }
  return null;
}

/**
 * Signal (v) — Prior open-loop notes. Mariana uses settlements.notes
 * as a TODO list ("haven't gotten back to it"). If a prior settlement
 * for the same parties has an open-loop note, this show inherits
 * relationship risk.
 */
export function signal_v_open_loop(ctx: SignalContext): SignalResult | null {
  const PATTERNS = [
    "outstanding",
    "haven't gotten back",
    "never resolved",
    "not yet been pushed back",
    "carrying as outstanding",
  ];
  for (const s of ctx.priorSettlements) {
    if (!s.notes) continue;
    const lower = s.notes.toLowerCase();
    for (const p of PATTERNS) {
      if (lower.includes(p)) {
        return {
          id: "v_open_loop",
          severity: "medium",
          label: `Prior open-loop note (${s.date})`,
          detail: `Earlier settlement for this artist/agent left something unresolved: notes contain "${p}". Close that loop before adding to it.`,
        };
      }
    }
  }
  return null;
}

/**
 * Signal (vi) — Deal not agent-confirmed. Fires within N days of show
 * if the agent hasn't yet clicked through the confirmation link.
 */
export function signal_vi_not_confirmed(
  deal: Pick<Deal, "agentConfirmedAt">,
  ctx: SignalContext,
): SignalResult | null {
  if (deal.agentConfirmedAt) return null;
  if (ctx.daysUntilShow < 0) return null; // show is past
  if (ctx.daysUntilShow > 14) {
    // Show is more than 2 weeks out — informational only
    return {
      id: "vi_not_confirmed",
      severity: "low",
      label: "Agent hasn't confirmed yet",
      detail: `Send the confirmation link to the agent — show is in ${ctx.daysUntilShow} days.`,
    };
  }
  // Show is within 2 weeks and still unconfirmed
  return {
    id: "vi_not_confirmed",
    severity: ctx.daysUntilShow <= 3 ? "high" : "medium",
    label: `Agent unconfirmed · ${ctx.daysUntilShow}d to show`,
    detail: `Send (or chase) the agent confirmation link. The agent reading the deal on Monday-after is where ${ctx.daysUntilShow <= 3 ? "most" : "many"} disputes start.`,
  };
}

/**
 * Signal (ix) — New-to-venue agent. Informational badge, NOT a firing
 * risk signal. Surfaces when the agent has zero prior settlements with
 * the venue, OR when their preferences_notes flag them as "new."
 */
export function signal_ix_new_agent(
  ctx: SignalContext,
): SignalResult | null {
  const prefs = ctx.agent?.preferencesNotes?.toLowerCase() ?? "";
  const flaggedNew = /\bnew (at|to)|just took over|still learning/.test(prefs);
  if (flaggedNew) {
    return {
      id: "ix_new_agent",
      severity: "low",
      label: `New agent — ${ctx.agent?.name ?? "agent"}`,
      detail: `Your notes flag this agent as new. Extra care on the deal-clarity step pays off here.`,
    };
  }
  // No prior settlements OR fewer than 2 means this is a new relationship
  if (ctx.priorSettlements.length === 0) {
    return {
      id: "ix_new_agent",
      severity: "low",
      label: "First show with this artist/agent",
      detail:
        "No prior settlements found. Treat as first-touch — high-quality deal capture sets the relationship tone.",
    };
  }
  return null;
}

// --------------------- Orchestration -----------------------------------------

export interface ComputeSignalsArgs {
  deal: Pick<
    Deal,
    | "dealNotesFreetext"
    | "bonusesJson"
    | "hospitalityCap"
    | "agentConfirmedAt"
    | "extractedDealJson"
  >;
  context: SignalContext;
}

/** Result of computing signals for a single show. */
export interface ShowSignals {
  signals: SignalResult[];
  /** Sum of severity weights after agent-posture adjustment. */
  riskScore: number;
  /** Agent posture (for UI to show "agent context" pill). */
  agentPosture: "elevated" | "neutral" | "low";
}

/**
 * Compute all signals for a show. Applies the agent severity modifier
 * (vii) by escalating/de-escalating each firing signal based on the
 * agent's preferences_notes posture.
 */
export function computeShowSignals(args: ComputeSignalsArgs): ShowSignals {
  const { deal, context } = args;

  // Use the validated loader (same one Mariana's review surface uses)
  // so we get shape-guarded ExtractionOutput, not a raw JSON cast.
  // Stale/malformed JSON resolves to `null`, which signal_i_ambiguous
  // handles cleanly.
  const loaded = getExtraction(deal);
  const extraction: ExtractionOutput | null = loaded.ok ? loaded.output : null;

  const raw: (SignalResult | null)[] = [
    signal_i_ambiguous(extraction),
    signal_ii_recoup_history(deal, context),
    signal_iii_hosp_history(deal, context),
    signal_iv_structure(deal),
    signal_v_open_loop(context),
    signal_vi_not_confirmed(deal, context),
    signal_ix_new_agent(context),
  ];

  const posture = classifyAgentPosture(context.agent?.preferencesNotes);

  // Apply posture modifier to ACTIONABLE signals (not the ix info badge)
  const signals = raw
    .filter((s): s is SignalResult => s !== null)
    .map((s) =>
      s.id === "ix_new_agent"
        ? s
        : { ...s, severity: adjustSeverity(s.severity, posture) },
    );

  const riskScore = signals
    .filter((s) => s.id !== "ix_new_agent")
    .reduce((sum, s) => sum + severityWeight(s.severity), 0);

  return { signals, riskScore, agentPosture: posture };
}
