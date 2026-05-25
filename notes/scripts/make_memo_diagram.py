"""
Generate the Before/After flow diagram for the memo.

Emits notes/memo-diagram.excalidraw (JSON). Open at https://excalidraw.com
via Menu -> Open, then export PNG/SVG to embed in the memo.

Two stacked swim lanes:
  TOP — TODAY — the deal is a ghost
  BOT — WITH SLICE — the deal is the shared artifact

Run:
  python -X utf8 notes/scripts/make_memo_diagram.py
"""
import json, os, secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "notes" / "memo-diagram.excalidraw"

# --------- color palette (matches Greenroom-ish: muted, professional) ---------
COL = {
    "ink": "#1f2937",
    "ink_soft": "#6b7280",
    "rose": "#be123c",
    "rose_bg": "#fff1f2",
    "amber": "#b45309",
    "amber_bg": "#fef3c7",
    "brand": "#0f766e",  # teal-700, stands in for Greenroom green
    "brand_bg": "#ecfdf5",
    "sky": "#0369a1",
    "sky_bg": "#e0f2fe",
    "white": "#ffffff",
    "transparent": "transparent",
}

def _id() -> str:
    return secrets.token_hex(10)

def _seed() -> int:
    return secrets.randbits(31)

_now = 1_716_500_000_000

# --------- element factories ---------
def rect(x, y, w, h, *, stroke=COL["ink"], fill=COL["transparent"], fillStyle="solid",
         strokeWidth=2, strokeStyle="solid", roughness=1, opacity=100, roundness=True,
         eid=None, groupIds=()):
    return {
        "id": eid or _id(),
        "type": "rectangle",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": stroke, "backgroundColor": fill,
        "fillStyle": fillStyle, "strokeWidth": strokeWidth, "strokeStyle": strokeStyle,
        "roughness": roughness, "opacity": opacity,
        "groupIds": list(groupIds), "frameId": None,
        "roundness": {"type": 3} if roundness else None,
        "seed": _seed(), "versionNonce": _seed(),
        "isDeleted": False, "boundElements": [], "updated": _now,
        "link": None, "locked": False,
    }

def text(x, y, content, *, size=18, color=COL["ink"], align="left", family=2,
         w=None, h=None, container_id=None, groupIds=()):
    # rough sizing if not provided
    if w is None:
        w = max(60, int(8 * size * max(len(line) for line in content.split("\n")) / 16))
    if h is None:
        h = (content.count("\n") + 1) * int(size * 1.25)
    el = {
        "id": _id(),
        "type": "text",
        "x": x, "y": y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": color, "backgroundColor": COL["transparent"],
        "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
        "roughness": 1, "opacity": 100,
        "groupIds": list(groupIds), "frameId": None, "roundness": None,
        "seed": _seed(), "versionNonce": _seed(),
        "isDeleted": False, "boundElements": [], "updated": _now,
        "link": None, "locked": False,
        "fontSize": size, "fontFamily": family, "text": content,
        "textAlign": align, "verticalAlign": "top",
        "containerId": container_id, "originalText": content,
        "lineHeight": 1.25,
    }
    return el

def arrow(x1, y1, x2, y2, *, color=COL["ink"], strokeWidth=2, strokeStyle="solid",
          dashed=False, end_head="arrow", roughness=1, groupIds=()):
    pts = [[0, 0], [x2 - x1, y2 - y1]]
    return {
        "id": _id(),
        "type": "arrow",
        "x": x1, "y": y1, "width": abs(x2 - x1), "height": abs(y2 - y1) or 1,
        "angle": 0,
        "strokeColor": color, "backgroundColor": COL["transparent"],
        "fillStyle": "solid", "strokeWidth": strokeWidth,
        "strokeStyle": "dashed" if dashed else strokeStyle,
        "roughness": roughness, "opacity": 100,
        "groupIds": list(groupIds), "frameId": None, "roundness": {"type": 2},
        "seed": _seed(), "versionNonce": _seed(),
        "isDeleted": False, "boundElements": [], "updated": _now,
        "link": None, "locked": False,
        "points": pts,
        "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": end_head,
    }

