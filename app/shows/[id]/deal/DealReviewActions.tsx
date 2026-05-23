"use client";

import { useState, useTransition } from "react";
import { Loader2, Sparkles, Check, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  triggerExtraction,
  confirmExtraction,
  resetReview,
  updateEmailText,
  type ActionResult,
} from "./actions";

interface Props {
  dealId: string;
  showId: string;
  hasExtraction: boolean;
  isMarianaConfirmed: boolean;
  currentEmailText: string | null;
}

export function DealReviewActions({
  dealId,
  showId,
  hasExtraction,
  isMarianaConfirmed,
  currentEmailText,
}: Props) {
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [emailEditOpen, setEmailEditOpen] = useState(false);
  const [emailDraft, setEmailDraft] = useState(currentEmailText ?? "");

  const runAction = async (
    action: () => Promise<ActionResult>,
  ): Promise<void> => {
    setError(null);
    startTransition(async () => {
      const result = await action();
      if (!result.ok) setError(result.error);
    });
  };

  return (
    <div className="space-y-4">
      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900">
          <span className="font-semibold">Action failed: </span>
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        {!hasExtraction ? (
          <Button
            onClick={() => runAction(() => triggerExtraction(dealId, showId))}
            disabled={isPending}
          >
            {isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {isPending ? "Extracting…" : "Extract deal"}
          </Button>
        ) : (
          <>
            <Button
              onClick={() => runAction(() => triggerExtraction(dealId, showId))}
              disabled={isPending}
              variant="secondary"
            >
              {isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {isPending ? "Re-extracting…" : "Re-extract"}
            </Button>

            {!isMarianaConfirmed ? (
              <Button
                onClick={() =>
                  runAction(() => confirmExtraction(dealId, showId))
                }
                disabled={isPending}
              >
                <Check className="h-4 w-4" />
                Confirm extraction
              </Button>
            ) : (
              <Button
                onClick={() =>
                  runAction(() => resetReview(dealId, showId))
                }
                disabled={isPending}
                variant="secondary"
                title="Clears both your confirmation and any agent confirmation"
              >
                <RotateCcw className="h-4 w-4" />
                Reset review
              </Button>
            )}
          </>
        )}

        <button
          type="button"
          onClick={() => setEmailEditOpen((v) => !v)}
          className="text-[12px] text-ink-500 hover:text-ink-900 underline underline-offset-2"
        >
          {currentEmailText ? "Edit agent email" : "Add agent email"}
        </button>
      </div>

      {emailEditOpen && (
        <div className="rounded-md border border-ink-200 bg-canvas/40 p-4 space-y-3">
          <div>
            <div className="eyebrow text-[10px] text-ink-500 mb-2">
              Paste the agent's deal email (optional)
            </div>
            <p className="text-[11.5px] text-ink-500 mb-2 max-w-xl leading-relaxed">
              When provided, the extractor uses the email as the primary
              source and flags any discrepancies against your notes.
              Editing clears the prior extraction and confirmations.
            </p>
            <textarea
              value={emailDraft}
              onChange={(e) => setEmailDraft(e.target.value)}
              rows={8}
              className="w-full rounded-md border border-ink-200 bg-white px-3 py-2 text-[12.5px] font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
              placeholder="From: agent@agency.com&#10;Date: ...&#10;&#10;Hi Mariana,&#10;Confirming our offer for [artist] on [date]: ..."
            />
          </div>
          <div className="flex items-center gap-2">
            <Button
              onClick={() =>
                runAction(async () => {
                  const r = await updateEmailText(dealId, showId, emailDraft);
                  if (r.ok) setEmailEditOpen(false);
                  return r;
                })
              }
              disabled={isPending}
            >
              Save email
            </Button>
            <Button
              onClick={() => {
                setEmailDraft(currentEmailText ?? "");
                setEmailEditOpen(false);
              }}
              variant="secondary"
            >
              Cancel
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
