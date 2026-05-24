import { notFound } from "next/navigation";
import { AlertTriangle, FileText, Mail } from "lucide-react";
import { eq } from "drizzle-orm";
import { db } from "@/db";
import { deals, shows, artists, agencies, agents, venues } from "@/db/schema";
import { resolveToken } from "@/lib/dealTokens";
import { getExtraction } from "@/lib/extraction";
import { formatMoney, formatShowDateFull } from "@/lib/format";
import { Logomark } from "@/components/brand/logo";
import { PlainBadge } from "@/components/ui/badge";
import type {
  ExtractionOutput,
  AmbiguityFlag,
  Bonus,
  Deal,
  PlannedRecoup,
} from "@/db/schema";
import {
  ItemActions,
  AmbiguityResolver,
  ConfirmAllButton,
} from "./AgentResponseActions";

const RECOUP_LABELS: Record<PlannedRecoup["category"], string> = {
  marketing: "Marketing recoup",
  hospitality_overage: "Hospitality overage",
  production_overage: "Production overage",
  prior_advance: "Prior advance",
  damages: "Damages",
};

type PayableBonus = Exclude<Bonus, { type: "tier_ratchet" }>;
function isPayableBonus(b: Bonus): b is PayableBonus {
  return b.type !== "tier_ratchet";
}

export default async function AgentDealPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;
  const resolution = await resolveToken(token);

  if (!resolution.ok) {
    return <InvalidTokenState reason={resolution.reason} />;
  }

  const dealId = resolution.token.dealId;
  const rows = await db
    .select({
      deal: deals,
      show: shows,
      artist: artists,
      agent: agents,
      agency: agencies,
      venue: venues,
    })
    .from(deals)
    .leftJoin(shows, eq(shows.id, deals.showId))
    .leftJoin(artists, eq(artists.id, shows.artistId))
    .leftJoin(agents, eq(agents.id, artists.agentId))
    .leftJoin(agencies, eq(agencies.id, agents.agencyId))
    .leftJoin(venues, eq(venues.id, shows.venueId))
    .where(eq(deals.id, dealId))
    .limit(1);

  if (rows.length === 0) notFound();
  const { deal, show, artist, agent, agency, venue } = rows[0];
  if (!deal || !show) notFound();

  const extractionResult = getExtraction(deal);
  const extraction = extractionResult.ok ? extractionResult.output : null;

  const venueName = venue?.name ?? "The Crescent";
  const greeting = agent?.name ? `Hi ${agent.name.split(" ")[0]}` : "Hi there";

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-ink-100 bg-white">
        <div className="max-w-3xl mx-auto px-5 sm:px-8 py-4 flex items-center gap-3">
          <Logomark className="h-6 w-6 text-brand-700" />
          <div className="font-display text-[15px] font-medium text-ink-900">
            {venueName}
          </div>
          {agency && (
            <span className="text-[11px] text-ink-400 ml-auto">
              for {agency.name}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 sm:px-8 py-8 sm:py-12 space-y-8">
        {/* Header */}
        <div>
          <div className="eyebrow mb-3">
            Deal confirmation · {formatShowDateFull(show.date)}
          </div>
          <h1
            className="font-display text-[28px] sm:text-[36px] font-medium text-ink-900 leading-tight"
            style={{ letterSpacing: "-0.02em", fontOpticalSizing: "auto" }}
          >
            {artist?.name ?? "Unknown artist"}
          </h1>
          <p className="text-[13.5px] text-ink-600 mt-3 leading-relaxed">
            {greeting} — here&apos;s how {venueName} has read your deal{" "}
            {deal.agentEmailText ? "email" : "(based on Mariana's notes)"}.
            Confirm the items that look right, flag anything that doesn&apos;t.
          </p>
        </div>

        {!extraction ? (
          <NoExtractionState />
        ) : (
          <AgentReviewContent
            deal={deal}
            extraction={extraction}
            token={token}
            agentEmailPresent={!!deal.agentEmailText}
            alreadyConfirmed={!!deal.agentConfirmedAt}
          />
        )}
      </main>
    </div>
  );
}