def poly_arrow(points, *, color=COL["ink"], strokeWidth=2, dashed=False,
               end_head="arrow", roughness=1):
    """
    Multi-segment arrow. `points` is a list of absolute (x, y) tuples.
    The arrowhead lands at the LAST point.
    """
    assert len(points) >= 2
    base_x, base_y = points[0]
    rel = [[p[0] - base_x, p[1] - base_y] for p in points]
    # Bounding box
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w = max(xs) - min(xs) or 1
    h = max(ys) - min(ys) or 1
    return {
        "id": _id(),
        "type": "arrow",
        "x": base_x, "y": base_y, "width": w, "height": h,
        "angle": 0,
        "strokeColor": color, "backgroundColor": COL["transparent"],
        "fillStyle": "solid", "strokeWidth": strokeWidth,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": roughness, "opacity": 100,
        "groupIds": [], "frameId": None, "roundness": {"type": 2},
        "seed": _seed(), "versionNonce": _seed(),
        "isDeleted": False, "boundElements": [], "updated": _now,
        "link": None, "locked": False,
        "points": rel,
        "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": end_head,
    }

def line(x1, y1, x2, y2, *, color=COL["ink"], strokeWidth=1, dashed=False, opacity=100):
    return {
        "id": _id(),
        "type": "line",
        "x": x1, "y": y1, "width": abs(x2 - x1) or 1, "height": abs(y2 - y1) or 1,
        "angle": 0,
        "strokeColor": color, "backgroundColor": COL["transparent"],
        "fillStyle": "solid", "strokeWidth": strokeWidth,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1, "opacity": opacity,
        "groupIds": [], "frameId": None, "roundness": {"type": 2},
        "seed": _seed(), "versionNonce": _seed(),
        "isDeleted": False, "boundElements": [], "updated": _now,
        "link": None, "locked": False,
        "points": [[0, 0], [x2 - x1, y2 - y1]],
        "lastCommittedPoint": None,
        "startBinding": None, "endBinding": None,
        "startArrowhead": None, "endArrowhead": None,
    }

# --------- composite: a stage card (rect + title + subtitle) ----------
def stage(x, y, w, h, title, subtitle=None, *, stroke=COL["ink"], fill=COL["white"],
          title_size=14, sub_size=11, sub_color=COL["ink_soft"]):
    out = []
    g = _id()
    out.append(rect(x, y, w, h, stroke=stroke, fill=fill, fillStyle="solid", roundness=True, groupIds=(g,)))
    out.append(text(x + 12, y + 10, title, size=title_size, color=stroke, w=w - 24, groupIds=(g,)))
    if subtitle:
        out.append(text(x + 12, y + 10 + int(title_size * 1.4), subtitle,
                        size=sub_size, color=sub_color, w=w - 24, groupIds=(g,)))
    return out

# --------- composite: a swim-lane background ---------
def lane(x, y, w, h, label, *, fill=COL["white"], border=COL["ink_soft"]):
    out = []
    out.append(rect(x, y, w, h, stroke=border, fill=fill, strokeWidth=1,
                    strokeStyle="solid", roughness=0))
    out.append(text(x + 16, y + 12, label, size=14, color=COL["ink_soft"], family=2))
    return out

# =============================================================================
# Layout
# =============================================================================
elements = []

# Canvas: ~1600 x 1100. Bigger lanes give callouts breathing room.
W = 1600
LANE_H = 440
LANE_GAP = 60

# ---------- Title ----------
elements.append(text(80, 30, "Deal flow at The Crescent — today vs. with the slice",
                     size=24, color=COL["ink"], w=1200))
elements.append(text(80, 60, "Slice 1 (deal capture & disambiguation) + Slice 3 (Wednesday pre-flight)",
                     size=14, color=COL["ink_soft"], w=1200))

# ---------- Lane 1: TODAY ----------
L1_Y = 110
elements += lane(60, L1_Y, W - 120, LANE_H, "TODAY  ·  the deal is a ghost",
                 fill="#fffaf0", border=COL["amber"])

# Stage positions in lane 1 — wider spacing so arrows breathe
sx = [110, 380, 660, 940, 1240]
sy = L1_Y + 90
sw, sh = 230, 110

# 1. Agent email (origin — neutral border)
elements += stage(sx[0], sy, sw, sh,
                  "Agent deal email",
                  "Andrea, WME · 80 words.\n4 of them are ambiguous.",
                  stroke=COL["ink"], fill=COL["white"])

