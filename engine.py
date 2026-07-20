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


# ---------- soft constraints (schedule quality) ----------

def day_of(slot):
    """'Mon 9AM' -> 'Mon'. The day part of a slot."""
    return slot.split()[0]


def placement_penalty(task, slot, assignment, data):
    """Soft-constraint cost of placing task at slot.
    +10 for every group that already has a task the same day (student fatigue).
    +5  if the staff member already works that day (staff load)."""
    penalty = 0
    for placed_name, (s, _v) in assignment.items():
        if day_of(s) != day_of(slot):
            continue
        placed = data["_by_name"][placed_name]
        penalty += 10 * len(set(task["groups"]) & set(placed["groups"]))
        if task["staff"] == placed["staff"]:
            penalty += 5
    return penalty


def quality_score(assignment, data):
    """0-100 score for a finished timetable. 100 = nobody has two
    tasks on the same day. Lower = more fatigue in the schedule."""
    total = 0
    items = list(assignment.items())
    for i, (name, (slot, _v)) in enumerate(items):
        others = dict(items[:i])
        total += placement_penalty(data["_by_name"][name], slot, others, data)
    return max(0, 100 - total)


# ---------- the solver ----------

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
    # value ordering by soft constraints: try the *kindest* placements first
    # (fewest same-day repeats for students and staff)
    ordered = sorted(
        options[name],
        key=lambda sv: placement_penalty(task, sv[0], assignment, data),
    )
    for slot, venue_name in ordered:
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


# ---------- explainability ----------

def explain_placement(name, assignment, data):
    """Human-readable reasons why a task sits where it does.
    Re-examines every alternative (slot, venue) and reports why each
    was worse or impossible — explainable AI for the end user."""
    slot, venue_name = assignment[name]
    task = data["_by_name"][name]
    people = attendance(task, data)
    others = {n: p for n, p in assignment.items() if n != name}

    lines = [f'"{name}" is at {slot} in {venue_name}:']
    lines.append(f"   - {people} people attend; {venue_name} holds "
                 f"{next(v['capacity'] for v in data['venues'] if v['name'] == venue_name)}.")

    too_small = [v["name"] for v in data["venues"] if v["capacity"] < people]
    if too_small:
        lines.append(f"   - Too small for it: {', '.join(too_small)}.")

    banned = data.get("staff_unavailable", {}).get(task["staff"], [])
    if banned:
        lines.append(f"   - {task['staff']} is unavailable at: {', '.join(banned)}.")

    # count what ruled out the other slot/venue combinations
    blocked = {"group busy": 0, "staff busy": 0, "venue taken": 0}
    open_alternatives = []
    for s in data["slots"]:
        for v in data["venues"]:
            if (s, v["name"]) == (slot, venue_name):
                continue
            if v["capacity"] < people or s in banned \
               or s in data.get("venue_unavailable", {}).get(v["name"], []):
                continue
            reason = None
            for on, (os_, ov) in others.items():
                if os_ != s:
                    continue
                other = data["_by_name"][on]
                if ov == v["name"]:
                    reason = "venue taken"
                elif set(task["groups"]) & set(other["groups"]):
                    reason = "group busy"
                elif task["staff"] == other["staff"]:
                    reason = "staff busy"
                if reason:
                    break
            if reason:
                blocked[reason] += 1
            else:
                open_alternatives.append((s, v["name"]))

    ruled_out = ", ".join(f"{n} by {r}" for r, n in blocked.items() if n)
    if ruled_out:
        lines.append(f"   - Alternatives ruled out: {ruled_out}.")

    here = placement_penalty(task, slot, others, data)
    if open_alternatives:
        better = [
            (s, v) for s, v in open_alternatives
            if placement_penalty(task, s, others, data) < here
        ]
        if better:
            lines.append(f"   - Note: {len(better)} kinder alternative(s) exist "
                         f"(may cost quality elsewhere).")
        else:
            lines.append(f"   - {len(open_alternatives)} legal alternative(s) exist, "
                         f"but none kinder (same-day fatigue would be equal or worse).")
    else:
        lines.append("   - No legal alternative exists: this was the ONLY valid placement.")

    return "\n".join(lines)


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
    print(f"Schedule quality score: {quality_score(result, data)}/100")
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
