"use client";

import { useState, useTransition } from "react";
import { Check, AlertTriangle, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { confirmAll, recordResponse, type AgentActionResult } from "./actions";

// =========================================================================
// Per-item confirm/flag buttons. Compact for mobile.
// =========================================================================

interface ItemActionProps {
  token: string;
  fieldPath: string;
  initialState?: "confirmed" | "flagged" | null;
}

export function ItemActions({
  token,
  fieldPath,
  initialState = null,
}: ItemActionProps) {
  const [isPending, startTransition] = useTransition();
  const [state, setState] = useState<"confirmed" | "flagged" | null>(initialState);
  const [error, setError] = useState<string | null>(null);
  const [flagOpen, setFlagOpen] = useState(false);
  const [comment, setComment] = useState("");

  const submitConfirm = () => {
    setError(null);
    startTransition(async () => {
      const result: AgentActionResult = await recordResponse({
        token,
        fieldPath,
        action: "confirmed",
      });
      if (result.ok) setState("confirmed");
      else setError(result.error);
    });
  };

  const submitFlag = (text: string) => {
    setError(null);
    startTransition(async () => {
      const result: AgentActionResult = await recordResponse({
        token,
        fieldPath,
        action: "flagged",
        details: { comment: text },
      });
      if (result.ok) {
        setState("flagged");
        setFlagOpen(false);
      } else {
        setError(result.error);
      }
    });
  };

  if (state === "confirmed") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-brand-700 font-medium">
        <Check className="h-3 w-3" /> confirmed
      </span>
    );
  }

  if (state === "flagged") {
    return (
      <span className="inline-flex items-center gap-1 text-[11px] text-rose-700 font-medium">
        <AlertTriangle className="h-3 w-3" /> flagged
      </span>
    );
  }

  return (
    <div className="inline-flex flex-col items-end gap-1.5">
      <div className="inline-flex items-center gap-1.5">
        <button
          type="button"
          onClick={submitConfirm}
          disabled={isPending}
          className="text-[11px] text-brand-700 hover:text-brand-900 hover:underline underline-offset-2 disabled:opacity-50"
        >
          {isPending ? "…" : "Looks right"}
        </button>
        <span className="text-ink-300 text-[11px]">·</span>
        <button
          type="button"
          onClick={() => setFlagOpen((v) => !v)}
          disabled={isPending}
          className="text-[11px] text-rose-700 hover:text-rose-900 hover:underline underline-offset-2 disabled:opacity-50"
        >
          Flag
        </button>
      </div>

      {flagOpen && (
        <div className="w-64 sm:w-72 rounded-md border border-ink-200 bg-white p-2.5 space-y-2 shadow-sm">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={3}
            className="w-full rounded-sm border border-ink-200 px-2 py-1.5 text-[12px] font-sans focus:outline-none focus:ring-2 focus:ring-rose-500/30 focus:border-rose-500"
            placeholder="What's wrong here?"
          />
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="danger"
              onClick={() => submitFlag(comment)}
              disabled={isPending || !comment.trim()}
            >
              {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
              Send flag
            </Button>
            <button
              type="button"
              onClick={() => {
                setComment("");
                setFlagOpen(false);
              }}
              className="text-[11px] text-ink-500 hover:text-ink-900"
            >
              Cancel
            </button>
          </div>
          {error && (
            <div className="text-[10.5px] text-rose-700">{error}</div>
          )}
        </div>
      )}
    </div>
  );
}

// =========================================================================
// Ambiguity flag: pick one of two readings (or write your own).
// =========================================================================

interface AmbiguityResolverProps {
  token: string;
  flagIndex: number;
  readings: { interpretation: string }[];
}

/** Explicit state model — replaces the previous `number | null | -1` overload. */
type ChosenState =
  | { kind: "none" }
  | { kind: "index"; i: number }
  | { kind: "custom" };

