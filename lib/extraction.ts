/**
 * Deal extraction via LLM (slice 1 spine).
 *
 * Reads the prompt from lib/extraction-prompt.md (shared with notes/eval_harness.py),
 * calls OpenRouter with the input, validates and persists the result.
 *
 * Production usage:
 *
 *   import { extractDeal, persistExtraction } from "@/lib/extraction";
 *
 *   const result = await extractDeal({
 *     emailText: deal.agentEmailText,
 *     notesText: deal.dealNotesFreetext,
 *     structuredFieldsContext: { dealType: ..., guarantee_amount: ..., ... },
 *   });
 *
 *   await persistExtraction(deal.id, result);
 *
 * Reliability notes:
 *   - Free-tier providers (e.g., openai/gpt-oss-120b:free) are non-deterministic
 *     even at temperature=0, with ~8-10% JSON validity failure rate per call.
 *   - This module retries ONCE on JSON parse failure (only) with a stronger
 *     formatting instruction. Other errors (auth, rate-limit, timeout) do NOT
 *     trigger retry — they propagate to the caller.
 *   - Bumps expected validity from ~92% to ~99% in our eval.
 *   - On final failure, throws a typed ExtractionError with cause chaining.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { db } from "@/db";
import { deals, type ExtractionOutput, type Deal } from "@/db/schema";
import { eq } from "drizzle-orm";

// --------------------- Types -----------------------------------------------

export interface ExtractionInput {
  /** Optional agent's deal email text. When present, the LLM treats it as primary. */
  emailText: string | null;
  /** Mariana's deal_notes_freetext. Always present in practice. */
  notesText: string;
  /** Existing structured columns Mariana entered; LLM cross-references for drift detection. */
  structuredFieldsContext: Record<string, unknown>;
}

export interface ExtractionMetadata {
  model: string;
  durationMs: number;
  retryUsed: boolean;
  promptTokens?: number;
  completionTokens?: number;
}

export interface ExtractionResult {
  output: ExtractionOutput;
  metadata: ExtractionMetadata;
}

type ChatMessage = {
  role: "system" | "user" | "assistant";
  content: string;
};

/**
 * Top-level extraction failure. Covers auth, network, model-side errors, and
 * unparseable output (when retry also fails). The standard `Error.cause` slot
 * carries the underlying cause; `reason` is a short tag for branching/logging.
 */
export class ExtractionError extends Error {
  readonly reason: string;
  readonly rawContent?: string;
  readonly model: string;

  constructor(
    reason: string,
    model: string,
    rawContent?: string,
    cause?: unknown,
  ) {
    super(`Extraction failed (${reason}) using model ${model}`, { cause });
    this.name = "ExtractionError";
    this.reason = reason;
    this.model = model;
    this.rawContent = rawContent;
  }
}

/**
 * Thrown when the LLM returned content that could not be parsed as the
 * expected ExtractionOutput shape (either invalid JSON or wrong structure).
 * This is the ONLY error type that triggers a retry inside `extractDeal`.
 */
export class ExtractionParseError extends Error {
  readonly rawContent: string;

  constructor(rawContent: string, cause?: unknown) {
    super("Failed to parse model output as ExtractionOutput", { cause });
    this.name = "ExtractionParseError";
    this.rawContent = rawContent;
  }
}

/** Result of loading an extraction from the DB. Discriminated for caller clarity. */
export type LoadedExtraction =
  | { ok: true; output: ExtractionOutput }
  | { ok: false; reason: "missing" | "malformed" };

// --------------------- Config ----------------------------------------------

const DEFAULT_MODEL = "openai/gpt-oss-120b:free";
const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const REQUEST_TIMEOUT_MS = 120_000;
const MAX_TOKENS = 4000;
const DEFAULT_REFERER = "https://github.com/ghuman30/greenroom-starter";

function getModel(): string {
  return process.env.OPENROUTER_MODEL ?? DEFAULT_MODEL;
}

