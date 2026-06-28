#!/usr/bin/env python3
"""
AZ1 — Universe One · daily tick (KNIFE'S EDGE / highly competitive).
One heartbeat a day: one epoch over the corpus, recorded in az1-chronicle.json,
commit + push (ONLY the chronicle file). Survival is a contest: every idea carries a
FITNESS, the pool has a tight carrying capacity, and prunes/catastrophes/contests take
the WEAKEST. Net pressure is slightly negative — the universe is always precarious:
it builds up, gets culled, and can crash. Idempotent per day. Touches az1 only.
Disable: Task Scheduler -> delete task "AZ1-Universe-Tick".

run_epoch() is pure (no IO, no git) so _simulate.py burns in the exact same code path.
"""
import json, os, re, sys, random, datetime, subprocess
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # epoch texts use — “ ” etc.
except Exception: pass

HERE = os.path.dirname(os.path.abspath(__file__))
CORP = os.path.join(HERE, "az1-corpus.json")
CHRON = os.path.join(HERE, "az1-chronicle.json")
STOP = set("the a of is to and in on my x ii iii iv v vi".split())

# knife's edge: build-heavy attempts, but contest+prune+catastrophe keep net pressure negative
ACTIONS = [("build", 0.40), ("contest", 0.14), ("prune", 0.10), ("mutate", 0.10),
           ("birth", 0.10), ("merge", 0.06), ("dormancy", 0.06), ("catastrophe", 0.04)]
CAP = 18   # carrying capacity — a full house forces the weakest out

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

def fitness(a, b):
    sa, sb = set(toks(a)), set(toks(b))
    shared = len(sa & sb); union = len(sa | sb)
    return round(union + (2 if shared else 0) + random.random() * 3, 1)

def weakest_index(ideas):
    return min(range(len(ideas)), key=lambda i: ideas[i]["f"])

def run_epoch(chron, corpus, today):
    """Advance one 24h block. Pure: mutates `chron`, returns the log entry."""
    random.seed(int(today.replace("-", "")) + chron["epoch"])
    ideas = chron["ideas"]; pop = chron["pop"]; tot = chron["totals"]
    # migrate any legacy string ideas -> dicts
    ideas = [it if isinstance(it, dict) else {"n": it, "f": 3.0} for it in ideas]

    r = random.random(); acc = 0; kind = "dormancy"
    for k, w in ACTIONS:
        acc += w
        if r <= acc:
            kind = k; break

    text = ""
    if kind == "build":
        a, b = random.choice(corpus), random.choice(corpus)
        ta, tb = distinct(toks(a)), distinct(toks(b))
        nm = (ta + "-recursion") if ta == tb else (ta + "-" + tb)
        f = fitness(a, b)
        ideas.insert(0, {"n": nm, "f": f}); tot["built"] += 1; pop += random.randint(1, 4)
        text = "built %s (f%.1f) — %s x %s." % (nm, f, a, b)
        if len(ideas) > CAP:
            wi = weakest_index(ideas); ev = ideas.pop(wi); tot["lost"] += 1
            text += " full house — evicted weakest %s (f%.1f)." % (ev["n"], ev["f"])
    elif kind == "contest" and len(ideas) >= 2:
        ia, ib = random.sample(range(len(ideas)), 2)
        A, B = ideas[ia], ideas[ib]
        loser = A if A["f"] <= B["f"] else B
        winner = B if loser is A else A
        ideas.remove(loser); tot["lost"] += 1
        text = "contest — %s (f%.1f) beat %s (f%.1f); the weaker eliminated." % (winner["n"], winner["f"], loser["n"], loser["f"])
    elif kind == "prune" and ideas:
        wi = weakest_index(ideas); gone = ideas.pop(wi); tot["lost"] += 1; pop = max(12, pop - random.randint(1, 3))
        text = "the weakest, %s (f%.1f), was culled." % (gone["n"], gone["f"])
    elif kind == "mutate" and ideas:
        it = random.choice(ideas); old = it["f"]; it["f"] = round(max(0.5, old + random.uniform(-3, 3)), 1)
        text = "%s re-contested — fitness %.1f → %.1f." % (it["n"], old, it["f"])
    elif kind == "birth":
        n = random.randint(2, 7); pop += n
        text = "%d new citizens crowded in — pressure rises." % n
    elif kind == "merge" and len(ideas) >= 2:
        x = ideas.pop(0); y = ideas.pop(0)
        nm = x["n"].split("-")[0] + "-" + y["n"].split("-")[0]
        f = round(max(x["f"], y["f"]) + 1, 1); ideas.insert(0, {"n": nm, "f": f})
        text = "%s and %s merged into %s (f%.1f)." % (x["n"], y["n"], nm, f)
    elif kind == "catastrophe" and ideas:
        k = min(len(ideas), random.randint(3, 6))
        ideas.sort(key=lambda d: d["f"])  # weakest first
        del ideas[:k]; tot["lost"] += k; pop = max(12, pop - random.randint(4, 12))
        text = "a catastrophe — %d of the weakest swept away in one night." % k
    else:
        kind = "dormancy"
        text = "the universe held its breath; no contest today."

    pop = max(12, min(220, pop))
    chron["ideas"] = ideas[:CAP]
    chron["pop"] = pop
    chron["epoch"] += 1
    chron["updated"] = today
    chron["totals"] = tot
    entry = {"date": today, "epoch": chron["epoch"], "kind": kind, "text": text,
             "pop": pop, "alive": len(chron["ideas"]), "built": tot["built"], "lost": tot["lost"]}
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
        run("git", "-c", "user.name=DavidWise01", "-c", "user.email=r.giskard.01@gmail.com",
            "commit", "-m", "az1 epoch %d · %s · %s" % (chron["epoch"], today, entry["kind"]))
        p = run("git", "push", "origin", "HEAD")
        print("push:", "ok" if p.returncode == 0 else "FAILED (left as local commit) " + (p.stderr or "").strip()[:120])
    except Exception as e:
        print("git step skipped:", e)
    return 0

if __name__ == "__main__":
    sys.exit(main())
