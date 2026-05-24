import Link from "next/link";
import {
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  CalendarClock,
  Check,
  Info,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { getPreFlightShows, type PreFlightRow } from "@/lib/preFlightQueries";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { PlainBadge, DealTypeBadge } from "@/components/ui/badge";
import { formatShowDate } from "@/lib/format";
import type {
  SignalResult,
  SignalSeverity,
  SignalId,
} from "@/lib/preFlightSignals";

const PREFLIGHT_WINDOW_DAYS = 60;

export default async function PreFlightPage() {
  const today = new Date();
  const rows = await getPreFlightShows({
    today,
    daysAhead: PREFLIGHT_WINDOW_DAYS,
  });

  // Bucket by risk level for the visual summary at the top.
  const high = rows.filter((r) => r.signals.riskScore >= 5).length;
  const medium = rows.filter(
    (r) => r.signals.riskScore >= 2 && r.signals.riskScore < 5,
  ).length;
  const clean = rows.filter((r) => r.signals.riskScore === 0).length;
  const lowOnly = rows.length - high - medium - clean;

  return (
    <div className="px-12 py-10 max-w-7xl">
      {/* Header */}
      <div className="mb-10">
        <div className="eyebrow mb-3">
          Wednesday pre-flight · {PREFLIGHT_WINDOW_DAYS}-day horizon
        </div>
        <h1
          className="font-display text-[48px] font-medium text-ink-900 leading-[1.05]"
          style={{ letterSpacing: "-0.02em", fontOpticalSizing: "auto" }}
        >
          What to fix before show
        </h1>
        <p className="text-[14px] text-ink-500 mt-3 max-w-2xl leading-relaxed">
          Upcoming shows ranked by settlement-risk signal. The dashboard
          only shows past disputes; this view surfaces the ones that
          haven&apos;t happened yet — while there&apos;s still time to
          fix them.
        </p>
      </div>

      {/* Risk summary strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-px bg-ink-200/40 rounded-xl overflow-hidden mb-10">
        <SummaryStat label="High risk" value={high} accent="rose" />
        <SummaryStat label="Medium risk" value={medium} accent="amber" />
        <SummaryStat label="Low-signal only" value={lowOnly} accent="sky" />
        <SummaryStat label="Clear" value={clean} accent="brand" />
      </div>

      {rows.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-4">
          {rows.map((row) => (
            <PreFlightCard key={row.showId} row={row} />
          ))}
        </div>
      )}

      <Footer />
    </div>
  );
}

// ===========================================================================
// Components
// ===========================================================================

type SummaryAccent = "rose" | "amber" | "sky" | "brand";

const SUMMARY_COLORS: Record<SummaryAccent, string> = {
  rose: "text-rose-700",
  amber: "text-amber-700",
  sky: "text-sky-700",
  brand: "text-brand-700",
};

function SummaryStat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent: SummaryAccent;
}) {
  return (
    <div className="bg-white px-6 py-5">
      <div
        className={`text-[36px] font-display font-medium leading-none ${SUMMARY_COLORS[accent]}`}
        style={{ letterSpacing: "-0.02em" }}
      >
        {value}
      </div>
      <div className="text-[11px] font-medium text-ink-500 uppercase tracking-[0.08em] mt-2">
        {label}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <Card>
      <CardContent className="text-center py-12">
        <div className="text-[14px] text-ink-500">
          No upcoming shows in the {PREFLIGHT_WINDOW_DAYS}-day window.
        </div>
      </CardContent>
    </Card>
  );
}

function PreFlightCard({ row }: { row: PreFlightRow }) {
  const tier = riskTier(row.signals.riskScore);
  const actionable = row.signals.signals.filter(
    (s) => s.id !== "ix_new_agent",
  );
  const informational = row.signals.signals.filter(
    (s) => s.id === "ix_new_agent",
  );

  return (
    <Card accent={tier === "high" ? "rose" : tier === "medium" ? "amber" : tier === "clear" ? "brand" : "sky"}>
      <CardHeader>
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-3 mb-1.5 flex-wrap">
            <CardTitle className="text-[15.5px]">{row.artistName}</CardTitle>
            <DealTypeBadge type={row.dealType} />
            {row.agencyName && (
              <span className="text-[11.5px] text-ink-500">
                {row.agencyName}
                {row.agentName ? ` · ${row.agentName}` : ""}
              </span>
            )}
          </div>
          <CardDescription className="flex items-center gap-2.5 text-[12.5px]">
            <CalendarClock className="h-3.5 w-3.5 text-ink-400" />
            <span>
              {formatShowDate(row.date)}
              <span className="text-ink-400 ml-1.5">
                · {row.daysUntilShow === 0
                  ? "today"
                  : row.daysUntilShow === 1
                    ? "tomorrow"
                    : `${row.daysUntilShow} days`}
              </span>
            </span>
            {row.signals.agentPosture === "elevated" && (
              <PlainBadge variant="rose">agent: pushes back</PlainBadge>
            )}
            {row.signals.agentPosture === "low" && (
              <PlainBadge variant="brand">agent: easygoing</PlainBadge>
            )}
          </CardDescription>
        </div>
        <RiskScoreBadge tier={tier} score={row.signals.riskScore} />
      </CardHeader>

      <CardContent className="space-y-3">
        {actionable.length === 0 && informational.length === 0 ? (
          <CleanShowMessage hasExtraction={row.hasExtraction} />
        ) : (
          <>
            {actionable.length > 0 && (
              <ul className="space-y-2">
                {actionable.map((s) => (
                  <SignalRow key={s.id} signal={s} />
                ))}
              </ul>
            )}
            {informational.length > 0 && (
              <div className="pt-3 border-t border-ink-100">
                <ul className="space-y-1.5">
                  {informational.map((s) => (
                    <li
                      key={s.id}
                      className="flex items-start gap-2 text-[12px] text-ink-500 italic"
                    >
                      <Info className="h-3.5 w-3.5 text-ink-400 mt-0.5 shrink-0" />
                      <span>{s.label} — {s.detail}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        )}

        <div className="flex items-center gap-3 pt-3 border-t border-ink-100/60 text-[11.5px]">
          <ConfirmationStatePill
            hasExtraction={row.hasExtraction}
            marianaConfirmedAt={row.marianaConfirmedAt}
            agentConfirmedAt={row.agentConfirmedAt}
          />
          <div className="ml-auto flex items-center gap-3">
            <Link
              href={`/shows/${row.showId}/deal`}
              className="text-brand-700 hover:text-brand-800 font-medium inline-flex items-center gap-1"
            >
              Review deal <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function SignalRow({ signal }: { signal: SignalResult }) {
  return (
    <li className="flex items-start gap-3">
      <SignalIcon id={signal.id} severity={signal.severity} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-[12.5px] font-medium text-ink-900">
            {signal.label}
          </span>
          <SeverityBadge severity={signal.severity} />
        </div>
        <div className="text-[11.5px] text-ink-600 mt-0.5 leading-relaxed">
          {signal.detail}
        </div>
      </div>
    </li>
  );
}

function SignalIcon({ id, severity }: { id: SignalId; severity: SignalSeverity }) {
  const color =
    severity === "high"
      ? "text-rose-600"
      : severity === "medium"
        ? "text-amber-600"
        : "text-sky-600";
  // Pick an icon hint per signal type
  if (id === "i_ambiguous")
    return <AlertTriangle className={`h-4 w-4 ${color} mt-0.5 shrink-0`} />;
  if (id === "iv_structure")
    return <ShieldAlert className={`h-4 w-4 ${color} mt-0.5 shrink-0`} />;
  if (id === "vi_not_confirmed")
    return <CalendarClock className={`h-4 w-4 ${color} mt-0.5 shrink-0`} />;
  if (id === "ii_recoup_history" || id === "iii_hosp_history")
    return <Sparkles className={`h-4 w-4 ${color} mt-0.5 shrink-0`} />;
  return <AlertCircle className={`h-4 w-4 ${color} mt-0.5 shrink-0`} />;
}

function SeverityBadge({ severity }: { severity: SignalSeverity }) {
  const variant: "rose" | "amber" | "default" =
    severity === "high" ? "rose" : severity === "medium" ? "amber" : "default";
  return <PlainBadge variant={variant}>{severity}</PlainBadge>;
}

function RiskScoreBadge({
  tier,
  score,
}: {
  tier: "high" | "medium" | "low" | "clear";
  score: number;
}) {
  if (tier === "clear") {
    return (
      <div className="inline-flex items-center gap-1.5 text-brand-700 text-[12px] font-medium shrink-0">
        <Check className="h-3.5 w-3.5" />
        clear
      </div>
    );
  }
  const colors = {
    high: "text-rose-700 bg-rose-50 ring-rose-200/80",
    medium: "text-amber-800 bg-amber-50 ring-amber-200/80",
    low: "text-sky-700 bg-sky-50 ring-sky-200/80",
  };
  return (
    <div
      className={`shrink-0 inline-flex items-center px-2.5 py-1 rounded-md text-[11px] font-medium ring-1 ring-inset ${colors[tier]}`}
    >
      risk {score}
    </div>
  );
}

function CleanShowMessage({ hasExtraction }: { hasExtraction: boolean }) {
  return (
    <div className="text-[12.5px] text-ink-500 flex items-center gap-2 py-1">
      <Check className="h-3.5 w-3.5 text-brand-700" />
      {hasExtraction
        ? "No risk signals firing. Deal is extracted and clean."
        : "No risk signals firing — but the deal hasn't been LLM-extracted yet, so coverage is limited."}
    </div>
  );
}

function ConfirmationStatePill({
  hasExtraction,
  marianaConfirmedAt,
  agentConfirmedAt,
}: {
  hasExtraction: boolean;
  marianaConfirmedAt: Date | null;
  agentConfirmedAt: Date | null;
}) {
  if (!hasExtraction) {
    return (
      <span className="text-ink-500 inline-flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-ink-300" /> not yet extracted
      </span>
    );
  }
  if (!marianaConfirmedAt) {
    return (
      <span className="text-ink-500 inline-flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-sky-500" /> awaiting your review
      </span>
    );
  }
  if (!agentConfirmedAt) {
    return (
      <span className="text-amber-700 inline-flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" /> agent unconfirmed
      </span>
    );
  }
  return (
    <span className="text-brand-700 inline-flex items-center gap-1.5">
      <span className="w-1.5 h-1.5 rounded-full bg-brand-700" /> fully confirmed
    </span>
  );
}

function Footer() {
  return (
    <div className="mt-12 text-[11px] text-ink-400 leading-relaxed max-w-2xl">
      Pre-flight reads the un-filtered show set (not the past-only view on{" "}
      <code className="font-mono">/reports</code>) so it can surface
      future-dated shows that haven&apos;t been settled yet. Signals are
      computed from the LLM-extracted deal, prior-settlement history,
      and the agent context note. Signal viii (marketing-expense
      heuristic) was dropped after stress-test for low discrimination
      power. See{" "}
      <code className="font-mono">notes/evidence.md</code> for the full
      analysis.
    </div>
  );
}

// ===========================================================================
// Helpers
// ===========================================================================

function riskTier(score: number): "high" | "medium" | "low" | "clear" {
  if (score === 0) return "clear";
  if (score >= 5) return "high";
  if (score >= 2) return "medium";
  return "low";
}