// =========================================================================
// Main agent content
// =========================================================================

function AgentReviewContent({
  deal,
  extraction,
  token,
  agentEmailPresent,
  alreadyConfirmed,
}: {
  deal: Deal;
  extraction: ExtractionOutput;
  token: string;
  agentEmailPresent: boolean;
  alreadyConfirmed: boolean;
}) {
  const { extracted } = extraction;
  const bonuses = (extracted.bonuses ?? []).filter(isPayableBonus);
  const ratchets = extracted.ratchets ?? [];
  const walkoutPots = extracted.walkout_pots ?? [];
  const plannedRecoups = extracted.planned_recoups ?? [];
  const ambiguityFlags = extraction.ambiguity_flags ?? [];

  return (
    <div className="space-y-8">
      {/* The basics — clean per-item layout */}
      <section className="space-y-1">
        <SectionHeader label="The basics" />
        <div className="rounded-xl border border-ink-200/80 bg-white divide-y divide-ink-100">
          {extracted.deal_kind && (
            <RestatedItem
              token={token}
              fieldPath="deal_kind"
              label="Deal type"
              value={formatDealKind(extracted.deal_kind)}
              source={extraction.source_spans?.deal_kind}
              sourceFrom={agentEmailPresent ? "your email" : "Mariana's notes"}
            />
          )}
          {extracted.guarantee_amount != null && (
            <RestatedItem
              token={token}
              fieldPath="guarantee_amount"
              label="Guarantee"
              value={formatMoney(extracted.guarantee_amount)}
              source={extraction.source_spans?.guarantee_amount}
              sourceFrom={agentEmailPresent ? "your email" : "Mariana's notes"}
            />
          )}
          {extracted.percentage != null && (
            <RestatedItem
              token={token}
              fieldPath="percentage"
              label={
                extracted.deal_kind === "vs"
                  ? `vs ${(extracted.percentage * 100).toFixed(0)}% of ${extracted.percentage_basis ?? "?"}`
                  : `${(extracted.percentage * 100).toFixed(0)}% of ${extracted.percentage_basis ?? "?"}`
              }
              value={extracted.deal_kind === "vs" ? "whichever greater" : ""}
              source={extraction.source_spans?.percentage}
              sourceFrom={agentEmailPresent ? "your email" : "Mariana's notes"}
            />
          )}
          {extracted.expense_cap != null && (
            <RestatedItem
              token={token}
              fieldPath="expense_cap"
              label="Expense cap"
              value={formatMoney(extracted.expense_cap)}
              source={extraction.source_spans?.expense_cap}
              sourceFrom={agentEmailPresent ? "your email" : "Mariana's notes"}
            />
          )}
          {extracted.hospitality_cap != null && (
            <RestatedItem
              token={token}
              fieldPath="hospitality_cap"
              label="Hospitality cap"
              value={formatMoney(extracted.hospitality_cap)}
              source={extraction.source_spans?.hospitality_cap}
              sourceFrom={agentEmailPresent ? "your email" : "Mariana's notes"}
            />
          )}
        </div>
      </section>

      {/* Bonuses */}
      {bonuses.length > 0 && (
        <section className="space-y-1">
          <SectionHeader label="Bonuses" />
          <div className="rounded-xl border border-ink-200/80 bg-white divide-y divide-ink-100">
            {bonuses.map((b, i) => (
              <RestatedItem
                key={i}
                token={token}
                fieldPath={`bonus_${i}`}
                label={`+${formatMoney(b.amount)}`}
                value={b.label}
              />
            ))}
          </div>
        </section>
      )}

      {/* Ratchets / walkout pots — structurally complex */}
      {(ratchets.length > 0 || walkoutPots.length > 0) && (
        <section className="space-y-1">
          <SectionHeader label="Structure" />
          <div className="rounded-xl border border-amber-200/60 bg-amber-50/30 divide-y divide-amber-100">
            {ratchets.map((r, i) => (
              <RestatedItem
                key={`r${i}`}
                token={token}
                fieldPath={`ratchet_${i}`}
                label="Tier ratchet"
                value={`${(r.from_pct * 100).toFixed(0)}% → ${(r.to_pct * 100).toFixed(0)}% over ${(r.threshold * 100).toFixed(0)}% ${r.trigger.replace("_", " ")}`}
              />
            ))}
            {walkoutPots.map((w, i) => (
              <RestatedItem
                key={`w${i}`}
                token={token}
                fieldPath={`walkout_${i}`}
                label="Walkout pot"
                value={`${(w.percent * 100).toFixed(0)}% of ${w.basis} above ${formatMoney(w.threshold)}`}
              />
            ))}
          </div>
        </section>
      )}

      {/* Planned recoups */}
      {plannedRecoups.length > 0 && (
        <section className="space-y-1">
          <SectionHeader label="Planned recoups" tone="amber" />
          <div className="rounded-xl border border-amber-200/60 bg-amber-50/30 divide-y divide-amber-100">
            {plannedRecoups.map((r, i) => (
              <RestatedItem
                key={i}
                token={token}
                fieldPath={`recoup_${i}`}
                label={RECOUP_LABELS[r.category] ?? r.category}
                value={
                  <span>
                    <span className="font-mono tabular mr-2">
                      {formatMoney(r.amount)}
                    </span>
                    <span className="text-ink-500">{r.description}</span>
                    {r.basis === "unspecified" && (
                      <PlainBadge variant="rose" className="ml-2">
                        basis ambiguous
                      </PlainBadge>
                    )}
                  </span>
                }
              />
            ))}
          </div>
        </section>
      )}

      {/* Ambiguity flags — needs explicit input */}
      {ambiguityFlags.length > 0 && (
        <section className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-rose-700" />
            <h2 className="text-[15px] font-semibold text-rose-900">
              Needs your input
            </h2>
          </div>
          <p className="text-[12.5px] text-ink-600 leading-relaxed max-w-prose">
            These clauses could be read more than one way. Pick the
            interpretation you intended, or write your own.
          </p>
          {ambiguityFlags.map((flag, i) => (
            <AmbiguityCard
              key={i}
              token={token}
              flag={flag}
              flagIndex={i}
              agentEmailPresent={agentEmailPresent}
            />
          ))}
        </section>
      )}

      {/* Confirm all */}
      <div className="pt-4 border-t border-ink-100">
        <ConfirmAllButton token={token} alreadyConfirmed={alreadyConfirmed} />
        <p className="text-[11.5px] text-ink-400 mt-2">
          Confirming sends a notification to Mariana that you&apos;ve reviewed
          the deal. You can still flag individual items above.
        </p>
      </div>
    </div>
  );
}