# 2. Mariana notes
elements += stage(sx[1], sy, sw, sh,
                  "Mariana's notes",
                  "Freetext, no structure.\nDrift from email begins.",
                  stroke=COL["amber"], fill=COL["amber_bg"])

# 3. Structured fields
elements += stage(sx[2], sy, sw, sh,
                  "Structured fields",
                  "29–76% NULL.\nStale where filled.",
                  stroke=COL["amber"], fill=COL["amber_bg"])

# 4. 2am settlement
elements += stage(sx[3], sy, sw, sh,
                  "Friday 2am settle",
                  "TM signs \"Looks good.\"\n(Same phrase whether OK\nor about to dispute.)",
                  stroke=COL["amber"], fill=COL["amber_bg"])

# 5. Monday dispute
elements += stage(sx[4], sy, sw, sh,
                  "Monday morning",
                  "Agent reads → dispute.\n$720 + agency goodwill\ngone.",
                  stroke=COL["rose"], fill=COL["rose_bg"])

# Arrows between stages (with drift indication)
for i in range(len(sx) - 1):
    x1 = sx[i] + sw
    x2 = sx[i + 1]
    color = COL["rose"] if i == 3 else COL["amber"] if i >= 1 else COL["ink_soft"]
    dashed = i == 3   # only the Friday->Monday arrow is dashed (the 12-36h gap)
    elements.append(arrow(x1 + 4, sy + sh // 2, x2 - 4, sy + sh // 2,
                          color=color, dashed=dashed, strokeWidth=2))

# ONE keystone annotation, ABOVE the arrow gap (no overlap with any box)
gap_x_center = (sx[3] + sw + sx[4]) // 2
elements.append(text(gap_x_center - 90, sy - 38,
                     "85% of disputes open\n12–36h AFTER \"Looks good\"",
                     size=11, color=COL["rose"], w=200, align="center"))
# Small vertical tick from the annotation down to the arrow
elements.append(line(gap_x_center, sy - 4, gap_x_center, sy + sh // 2 - 6,
                     color=COL["rose"], strokeWidth=1, dashed=True, opacity=70))

# Bottom strip: Coastal Spell callout in TODAY lane
cy = L1_Y + LANE_H - 110
elements += stage(110, cy, 1380, 84,
                  "Coastal Spell · March 2025  (the canonical case)",
                  '"Expenses capped at $2,500, marketing recoup of $900 against gross."     →     Two readings.     $11,565 vs $12,285.     $720 paid out + agent trust lost.',
                  stroke=COL["rose"], fill=COL["rose_bg"], title_size=13, sub_size=12,
                  sub_color=COL["ink"])

# ---------- Lane 2: WITH SLICE ----------
L2_Y = L1_Y + LANE_H + LANE_GAP
elements += lane(60, L2_Y, W - 120, LANE_H, "WITH SLICE  ·  the deal is the shared artifact",
                 fill="#f0fdf4", border=COL["brand"])

# Lane 2 — 6 stages, narrower boxes, tight spacing, room for callouts above/below
ax = [80, 320, 555, 790, 1025, 1280]
ay = L2_Y + 100   # leave headroom for top callouts (2-line ones need ~60px above)
aw, ah = 215, 110

# 1. Deal sources
elements += stage(ax[0], ay, aw, ah,
                  "Agent email + notes",
                  "Mariana pastes email\n(optional). Notes always.",
                  stroke=COL["ink"], fill=COL["white"])

# 2. LLM extraction
elements += stage(ax[1], ay, aw, ah,
                  "LLM extraction",
                  "Source spans + confidence.\nAmbiguity flags w/ $ delta.",
                  stroke=COL["brand"], fill=COL["brand_bg"])

# 3. Mariana review
elements += stage(ax[2], ay, aw, ah,
                  "Mariana review",
                  "Per-field confirm/edit.\n/shows/[id]/deal",
                  stroke=COL["brand"], fill=COL["brand_bg"])

# 4. Agent confirm
elements += stage(ax[3], ay, aw, ah,
                  "Agent confirms",
                  "/deal/[token]\nConfirm or flag per item.",
                  stroke=COL["brand"], fill=COL["brand_bg"])

# 5. Wednesday pre-flight
elements += stage(ax[4], ay, aw, ah,
                  "Wednesday pre-flight",
                  "/preflight · 8 signals\nranked by risk score.",
                  stroke=COL["brand"], fill=COL["brand_bg"])

