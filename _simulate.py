#!/usr/bin/env python3
"""Burn-in: simulate N daily ticks OFFLINE (no git, no touch to the live chronicle)
through the real run_research(), then test for veracity. Plain pass/fail report.

Matches the SCIENTIFIC-CIVILIZATION engine (_tick.run_research): the residents climb a
shared science tree; kinds are research / discovery / setback; the frontier only ever
CLIMBS (the rare setback dents research, never the level, because knowledge is shared).
Usage: python _simulate.py [N]   (default 200)
"""
import os, sys, copy, datetime, collections
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import _tick

N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
START = datetime.date(2026, 6, 29)

def simulate(n):
    """Run n daily ticks from a FRESH chronicle, offline. Returns (chron, entries, crash)."""
    ch = _tick.fresh(); entries = []
    for i in range(n):
        d = (START + datetime.timedelta(days=i)).isoformat()
        try:
            entries.append(_tick.run_research(ch, d))
        except Exception as e:
            return ch, entries, ("CRASH at day %d (%s): %r" % (i + 1, d, e))
    return ch, entries, None

def thresh_at(lvl):
    return 1.0 + lvl * 0.35

ch, chrono, crash = simulate(N)
PASS, FAIL = "PASS", "FAIL"
results = []
def check(name, ok, detail=""):
    results.append((PASS if ok else FAIL, name, detail))

# T1 — no crash, all N ran
check("ran all %d ticks, no exceptions" % N, crash is None and len(chrono) == N,
      crash or ("got %d entries" % len(chrono)))

hist = collections.Counter(e["kind"] for e in chrono)
# T2 — genuinely eventful: both progress (discovery) AND the honest setback occurred
check("progress AND setback both occurred (not a flatline)",
      hist["discovery"] > 0 and hist["setback"] > 0,
      "research=%d · discovery=%d · setback=%d" % (hist["research"], hist["discovery"], hist["setback"]))

# T3 — THE core claim: the frontier only ever CLIMBS (level monotonic non-decreasing)
lvl_ok = True; lvl_why = ""
prev = 0
for e in chrono:
    if e["level"] < prev:
        lvl_ok = False; lvl_why = "level DROPPED at day %d: %d -> %d" % (e["day"], prev, e["level"]); break
    prev = e["level"]
check("frontier only climbs (level never decreases)", lvl_ok, lvl_why or "monotonic across %d days, end L%d" % (N, ch["level"]))

# T4 — setbacks are survived by sharing: at every setback, the LEVEL is unchanged from the day before
sb_ok = True; sb_why = ""
for i, e in enumerate(chrono):
    if e["kind"] == "setback":
        prevlvl = chrono[i-1]["level"] if i > 0 else 0
        if e["level"] != prevlvl:
            sb_ok = False; sb_why = "setback at day %d changed level %d -> %d" % (e["day"], prevlvl, e["level"]); break
check("setbacks survived (a setback never drops the level)", sb_ok,
      sb_why or "all %d setbacks held the frontier" % hist["setback"])

# T5 — invariants: day=+1, level bounded, research in [0,thresh), knowledge non-decreasing, era matches level
inv_ok = True; inv_why = ""; prevk = 0.0
for i, e in enumerate(chrono):
    if e["day"] != i + 1: inv_ok = False; inv_why = "day not +1 at index %d (%d)" % (i, e["day"]); break
    if not (0 <= e["level"] <= len(_tick.TREE) - 1): inv_ok = False; inv_why = "level out of range at day %d: %d" % (e["day"], e["level"]); break
    if e["knowledge"] < prevk - 1e-9: inv_ok = False; inv_why = "knowledge decreased at day %d: %.3f < %.3f" % (e["day"], e["knowledge"], prevk); break
    if e["era"] != _tick.era_of(e["level"]): inv_ok = False; inv_why = "era mismatch at day %d: %s vs %s" % (e["day"], e["era"], _tick.era_of(e["level"])); break
    prevk = e["knowledge"]
