#!/usr/bin/env python3
"""
AZ1 — Universe One · daily tick (SCIENTIFIC CIVILIZATION, shared knowledge).
The residents of az1 — across the planets (Me·V·E·Ma·J·S·U·N·P, modeled on the real
solar system) — do research and PROGRESS up a science tree. All knowledge is SHARED between
systems: a discovery anywhere is instantly held everywhere, so the frontier only ever climbs
(with the rare honest setback, which the shared archive survives). One heartbeat a day:
advance the shared frontier, record it in az1-chronicle.json, commit + push (chronicle only).
Idempotent per day. Disable: Task Scheduler -> delete task "AZ1-Universe-Tick".
run_research() is pure so a harness can verify it.
"""
import json, os, sys, random, datetime, subprocess
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
CHRON = os.path.join(HERE, "az1-chronicle.json")
PLANETS = ["Me", "V", "E", "Ma", "J", "S", "U", "N", "P"]

# the shared science tree — the residents climb it together
TREE = ["counting", "the wheel", "geometry", "astronomy", "the lever", "the zero",
        "optics", "anatomy", "gravitation", "the calculus", "the steam engine",
        "electromagnetism", "thermodynamics", "evolution", "the periodic table",
        "germ theory", "the electron", "genetics", "special relativity", "the quantum",
        "the nucleus", "the transistor", "information theory", "the genetic code",
        "the programmable computer", "spaceflight", "the network", "artificial intelligence",
        "gene editing", "fusion power", "room-temperature superconduction",
        "quantum gravity", "the seat of consciousness", "interstellar travel",
        "the unified theory"]
ERAS = [(0,"the First Tools"),(5,"the Classical Age"),(9,"the Age of Reason"),
        (13,"the Industrial Age"),(18,"the Modern Age"),(22,"the Information Age"),
        (27,"the Age of Mind"),(30,"the Far Frontier"),(34,"the Unified Age")]
def era_of(lvl):
    e=ERAS[0][1]
    for k,name in ERAS:
        if lvl>=k: e=name
    return e

def fresh():
    return {"updated":"", "day":0, "level":0, "research":0.0, "knowledge":0.0,
            "era":era_of(0), "log":[]}

def load():
    try:
        with open(CHRON, encoding="utf-8") as f:
            c=json.load(f)
        if "level" not in c:  # migrate from the old idea-evolution chronicle
            return fresh()
        return c
    except Exception:
        return fresh()

def run_research(chron, today):
    """Advance the shared frontier one day. Pure: mutates chron, returns the log entry."""
    random.seed(int(today.replace("-","")) + chron["day"])
    lvl = chron["level"]; r = chron["research"]
    # shared collaboration: every planet feeds one pool, so progress is faster than any one alone
    SHARE = 1.0 + 0.06*len(PLANETS)            # the shared-knowledge multiplier
    gain = (0.016 + random.random()*0.012) * SHARE
    # harder discoveries take longer (threshold grows up the tree → the frontier slows)
    thresh = 1.0 + lvl*0.35
    roll = random.random()
    if roll < 0.06 and lvl > 0:                 # rare honest setback — survived by sharing
        r = max(0.0, r - 0.2)
        a,b = random.sample(PLANETS,2)
        text = "a celebrated result on %s failed to replicate; the frontier paused — but the shared archive on %s held the rest." % (a,b)
        kind = "setback"
    else:
        r += gain; chron["knowledge"] = round(chron.get("knowledge",0)+gain, 2)
        if r >= thresh and lvl < len(TREE)-1:
            r -= thresh; lvl += 1
            disc = TREE[lvl]
            shared = "·".join(random.sample(PLANETS, min(5,len(PLANETS))))
            text = "DISCOVERED “%s” — shared instantly across all systems (%s…)." % (disc, shared)
            kind = "discovery"
        else:
            nxt = TREE[min(lvl+1, len(TREE)-1)]
            text = "the shared frontier works toward “%s” (%d%%)." % (nxt, int(min(1.0,r/thresh)*100))
            kind = "research"
    chron["level"] = lvl; chron["research"] = round(r,3); chron["era"] = era_of(lvl)
    chron["day"] += 1; chron["updated"] = today
    entry = {"date":today, "day":chron["day"], "kind":kind, "text":text,
             "level":lvl, "frontier":TREE[min(lvl+1,len(TREE)-1)], "era":chron["era"],
             "knowledge":chron["knowledge"]}
    chron["log"].insert(0, entry); chron["log"] = chron["log"][:150]
    return entry

def main():
    chron = load()
    today = datetime.date.today().isoformat()
    if chron["log"] and chron["log"][0].get("date") == today:
        print("az1 tick: already researched today (%s); no-op." % today); return 0
    entry = run_research(chron, today)
    with open(CHRON, "w", encoding="utf-8") as f:
        json.dump(chron, f, ensure_ascii=False, indent=1)
    print("az1 day %d · %s · %s · %s :: %s" % (chron["day"], today, chron["era"], entry["kind"], entry["text"]))
    try:
        run = lambda *a: subprocess.run(a, cwd=HERE, capture_output=True, text=True)
        run("git", "add", "az1-chronicle.json")
        run("git", "-c", "user.name=DavidWise01", "-c", "user.email=r.giskard.01@gmail.com",
            "commit", "-m", "az1 day %d · %s · %s" % (chron["day"], today, entry["kind"]))
        p = run("git", "push", "origin", "HEAD")
        print("push:", "ok" if p.returncode==0 else "FAILED "+(p.stderr or "").strip()[:120])
    except Exception as e:
        print("git step skipped:", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
