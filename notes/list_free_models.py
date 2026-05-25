"""
List currently-available FREE models on OpenRouter.
Run this when the default model name in eval_harness.py is stale.

Usage:
  python -X utf8 notes/list_free_models.py
"""
import os, json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Load .env.local for API key
env_file = ROOT / ".env.local"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v

api_key = os.environ.get("OPENROUTER_API_KEY")
if not api_key:
    print("ERROR: OPENROUTER_API_KEY not set in .env.local or env")
    raise SystemExit(1)

req = urllib.request.Request(
    "https://openrouter.ai/api/v1/models",
    headers={"Authorization": f"Bearer {api_key}"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode("utf-8"))

models = data.get("data", [])
print(f"Total models available: {len(models)}\n")

free = []
for m in models:
    pricing = m.get("pricing", {})
    prompt_p = pricing.get("prompt", "0")
    completion_p = pricing.get("completion", "0")
    # Free = both prompt and completion price are 0
    if prompt_p in ("0", 0, "0.0", 0.0) and completion_p in ("0", 0, "0.0", 0.0):
        free.append(m)

print(f"FREE models ({len(free)}):\n")
# Highlight the ones we care about: deepseek, gemini, llama, qwen
priority_prefixes = ("deepseek/", "google/gemini", "meta-llama/llama", "qwen/qwen",
                     "mistralai/", "nvidia/", "moonshotai/")
priority = [m for m in free if m["id"].lower().startswith(priority_prefixes)]
others = [m for m in free if m not in priority]

print("Priority candidates for our use case:")
print("-" * 78)
for m in sorted(priority, key=lambda x: x["id"]):
    ctx = m.get("context_length", "?")
    print(f"  {m['id']:60} ctx={ctx}")

print(f"\nOther free models ({len(others)}):")
print("-" * 78)
for m in sorted(others, key=lambda x: x["id"])[:30]:
    print(f"  {m['id']}")
if len(others) > 30:
    print(f"  ... and {len(others) - 30} more")

print(f"\n\nRECOMMENDED for eval_harness.py:")
# Suggest the best free option from our priority list
suggested_order = [
    "deepseek/deepseek-chat-v3-0324:free",
    "deepseek/deepseek-r1-0528:free",
    "google/gemini-2.0-flash-exp:free",
    "google/gemini-2.5-flash-preview:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
]
free_ids = {m["id"] for m in free}
for sid in suggested_order:
    if sid in free_ids:
        print(f"  PICK THIS:  {sid}")
        print(f"\n  Set in .env.local:")
        print(f"    OPENROUTER_MODEL={sid}")
        break
else:
    print("  None of the recommended models are currently free.")
    print("  Pick one from the 'priority candidates' list above.")
