"""
Eval harness for the LLM deal extractor (T1).

Reads:
  - lib/extraction-prompt.md   (the shared prompt — single source of truth)
  - notes/eval_set_with_labels.json (12 hand-labeled cases)

For each case:
  1. Build the system + few-shot + user messages from the prompt file
  2. Call OpenRouter
  3. Parse the JSON response
  4. Score against the expected block in the eval

Outputs:
  - Per-case detail (printed)
  - Aggregate metrics (recall, precision, field accuracy)
  - notes/eval_results.json (full audit trail of LLM outputs)

Run:
  # Set your key first, see .env.example
  export OPENROUTER_API_KEY=sk-or-v1-...
  python -X utf8 notes/eval_harness.py

  # Optional model override:
  OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free python -X utf8 notes/eval_harness.py
"""

import os, sys, json, re, time
import urllib.request, urllib.error
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = ROOT / "lib" / "extraction-prompt.md"
EVAL_FILE = ROOT / "notes" / "eval_set_with_labels.json"
RESULTS_FILE = ROOT / "notes" / "eval_results.json"

DEFAULT_MODEL = "deepseek/deepseek-v4-flash:free"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---------------------------------------------------------------------------
# Load .env.local for OPENROUTER_API_KEY (simple parser, no python-dotenv dep)
# ---------------------------------------------------------------------------
def load_env_local() -> None:
    env_file = ROOT / ".env.local"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

load_env_local()

# ---------------------------------------------------------------------------
# Prompt loader — parses the markdown into system + fewshots + user template
# ---------------------------------------------------------------------------
def load_prompt() -> Dict[str, Any]:
    text = PROMPT_FILE.read_text(encoding="utf-8")
    # Split on '## SECTION_NAME' markers
    sections = re.split(r"^## ([A-Z_0-9]+)\s*$", text, flags=re.MULTILINE)
    # sections == [preamble, name1, body1, name2, body2, ...]
    result: Dict[str, str] = {}
    for i in range(1, len(sections), 2):
        name = sections[i].strip()
        body = sections[i + 1].strip() if i + 1 < len(sections) else ""
        result[name] = body
    return result

# ---------------------------------------------------------------------------
# Build messages list from prompt sections
# ---------------------------------------------------------------------------
def build_messages(prompt: Dict[str, str], user_input: str) -> List[Dict[str, str]]:
    """
    Returns OpenAI-style messages: [
      {role: 'system', content: SYSTEM},
      {role: 'user',   content: FEWSHOT_1 input},
      {role: 'assistant', content: FEWSHOT_1 expected},
      ...
      {role: 'user', content: actual input}
    ]
    """
    messages: List[Dict[str, str]] = []
    messages.append({"role": "system", "content": prompt["SYSTEM"]})

    # Parse fewshots: each FEWSHOT_N has an Input block and Expected output block
    for k in sorted(k for k in prompt if k.startswith("FEWSHOT_")):
        body = prompt[k]
        # Body has format: **Input — ...:**\n\n```...input...```\n\n**Expected output:**\n\n```json\n...output...\n```
        in_match = re.search(r"\*\*Input.*?:\*\*\s*```(?:\w*)?\n(.*?)```", body, re.DOTALL)
        out_match = re.search(r"\*\*Expected output:\*\*\s*```json\n(.*?)```", body, re.DOTALL)
        if not in_match or not out_match:
            print(f"WARNING: couldn't parse {k}", file=sys.stderr)
            continue
        messages.append({"role": "user", "content": in_match.group(1).strip()})
        messages.append({"role": "assistant", "content": out_match.group(1).strip()})

    # Actual user input
    messages.append({"role": "user", "content": user_input})
    return messages

