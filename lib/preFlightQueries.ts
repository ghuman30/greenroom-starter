/**
 * Server-side queries for the Wednesday pre-flight surface (T4 / slice 3).
 *
 * Intentionally does NOT use lib/queries.ts:getReports() or getAllShows()
 * — those filter to past shows only (date <= today), which is the
 * documented bug we're working around (see D18-D21 in
 * notes/evidence.md). Pre-flight needs UNFILTERED visibility into
 * upcoming shows.
 */

import { and, asc, eq, gte, lt, lte, or, sql, desc } from "drizzle-orm";
import { db } from "@/db";
import {
  shows,
  deals,
  artists,
  agents,
  agencies,
  settlements,
  expenses,
  type Deal,
} from "@/db/schema";
import {
  computeShowSignals,
  type PriorSettlement,
  type ShowSignals,
} from "./preFlightSignals";

export interface PreFlightRow {
  showId: string;
  date: string;
  daysUntilShow: number;
  artistName: string;
  agentName: string | null;
  agencyName: string | null;
  dealType: Deal["dealType"];
  /** Whether the structured deal has been agent-confirmed yet. */
  agentConfirmedAt: Date | null;
  /** Whether Mariana has at least reviewed the LLM extraction. */
  marianaConfirmedAt: Date | null;
  hasExtraction: boolean;
  signals: ShowSignals;
}

interface PreFlightArgs {
  today: Date;
  daysAhead: number;
  /** Cap on rows returned. Default 30. */
  limit?: number;
}

/**
 * Build the Wednesday pre-flight list — upcoming shows in [today, today
 * + daysAhead], each annotated with computed signals + a risk score.
 *
 * Sorted with highest-risk shows first; ties broken by date ascending
 * (the soonest show wins the tie).
 */
export async function getPreFlightShows(args: PreFlightArgs): Promise<PreFlightRow[]> {
  const today = isoDate(args.today);
  const horizon = isoDate(addDays(args.today, args.daysAhead));

  // 1) Fetch upcoming shows with their joins. Single SQL.
  const upcoming = await db
    .select({
      show: shows,
      deal: deals,
      artist: artists,
      agent: agents,
      agency: agencies,
    })
    .from(shows)
    .innerJoin(deals, eq(deals.showId, shows.id))
    .leftJoin(artists, eq(artists.id, shows.artistId))
    .leftJoin(agents, eq(agents.id, artists.agentId))
    .leftJoin(agencies, eq(agencies.id, agents.agencyId))
    .where(and(gte(shows.date, today), lte(shows.date, horizon)))
    .orderBy(asc(shows.date));

  // 2) Build context (prior settlements) per show. We do this per-show
  // because the relationship is (same artist OR same agent OR same agency)
  // — multi-key joins. N is small (~30 upcoming shows), so N+1 is fine.
  const rows: PreFlightRow[] = [];
  for (const r of upcoming) {
    const priorSettlements = await fetchPriorSettlementsFor({
      artistId: r.show.artistId,
      agentId: r.artist?.agentId ?? null,
      agencyId: r.agent?.agencyId ?? null,
      beforeDate: r.show.date,
      windowMonths: 18,
    });

    const daysUntilShow = daysBetween(args.today, parseIsoDate(r.show.date));

    const sigs = computeShowSignals({
      deal: r.deal,
      context: {
        priorSettlements,
        agent: r.agent
          ? {
              name: r.agent.name,
              preferencesNotes: r.agent.preferencesNotes,
            }
          : null,
        showDate: r.show.date,
        daysUntilShow,
      },
    });

    rows.push({
      showId: r.show.id,
      date: r.show.date,
      daysUntilShow,
      artistName: r.artist?.name ?? "Unknown artist",
      agentName: r.agent?.name ?? null,
      agencyName: r.agency?.name ?? null,
      dealType: r.deal.dealType,
      agentConfirmedAt: r.deal.agentConfirmedAt,
      marianaConfirmedAt: r.deal.marianaConfirmedAt,
      hasExtraction: !!r.deal.extractedDealJson,
      signals: sigs,
    });
  }

  // 3) Sort: highest risk score first, tiebreak by date ASC
  rows.sort((a, b) => {
    if (b.signals.riskScore !== a.signals.riskScore) {
      return b.signals.riskScore - a.signals.riskScore;
    }
    return a.date.localeCompare(b.date);
  });

  return args.limit ? rows.slice(0, args.limit) : rows;
}

