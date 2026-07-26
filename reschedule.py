"""
Rescheduling under uncertainty.

When a teacher falls sick or a hall closes, the timetable is repaired rather
than rebuilt: only the tasks that now break a constraint are un-placed and
re-solved, so everything else stays where students already saw it.
This is the minimal-disruption principle.
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


def pick_disruption(assignment, data, who=None):
    """Pick a staff member and a day they actually work, so the demo stays
    meaningful when the dataset or the solver output changes.

    Returns (staff_name, day, slots_lost).
    """
    from collections import defaultdict

    day_of = lambda slot: slot.split()[0]
    by_staff = defaultdict(lambda: defaultdict(list))
    for name, (slot, _venue) in assignment.items():
        by_staff[data["_by_name"][name]["staff"]][day_of(slot)].append(slot)

    candidates = []
    for staff, days in by_staff.items():
        for day, slots in days.items():
            candidates.append((len(slots), staff, day, sorted(slots)))

    if who:                                   # honour a requested person
        mine = [c for c in candidates if c[1] == who]
        if mine:
            candidates = mine

    # busiest single day wins; ties broken alphabetically for a stable demo
    _n, staff, day, slots = max(candidates, key=lambda c: (c[0], c[1], c[2]))

    # the whole day is lost, not just the slots they happened to be given
    lost = [s for s in data["slots"] if day_of(s) == day]
    return staff, day, lost


def demo(path="data/softwarica_exams.json", who="Sarita Rai"):
    data = load_data(path)
    data["_by_name"] = {t["name"]: t for t in data["tasks"]}

    print("STEP 1: normal timetable")
    stats = {"attempts": 0, "backtracks": 0}
    original = solve({}, data["tasks"], data, stats)
    print_timetable(original, data)

    staff, day, lost = pick_disruption(original, data, who)
    affected_now = [n for n, (s, _v) in original.items()
                    if s in lost and data["_by_name"][n]["staff"] == staff]

    print("=" * 62)
    print(f"STEP 2: DISRUPTION. {staff} is unavailable all day on {day}")
    print(f"        slots lost: {', '.join(lost)}")
    print(f"        exams affected: {', '.join(sorted(affected_now)) or 'none'}")
    print("=" * 62)

    disrupted = copy.deepcopy(data)
    disrupted["_by_name"] = {t["name"]: t for t in disrupted["tasks"]}
    apply_disruption(disrupted, "staff", staff, lost)

    repaired, moved = repair(dict(original), disrupted)
    if repaired is None:
        print("Could not repair; affected:", moved)
        return

    print(f"\nSTEP 3: repaired by moving only {len(moved)} exam(s)")
    for name, (old_s, old_v), (new_s, new_v) in moved:
        print(f"    {name}: {old_s} / {old_v}  ->  {new_s} / {new_v}")
    untouched = len(repaired) - len(moved)
    print(f"    ({untouched} of {len(repaired)} exams left exactly where they were)")

    print_timetable(repaired, disrupted)
    problems = verify(repaired, disrupted)
    print("Verified: 0 clashes." if not problems else f"PROBLEMS: {problems}")


if __name__ == "__main__":
    demo(sys.argv[1] if len(sys.argv) > 1 else "data/softwarica_exams.json")