# ---------------------------------------------------------------------------
# Build user input from an eval case
# ---------------------------------------------------------------------------
def format_case_input(case: Dict[str, Any]) -> str:
    email = case["input"].get("email_text") or "<none provided>"
    notes = case["input"]["notes_text"]
    struct = case["input"].get("structured_fields_context") or {}
    struct_lines = []
    for k, v in struct.items():
        struct_lines.append(f"  {k}: {json.dumps(v) if not isinstance(v, (str, int, float, type(None))) else v}")
    struct_str = "\n".join(struct_lines) if struct_lines else "  (none)"

    return f"""SOURCE A — Agent's email (optional):
{email}

SOURCE B — Mariana's notes:
{notes}

CONTEXT — Structured fields previously entered:
{struct_str}

Extract per the rules above. Respond with the JSON object only."""

# ---------------------------------------------------------------------------
# OpenRouter call
# ---------------------------------------------------------------------------
def call_openrouter(messages: List[Dict[str, str]], model: str) -> Dict[str, Any]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY not set. Add to .env.local or export it.")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,  # deterministic
        "max_tokens": 4000,
        "response_format": {"type": "json_object"},  # not all providers honor this; the prompt also enforces
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/ghuman30/greenroom-starter",
        "X-Title": "Greenroom case study - deal extraction eval",
    }
    req = urllib.request.Request(
        OPENROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e

    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"No choices in response: {json.dumps(data)[:500]}")

    msg = data["choices"][0]["message"]
    content = msg.get("content")

    # Fall back to tool_calls only if present. NEVER fall back to `reasoning` —
    # that's chain-of-thought, not the answer; it will fail JSON parse 100% of
    # the time and waste a retry slot.
    if not content and msg.get("tool_calls"):
        tc = msg["tool_calls"][0] if msg["tool_calls"] else {}
        content = tc.get("function", {}).get("arguments", "")

    if not content:
        raise RuntimeError(
            f"Model returned no usable content. Message shape: {json.dumps(msg)[:500]}"
        )

    # Strip markdown fences if model added them despite instructions
    content = re.sub(r"^```(?:json)?\s*", "", content.strip())
    content = re.sub(r"\s*```$", "", content)

    # Attempt JSON repair on obvious failures (escaped quotes everywhere)
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as e1:
        # Heuristic repair: model sometimes double-escapes quotes
        repaired = content.replace('\\"', '"').replace("\\\\", "\\")
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError:
            raise RuntimeError(
                f"Model returned invalid JSON (could not repair): {e1}\n"
                f"First 500 chars: {content[:500]}"
            ) from e1

    return {
        "parsed": parsed,
        "raw_content": content,
        "usage": data.get("usage", {}),
    }

# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------
def score_extracted_fields(actual: Dict, expected: Dict) -> Dict[str, Any]:
    """Field-by-field comparison. Returns per-field pass/fail and overall score."""
    field_results = {}
    simple_fields = ["deal_kind", "guarantee_amount", "percentage", "percentage_basis",
                     "expense_cap", "hospitality_cap"]
    for f in simple_fields:
        if f not in expected:
            continue
        if isinstance(expected[f], dict) and "_acceptable" in str(expected[f]):
            continue  # handled below
        a = actual.get(f)
        e = expected[f]
        if isinstance(e, (int, float)) and isinstance(a, (int, float)):
            field_results[f] = abs(a - e) < 0.01
        else:
            field_results[f] = a == e

    # "_acceptable" pattern: list of allowed values
    for k, v in expected.items():
        if isinstance(v, list) and k.endswith("_acceptable"):
            real_field = k.replace("_acceptable", "")
            field_results[real_field] = actual.get(real_field) in v

    return {
        "passed": sum(1 for v in field_results.values() if v),
        "total": len(field_results),
        "per_field": field_results,
    }

def score_planned_recoups(actual_list: List[Dict], expected: Dict) -> Dict[str, Any]:
    """Check planned_recoups assertions: must_contain entries."""
    must_contain = expected.get("planned_recoups_must_contain", [])
    if not must_contain and expected.get("planned_recoups") == []:
        # Assert empty
        return {
            "passed": len(actual_list) == 0,
            "total": 1,
            "detail": f"Expected empty, got {len(actual_list)} recoups",
        }
    if not must_contain:
        return {"passed": 0, "total": 0, "detail": "No assertion"}
    matches = 0
    for must in must_contain:
        cat = must.get("category")
        amt = must.get("amount")
        for r in actual_list:
            if r.get("category") == cat and (amt is None or abs(r.get("amount", 0) - amt) < 0.01):
                matches += 1
                break
    return {"passed": matches, "total": len(must_contain)}

