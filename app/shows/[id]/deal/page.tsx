import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  AlertTriangle,
  AlertCircle,
  Clock,
  FileText,
  Mail,
  Sparkles,
  Info,
} from "lucide-react";
import { getShowById } from "@/lib/queries";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { PlainBadge } from "@/components/ui/badge";
import { getExtraction } from "@/lib/extraction";
import {
  formatMoney,
  formatShowDateFull,
} from "@/lib/format";
import type {
  Bonus,
  ExtractionOutput,
  AmbiguityFlag,
  Discrepancy,
  PlannedRecoup,
} from "@/db/schema";
import { DealReviewActions } from "./DealReviewActions";

const RECOUP_LABELS: Record<PlannedRecoup["category"], string> = {
  marketing: "Marketing",
  hospitality_overage: "Hospitality overage",
  production_overage: "Production overage",
  prior_advance: "Prior advance",
  damages: "Damages",
};

/**
 * Short relative time string ("just now", "5m ago", "2h ago", "3d ago").
 * Module-scope to avoid re-allocating per render.
 */
function fmtRelative(d: Date | string | null | undefined): string {
  if (!d) return "—";
  const date = typeof d === "string" ? new Date(d) : d;
  const ms = Date.now() - date.getTime();
  if (ms < 60_000) return "just now";
  if (ms < 3_600_000) return `${Math.floor(ms / 60_000)}m ago`;
  if (ms < 86_400_000) return `${Math.floor(ms / 3_600_000)}h ago`;
  return `${Math.floor(ms / 86_400_000)}d ago`;
}

/**
 * Type predicate to narrow Bonus to the variants that have an `amount`
 * field (everything except tier_ratchet, which uses `tiers` instead).
 * Lets `.map((b) => b.amount)` typecheck after filtering.
 */
type PayableBonus = Exclude<Bonus, { type: "tier_ratchet" }>;
function isPayableBonus(b: Bonus): b is PayableBonus {
  return b.type !== "tier_ratchet";
}

export default async function DealReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data = await getShowById(id);
  if (!data) notFound();

  const { show, artist, agent, agency, deal } = data;
  if (!deal) {
    return (
      <div className="px-12 py-10 max-w-4xl">
        <BackLink showId={show.id} />
        <h1 className="font-display text-[32px] font-medium text-ink-900 mb-2">
          No deal entered
        </h1>
        <p className="text-[13.5px] text-ink-500">
          Enter a deal for this show before reviewing.
        </p>
      </div>
    );
  }

  const extractionResult = getExtraction(deal);
  const extraction: ExtractionOutput | null =
    extractionResult.ok ? extractionResult.output : null;

  return (
    <div className="px-12 py-10 max-w-7xl">
      <BackLink showId={show.id} />

      {/* Page header */}
      <div className="mb-8">
        <div className="eyebrow mb-3">
          Deal review · {formatShowDateFull(show.date)}
        </div>
        <h1
          className="font-display text-[40px] font-medium text-ink-900 leading-[1.05]"
          style={{ letterSpacing: "-0.02em", fontOpticalSizing: "auto" }}
        >
          {artist?.name ?? "Unknown artist"}
        </h1>
        <p className="text-[13.5px] text-ink-500 mt-2 max-w-2xl leading-relaxed">
          Review how the deal terms have been read. Confirm to share with
          the agent, or flag any clause that needs clarification first.
        </p>
      </div>

      {/* Agent context banner — only when preferences_notes exist */}
      {agent?.preferencesNotes && (
        <AgentContextBanner
          agentName={agent.name}
          agencyName={agency?.name ?? "Independent"}
          note={agent.preferencesNotes}
        />
      )}

      {/* Status row */}
      <StatusRow
        hasExtraction={!!extraction}
        marianaConfirmedAt={deal.marianaConfirmedAt}
        agentConfirmedAt={deal.agentConfirmedAt}
        extractionModel={extraction?.model}
        extractionGeneratedAt={extraction?.generated_at}
      />

      {/* Action bar */}
      <div className="mb-8">
        <DealReviewActions
          dealId={deal.id}
          showId={show.id}
          hasExtraction={!!extraction}
          isMarianaConfirmed={!!deal.marianaConfirmedAt}
          currentEmailText={deal.agentEmailText}
        />
      </div>

      {extraction ? (
        <ExtractionView
          agentEmail={deal.agentEmailText}
          notes={deal.dealNotesFreetext ?? ""}
          extraction={extraction}
        />
      ) : (
        <EmptyExtractionState
          notes={deal.dealNotesFreetext ?? ""}
          hadMalformedJson={!extractionResult.ok && extractionResult.reason === "malformed"}
        />
      )}
    </div>
  );
}