export function AmbiguityResolver({
  token,
  flagIndex,
  readings,
}: AmbiguityResolverProps) {
  const [isPending, startTransition] = useTransition();
  const [chosen, setChosen] = useState<ChosenState>({ kind: "none" });
  const [customOpen, setCustomOpen] = useState(false);
  const [custom, setCustom] = useState("");
  const [error, setError] = useState<string | null>(null);

  const submitIndex = (i: number) => {
    setError(null);
    startTransition(async () => {
      const result = await recordResponse({
        token,
        fieldPath: `ambiguity_${flagIndex}`,
        action: "reading_chosen",
        details: { reading_index: i },
      });
      if (result.ok) setChosen({ kind: "index", i });
      else setError(result.error);
    });
  };

  const submitCustom = (text: string) => {
    setError(null);
    startTransition(async () => {
      const result = await recordResponse({
        token,
        fieldPath: `ambiguity_${flagIndex}`,
        action: "reading_chosen",
        details: { custom_reading: text },
      });
      if (result.ok) {
        setChosen({ kind: "custom" });
        setCustomOpen(false);
      } else {
        setError(result.error);
      }
    });
  };

  if (chosen.kind === "index") {
    return (
      <div className="text-[12px] text-brand-800 font-medium inline-flex items-center gap-1.5 bg-brand-50 px-2 py-1 rounded">
        <Check className="h-3 w-3" />
        Reading {chosen.i + 1} chosen
      </div>
    );
  }

  if (chosen.kind === "custom") {
    return (
      <div className="text-[12px] text-brand-800 font-medium inline-flex items-center gap-1.5 bg-brand-50 px-2 py-1 rounded">
        <Check className="h-3 w-3" />
        Custom clarification sent
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {readings.map((r, i) => (
        <button
          key={i}
          type="button"
          onClick={() => submitIndex(i)}
          disabled={isPending}
          className="block w-full text-left rounded-md border border-ink-200 hover:border-brand-600 hover:bg-brand-50/40 px-3 py-2 text-[12.5px] text-ink-800 transition-colors disabled:opacity-50"
        >
          <span className="font-mono text-[10px] text-ink-500 mr-2">○</span>
          {r.interpretation}
        </button>
      ))}
      <button
        type="button"
        onClick={() => setCustomOpen((v) => !v)}
        disabled={isPending}
        className="block w-full text-left rounded-md border border-dashed border-ink-300 hover:border-ink-500 px-3 py-2 text-[12.5px] text-ink-600 transition-colors disabled:opacity-50"
      >
        <span className="font-mono text-[10px] text-ink-500 mr-2">○</span>
        Neither — let me clarify
      </button>
      {customOpen && (
        <div className="rounded-md border border-ink-200 p-2.5 space-y-2 bg-white">
          <textarea
            value={custom}
            onChange={(e) => setCustom(e.target.value)}
            rows={3}
            className="w-full rounded-sm border border-ink-200 px-2 py-1.5 text-[12px] focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
            placeholder="Explain in your own words..."
          />
          <Button
            size="sm"
            onClick={() => submitCustom(custom)}
            disabled={isPending || !custom.trim()}
          >
            {isPending ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
            Send clarification
          </Button>
          {error && <div className="text-[10.5px] text-rose-700">{error}</div>}
        </div>
      )}
    </div>
  );
}

// =========================================================================
// "Confirm all" — single button at the bottom for the happy path.
// =========================================================================

interface ConfirmAllProps {
  token: string;
  alreadyConfirmed: boolean;
}

export function ConfirmAllButton({
  token,
  alreadyConfirmed,
}: ConfirmAllProps) {
  const [isPending, startTransition] = useTransition();
  const [done, setDone] = useState(alreadyConfirmed);
  const [error, setError] = useState<string | null>(null);

  if (done) {
    return (
      <div className="rounded-lg bg-brand-50 border border-brand-200 px-5 py-4 flex items-center gap-3 text-brand-900">
        <Check className="h-5 w-5 text-brand-700 shrink-0" />
        <div>
          <div className="font-semibold text-[13px]">
            Thanks — Mariana is notified.
          </div>
          <div className="text-[11.5px] text-brand-800/80 mt-0.5">
            You confirmed this deal. The Crescent will use these terms at settlement.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Button
        variant="brand"
        size="lg"
        className="w-full sm:w-auto"
        disabled={isPending}
        onClick={() => {
          setError(null);
          startTransition(async () => {
            const result = await confirmAll(token);
            if (result.ok) setDone(true);
            else setError(result.error);
          });
        }}
      >
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Check className="h-4 w-4" />
        )}
        {isPending ? "Sending…" : "Confirm — everything looks right"}
      </Button>
      {error && (
        <div className="text-[12px] text-rose-700">{error}</div>
      )}
    </div>
  );
}
