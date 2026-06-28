#!/usr/bin/env python3
"""Burn-in: simulate N 24h blocks OFFLINE (no git, no touch to the live chronicle)
through the real run_epoch(), then test for veracity. Prints a plain pass/fail report."""
import os, sys, json, datetime, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import _tick

N = int(sys.argv[1]) if len(sys.argv) > 1 else 100
corpus = _tick.load(_tick.CORP, [])
START = datetime.date(2026, 6, 28)

def fresh():
    return {"updated": "", "epoch": 0, "totals": {"built": 0, "lost": 0}, "pop": 64, "ideas": [], "log": []}

def simulate(n):
    ch = fresh(); entries = []
    for i in range(n):
        d = (START + datetime.timedelta(days=i)).isoformat()
        try:
            entries.append(_tick.run_epoch(ch, corpus, d))
        except Exception as e:
            return ch, entries, ("CRASH at epoch %d: %r" % (i + 1, e))
    return ch, entries, None

ch, entries, crash = simulate(N)
chrono = list(reversed(ch["log"]))  # oldest -> newest (full since N<=150)
PASS, FAIL = "PASS", "FAIL"
results = []
def check(name, ok, detail=""):
    results.append((PASS if ok else FAIL, name, detail))

# T1 — no crash, all N ran
check("ran all %d epochs, no exceptions" % N, crash is None and len(chrono) == N,
      crash or ("got %d entries" % len(chrono)))

hist = collections.Counter(e["kind"] for e in chrono)
prog = hist["build"] + hist["birth"]
regr = hist["prune"] + hist["catastrophe"]
# T2 — genuinely bidirectional
check("progress AND regress both occurred (not a flatline)", prog > 0 and regr > 0,
      "progress=%d (build %d, birth %d) · regress=%d (prune %d, catastrophe %d)"
      % (prog, hist["build"], hist["birth"], regr, hist["prune"], hist["catastrophe"]))

# T3 — distribution roughly tracks weights (generous tol for n=100; executed kinds, fallbacks land in dormancy)
wmap = dict(_tick.ACTIONS)
dist_ok = True; dist_lines = []
for k, w in _tick.ACTIONS:
    obs = hist.get(k, 0) / N
    # dormancy absorbs failed prune/merge/etc on empty ideas, so allow it to run high; others within ~2x band
    lo, hi = (0.0, 0.6) if k == "dormancy" else (max(0.0, w - 0.13), w + 0.13)
    okk = lo <= obs <= hi
    dist_ok = dist_ok and okk
    dist_lines.append("  %-12s exp %.2f  obs %.2f  %s" % (k, w, obs, "ok" if okk else "OUT"))
check("action distribution within tolerance of weights", dist_ok, "\n" + "\n".join(dist_lines))

# T4 — invariants every epoch
inv_ok = True; inv_why = ""
prev = None
for i, e in enumerate(chrono):
    if not (12 <= e["pop"] <= 220): inv_ok = False; inv_why = "pop out of [12,220] at epoch %d: %d" % (e["epoch"], e["pop"]); break
    if e["epoch"] != i + 1: inv_ok = False; inv_why = "epoch not monotonic +1 at index %d" % i; break
    if prev:
        if e["built"] < prev["built"]: inv_ok = False; inv_why = "built decreased at epoch %d" % e["epoch"]; break
        if e["lost"] < prev["lost"]: inv_ok = False; inv_why = "lost decreased at epoch %d" % e["epoch"]; break
    prev = e
check("invariants hold (pop bound, epoch+1, built/lost monotonic)", inv_ok, inv_why or "all %d ok" % N)

# T5 — accounting: per-epoch deltas reconcile with the action
acc_ok = True; acc_why = ""
prev = None
for e in chrono:
    db = e["built"] - (prev["built"] if prev else 0)
    dl = e["lost"] - (prev["lost"] if prev else 0)
    k = e["kind"]
    okk = True
    if k == "build": okk = (db == 1 and dl == 0)
    elif k == "prune": okk = (db == 0 and dl == 1)
    elif k == "catastrophe": okk = (db == 0 and 3 <= dl <= 6)
    else: okk = (db == 0 and dl == 0)  # birth/mutate/merge/dormancy change neither built nor lost
    if not okk:
        acc_ok = False; acc_why = "epoch %d kind=%s but dbuilt=%d dlost=%d" % (e["epoch"], k, db, dl); break
    prev = e
check("accounting reconciles (built/lost deltas match each action)", acc_ok,
      acc_why or "built=%d == build-events=%d; lost=%d" % (ch["totals"]["built"], hist["build"], ch["totals"]["lost"]))

# T6 — determinism: same run twice -> identical trajectory
ch2, e2, _ = simulate(N)
det = [ (e["epoch"], e["kind"], e["pop"], e["built"], e["lost"]) for e in chrono ] == \
      [ (e["epoch"], e["kind"], e["pop"], e["built"], e["lost"]) for e in list(reversed(ch2["log"])) ]
check("deterministic (identical trajectory on re-run)", det, "re-ran %d epochs" % N)

pops = [e["pop"] for e in chrono]
# ---- report ----
print("=" * 64)
print("AZ1 BURN-IN · %d simulated 24h blocks (offline, real engine)" % N)
print("=" * 64)
for status, name, detail in results:
    print("[%s] %s" % (status, name))
    if detail and (status == FAIL or "\n" in detail or name.startswith("action")):
        print("      " + detail.replace("\n", "\n      "))
print("-" * 64)
print("final state:  epoch %d · pop %d · ideas alive %d · built %d · lost %d"
      % (ch["epoch"], ch["pop"], len(ch["ideas"]), ch["totals"]["built"], ch["totals"]["lost"]))
print("pop range:    min %d  max %d  (start 64)" % (min(pops), max(pops)))
print("histogram:    " + "  ".join("%s=%d" % (k, hist.get(k, 0)) for k, _ in _tick.ACTIONS))
# sample notable days
cat = next((e for e in chrono if e["kind"] == "catastrophe"), None)
bld = next((e for e in chrono if e["kind"] == "build"), None)
prn = next((e for e in chrono if e["kind"] == "prune"), None)
print("-" * 64)
for lbl, e in [("first build", bld), ("first prune", prn), ("first catastrophe", cat)]:
    print("%-18s %s" % (lbl + ":", (e["date"] + " e" + str(e["epoch"]) + " :: " + e["text"]) if e else "(none in 100)"))
nfail = sum(1 for s, _, _ in results if s == FAIL)
print("=" * 64)
print("VERDICT: %d/%d tests passed%s" % (len(results) - nfail, len(results), "" if nfail == 0 else "  — %d FAILED" % nfail))
