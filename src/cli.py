"""
Command-Line Interface (CLI) for the Timetable Scheduling Engine
----------------------------------------------------------------
A simple menu program:

    1. Generate timetable
    2. Simulate a disruption (staff sick / venue closed) and repair
    3. Show input data summary
    4. Save current timetable to a text file
    5. Exit

Run:  python cli.py [dataset]     (default: data/exam_schedule.json)
"""

import copy
import sys
import time

from engine import (load_data, solve, verify, print_timetable,
                    quality_score, explain_placement)
from reschedule import apply_disruption, repair


LINE = "-" * 58


def fresh(data_path):
    data = load_data(data_path)
    data["_by_name"] = {t["name"]: t for t in data["tasks"]}
    return data


def generate(data):
    stats = {"attempts": 0, "backtracks": 0}
    start = time.time()
    result = solve({}, data["tasks"], data, stats)
    elapsed = time.time() - start
    if result is None:
        print("\nNo valid timetable possible with current constraints.")
        return None
    print_timetable(result, data)
    problems = verify(result, data)
    status = "0 clashes" if not problems else f"{len(problems)} PROBLEMS: {problems}"
    print(f"Verified: {status} | solved in {elapsed:.3f}s | backtracks: {stats['backtracks']}")
    print(f"Schedule quality score: {quality_score(result, data)}/100 "
          f"(100 = no group or teacher has two exams on the same day)")
    return result


def choose_from(options, label):
    print(f"\nAvailable {label}:")
    for i, name in enumerate(options, 1):
        print(f"   {i}. {name}")
    while True:
        pick = input(f"Choose {label[:-1]} number: ").strip()
        if pick.isdigit() and 1 <= int(pick) <= len(options):
            return options[int(pick) - 1]
        print("Invalid choice, try again.")


def choose_slots(data):
    print("\nSlots:", ", ".join(data["slots"]))
    raw = input("Type unavailable slot(s), comma-separated (e.g. Mon 9AM, Mon 1PM): ")
    slots = [s.strip() for s in raw.split(",") if s.strip() in data["slots"]]
    if not slots:
        print("No valid slots recognised.")
    return slots


def simulate_disruption(data, timetable):
    if timetable is None:
        print("\nGenerate a timetable first (option 1).")
        return data, timetable

    kind = input("\nDisrupt (s)taff or (v)enue? ").strip().lower()
    if kind not in ("s", "v"):
        print("Type s or v.")
        return data, timetable

    disrupted = copy.deepcopy(data)
    disrupted["_by_name"] = {t["name"]: t for t in disrupted["tasks"]}

    if kind == "s":
        staff = sorted({t["staff"] for t in data["tasks"]})
        who = choose_from(staff, "staff")
    else:
        venues = [v["name"] for v in data["venues"]]
        who = choose_from(venues, "venues")

    slots = choose_slots(data)
    if not slots:
        return data, timetable

    apply_disruption(disrupted, "staff" if kind == "s" else "venue", who, slots)
    repaired, moved = repair(dict(timetable), disrupted)

    if repaired is None:
        print(f"\nCould not repair automatically. Affected: {moved}")
        return data, timetable

    print(f"\nDisruption: {who} unavailable at {', '.join(slots)}")
    if not moved:
        print("Timetable unaffected, nothing needed to move.")
    else:
        print(f"Repaired by moving {len(moved)} task(s):")
        for name, (os_, ov), (ns, nv) in moved:
            print(f"   {name}: {os_}/{ov}  ->  {ns}/{nv}")
        print(f"({len(repaired) - len(moved)} of {len(repaired)} tasks untouched)")
    print_timetable(repaired, disrupted)
    return disrupted, repaired


def show_summary(data):
    print(f"\n{LINE}")
    print(f"Dataset: {data.get('title', 'untitled')}")
    print(f"   Tasks (exams): {len(data['tasks'])}")
    print(f"   Venues:        {len(data['venues'])}  "
          f"({', '.join(v['name'] for v in data['venues'])})")
    print(f"   Groups:        {len(data['groups'])}  "
          f"(total {sum(data['groups'].values())} students)")
    print(f"   Staff:         {len({t['staff'] for t in data['tasks']})}")
    print(f"   Slots:         {len(data['slots'])}")
    unavailable = data.get("staff_unavailable", {})
    for who, slots in unavailable.items():
        print(f"   Unavailable:   {who} -> {', '.join(slots)}")
    print(LINE)


def save_timetable(timetable, data):
    if timetable is None:
        print("\nNothing to save yet, generate a timetable first.")
        return
    filename = "timetable_output.txt"
    import io
    from contextlib import redirect_stdout
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        print_timetable(timetable, data)
    with open(filename, "w") as f:
        f.write(buffer.getvalue())
    print(f"\nSaved to {filename}")


def explain(data, timetable):
    if timetable is None:
        print("\nGenerate a timetable first (option 1).")
        return
    names = sorted(timetable.keys())
    which = choose_from(names, "exams")
    print()
    print(explain_placement(which, timetable, data))


def main():
    data_path = sys.argv[1] if len(sys.argv) > 1 else "data/exam_schedule.json"
    data = fresh(data_path)
    timetable = None

    print(LINE)
    print("   TIMETABLE SCHEDULER, CSP Engine (ST5001CMD)")
    print(LINE)

    while True:
        print("\n  1. Generate timetable")
        print("  2. Simulate disruption and repair")
        print("  3. Show data summary")
        print("  4. Save timetable to file")
        print("  5. Explain a placement (why is this exam here?)")
        print("  6. Open visual timetable in browser")
        print("  7. Exit")
        choice = input("\nChoice: ").strip()

        if choice == "1":
            data = fresh(data_path)          # reset any old disruptions
            timetable = generate(data)
        elif choice == "2":
            data, timetable = simulate_disruption(data, timetable)
        elif choice == "3":
            show_summary(data)
        elif choice == "4":
            save_timetable(timetable, data)
        elif choice == "5":
            explain(data, timetable)
        elif choice == "6":
            if timetable is None:
                print("\nGenerate a timetable first (option 1).")
            else:
                from viz import show
                show(timetable, data)
        elif choice == "7":
            print("Goodbye.")
            break
        else:
            print("Pick 1-7.")


if __name__ == "__main__":
    main()
