"""
Experiments for Part D, Evaluation
-----------------------------------
Compares four scheduling methods on three scenarios.

Methods:
    full        backtracking + MRV + value ordering (our system)
    no-mrv      backtracking, tasks in file order (MRV switched OFF)
    no-order    backtracking + MRV, but random value order (kindness OFF)
    random      baseline: every task gets a random slot+venue (no AI at all)

Scenarios:
    small       first 10 exams, all 10 slots      (easy)
    full        all 20 exams, all 10 slots        (realistic)
    stress      all 20 exams, only 5 slots        (exam-crunch week)
    impossible  all 20 exams, only 4 slots        (over-constrained: no
                solution exists; tests how fast each method PROVES it)

Metrics:
    solved | time (s) | placements tried | backtracks | clashes | quality /100

Run:  python experiments.py
"""

import copy
import random
import time

from engine import (load_data, valid_options, placement_penalty,
                    quality_score, verify)

ATTEMPT_CAP = 100_000   # stop hopeless runs so the table always finishes


# --- solver with switchable features ---

def solve_flex(assignment, unscheduled, data, stats, use_mrv, use_ordering):
    if not unscheduled:
        return assignment
    if stats["attempts"] > ATTEMPT_CAP:
        stats["capped"] = True
        return None

    options = {t["name"]: valid_options(t, assignment, data) for t in unscheduled}

    if use_mrv:
        name = min(options, key=lambda n: len(options[n]))
    else:
        name = unscheduled[0]["name"]          # naive: file order
    if not options[name]:
        return None

    task = data["_by_name"][name]
    opts = options[name]
    if use_ordering:
        opts = sorted(opts, key=lambda sv: placement_penalty(task, sv[0], assignment, data))

    for slot, venue_name in opts:
        stats["attempts"] += 1
        assignment[name] = (slot, venue_name)
        rest = [t for t in unscheduled if t["name"] != name]
        result = solve_flex(assignment, rest, data, stats, use_mrv, use_ordering)
        if result is not None:
            return result
        del assignment[name]
        stats["backtracks"] += 1
        if stats.get("capped"):
            return None
    return None


# --- random baseline ---

def random_baseline(data, seed=42):
    rng = random.Random(seed)
    assignment = {}
    for task in data["tasks"]:
        slot = rng.choice(data["slots"])
        venue = rng.choice(data["venues"])["name"]
        assignment[task["name"]] = (slot, venue)
    return assignment


# --- scenarios ---

def make_scenarios(path="data/exam_schedule.json"):
    base = load_data(path)

    small = copy.deepcopy(base)
    small["tasks"] = small["tasks"][:10]

    stress = copy.deepcopy(base)
    stress["slots"] = stress["slots"][:5]

    impossible = copy.deepcopy(base)
    impossible["slots"] = impossible["slots"][:4]

    scenarios = {"small": small, "full": base,
                 "stress": stress, "impossible": impossible}
    for d in scenarios.values():
        d["_by_name"] = {t["name"]: t for t in d["tasks"]}
    return scenarios


# --- run ---

def run_method(method, data):
    stats = {"attempts": 0, "backtracks": 0}
    start = time.time()

    if method == "random":
        result = random_baseline(data)
    else:
        use_mrv = method != "no-mrv"
        use_ordering = method != "no-order"
        result = solve_flex({}, data["tasks"], data, stats, use_mrv, use_ordering)

    elapsed = time.time() - start

    if result is None:
        solved = "CAPPED" if stats.get("capped") else "no"
        return [solved, f"{elapsed:.3f}", stats["attempts"], stats["backtracks"], "-", "-"]

    clashes = len(verify(result, data))
    quality = quality_score(result, data)
    solved = "yes" if clashes == 0 else "INVALID"
    return [solved, f"{elapsed:.3f}", stats["attempts"], stats["backtracks"], clashes, quality]


def main():
    methods = ["full", "no-mrv", "no-order", "random"]
    scenarios = make_scenarios()

    header = ["scenario", "method", "solved", "time(s)", "tried", "backtracks", "clashes", "quality"]
    rows = []
    for sc_name, data in scenarios.items():
        for m in methods:
            rows.append([sc_name, m] + run_method(m, data))

    widths = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = "  ".join(h.ljust(w) for h, w in zip(header, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(r, widths)))

    print("\nNotes:")
    print("  full     = our system (MRV + value ordering)")
    print("  no-mrv   = naive task order; shows why the MRV heuristic matters")
    print("  no-order = valid but unkind schedules; shows why soft constraints matter")
    print("  random   = no AI baseline; clashes show the problem is not trivial")
    print("  'no' on impossible = correctly proved no timetable exists")
    print("  CAPPED   = gave up after", ATTEMPT_CAP, "attempts without an answer")


if __name__ == "__main__":
    main()