def score_ambiguity(actual_flags: List[Dict], expected: Dict) -> Dict[str, Any]:
    """Check ambiguity_flags assertions: must_contain (recall) + must_not_contain (precision)."""
    must = expected.get("ambiguity_flags_must_contain", [])
    must_not = expected.get("ambiguity_flags_must_not_contain_substrings", [])
    should_empty = expected.get("ambiguity_flags_should_be_empty", False)

    if should_empty:
        return {
            "recall_pass": 1, "recall_total": 1,  # vacuously satisfied
            "precision_pass": 1 if len(actual_flags) == 0 else 0, "precision_total": 1,
            "detail": f"Expected empty, got {len(actual_flags)} flags",
        }

    recall_pass = 0
    for m in must:
        sub = m.get("clause_substring", "").lower()
        min_sev = m.get("min_severity", "low")
        sev_rank = {"low": 0, "medium": 1, "high": 2}
        for flag in actual_flags:
            if sub in flag.get("clause", "").lower():
                if sev_rank.get(flag.get("severity", "low"), 0) >= sev_rank.get(min_sev, 0):
                    recall_pass += 1
                    break

    # Precision is only counted when must_not has entries.
    # Otherwise both pass and total are 0 (no measurement).
    if must_not:
        precision_pass = 1
        for sub in must_not:
            for flag in actual_flags:
                if sub.lower() in flag.get("clause", "").lower():
                    precision_pass = 0
                    break
        precision_total = 1
    else:
        precision_pass = 0
        precision_total = 0

    return {
        "recall_pass": recall_pass,
        "recall_total": len(must),
        "precision_pass": precision_pass,
        "precision_total": precision_total,
    }

def score_discrepancies(actual_disc: List[Dict], expected: Dict) -> Dict[str, Any]:
    must = expected.get("discrepancies_must_contain", [])
    should_empty = expected.get("discrepancies_should_be_empty", False)
    if should_empty:
        return {"passed": 1 if len(actual_disc) == 0 else 0, "total": 1}
    if not must:
        return {"passed": 0, "total": 0}
    matches = 0
    for m in must:
        sub = m.get("field_substring", "").lower()
        for d in actual_disc:
            if sub in d.get("field", "").lower():
                matches += 1
                break
    return {"passed": matches, "total": len(must)}