// =========================================================================
// Components
// =========================================================================

function SectionHeader({
  label,
  tone = "default",
}: {
  label: string;
  tone?: "default" | "amber" | "rose";
}) {
  const color =
    tone === "amber"
      ? "text-amber-800"
      : tone === "rose"
        ? "text-rose-800"
        : "text-ink-500";
  return (
    <div className={`eyebrow text-[10px] ${color}`}>{label}</div>
  );
}

function RestatedItem({
  token,
  fieldPath,
  label,
  value,
  source,
  sourceFrom,
}: {
  token: string;
  fieldPath: string;
  label: string;
  value: React.ReactNode;
  source?: string;
  sourceFrom?: string;
}) {
  return (
    <div className="px-4 sm:px-5 py-3.5 flex items-start gap-4">
      <div className="flex-1 min-w-0">
        <div className="text-[12.5px] text-ink-500 mb-1">{label}</div>
        <div className="text-[14px] text-ink-900 leading-snug">{value}</div>
        {source && sourceFrom && (
          <div className="text-[11px] text-ink-400 mt-1.5 leading-relaxed italic flex items-start gap-1.5">
            <span className="text-[9.5px] mt-0.5 not-italic">↳</span>
            from {sourceFrom}: <span className="not-italic font-mono">&ldquo;{source}&rdquo;</span>
          </div>
        )}
      </div>
      <div className="shrink-0 pt-1">
        <ItemActions token={token} fieldPath={fieldPath} />
      </div>
    </div>
  );
}