function getReferer(): string {
  return process.env.OPENROUTER_REFERER ?? DEFAULT_REFERER;
}

function getApiKey(model: string): string {
  const key = process.env.OPENROUTER_API_KEY;
  if (!key) {
    throw new ExtractionError(
      "missing_api_key",
      model,
      "OPENROUTER_API_KEY not set. Add to .env.local.",
    );
  }
  return key;
}

// --------------------- Prompt loader ---------------------------------------

interface PromptSections {
  system: string;
  fewshots: Array<{ user: string; assistant: string }>;
}

let cachedPrompt: PromptSections | null = null;

function loadPrompt(): PromptSections {
  if (cachedPrompt) return cachedPrompt;

  const promptPath = join(process.cwd(), "lib", "extraction-prompt.md");
  const text = readFileSync(promptPath, "utf-8");

  // Split on '## SECTION_NAME' markers — mirrors notes/eval_harness.py.
  const parts = text.split(/^## ([A-Z_0-9]+)\s*$/m);
  const sections: Record<string, string> = {};
  for (let i = 1; i < parts.length; i += 2) {
    sections[parts[i].trim()] = (parts[i + 1] ?? "").trim();
  }

  const fewshots: Array<{ user: string; assistant: string }> = [];
  for (const name of Object.keys(sections).sort()) {
    if (!name.startsWith("FEWSHOT_")) continue;
    const body = sections[name];
    // Body: **Input — ...:**\n\n```...\n```\n\n**Expected output:**\n\n```json\n...\n```
    const inputMatch = body.match(/\*\*Input.*?:\*\*\s*```(?:\w*)?\n([\s\S]*?)```/);
    const outputMatch = body.match(/\*\*Expected output:\*\*\s*```json\n([\s\S]*?)```/);
    if (!inputMatch || !outputMatch) {
      console.warn(`[extraction] Skipping malformed fewshot ${name}`);
      continue;
    }
    fewshots.push({
      user: inputMatch[1].trim(),
      assistant: outputMatch[1].trim(),
    });
  }

  cachedPrompt = { system: sections["SYSTEM"], fewshots };
  return cachedPrompt;
}

// --------------------- Message builder -------------------------------------

function formatStructuredContext(ctx: Record<string, unknown>): string {
  const lines: string[] = [];
  for (const [k, v] of Object.entries(ctx)) {
    if (v === null || v === undefined) {
      lines.push(`  ${k}: <unset>`);
    } else if (typeof v === "string" || typeof v === "number" || typeof v === "boolean") {
      lines.push(`  ${k}: ${v}`);
    } else {
      lines.push(`  ${k}: ${JSON.stringify(v)}`);
    }
  }
  return lines.length ? lines.join("\n") : "  (none)";
}

function buildUserMessage(input: ExtractionInput, extraGuidance = ""): string {
  const email = input.emailText?.trim() || "<none provided>";
  const ctx = formatStructuredContext(input.structuredFieldsContext);
  const guidance = extraGuidance ? `\n\n${extraGuidance}` : "";
  return `SOURCE A — Agent's email (optional):
${email}

SOURCE B — Mariana's notes:
${input.notesText}

CONTEXT — Structured fields previously entered:
${ctx}

Extract per the rules above. Respond with the JSON object only.${guidance}`;
}

function buildMessages(input: ExtractionInput, extraGuidance = ""): ChatMessage[] {
  const prompt = loadPrompt();
  const messages: ChatMessage[] = [];
  messages.push({ role: "system", content: prompt.system });
  for (const fs of prompt.fewshots) {
    messages.push({ role: "user", content: fs.user });
    messages.push({ role: "assistant", content: fs.assistant });
  }
  messages.push({ role: "user", content: buildUserMessage(input, extraGuidance) });
  return messages;
}

// --------------------- OpenRouter call -------------------------------------

interface OpenRouterResponse {
  choices?: Array<{
    message?: {
      content?: string | null;
      reasoning?: string | null;
      tool_calls?: Array<{ function?: { arguments?: string } }>;
    };
  }>;
  usage?: { prompt_tokens?: number; completion_tokens?: number };
}

async function callOpenRouter(
  messages: ChatMessage[],
  model: string,
): Promise<{ content: string; usage?: OpenRouterResponse["usage"] }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${getApiKey(model)}`,
        "Content-Type": "application/json",
        "HTTP-Referer": getReferer(),
        "X-Title": "Greenroom case study - deal extraction",
      },
      body: JSON.stringify({
        model,
        messages,
        temperature: 0.0,
        max_tokens: MAX_TOKENS,
        response_format: { type: "json_object" },
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const body = await response.text().catch(() => "<no body>");
    throw new ExtractionError(
      `http_${response.status}`,
      model,
      body.slice(0, 500),
    );
  }

  const data = (await response.json()) as OpenRouterResponse;
  const msg = data.choices?.[0]?.message;
  if (!msg) {
    throw new ExtractionError(
      "no_choices",
      model,
      JSON.stringify(data).slice(0, 500),
    );
  }

  // Prefer content; fall back to tool_calls only. NEVER fall back to
  // reasoning — that's chain-of-thought, not the answer, and will always
  // fail to parse as ExtractionOutput JSON.
  let content = msg.content ?? "";
  if (!content && msg.tool_calls?.[0]?.function?.arguments) {
    content = msg.tool_calls[0].function.arguments;
  }
  if (!content) {
    throw new ExtractionError(
      "empty_content",
      model,
      JSON.stringify(msg).slice(0, 500),
    );
  }

  // Strip markdown fences if model added them despite instructions
  content = content
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/i, "");

  return { content, usage: data.usage };
}

// --------------------- JSON parsing + shape validation ----------------------

/**
 * Minimal runtime shape guard. We don't pull in a runtime-validation library
 * (zod/valibot) for this one boundary — the eval harness gives us high
 * confidence the model usually returns the right shape. This guard catches
 * the "totally wrong" cases (string where object expected, missing required
 * top-level keys) without trying to deeply validate every nested type.
 *
 * Callers needing deeper guarantees should validate downstream consumption.
 */
function isExtractionOutputShape(value: unknown): value is ExtractionOutput {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  if (!v.extracted || typeof v.extracted !== "object") return false;
  if (!Array.isArray(v.ambiguity_flags)) return false;
  if (!Array.isArray(v.discrepancies)) return false;
  if (!Array.isArray(v.low_confidence)) return false;
  // source_spans and confidence_per_field are optional-ish: model sometimes
  // omits them. Default to empty objects so downstream reads don't crash.
  if (v.source_spans !== undefined && (typeof v.source_spans !== "object" || v.source_spans === null)) return false;
  if (v.confidence_per_field !== undefined && (typeof v.confidence_per_field !== "object" || v.confidence_per_field === null)) return false;
  return true;
}

function parseExtractionJson(content: string): ExtractionOutput {
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch (firstErr) {
    // Heuristic repair: model sometimes double-escapes property-name quotes,
    // producing strings like {"extracted\":...}. Only safe to try AFTER the
    // strict parse has already failed — if the original JSON has legitimate
    // escaped quotes in string values, this could corrupt them, but we've
    // ruled out the valid case by reaching this branch.
    const repaired = content.replace(/\\"/g, '"').replace(/\\\\/g, "\\");
    try {
      parsed = JSON.parse(repaired);
    } catch {
      throw new ExtractionParseError(content, firstErr);
    }
  }

  if (!isExtractionOutputShape(parsed)) {
    throw new ExtractionParseError(
      content,
      new Error("Parsed JSON does not match ExtractionOutput shape"),
    );
  }

  // Defaults for optional fields the model may have omitted.
  const result: ExtractionOutput = parsed;
  if (!result.source_spans) result.source_spans = {};
  if (!result.confidence_per_field) result.confidence_per_field = {};
  return result;
}

// --------------------- Main entry point ------------------------------------

/**
 * Extract a structured deal from prose + (optional) email.
 *
 * Retries ONCE on ExtractionParseError with a stronger formatting instruction.
 * All other errors (auth, network, rate-limit, timeout) propagate immediately
 * without retry.
 *
 * @throws ExtractionError on auth, network, or final-attempt parsing failure.
 */
export async function extractDeal(
  input: ExtractionInput,
  options: { model?: string } = {},
): Promise<ExtractionResult> {
  const model = options.model ?? getModel();
  const start = Date.now();
  let retryUsed = false;
  let messages = buildMessages(input);

  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const { content, usage } = await callOpenRouter(messages, model);
      const output = parseExtractionJson(content);

      // Fill optional metadata at the boundary. Type now declares these
      // as optional so this mutation is honest (see db/schema.ts).
      if (!output.model) output.model = model;
      if (!output.generated_at) output.generated_at = new Date().toISOString();
      if (!output.source) {
        output.source = input.emailText && input.notesText
          ? "both"
          : input.emailText
            ? "email"
            : "notes";
      }

      return {
        output,
        metadata: {
          model,
          durationMs: Date.now() - start,
          retryUsed,
          promptTokens: usage?.prompt_tokens,
          completionTokens: usage?.completion_tokens,
        },
      };
    } catch (err) {
      // Only ExtractionParseError is retryable. All others propagate.
      if (attempt === 0 && err instanceof ExtractionParseError) {
        retryUsed = true;
        messages = buildMessages(
          input,
          "Your previous attempt produced output that could not be parsed as valid JSON " +
            "matching the schema. Respond again with ONLY a valid JSON object conforming " +
            "to the schema. Use straight double quotes; never escape the quotes around " +
            "property names with backslashes. Do not include markdown fences.",
        );
        continue;
      }
      // Wrap parse errors that survived retry; let ExtractionError pass through.
      if (err instanceof ExtractionParseError) {
        throw new ExtractionError("parse_failed_after_retry", model, err.rawContent, err);
      }
      throw err;
    }
  }

  // Unreachable — loop either returns or throws on attempt 1.
  throw new ExtractionError("unreachable", model);
}

// --------------------- Persistence -----------------------------------------

/**
 * Save the extraction output to deals.extracted_deal_json. Idempotent —
 * safe to call repeatedly; latest extraction overwrites prior. Amendment
 * versioning is handled separately by the deal_versions table (not in this
 * module).
 *
 * @param dealId  the deals.id (NOT a show_id)
 * @returns the updated Deal row, or null if no deal matched dealId.
 */
export async function persistExtraction(
  dealId: string,
  result: ExtractionResult,
): Promise<Deal | null> {
  const json = JSON.stringify(result.output);
  const [row] = await db
    .update(deals)
    .set({ extractedDealJson: json })
    .where(eq(deals.id, dealId))
    .returning();
  return row ?? null;
}

/**
 * Load a deal's stored extraction. Returns a discriminated result so callers
 * can distinguish "no extraction yet" from "stored JSON is malformed."
 */
export function getExtraction(deal: Pick<Deal, "extractedDealJson">): LoadedExtraction {
  if (!deal.extractedDealJson) return { ok: false, reason: "missing" };
  try {
    const parsed = JSON.parse(deal.extractedDealJson) as unknown;
    if (!isExtractionOutputShape(parsed)) {
      // Malformed JSON shape — log so it doesn't silently rot.
      console.warn("[extraction] Stored extractedDealJson does not match shape");
      return { ok: false, reason: "malformed" };
    }
    return { ok: true, output: parsed };
  } catch {
    console.warn("[extraction] Stored extractedDealJson is invalid JSON");
    return { ok: false, reason: "malformed" };
  }
}