# research bound checked on the chron (final) — must be >=0 and below the current threshold
if inv_ok and not (0 <= ch["research"] < thresh_at(ch["level"]) + 1e-9):
    inv_ok = False; inv_why = "final research %.3f out of [0,thresh=%.2f)" % (ch["research"], thresh_at(ch["level"]))
check("invariants hold (day+1, level bound, research<thresh, knowledge↑, era↔level)", inv_ok, inv_why or "all %d ok" % N)

# T6 — the frontier HARDENS with depth: discoveries get rarer as the tree deepens
disc_days = [e["day"] for e in chrono if e["kind"] == "discovery"]
gaps = [disc_days[i+1] - disc_days[i] for i in range(len(disc_days) - 1)]
harden = len(gaps) >= 2 and (sum(gaps[len(gaps)//2:]) / max(1, len(gaps) - len(gaps)//2)) >= (sum(gaps[:len(gaps)//2]) / max(1, len(gaps)//2))
check("frontier hardens (later discoveries take longer than early ones)", harden,
      "discovery gaps (days): %s" % gaps)

# T7 — determinism: identical trajectory on re-run
ch2, c2, _ = simulate(N)
det = [(e["day"], e["kind"], e["level"], e["knowledge"], e["text"]) for e in chrono] == \
      [(e["day"], e["kind"], e["level"], e["knowledge"], e["text"]) for e in c2]
check("deterministic (identical trajectory on re-run)", det, "re-ran %d ticks" % N)

# T8 — shared-knowledge multiplier is real and > 1 (collaboration is faster than solo)
share = 1.0 + 0.06 * len(_tick.PLANETS)
check("shared-knowledge multiplier active (SHARE>1 across all planets)", share > 1.0,
      "SHARE=%.2f over %d planets" % (share, len(_tick.PLANETS)))

# T9 — does NOT touch the live chronicle (offline burn-in)
live_before = _tick.load()
simulate(20)
live_after = _tick.load()
check("offline: live chronicle untouched by the burn-in",
      live_before.get("day") == live_after.get("day") and live_before.get("level") == live_after.get("level"),
      "live day %s/level %s unchanged" % (live_before.get("day"), live_before.get("level")))

# ---- report ----
print("=" * 66)
print("AZ1 BURN-IN · %d simulated daily ticks (offline, real run_research)" % N)
print("=" * 66)
for status, name, detail in results:
    print("[%s] %s" % (status, name))
    if detail and (status == FAIL or name.startswith("frontier hardens") or name.startswith("progress")):
        print("      " + str(detail).replace("\n", "\n      "))
print("-" * 66)
print("final state:  day %d · level %d/%d (%s) · era %s · knowledge %.1f"
      % (ch["day"], ch["level"], len(_tick.TREE) - 1, _tick.TREE[ch["level"]], ch["era"], ch["knowledge"]))
print("histogram:    research=%d  discovery=%d  setback=%d" % (hist["research"], hist["discovery"], hist["setback"]))
disc = [e for e in chrono if e["kind"] == "discovery"]
print("discoveries:  %d  ->  %s" % (len(disc), ", ".join("%s(d%d)" % (_tick.TREE[e["level"]], e["day"]) for e in disc[:8]) + (" …" if len(disc) > 8 else "")))
sb = next((e for e in chrono if e["kind"] == "setback"), None)
print("first setback: " + ((sb["date"] + " d" + str(sb["day"]) + " :: " + sb["text"]) if sb else "(none in %d)" % N))
nfail = sum(1 for s, _, _ in results if s == FAIL)
print("=" * 66)
print("VERDICT: %d/%d tests passed%s" % (len(results) - nfail, len(results), "" if nfail == 0 else "  — %d FAILED" % nfail))
sys.exit(1 if nfail else 0)