# ---------------------------------------------------------------------------
# Main eval loop
# ---------------------------------------------------------------------------
def run_eval(model: Optional[str] = None, only: Optional[List[str]] = None) -> None:
    model = model or os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    prompt = load_prompt()
    eval_set = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    cases = eval_set["cases"]
    if only:
        cases = [c for c in cases if c["show_id"] in only]

    print(f"\n{'='*78}")
    print(f"EVAL HARNESS — model={model}, cases={len(cases)}")
    print(f"{'='*78}\n")

    results = []
    total_field_pass, total_field_total = 0, 0
    total_ambig_recall_pass, total_ambig_recall_total = 0, 0
    total_ambig_prec_pass, total_ambig_prec_total = 0, 0
    total_disc_pass, total_disc_total = 0, 0
    total_recoup_pass, total_recoup_total = 0, 0
    errors = []

    for i, case in enumerate(cases, 1):
        sid = case["show_id"]
        label = case["label"][:60]
        print(f"[{i}/{len(cases)}] {sid}  {label}")

        user_input = format_case_input(case)
        messages = build_messages(prompt, user_input)

        try:
            llm_out = call_openrouter(messages, model)
            parsed = llm_out["parsed"]
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            errors.append({"show_id": sid, "error": str(e)})
            results.append({"show_id": sid, "error": str(e)})
            continue

        actual_extracted = parsed.get("extracted", {})
        actual_ambig = parsed.get("ambiguity_flags", [])
        actual_disc = parsed.get("discrepancies", [])
        actual_recoups = actual_extracted.get("planned_recoups", [])

        f_score = score_extracted_fields(actual_extracted, case["expected"].get("extracted", {}))
        a_score = score_ambiguity(actual_ambig, case["expected"])
        d_score = score_discrepancies(actual_disc, case["expected"])
        r_score = score_planned_recoups(actual_recoups, case["expected"].get("extracted", {}))

        total_field_pass += f_score["passed"]; total_field_total += f_score["total"]
        total_ambig_recall_pass += a_score["recall_pass"]; total_ambig_recall_total += a_score["recall_total"]
        total_ambig_prec_pass += a_score["precision_pass"]; total_ambig_prec_total += a_score["precision_total"]
        total_disc_pass += d_score["passed"]; total_disc_total += d_score["total"]
        total_recoup_pass += r_score["passed"]; total_recoup_total += r_score["total"]

        f_str = f"fields {f_score['passed']}/{f_score['total']}"
        a_str = f"ambig_recall {a_score['recall_pass']}/{a_score['recall_total']}"
        d_str = f"disc {d_score['passed']}/{d_score['total']}"
        r_str = f"recoups {r_score['passed']}/{r_score['total']}"
        print(f"  ✓ {f_str}, {a_str}, {d_str}, {r_str}")

        results.append({
            "show_id": sid,
            "label": case["label"],
            "field_score": f_score,
            "ambiguity_score": a_score,
            "discrepancy_score": d_score,
            "recoup_score": r_score,
            "actual_output": parsed,
            "usage": llm_out.get("usage", {}),
        })

    print(f"\n{'='*78}")
    print(f"AGGREGATE RESULTS")
    print(f"{'='*78}")
    def pct(p, t):
        return f"{100*p/t:.1f}%" if t else "n/a"
    print(f"  Field accuracy:         {total_field_pass}/{total_field_total} = {pct(total_field_pass, total_field_total)}")
    print(f"  Ambiguity recall:       {total_ambig_recall_pass}/{total_ambig_recall_total} = {pct(total_ambig_recall_pass, total_ambig_recall_total)}")
    print(f"  Ambiguity precision*:   {total_ambig_prec_pass}/{total_ambig_prec_total} = {pct(total_ambig_prec_pass, total_ambig_prec_total)}")
    print(f"  Discrepancy recall:     {total_disc_pass}/{total_disc_total} = {pct(total_disc_pass, total_disc_total)}")
    print(f"  Planned-recoup recall:  {total_recoup_pass}/{total_recoup_total} = {pct(total_recoup_pass, total_recoup_total)}")
    print(f"  Errors:                 {len(errors)}/{len(cases)}")
    print(f"  (*precision = no false flags on cases where must_not_contain is specified)")

    targets = eval_set["meta"].get("scoring", {})
    print(f"\n  Target field accuracy:    {targets.get('field_accuracy_target', 0)*100:.0f}%")
    print(f"  Target ambiguity recall:  {targets.get('ambiguity_recall_target', 0)*100:.0f}%")
    print(f"  Target discrepancy recall:{targets.get('discrepancy_recall_target', 0)*100:.0f}%")

    summary = {
        "model": model,
        "ran_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "totals": {
            "field_pass": total_field_pass, "field_total": total_field_total,
            "ambig_recall_pass": total_ambig_recall_pass, "ambig_recall_total": total_ambig_recall_total,
            "ambig_precision_pass": total_ambig_prec_pass, "ambig_precision_total": total_ambig_prec_total,
            "discrepancy_pass": total_disc_pass, "discrepancy_total": total_disc_total,
            "recoup_pass": total_recoup_pass, "recoup_total": total_recoup_total,
        },
        "results": results,
        "errors": errors,
    }
    RESULTS_FILE.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(f"\n  Full results written to: {RESULTS_FILE.relative_to(ROOT)}")


if __name__ == "__main__":
    # Optional: pass specific show IDs as args to run only those
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    run_eval(only=only)