// ===========================================================================
// Components
// ===========================================================================

function BackLink({ showId }: { showId: string }) {
  return (
    <Link
      href={`/shows/${showId}`}
      className="inline-flex items-center gap-1 text-[12px] text-ink-400 hover:text-ink-900 mb-8 transition-colors"
    >
      <ArrowLeft className="h-3.5 w-3.5" /> Back to show
    </Link>
  );
}

function AgentContextBanner({
  agentName,
  agencyName,
  note,
}: {
  agentName: string;
  agencyName: string;
  note: string;
}) {
  return (
    <div className="rounded-xl border border-amber-200/60 bg-gradient-to-r from-amber-50/60 to-canvas p-5 flex gap-4 mb-6">
      <div className="w-9 h-9 rounded-lg bg-white ring-1 ring-amber-200/50 flex items-center justify-center shrink-0">
        <Info className="h-4 w-4 text-amber-700" />
      </div>
      <div className="flex-1">
        <div className="eyebrow text-[10px] text-amber-800 mb-1.5">
          Your notes on {agentName} · {agencyName}
        </div>
        <p className="text-[13.5px] text-ink-800 leading-relaxed italic">
          &ldquo;{note}&rdquo;
        </p>
      </div>
    </div>
  );
}

function StatusRow({
  hasExtraction,
  marianaConfirmedAt,
  agentConfirmedAt,
  extractionModel,
  extractionGeneratedAt,
}: {
  hasExtraction: boolean;
  marianaConfirmedAt: Date | null;
  agentConfirmedAt: Date | null;
  extractionModel?: string;
  extractionGeneratedAt?: string;
}) {
  return (
    <div className="flex items-center gap-6 pt-4 pb-6 border-y border-ink-100 mb-8">
      <StatusDot
        active={hasExtraction}
        label="Extracted"
        detail={
          hasExtraction
            ? `${fmtRelative(extractionGeneratedAt)}${extractionModel ? ` · ${extractionModel}` : ""}`
            : "Not yet"
        }
      />
      <StatusDot
        active={!!marianaConfirmedAt}
        label="Mariana confirmed"
        detail={marianaConfirmedAt ? fmtRelative(marianaConfirmedAt) : "Pending review"}
      />
      <StatusDot
        active={!!agentConfirmedAt}
        label="Agent confirmed"
        detail={agentConfirmedAt ? fmtRelative(agentConfirmedAt) : "Not sent yet"}
      />
    </div>
  );
}

function StatusDot({
  active,
  label,
  detail,
}: {
  active: boolean;
  label: string;
  detail: string;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <div
        className={`w-2 h-2 rounded-full ${
          active ? "bg-brand-700" : "bg-ink-300"
        }`}
      />
      <div>
        <div className="text-[12.5px] font-medium text-ink-900">{label}</div>
        <div className="text-[11px] text-ink-500 font-mono tabular">{detail}</div>
      </div>
    </div>
  );
}