// --------------------- Helpers ---------------------------------------------

interface FetchPriorArgs {
  artistId: string;
  agentId: string | null;
  agencyId: string | null;
  beforeDate: string;
  windowMonths: number;
}

/**
 * Prior settlements for the SAME artist, OR the SAME agent, OR the
 * SAME agency (unioned, deduped by show_id), within the window. Each
 * row includes the show's hospitality_cap (from deals) and actual
 * hospitality spend (summed from expenses).
 */
async function fetchPriorSettlementsFor(
  a: FetchPriorArgs,
): Promise<PriorSettlement[]> {
  const cutoff = isoDate(addMonths(parseIsoDate(a.beforeDate), -a.windowMonths));

  // Find candidate show IDs by artist OR agent OR agency. Build the OR
  // list conditionally so we never compare a column to a NULL sentinel
  // string (a real `__null__` value in an id column would silently
  // collide and inflate priorSettlements). Self is excluded via strict
  // `lt` — "prior" means strictly before this show's date.
  const orBranches = [eq(artists.id, a.artistId)];
  if (a.agentId) orBranches.push(eq(artists.agentId, a.agentId));
  if (a.agencyId) orBranches.push(eq(agents.agencyId, a.agencyId));

  const candidateShows = await db
    .select({
      showId: shows.id,
      date: shows.date,
      status: settlements.status,
      recoupsJson: settlements.recoupsJson,
      notes: settlements.notes,
      hospitalityCap: deals.hospitalityCap,
    })
    .from(shows)
    .innerJoin(settlements, eq(settlements.showId, shows.id))
    .innerJoin(deals, eq(deals.showId, shows.id))
    .innerJoin(artists, eq(artists.id, shows.artistId))
    .leftJoin(agents, eq(agents.id, artists.agentId))
    .where(
      and(
        lt(shows.date, a.beforeDate),
        gte(shows.date, cutoff),
        or(...orBranches),
      ),
    )
    .orderBy(desc(shows.date));

  if (candidateShows.length === 0) return [];

  // Aggregate hospitality actuals per show
  const showIds = candidateShows.map((s) => s.showId);
  // Drizzle in() over a list of strings:
  const expenseSums = await db
    .select({
      showId: expenses.showId,
      hosp: sql<number>`coalesce(sum(case when ${expenses.category} = 'hospitality' then ${expenses.amount} else 0 end), 0)`,
    })
    .from(expenses)
    .where(sql`${expenses.showId} IN (${sql.join(showIds.map((id) => sql`${id}`), sql`, `)})`)
    .groupBy(expenses.showId);

  const hospMap = new Map(expenseSums.map((r) => [r.showId, r.hosp]));

  return candidateShows.map((s) => ({
    showId: s.showId,
    date: s.date,
    status: s.status,
    recoupsJson: s.recoupsJson,
    notes: s.notes,
    hospitalityCap: s.hospitalityCap,
    hospitalityActual: hospMap.get(s.showId) ?? 0,
  }));
}

function isoDate(d: Date): string {
  // YYYY-MM-DD in local time; matches shows.date format
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const dd = String(d.getDate()).padStart(2, "0");
  return `${yyyy}-${mm}-${dd}`;
}

function parseIsoDate(s: string): Date {
  // shows.date is YYYY-MM-DD without TZ; parse as local midnight.
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, (m ?? 1) - 1, d ?? 1);
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

function addMonths(d: Date, n: number): Date {
  const out = new Date(d);
  out.setMonth(out.getMonth() + n);
  return out;
}

function daysBetween(a: Date, b: Date): number {
  const ONE = 86_400_000;
  const aMid = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
  const bMid = new Date(b.getFullYear(), b.getMonth(), b.getDate()).getTime();
  return Math.round((bMid - aMid) / ONE);
}
