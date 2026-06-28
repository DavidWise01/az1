#!/usr/bin/env python3
"""
AZ1 — Universe One · daily tick.
One heartbeat a day: run one epoch over the corpus, record it in az1-chronicle.json,
commit + push (ONLY the chronicle file). Build can be progress OR regress — births,
build-outs, mutations, prunings, merges, dormancy, and the rare catastrophe.
Idempotent per day (re-running the same day is a no-op). Touches az1 only.
Disable: Task Scheduler -> delete task "AZ1-Universe-Tick".

run_epoch() is a pure function (no IO, no git) so the burn-in harness (_simulate.py)
exercises the exact same code path.
"""
import json, os, re, sys, random, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
CORP = os.path.join(HERE, "az1-corpus.json")
CHRON = os.path.join(HERE, "az1-chronicle.json")
STOP = set("the a of is to and in on my x ii iii iv v vi".split())

ACTIONS = [("build", 0.34), ("birth", 0.16), ("mutate", 0.14),
           ("prune", 0.16), ("merge", 0.08), ("dormancy", 0.08), ("catastrophe", 0.04)]

def load(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def toks(name):
    return [w for w in re.split(r"[^a-z0-9]+", name.lower()) if w and w not in STOP and len(w) > 2]

def distinct(ws):
    return sorted(ws, key=len, reverse=True)[0] if ws else "idea"

def run_epoch(chron, corpus, today):
    """Advance the universe one 24h block. Pure: mutates `chron`, returns the log entry."""
    random.seed(int(today.replace("-", "")) + chron["epoch"])
    ideas = chron["ideas"]; pop = chron["pop"]; tot = chron["totals"]
    r = random.random(); acc = 0; kind = "dormancy"
    for k, w in ACTIONS:
        acc += w
        if r <= acc:
            kind = k; break

    def two(): return random.choice(corpus), random.choice(corpus)
    text = ""
    if kind == "build":
        a, b = two(); ta, tb = distinct(toks(a)), distinct(toks(b))
        nm = (ta + "-recursion") if ta == tb else (ta + "-" + tb)
        ideas.insert(0, nm); tot["built"] += 1; pop += random.randint(1, 4)
        text = "built %s — %s x %s, “%s” met “%s”." % (nm, a, b, ta, tb)
    elif kind == "birth":
        n = random.randint(2, 7); pop += n
        text = "%d new citizens drifted in from the corpus." % n
    elif kind == "mutate" and ideas:
        i = random.randrange(len(ideas)); old = ideas[i]
        new = old.split("-")[0] + "-" + distinct(toks(random.choice(corpus)))
        ideas[i] = new
        text = "%s mutated — became %s." % (old, new)
    elif kind == "prune" and ideas:
        gone = ideas.pop(); tot["lost"] += 1; pop = max(12, pop - random.randint(1, 3))
        text = "%s died out — pruned, the weakest let go." % gone
    elif kind == "merge" and len(ideas) >= 2:
        x = ideas.pop(0); y = ideas.pop(0)
        nm = x.split("-")[0] + "-" + y.split("-")[0]
        ideas.insert(0, nm)
        text = "%s and %s merged into %s — two lineages became one." % (x, y, nm)
    elif kind == "catastrophe" and ideas:
        k = min(len(ideas), random.randint(3, 6))
        for _ in range(k):
            ideas.pop()
        tot["lost"] += k; pop = max(12, pop - random.randint(4, 12))
        text = "a catastrophe — %d ideas went extinct in a single night." % k
    else:
        kind = "dormancy"
        text = "the universe rested; nothing crossed today."

    pop = max(12, min(220, pop))
    chron["ideas"] = ideas[:60]
    chron["pop"] = pop
    chron["epoch"] += 1
    chron["updated"] = today
    chron["totals"] = tot
    entry = {"date": today, "epoch": chron["epoch"], "kind": kind, "text": text,
             "pop": pop, "built": tot["built"], "lost": tot["lost"]}
    chron["log"].insert(0, entry)
    chron["log"] = chron["log"][:150]
    return entry

def main():
    corpus = load(CORP, [])
    if not corpus:
        print("az1 tick: no corpus.json; abort."); return 0
    chron = load(CHRON, {"updated": "", "epoch": 0, "totals": {"built": 0, "lost": 0},
                         "pop": 64, "ideas": [], "log": []})
    today = datetime.date.today().isoformat()
    if chron["log"] and chron["log"][0].get("date") == today:
        print("az1 tick: already ticked today (%s); no-op." % today); return 0

    entry = run_epoch(chron, corpus, today)
    with open(CHRON, "w", encoding="utf-8") as f:
        json.dump(chron, f, ensure_ascii=False, indent=1)
    print("az1 epoch %d · %s · %s :: %s" % (chron["epoch"], today, entry["kind"], entry["text"]))

    try:
        run = lambda *a: subprocess.run(a, cwd=HERE, capture_output=True, text=True)
        run("git", "add", "az1-chronicle.json")
        c = run("git", "-c", "user.name=DavidWise01", "-c", "user.email=r.giskard.01@gmail.com",
                "commit", "-m", "az1 epoch %d · %s · %s" % (chron["epoch"], today, entry["kind"]))
        p = run("git", "push", "origin", "HEAD")
        print("push:", "ok" if p.returncode == 0 else "FAILED (left as local commit) " + (p.stderr or "").strip()[:120])
    except Exception as e:
        print("git step skipped:", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