function EmptyExtractionState({
  notes,
  hadMalformedJson,
}: {
  notes: string;
  hadMalformedJson: boolean;
}) {
  return (
    <div className="space-y-4">
      {hadMalformedJson && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900">
          The stored extraction is malformed. Click <strong>Re-extract</strong> above to regenerate.
        </div>
      )}
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Mariana&apos;s notes</CardTitle>
            <CardDescription>
              The source the extractor will read. Click <strong>Extract deal</strong> above to populate the structured representation.
            </CardDescription>
          </div>
          <FileText className="h-4 w-4 text-ink-400 shrink-0" />
        </CardHeader>
        <CardContent>
          <pre className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-800 font-mono">
            {notes || "(no notes entered)"}
          </pre>
        </CardContent>
      </Card>
    </div>
  );
}

function ExtractionView({
  agentEmail,
  notes,
  extraction,
}: {
  agentEmail: string | null;
  notes: string;
  extraction: ExtractionOutput;
}) {
  return (
    <div className="space-y-6">
      {/* Two-column source ↔ extracted */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <SourceColumn agentEmail={agentEmail} notes={notes} extraction={extraction} />
        <ExtractedColumn extraction={extraction} />
      </div>

      {/* Ambiguity flags */}
      {extraction.ambiguity_flags.length > 0 && (
        <AmbiguitySection flags={extraction.ambiguity_flags} />
      )}

      {/* Discrepancies */}
      {extraction.discrepancies.length > 0 && (
        <DiscrepancySection discrepancies={extraction.discrepancies} />
      )}

      {/* Low-confidence */}
      {extraction.low_confidence.length > 0 && (
        <LowConfidenceSection items={extraction.low_confidence} />
      )}
    </div>
  );
}

function SourceColumn({
  agentEmail,
  notes,
  extraction,
}: {
  agentEmail: string | null;
  notes: string;
  extraction: ExtractionOutput;
}) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Source</CardTitle>
          <CardDescription>
            {agentEmail ? "Agent email + Mariana's notes" : "Mariana's notes only"} · highlighted spans show what each extracted field came from.
          </CardDescription>
        </div>
        {agentEmail ? (
          <Mail className="h-4 w-4 text-brand-700 shrink-0" />
        ) : (
          <FileText className="h-4 w-4 text-ink-400 shrink-0" />
        )}
      </CardHeader>
      <CardContent className="space-y-5">
        {agentEmail && (
          <div>
            <div className="eyebrow text-[10px] text-ink-500 mb-2">
              From agent email
            </div>
            <SourceText
              text={agentEmail}
              highlights={Object.values(extraction.source_spans ?? {})}
            />
          </div>
        )}
        <div>
          <div className="eyebrow text-[10px] text-ink-500 mb-2">
            Mariana&apos;s notes
          </div>
          <SourceText
            text={notes}
            highlights={Object.values(extraction.source_spans ?? {})}
          />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Render text with substrings from `highlights` wrapped in <mark>. Highlights
 * are exact-substring matches; we render the longest matches first so shorter
 * ones don't break a larger highlight.
 *
 * KNOWN LIMITATION: source_spans in ExtractionOutput is a string→string map
 * (field path → quoted source span) without a `source` flag, so we can't
 * tell which spans came from the email vs the notes. Both columns receive
 * all spans, which produces false-positive highlights when a substring
 * happens to appear in the non-source column (e.g., a $-amount that shows
 * up in both). Acceptable for the demo; a v2 should add `{ text, source }`
 * tuples (matching AmbiguityFlag.source) so each column highlights only
 * its own spans.
 */
function SourceText({
  text,
  highlights,
}: {
  text: string;
  highlights: string[];
}) {
  if (!text) {
    return <p className="text-[12px] text-ink-400 italic">(empty)</p>;
  }

  const segments = highlightSegments(text, highlights);

  return (
    <p className="text-[13px] leading-[1.7] text-ink-800 font-mono whitespace-pre-wrap">
      {segments.map((seg, i) =>
        seg.highlight ? (
          <mark
            key={i}
            className="bg-brand-100/80 text-brand-900 rounded-sm px-0.5 -mx-0.5"
          >
            {seg.text}
          </mark>
        ) : (
          <span key={i}>{seg.text}</span>
        ),
      )}
    </p>
  );
}

/** Split text into alternating highlighted/un-highlighted segments. */
function highlightSegments(
  text: string,
  highlights: string[],
): Array<{ text: string; highlight: boolean }> {
  const valid = highlights
    .filter((h): h is string => typeof h === "string" && h.length > 3)
    .sort((a, b) => b.length - a.length); // longest first

  if (valid.length === 0) return [{ text, highlight: false }];

  type Match = { start: number; end: number };
  const matches: Match[] = [];
  for (const h of valid) {
    let from = 0;
    while (true) {
      const idx = text.indexOf(h, from);
      if (idx === -1) break;
      // Skip if this range overlaps an existing match
      const overlaps = matches.some(
        (m) => idx < m.end && idx + h.length > m.start,
      );
      if (!overlaps) matches.push({ start: idx, end: idx + h.length });
      from = idx + h.length;
    }
  }
  matches.sort((a, b) => a.start - b.start);

  if (matches.length === 0) return [{ text, highlight: false }];

  const out: Array<{ text: string; highlight: boolean }> = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) {
      out.push({ text: text.slice(cursor, m.start), highlight: false });
    }
    out.push({ text: text.slice(m.start, m.end), highlight: true });
    cursor = m.end;
  }
  if (cursor < text.length) {
    out.push({ text: text.slice(cursor), highlight: false });
  }
  return out;
}

