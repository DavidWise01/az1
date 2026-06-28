#!/usr/bin/env python3
"""
AZ1 — FOUNDATIONAL PHYSICS AUDIT
Steward: Marie Curie (first directive — "verify the foundational physics are in place").
Audits the laws the universe actually runs on, against the real engine (run_epoch).
Honest: az1's "physics" = the simulation's governing laws, not laws of nature.
"""
import os, sys, datetime, copy
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import _tick

corpus = _tick.load(_tick.CORP, [])
START = datetime.date(2026, 6, 28)

def fresh():
    return {"updated": "", "epoch": 0, "totals": {"built": 0, "lost": 0}, "pop": 64, "ideas": [], "log": []}

def run(n):
    ch = fresh(); es = []
    for i in range(n):
        es.append(_tick.run_epoch(ch, corpus, (START + datetime.timedelta(days=i)).isoformat()))
    return ch, es

laws = []
def law(name, ok, detail=""):
    laws.append(("✓" if ok else "✗", name, detail)); return ok

# ---- L1 Conservation: nothing is created or destroyed without a record ----
ch, es = run(300)
ok = True; why = ""
prevb = prevl = 0
for e in es:
    db, dl = e["built"] - prevb, e["lost"] - prevl; k = e["kind"]
    good = ((k == "build" and db == 1 and dl in (0, 1)) or
            (k in ("contest", "prune") and db == 0 and dl == 1) or
            (k == "catastrophe" and db == 0 and 1 <= dl <= 6 and (dl >= 3 or e["alive"] == 0)) or
            (k in ("birth", "mutate", "merge", "dormancy") and db == 0 and dl == 0))
    if not good: ok = False; why = "epoch %d %s: dbuilt=%d dlost=%d" % (e["epoch"], k, db, dl); break
    prevb, prevl = e["built"], e["lost"]
law("L1 · conservation — every birth & death is booked (built/lost reconcile)", ok, why or "300 epochs reconcile")

# ---- L2 Bounded cosmos: no infinities ----
ok = True; why = ""
for e in es:
    if not (12 <= e["pop"] <= 220): ok = False; why = "pop %d out of bounds @e%d" % (e["pop"], e["epoch"]); break
    if not (0 <= e["alive"] <= _tick.CAP): ok = False; why = "alive %d over capacity @e%d" % (e["alive"], e["epoch"]); break
law("L2 · bounded cosmos — population & idea-pool stay finite (pop≤220, alive≤%d)" % _tick.CAP, ok, why or "no runaway")

# ---- L3 Arrow of time: monotone, irreversible ----
ok = True; why = ""
for i, e in enumerate(es):
    if e["epoch"] != i + 1: ok = False; why = "epoch jump @index %d" % i; break
    if i and (e["built"] < es[i-1]["built"] or e["lost"] < es[i-1]["lost"]): ok = False; why = "totals went backwards @e%d" % e["epoch"]; break
law("L3 · arrow of time — epochs step +1; built/lost never decrease", ok, why or "monotone over 300")

# ---- L4 Determinism: identical initial conditions -> identical history ----
a = [(e["epoch"], e["kind"], e["pop"], e["built"], e["lost"]) for e in run(150)[1]]
b = [(e["epoch"], e["kind"], e["pop"], e["built"], e["lost"]) for e in run(150)[1]]
law("L4 · determinism — same seed yields the same universe (reproducible)", a == b, "150 epochs identical" if a == b else "DIVERGED")

# ---- L5 Selection (Noether-adjacent: the law that gives the universe its direction) ----
# the weakest fall: prune removes the global minimum; catastrophe removes the k smallest; a contest's loser <= winner.
def force(kind):
    base = [{"n": "f%d" % i, "f": float(i)} for i in range(1, 9)]  # fitness 1..8
    for E in range(0, 4000):
        ch = {"updated": "", "epoch": E, "totals": {"built": 0, "lost": 0}, "pop": 64,
              "ideas": [dict(x) for x in base], "log": []}
        e = _tick.run_epoch(ch, corpus, "2026-06-28")
        if e["kind"] == kind:
            return base, ch["ideas"], e
    return None, None, None

sel_ok = True; sel_why = []
b0, after, e = force("prune")
names_after = {x["n"] for x in after}
if "f1" in names_after or len(after) != 7: sel_ok = False; sel_why.append("prune did not remove the weakest")
else: sel_why.append("prune→removed f1 (min)")
b0, after, e = force("catastrophe")
removed = {"f%d" % i for i in range(1, 9)} - {x["n"] for x in after}
k = len(removed); expected = {"f%d" % i for i in range(1, k + 1)}
if removed != expected: sel_ok = False; sel_why.append("catastrophe removed %s, expected smallest %s" % (sorted(removed), sorted(expected)))
else: sel_why.append("catastrophe→removed the %d smallest" % k)
b0, after, e = force("contest")
import re
m = re.findall(r"f([0-9.]+)\)", e["text"])
if len(m) == 2 and float(m[1]) <= float(m[0]): sel_why.append("contest→loser (f%s) ≤ winner (f%s)" % (m[1], m[0]))
else: sel_ok = False; sel_why.append("contest loser not weaker: %s" % e["text"])
law("L5 · selection — the weakest fall (prune/catastrophe/contest cull the least fit)", sel_ok, " · ".join(sel_why))

# ---- report ----
print("=" * 66)
print("AZ1 · FOUNDATIONAL PHYSICS AUDIT")
print("steward: Marie Curie  ·  standard: Noether (symmetry → conservation)")
print("=" * 66)
for mark, name, detail in laws:
    print(" [%s] %s" % (mark, name))
    if detail: print("       %s" % detail)
allok = all(m == "✓" for m, _, _ in laws)
print("-" * 66)
print("note: az1's 'physics' = the laws the simulation runs on, not laws of nature.")
print("      conservation (L1) is the bookkeeping symmetry's Noether charge — analogy, flagged.")
print("=" * 66)
print("VERDICT: foundational physics %s (%d/%d laws hold)" %
      ("IN PLACE" if allok else "BROKEN", sum(1 for m, _, _ in laws if m == "✓"), len(laws)))
sys.exit(0 if allok else 1)