function AmbiguityCard({
  token,
  flag,
  flagIndex,
  agentEmailPresent,
}: {
  token: string;
  flag: AmbiguityFlag;
  flagIndex: number;
  agentEmailPresent: boolean;
}) {
  // Defensive: LLM occasionally emits a flag with no readings. Skip rather
  // than crash — the agent shouldn't see a partial card.
  const readings = flag.readings ?? [];
  if (readings.length === 0) return null;

  const sourceLabel =
    flag.source === "email" ? "your email" : "Mariana's notes";
  // If the LLM said the source was email but we don't have one, soften the label
  const safeSourceLabel =
    flag.source === "email" && !agentEmailPresent
      ? "Mariana's notes (the email wasn't shared with us)"
      : sourceLabel;
  return (
    <div className="rounded-xl border border-rose-200/70 bg-rose-50/30 p-4 sm:p-5 space-y-3">
      <div>
        <div className="text-[11px] text-ink-500 mb-1.5 inline-flex items-center gap-1.5">
          {agentEmailPresent && flag.source === "email" ? (
            <Mail className="h-3 w-3" />
          ) : (
            <FileText className="h-3 w-3" />
          )}
          From {safeSourceLabel}:
        </div>
        <blockquote className="text-[14px] sm:text-[14.5px] text-ink-900 font-mono leading-snug border-l-2 border-rose-300 pl-3 italic">
          &ldquo;{flag.clause}&rdquo;
        </blockquote>
      </div>
      <div>
        <div className="text-[12.5px] text-ink-700 mb-2">
          We read this {readings.length === 1 ? "one way" : `${readings.length === 2 ? "two" : readings.length} ways`}:
        </div>
        <AmbiguityResolver
          token={token}
          flagIndex={flagIndex}
          readings={readings.map((r) => ({
            interpretation: formatReading(r),
          }))}
        />
      </div>
    </div>
  );
}

// =========================================================================
// Empty states
// =========================================================================

function InvalidTokenState({
  reason,
}: {
  reason: "not_found" | "expired" | "revoked";
}) {
  const msg: Record<typeof reason, { title: string; body: string }> = {
    not_found: {
      title: "Link not found",
      body:
        "This confirmation link doesn't exist or has been deleted. Ask the venue for a new one.",
    },
    expired: {
      title: "Link expired",
      body:
        "This confirmation link is no longer active. Ask the venue to send a fresh one.",
    },
    revoked: {
      title: "Link revoked",
      body:
        "This confirmation link has been revoked, probably because the deal was updated. Ask the venue for the new link.",
    },
  };
  return (
    <div className="min-h-screen bg-canvas flex items-center justify-center px-5">
      <div className="max-w-md text-center space-y-4">
        <h1 className="font-display text-[28px] font-medium text-ink-900">
          {msg[reason].title}
        </h1>
        <p className="text-[13.5px] text-ink-500 leading-relaxed">
          {msg[reason].body}
        </p>
      </div>
    </div>
  );
}

function NoExtractionState() {
  return (
    <div className="rounded-xl border border-ink-200/80 bg-white p-6 text-center text-[13px] text-ink-500">
      The venue hasn&apos;t completed the deal review yet. You&apos;ll get an
      update once they share their reading.
    </div>
  );
}

// =========================================================================
// Helpers
// =========================================================================

function formatDealKind(kind: string): string {
  const labels: Record<string, string> = {
    flat: "Flat guarantee",
    percentage_of_gross: "Percentage of gross",
    percentage_of_net: "Percentage of net",
    vs: "Guarantee vs percentage",
    door: "Door deal",
  };
  return labels[kind] ?? kind;
}

function formatReading(r: AmbiguityFlag["readings"][number]): string {
  let text = r.interpretation;
  if (r.implied_payout_change_usd != null) {
    const sign = r.implied_payout_change_usd >= 0 ? "+" : "−";
    text += ` (${sign}${formatMoney(Math.abs(r.implied_payout_change_usd))} to artist)`;
  }
  return text;
}
