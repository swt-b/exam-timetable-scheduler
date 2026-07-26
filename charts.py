"""
Charts for the evaluation.

Runs the solver, compares it against the baselines, and shows the results as
graphs. Each chart opens in a window; close it to see the next one. Every
chart is also saved as a .png next to this file.

Run:  python charts.py
      python charts.py --save    (save the files without opening windows)
"""

import copy
import os
import sys
import time

import matplotlib
import matplotlib.pyplot as plt

from engine import (load_data, solve, verify, quality_score, attendance)
from experiments import make_scenarios, solve_flex, random_baseline

DATASET = "data/softwarica_exams.json"
OUT = os.path.dirname(os.path.abspath(__file__))

NAVY, INDIGO, GREEN, AMBER, RED = "#1a1f36", "#818cf8", "#059669", "#d97706", "#dc2626"
PALETTE = ["#4e79a7", "#f28e2b", "#59a14f", "#e15759", "#76b7b2", "#af7aa1"]

SAVE_ONLY = "--save" in sys.argv
if SAVE_ONLY:
    matplotlib.use("Agg")

plt.rcParams.update({
    "figure.figsize": (9, 5),
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "--",
})


def finish(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    print(f"  saved {name}")
    if SAVE_ONLY:
        plt.close(fig)
    else:
        plt.show()


# --- 1. the problem ---

def chart_problem(data):
    groups = sorted(data["groups"].items(), key=lambda kv: -kv[1])
    venues = sorted(data["venues"], key=lambda v: -v["capacity"])

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    bars = axes[0].bar([g for g, _ in groups], [n for _, n in groups], color=PALETTE)
    axes[0].bar_label(bars, padding=3, fontsize=9)
    axes[0].set_ylabel("Students")
    axes[0].set_title("Students per group", fontweight="bold", loc="left")
    axes[0].tick_params(axis="x", rotation=20)

    bars = axes[1].bar([v["name"] for v in venues],
                       [v["capacity"] for v in venues], color=NAVY)
    axes[1].bar_label(bars, padding=3, fontsize=9)
    axes[1].set_ylabel("Seats")
    axes[1].set_title("Room capacity", fontweight="bold", loc="left")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle("The problem: who needs scheduling, and where can they sit",
                 fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    finish(fig, "chart_problem.png")


# --- 2. exam sizes against room capacities ---

def chart_sizes(data):
    sizes = sorted(((attendance(t, data), t["name"]) for t in data["tasks"]),
                   reverse=True)
    caps = sorted({v["capacity"] for v in data["venues"]})

    fig, ax = plt.subplots(figsize=(9, 6))
    fits = [sum(1 for v in data["venues"] if v["capacity"] >= n) for n, _ in sizes]
    colors = [RED if f == 1 else AMBER if f == 2 else INDIGO for f in fits]
    bars = ax.barh([n for _, n in sizes][::-1], [n for n, _ in sizes][::-1],
                   color=colors[::-1])
    ax.bar_label(bars, padding=3, fontsize=8)
    for c in caps:
        ax.axvline(c, color="#bbb", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Students sitting the exam")
    ax.set_title("Exam sizes (red: only one room fits, amber: two)",
                 fontweight="bold", loc="left")
    ax.set_xlim(0, max(n for n, _ in sizes) * 1.15)
    fig.tight_layout()
    finish(fig, "chart_exam_sizes.png")


# --- 3. the solution ---

def chart_solution(data, result):
    per_slot = {s: 0 for s in data["slots"]}
    per_room = {}
    util = []
    caps = {v["name"]: v["capacity"] for v in data["venues"]}
    for name, (slot, room) in result.items():
        per_slot[slot] += 1
        per_room[room] = per_room.get(room, 0) + 1
        util.append(attendance(data["_by_name"][name], data) / caps[room] * 100)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    bars = axes[0].bar(range(len(per_slot)), list(per_slot.values()), color=INDIGO)
    axes[0].bar_label(bars, padding=2, fontsize=8)
    axes[0].set_xticks(range(len(per_slot)))
    axes[0].set_xticklabels(per_slot.keys(), rotation=45, ha="right", fontsize=8)
    axes[0].set_ylabel("Exams")
    axes[0].set_title("Exams per time slot", fontweight="bold", loc="left")

    rooms = sorted(per_room.items(), key=lambda kv: -kv[1])
    axes[1].pie([n for _, n in rooms], labels=[r for r, _ in rooms],
                autopct="%1.0f%%", colors=PALETTE, startangle=90,
                wedgeprops={"edgecolor": "white", "linewidth": 1.5})
    axes[1].set_title("Share of exams by room", fontweight="bold", loc="left")

    fig.suptitle(f"The solution: {len(result)} exams, "
                 f"{len(verify(result, data))} clashes, "
                 f"quality {quality_score(result, data)}/100, "
                 f"{sum(util)/len(util):.0f}% mean room utilisation",
                 fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    finish(fig, "chart_solution.png")


# --- 4. fairness: exams per group per day ---

def chart_fairness(data, result):
    days = []
    for s in data["slots"]:
        d = s.split()[0]
        if d not in days:
            days.append(d)
    groups = sorted(data["groups"])
    grid = [[0] * len(days) for _ in groups]
    for name, (slot, _room) in result.items():
        d = days.index(slot.split()[0])
        for g in data["_by_name"][name]["groups"]:
            grid[groups.index(g)][d] += 1

    fig, ax = plt.subplots(figsize=(8, 4.2))
    im = ax.imshow(grid, cmap="YlOrRd", vmin=0,
                   vmax=max(2, max(max(r) for r in grid)))
    ax.set_xticks(range(len(days)), days)
    ax.set_yticks(range(len(groups)), groups)
    ax.grid(False)
    for i in range(len(groups)):
        for j in range(len(days)):
            ax.text(j, i, grid[i][j], ha="center", va="center",
                    fontweight="bold",
                    color="white" if grid[i][j] >= 2 else "#333")
    ax.set_title("Exams per group per day (2 or more would cost quality)",
                 fontweight="bold", loc="left")
    fig.colorbar(im, ax=ax, shrink=0.8, label="exams")
    fig.tight_layout()
    finish(fig, "chart_fairness.png")


# --- 5. comparison against baselines ---

def chart_comparison():
    print("  running experiments, the impossible scenario takes ~20s...")
    scenarios = make_scenarios(DATASET)
    rows = []
    for sname, sdata in scenarios.items():
        for method, kw in [("full", dict(use_mrv=True, use_ordering=True)),
                           ("no-mrv", dict(use_mrv=False, use_ordering=True)),
                           ("no-order", dict(use_mrv=True, use_ordering=False))]:
            d = copy.deepcopy(sdata)
            st = {"attempts": 0, "backtracks": 0}
            t0 = time.time()
            res = solve_flex({}, d["tasks"], d, st, **kw)
            rows.append({"scenario": sname, "method": method,
                         "time": time.time() - t0, "tried": st["attempts"],
                         "quality": quality_score(res, d) if res else None,
                         "clashes": len(verify(res, d)) if res else None})
        d = copy.deepcopy(sdata)
        res = random_baseline(d)
        rows.append({"scenario": sname, "method": "random", "time": 0.0,
                     "tried": 0, "quality": quality_score(res, d),
                     "clashes": len(verify(res, d))})

    pick = lambda s, m, k: next(r[k] for r in rows
                                if r["scenario"] == s and r["method"] == m)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.3))

    methods = ["full", "no-mrv", "no-order"]
    q = [pick("full", m, "quality") for m in methods]
    bars = axes[0].bar(methods, q,
                       color=[GREEN if v >= 80 else AMBER if v >= 40 else RED for v in q])
    axes[0].bar_label(bars, fmt="%.0f", padding=3, fontweight="bold")
    axes[0].set_ylim(0, 115)
    axes[0].set_ylabel("Quality score")
    axes[0].set_title("Soft constraints decide quality", fontweight="bold", loc="left")

    scen = list(scenarios)
    cl = [pick(s, "random", "clashes") for s in scen]
    bars = axes[1].bar(scen, cl, color=RED)
    axes[1].bar_label(bars, padding=3, fontweight="bold")
    axes[1].set_ylabel("Constraint violations")
    axes[1].set_title("Random baseline always clashes", fontweight="bold", loc="left")
    axes[1].tick_params(axis="x", rotation=20)

    t = [pick("impossible", m, "time") for m in methods]
    bars = axes[2].bar(methods, t, color=[GREEN, RED, GREEN])
    axes[2].bar_label(bars, fmt="%.2fs", padding=3, fontweight="bold")
    axes[2].set_yscale("log")
    axes[2].set_ylabel("Seconds (log scale)")
    axes[2].set_title("MRV proves impossibility faster", fontweight="bold", loc="left")

    fig.suptitle("Our system against three alternatives",
                 fontweight="bold", x=0.02, ha="left")
    fig.tight_layout()
    finish(fig, "chart_comparison.png")

    print(f"\n  quality with soft constraints    : {pick('full','full','quality')}/100")
    print(f"  quality without them             : {pick('full','no-order','quality')}/100")
    print(f"  random baseline clashes (full)   : {pick('full','random','clashes')}")
    print(f"  prove impossible, with MRV       : {pick('impossible','full','time'):.2f}s")
    print(f"  prove impossible, without MRV    : {pick('impossible','no-mrv','time'):.2f}s")


def main():
    data = load_data(DATASET)
    stats = {"attempts": 0, "backtracks": 0}
    t0 = time.time()
    result = solve({}, data["tasks"], data, stats)
    elapsed = time.time() - t0

    print(f"\nSolved {len(result)} exams in {elapsed:.3f}s")
    print(f"  clashes    : {len(verify(result, data))}")
    print(f"  quality    : {quality_score(result, data)}/100")
    print(f"  backtracks : {stats['backtracks']}\n")

    chart_problem(data)
    chart_sizes(data)
    chart_solution(data, result)
    chart_fairness(data, result)
    chart_comparison()

    print("\nDone. All charts saved as chart_*.png")


if __name__ == "__main__":
    main()