function ExtractedColumn({ extraction }: { extraction: ExtractionOutput }) {
  const { extracted, confidence_per_field } = extraction;

  // Defensive defaults — the shape guard in lib/extraction.ts verifies the
  // top-level structure, but the LLM can omit nested arrays. We coerce to
  // empty arrays so the renderer never crashes on `.length` / `.map`.
  const bonuses = extracted.bonuses ?? [];
  const ratchets = extracted.ratchets ?? [];
  const walkoutPots = extracted.walkout_pots ?? [];
  const plannedRecoups = extracted.planned_recoups ?? [];
  const payableBonuses = bonuses.filter(isPayableBonus);

  return (
    <Card accent="brand">
      <CardHeader>
        <div>
          <CardTitle>Structured deal</CardTitle>
          <CardDescription>
            Extracted by {extraction.model ?? "LLM"}. Hover any value to see
            its source in the prose.
          </CardDescription>
        </div>
        <Sparkles className="h-4 w-4 text-brand-700 shrink-0" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-x-6 gap-y-4">
          <FieldWithConfidence
            label="Deal kind"
            value={
              <span className="capitalize">
                {extracted.deal_kind.replace(/_/g, " ")}
              </span>
            }
            confidence={confidence_per_field?.deal_kind}
          />
          {extracted.guarantee_amount != null && (
            <FieldWithConfidence
              label="Guarantee"
              value={
                <span className="font-mono tabular">
                  {formatMoney(extracted.guarantee_amount)}
                </span>
              }
              confidence={confidence_per_field?.guarantee_amount}
            />
          )}
          {extracted.percentage != null && (
            <FieldWithConfidence
              label="Percentage"
              value={
                <span className="font-mono tabular">
                  {(extracted.percentage * 100).toFixed(0)}%
                  {extracted.percentage_basis && (
                    <span className="text-ink-500 ml-1.5 text-[11.5px]">
                      of {extracted.percentage_basis}
                    </span>
                  )}
                </span>
              }
              confidence={confidence_per_field?.percentage}
            />
          )}
          {extracted.expense_cap != null && (
            <FieldWithConfidence
              label="Expense cap"
              value={
                <span className="font-mono tabular">
                  {formatMoney(extracted.expense_cap)}
                </span>
              }
              confidence={confidence_per_field?.expense_cap}
            />
          )}
          {extracted.hospitality_cap != null && (
            <FieldWithConfidence
              label="Hospitality cap"
              value={
                <span className="font-mono tabular">
                  {formatMoney(extracted.hospitality_cap)}
                </span>
              }
              confidence={confidence_per_field?.hospitality_cap}
            />
          )}
        </div>

        {payableBonuses.length > 0 && (
          <SubSection title="Bonuses">
            <ul className="space-y-1.5">
              {payableBonuses.map((b, i) => (
                <li
                  key={i}
                  className="text-[12.5px] text-ink-800 font-mono tabular"
                >
                  <span className="text-ink-500 mr-2">+</span>
                  {formatMoney(b.amount)} — {b.label}
                </li>
              ))}
            </ul>
          </SubSection>
        )}

        {ratchets.length > 0 && (
          <SubSection title="Tier ratchets" amber>
            <ul className="space-y-1.5">
              {ratchets.map((r, i) => (
                <li
                  key={i}
                  className="text-[12.5px] text-ink-800 font-mono tabular"
                >
                  {(r.from_pct * 100).toFixed(0)}% →{" "}
                  {(r.to_pct * 100).toFixed(0)}% over{" "}
                  {(r.threshold * 100).toFixed(0)}% {r.trigger.replace("_", " ")}
                </li>
              ))}
            </ul>
          </SubSection>
        )}

        {walkoutPots.length > 0 && (
          <SubSection title="Walkout pot" amber>
            <ul className="space-y-1.5">
              {walkoutPots.map((w, i) => (
                <li
                  key={i}
                  className="text-[12.5px] text-ink-800 font-mono tabular"
                >
                  {(w.percent * 100).toFixed(0)}% of {w.basis} above{" "}
                  {formatMoney(w.threshold)}
                </li>
              ))}
            </ul>
          </SubSection>
        )}

        {plannedRecoups.length > 0 && (
          <SubSection title="Planned recoups" rose>
            <ul className="space-y-2">
              {plannedRecoups.map((r, i) => (
                <li key={i} className="text-[12.5px] text-ink-800">
                  <div className="flex items-baseline gap-2">
                    <span className="font-mono tabular">
                      {formatMoney(r.amount)}
                    </span>
                    <span className="text-ink-500">
                      {RECOUP_LABELS[r.category] ?? r.category}
                    </span>
                    {r.basis === "unspecified" && (
                      <PlainBadge variant="rose">basis ambiguous</PlainBadge>
                    )}
                  </div>
                  <div className="text-[11.5px] text-ink-500 mt-0.5 italic">
                    {r.description}
                  </div>
                </li>
              ))}
            </ul>
          </SubSection>
        )}
      </CardContent>
    </Card>
  );
}

