"""
General Timetable Scheduling Engine
-----------------------------------
CSP solver: backtracking search + MRV heuristic + forward checking.

The engine knows nothing about exams, classes, or shifts.
It only understands:
    tasks   - things that need a time slot and a venue
    venues  - places with limited capacity
    staff   - a person attached to a task (cannot be double-booked)
    groups  - sets of people attending a task (cannot be double-booked)

Hard constraints enforced:
    C1  a group cannot attend two tasks in the same slot
    C2  a venue hosts only one task per slot
    C3  venue capacity >= people attending
    C4  staff cannot run two tasks in the same slot
    C5  staff unavailable slots are respected
"""

import json
import sys
import time


# data loading 

def load_data(path):
    with open(path) as f:
        return json.load(f)


def attendance(task, data):
    """Total people attending a task."""
    return sum(data["groups"][g] for g in task["groups"])


# constraint checking

def conflicts(task, slot, venue, assignment, data):
    """Return True if placing task at (slot, venue) breaks any constraint."""
    # C5: staff availability
    if slot in data.get("staff_unavailable", {}).get(task["staff"], []):
        return True
    # C6: venue availability (e.g., hall closed for maintenance)
    if slot in data.get("venue_unavailable", {}).get(venue["name"], []):
        return True
    # C3: capacity
    if attendance(task, data) > venue["capacity"]:
        return True
    # against already-placed tasks
    for placed_name, (s, v) in assignment.items():
        if s != slot:
            continue
        placed = data["_by_name"][placed_name]
        if v == venue["name"]:                                # C2 venue clash
            return True
        if set(task["groups"]) & set(placed["groups"]):       # C1 group clash
            return True
        if task["staff"] == placed["staff"]:                  # C4 staff clash
            return True
    return False


def valid_options(task, assignment, data):
    """All legal (slot, venue) pairs for a task right now."""
    return [
        (slot, venue["name"])
        for slot in data["slots"]
        for venue in data["venues"]
        if not conflicts(task, slot, venue, assignment, data)
    ]


# the solver 

def solve(assignment, unscheduled, data, stats):
    """Backtracking search with MRV (schedule the most constrained task first)."""
    if not unscheduled:
        return assignment

    # MRV heuristic + forward check:
    # compute remaining options for every unscheduled task,
    # pick the one with the fewest — and fail immediately if any task has none.
    options = {t["name"]: valid_options(t, assignment, data) for t in unscheduled}
    name = min(options, key=lambda n: len(options[n]))
    if not options[name]:
        return None  # dead end detected early (forward checking)

    task = data["_by_name"][name]
    for slot, venue_name in options[name]:
        stats["attempts"] += 1
        assignment[name] = (slot, venue_name)
        rest = [t for t in unscheduled if t["name"] != name]
        result = solve(assignment, rest, data, stats)
        if result is not None:
            return result
        del assignment[name]  # backtrack
        stats["backtracks"] += 1

    return None


#  verification (independent proof) 

def verify(assignment, data):
    """Re-check every constraint pair from scratch. Returns list of problems."""
    problems = []
    items = list(assignment.items())
    for name, (slot, venue_name) in items:
        task = data["_by_name"][name]
        venue = next(v for v in data["venues"] if v["name"] == venue_name)
        if attendance(task, data) > venue["capacity"]:
            problems.append(f"Capacity: {name} has {attendance(task, data)} in {venue_name}")
        if slot in data.get("staff_unavailable", {}).get(task["staff"], []):
            problems.append(f"Unavailable staff: {task['staff']} for {name} at {slot}")
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (n1, (s1, v1)), (n2, (s2, v2)) = items[i], items[j]
            if s1 != s2:
                continue
            t1, t2 = data["_by_name"][n1], data["_by_name"][n2]
            if v1 == v2:
                problems.append(f"Venue clash: {n1} / {n2} at {s1} in {v1}")
            if set(t1["groups"]) & set(t2["groups"]):
                problems.append(f"Group clash: {n1} / {n2} at {s1}")
            if t1["staff"] == t2["staff"]:
                problems.append(f"Staff clash: {n1} / {n2} at {s1} ({t1['staff']})")
    return problems


#  output 

def print_timetable(assignment, data):
    label = data.get("task_label", "Task")
    print(f"\n=== {data.get('title', 'TIMETABLE')} ===\n")
    for slot in data["slots"]:
        here = [(n, v) for n, (s, v) in assignment.items() if s == slot]
        if not here:
            continue
        print(f"{slot}")
        for name, venue in sorted(here, key=lambda x: x[1]):
            task = data["_by_name"][name]
            n = attendance(task, data)
            print(f"    {name:<32} {venue:<10} {n:>3} people   {task['staff']}")
        print()


# main 

def run(path):
    data = load_data(path)
    data["_by_name"] = {t["name"]: t for t in data["tasks"]}

    stats = {"attempts": 0, "backtracks": 0}
    start = time.time()
    result = solve({}, data["tasks"], data, stats)
    elapsed = time.time() - start

    if result is None:
        print("No valid timetable exists with these constraints.")
        return

    print_timetable(result, data)
    problems = verify(result, data)
    if problems:
        print("PROBLEMS FOUND:")
        for p in problems:
            print("   ", p)
    else:
        print(f"Verified: 0 clashes across {len(result)} tasks.")
    print(f"Solved in {elapsed:.3f}s | placements tried: {stats['attempts']} | backtracks: {stats['backtracks']}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "softwarica_exams.json")