# 6. Friday clean (clean white box, brand border — denotes successful outcome)
elements += stage(ax[5], ay, aw - 20, ah,
                  "Friday — clean settle",
                  "No Monday surprise.\nLink to settlement\n(natural v2).",
                  stroke=COL["brand"], fill=COL["white"])

# Forward arrows
for i in range(len(ax) - 1):
    x1 = ax[i] + (aw - 20 if i == len(ax) - 2 else aw)
    x2 = ax[i + 1]
    elements.append(arrow(x1 + 4, ay + ah // 2, x2 - 4, ay + ah // 2,
                          color=COL["brand"], strokeWidth=2))

# Top callout for LLM extraction (ABOVE the box, no overlap with Mariana review)
llm_cx = ax[1] + aw // 2
elements.append(text(llm_cx - 110, ay - 50,
                     "Catches the ambiguous clause\nbefore the agent ever sees it",
                     size=11, color=COL["brand"], w=220, align="center"))
elements.append(line(llm_cx, ay - 10, llm_cx, ay - 2,
                     color=COL["brand"], strokeWidth=1, opacity=70))

# Top callout for Wednesday pre-flight (ABOVE the box)
pf_cx = ax[4] + aw // 2
elements.append(text(pf_cx - 175, ay - 62,
                     "Surfaces what /reports can't:\nSunday Drivers 2026-07-01 (tier_ratchet, hidden)\n+ House of Lights 2026-06-10 (planned marketing recoup)",
                     size=11, color=COL["brand"], w=350, align="center"))
elements.append(line(pf_cx, ay - 10, pf_cx, ay - 2,
                     color=COL["brand"], strokeWidth=1, opacity=70))

# Feedback loop — single multi-segment arrow that visibly returns INTO
# Mariana review's bottom edge. Reads as a true loop, not a leftward dead-end.
loop_y = ay + ah + 28
loop_start_x = ax[3] + aw // 2      # below Agent confirms
loop_end_x = ax[2] + aw // 2        # below Mariana review
elements.append(poly_arrow(
    [
        (loop_start_x, ay + ah + 2),   # start: just below Agent confirms
        (loop_start_x, loop_y),        # down
        (loop_end_x, loop_y),          # left
        (loop_end_x, ay + ah + 2),     # back up INTO Mariana review's bottom
    ],
    color=COL["amber"], dashed=True, strokeWidth=2,
))

# Loop label — BELOW the horizontal segment, centered between the two boxes
loop_label_w = 540
loop_label_x = (loop_start_x + loop_end_x) // 2 - loop_label_w // 2
elements.append(text(loop_label_x, loop_y + 8,
                     "if agent flags any item  →  Mariana revises & re-shares (tokens revoke, responses clear)",
                     size=11, color=COL["amber"], w=loop_label_w, align="center"))

# Bottom strip: measured outcome — pushed down to give the loop label room
my = L2_Y + LANE_H - 100
elements += stage(80, my, 1410, 78,
                  "Measured  ·  12-case eval + 537-show backtest",
                  "Extraction:  100% field accuracy · 100% ambiguity recall · 100% precision on clean baselines.    Wednesday-honest backtest:  41.7% recall floor (5 production signals, signal viii dropped after Q13 stress-test).    Both currently-hidden future disputes surfaced.",
                  stroke=COL["brand"], fill=COL["brand_bg"], title_size=13, sub_size=12,
                  sub_color=COL["ink"])

# ---------- Footer ----------
elements.append(text(80, L2_Y + LANE_H + 30,
                     "Repo: github.com/ghuman30/greenroom-starter   ·   branch: slice/deal-capture-preflight   ·   notes/evidence.md  carries 35 cited findings, all reproducible via notes/queries/q01-q14.py",
                     size=11, color=COL["ink_soft"], w=1500))

# =============================================================================
# Write file
# =============================================================================
out_obj = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": elements,
    "appState": {
        "viewBackgroundColor": "#fffdf7",  # warm off-white, matches Greenroom canvas
        "gridSize": None,
        "gridStep": 5,
    },
    "files": {},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out_obj, indent=2), encoding="utf-8")
print(f"Wrote {OUT}  ({len(elements)} elements)")
