"""
Rescheduling under uncertainty
------------------------------
Real life breaks published timetables: a teacher falls sick, a hall closes.
This module REPAIRS the timetable instead of rebuilding it:

    1. Apply the disruption (new unavailability).
    2. Find only the tasks that now break a constraint.
    3. Un-place just those tasks; everything else stays fixed.
    4. Re-run the CSP solver on the affected tasks only.
    5. Report exactly what moved (minimal-disruption principle).
"""

import copy
import sys

from engine import load_data, solve, verify, conflicts, print_timetable


def apply_disruption(data, kind, who, slots):
    """kind: 'staff' or 'venue'. who: name. slots: list of slots now unavailable."""
    key = "staff_unavailable" if kind == "staff" else "venue_unavailable"
    data.setdefault(key, {}).setdefault(who, []).extend(slots)


def affected_tasks(assignment, data):
    """Tasks whose current placement now breaks a constraint."""
    broken = []
    for name, (slot, venue_name) in assignment.items():
        task = data["_by_name"][name]
        venue = next(v for v in data["venues"] if v["name"] == venue_name)
        others = {n: p for n, p in assignment.items() if n != name}
        if conflicts(task, slot, venue, others, data):
            broken.append(name)
    return broken


def repair(assignment, data):
    """Fix only the broken part of the timetable. Returns (new_assignment, moved)."""
    broken = affected_tasks(assignment, data)
    if not broken:
        return assignment, []

    fixed = {n: p for n, p in assignment.items() if n not in broken}
    to_place = [data["_by_name"][n] for n in broken]

    stats = {"attempts": 0, "backtracks": 0}
    result = solve(dict(fixed), to_place, data, stats)
    if result is None:
        return None, broken
    moved = [(n, assignment[n], result[n]) for n in broken]
    return result, moved


def demo(path="softwarica_exams.json"):
    data = load_data(path)
    data["_by_name"] = {t["name"]: t for t in data["tasks"]}

    print("STEP 1 — normal timetable:")
    stats = {"attempts": 0, "backtracks": 0}
    original = solve({}, data["tasks"], data, stats)
    print_timetable(original, data)

    print("=" * 60)
    print("STEP 2 — DISRUPTION: Sarita Rai is sick on Monday.")
    print("=" * 60)
    disrupted = copy.deepcopy(data)
    disrupted["_by_name"] = {t["name"]: t for t in disrupted["tasks"]}
    apply_disruption(disrupted, "staff", "Sarita Rai", ["Mon 9AM", "Mon 1PM"])

    repaired, moved = repair(dict(original), disrupted)
    if repaired is None:
        print("Could not repair; affected:", moved)
        return

    print(f"\nSTEP 3 — repaired by moving only {len(moved)} exam(s):")
    for name, (old_s, old_v), (new_s, new_v) in moved:
        print(f"    {name}: {old_s}/{old_v}  ->  {new_s}/{new_v}")
    untouched = len(repaired) - len(moved)
    print(f"    ({untouched} of {len(repaired)} exams untouched)")

    print_timetable(repaired, disrupted)
    problems = verify(repaired, disrupted)
    print("Verified: 0 clashes." if not problems else f"PROBLEMS: {problems}")


if __name__ == "__main__":
    demo(sys.argv[1] if len(sys.argv) > 1 else "softwarica_exams.json")