function FieldWithConfidence({
  label,
  value,
  confidence,
}: {
  label: string;
  value: React.ReactNode;
  confidence?: number;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between mb-1">
        <div className="eyebrow text-[10px] text-ink-500">{label}</div>
        {confidence != null && (
          <span
            className={`text-[10px] font-mono tabular ${
              confidence >= 80
                ? "text-brand-700"
                : confidence >= 50
                  ? "text-amber-700"
                  : "text-rose-700"
            }`}
            title={`${confidence}% confidence`}
          >
            {confidence}%
          </span>
        )}
      </div>
      <div className="text-[13.5px] text-ink-900">{value}</div>
    </div>
  );
}

function SubSection({
  title,
  children,
  amber,
  rose,
}: {
  title: string;
  children: React.ReactNode;
  amber?: boolean;
  rose?: boolean;
}) {
  const color = rose
    ? "text-rose-800"
    : amber
      ? "text-amber-800"
      : "text-ink-700";
  return (
    <div className="pt-3 border-t border-ink-100">
      <div className={`eyebrow text-[10px] ${color} mb-2`}>{title}</div>
      {children}
    </div>
  );
}

function AmbiguitySection({ flags }: { flags: AmbiguityFlag[] }) {
  return (
    <Card accent="rose">
      <CardHeader>
        <div>
          <CardTitle className="text-rose-900">
            Ambiguity — resolve with agent
          </CardTitle>
          <CardDescription>
            These clauses could be read more than one way. Each reading has a
            different artist payout.
          </CardDescription>
        </div>
        <AlertTriangle className="h-4 w-4 text-rose-700 shrink-0" />
      </CardHeader>
      <CardContent className="space-y-6">
        {flags.map((flag, i) => (
          <div
            key={i}
            className="space-y-3"
          >
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <SeverityBadge severity={flag.severity} />
                <span className="text-[10px] uppercase tracking-wider text-ink-500">
                  from {flag.source}
                </span>
              </div>
              <blockquote className="text-[13px] text-ink-900 font-mono leading-relaxed border-l-2 border-rose-300 pl-3 italic">
                &ldquo;{flag.clause}&rdquo;
              </blockquote>
            </div>
            <div className="space-y-2 pl-3">
              {flag.readings.map((reading, j) => (
                <div
                  key={j}
                  className="flex items-start gap-3 text-[12.5px] text-ink-700"
                >
                  <span className="mt-1 w-1.5 h-1.5 rounded-full bg-rose-400 shrink-0" />
                  <div className="flex-1">
                    <div>{reading.interpretation}</div>
                    {(reading.implied_payout_change_usd != null ||
                      reading.implied_payout_change_pct != null) && (
                      <div className="text-[11.5px] text-ink-500 mt-0.5 font-mono tabular">
                        {reading.implied_payout_change_usd != null &&
                          `→ ${reading.implied_payout_change_usd > 0 ? "+" : ""}${formatMoney(reading.implied_payout_change_usd)}`}
                        {reading.implied_payout_change_pct != null &&
                          ` (${reading.implied_payout_change_pct > 0 ? "+" : ""}${reading.implied_payout_change_pct}%)`}{" "}
                        to artist
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function DiscrepancySection({
  discrepancies,
}: {
  discrepancies: Discrepancy[];
}) {
  return (
    <Card accent="amber">
      <CardHeader>
        <div>
          <CardTitle className="text-amber-900">
            Discrepancies — email vs notes
          </CardTitle>
          <CardDescription>
            What the agent wrote and what Mariana entered disagree. Resolve
            before sending to agent.
          </CardDescription>
        </div>
        <AlertCircle className="h-4 w-4 text-amber-700 shrink-0" />
      </CardHeader>
      <CardContent className="space-y-4">
        {discrepancies.map((d, i) => (
          <div key={i} className="space-y-1.5">
            <div className="flex items-center gap-2">
              <SeverityBadge severity={d.severity} />
              <code className="text-[11.5px] font-mono text-ink-700 bg-ink-100/80 px-1.5 py-0.5 rounded">
                {d.field}
              </code>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 ml-1">
              <div className="text-[12.5px]">
                <span className="text-ink-500 text-[10px] uppercase tracking-wider">
                  Email says
                </span>
                <div className="text-ink-800 font-mono mt-0.5">{d.email_says}</div>
              </div>
              <div className="text-[12.5px]">
                <span className="text-ink-500 text-[10px] uppercase tracking-wider">
                  Notes say
                </span>
                <div className="text-ink-800 font-mono mt-0.5">{d.notes_says}</div>
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function LowConfidenceSection({
  items,
}: {
  items: ExtractionOutput["low_confidence"];
}) {
  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle>Low confidence fields</CardTitle>
          <CardDescription>
            The extractor couldn&apos;t confidently determine these from the
            source. Fill in manually if you need them downstream.
          </CardDescription>
        </div>
        <Clock className="h-4 w-4 text-ink-400 shrink-0" />
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="text-[12.5px] text-ink-800">
              <code className="font-mono text-[11px] text-ink-700 bg-ink-100/80 px-1.5 py-0.5 rounded mr-2">
                {item.field}
              </code>
              <span className="text-ink-500 italic">{item.reason}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function SeverityBadge({ severity }: { severity: "low" | "medium" | "high" }) {
  const variant: "rose" | "amber" | "default" =
    severity === "high" ? "rose" : severity === "medium" ? "amber" : "default";
  return <PlainBadge variant={variant}>{severity}</PlainBadge>;
}
