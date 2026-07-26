"""
Convert the Kaggle "University Exam Scheduling" dataset into the internal
JSON format used by the CSP engine.

Source: https://www.kaggle.com/datasets/smrezwanulazad/exam-schedule

The Kaggle files are six related tables (classrooms, courses, instructors,
students, timeslots, schedule). Each row of `schedule.csv` is one student
in one course in one timeslot in one room. Because the same course is sat by
hundreds of students and no single room holds them all, the source data is
really "each cohort sits its own session". We model it the same way.

Mapping to our engine:
    (course, cohort)   ->  task    (an exam session that one cohort attends)
    classroom          ->  venue
    timeslot           ->  slot
    program + year     ->  student group  (e.g. "MSc-Marketing-Sophomore")
    instructor         ->  staff

The result mirrors the shape of our custom Softwarica dataset so every page
in the web app, the CLI, and the notebook work on it unchanged.

Run:  python import_kaggle.py
"""

import csv
import json
import os
import re
from collections import Counter, defaultdict

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(_ROOT, "data", "exam_schedule")
OUT_JSON = os.path.join(_ROOT, "data", "exam_schedule.json")

# keep the demo tractable
MAX_TASKS = 22            # cap number of exam sessions to schedule
MIN_STUDENTS = 8          # ignore very small course/cohort pairs (noise)


# --- helpers ---

def read(name):
    with open(os.path.join(SRC, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def slot_label(row):
    """timeslots row -> a compact slot like 'Mon 9AM'."""
    day = (row["day"] or "").strip()[:3]
    hour = int(row["start_time"].split(":")[0])
    ampm = "AM" if hour < 12 else "PM"
    h = hour if hour <= 12 else hour - 12
    return f"{day} {h}{ampm}"


def tidy_program(name):
    """'M.Sc. in International Management' -> 'MSc-International-Management'."""
    n = re.sub(r"\s+", " ", (name or "").strip())
    n = n.replace("M.Sc. in ", "MSc-").replace("B.Sc. in ", "BSc-")
    n = n.replace("MBA in ", "MBA-").replace("Ph.D. in ", "PhD-")
    return n.replace(" ", "-")


def group_of(student):
    p, y = tidy_program(student.get("program_name")), (student.get("year") or "").strip()
    return f"{p}-{y}" if y else p


# --- main ---

def main():
    classrooms  = read("classrooms.csv")
    courses     = read("courses.csv")
    instructors = read("instructors.csv")
    students    = read("students.csv")
    timeslots   = read("timeslots.csv")
    schedule    = read("schedule.csv")

    print(f"Source: {len(courses)} courses, {len(students)} students, "
          f"{len(classrooms)} classrooms, {len(timeslots)} timeslots, "
          f"{len(schedule)} enrolment rows.")

    # --- venues (keep only the biggest handful, plenty for a 20-exam demo) ---
    all_venues = sorted(
        ({"name": f"{r['building_name']}-{r['room_number']}",
          "capacity": int(r["capacity"])}
         for r in classrooms),
        key=lambda v: -v["capacity"])
    venues = all_venues[:8]
    biggest = venues[0]["capacity"]

    # --- slots (dedupe by label) ---
    slots, seen = [], set()
    for r in timeslots:
        label = slot_label(r)
        if label not in seen:
            seen.add(label); slots.append(label)
    if len(slots) > 12:                     # cap for a readable grid
        slots = slots[:12]

    # --- lookup tables ---
    course_name   = {c["course_id"]: c["course_name"].strip() for c in courses}
    instructor_of = {i["instructor_id"]:
                     f"{i['first_name']} {i['last_name']}".strip()
                     for i in instructors}
    student_group = {s["student_id"]: group_of(s) for s in students}

    # --- for each (course, group), how many students and which instructor ---
    pair_students = defaultdict(set)                      # (cid, group) -> {student_id}
    pair_inst     = defaultdict(Counter)                  # (cid, group) -> {inst: n}
    for row in schedule:
        g = student_group.get(row["student_id"])
        if not g: continue
        key = (row["course_id"], g)
        pair_students[key].add(row["student_id"])
        pair_inst[key][row["instructor_id"]] += 1

    group_sizes = Counter(student_group.values())

    # build one candidate task per (course, group) pair.
    # The engine sums group sizes to compute attendance, so we filter using the
    # full group size, not just how many are enrolled on this particular course.
    candidates = []
    for (cid, g), sids in pair_students.items():
        enrolled = len(sids)
        group_total = group_sizes[g]
        if enrolled < MIN_STUDENTS or group_total > biggest:
            continue
        top_inst, _ = pair_inst[(cid, g)].most_common(1)[0]
        candidates.append({
            "name": f"{course_name[cid]} ({g})",
            "staff": instructor_of.get(top_inst, "Unknown"),
            "groups": [g],
            "people": group_total,
        })

    # largest first, then keep the top N so the demo runs quickly
    candidates.sort(key=lambda t: -t["people"])
    kept = candidates[:MAX_TASKS]

    # only keep the groups that actually appear
    used_groups = sorted({g for t in kept for g in t["groups"]})

    tasks = [{"name": t["name"], "staff": t["staff"], "groups": t["groups"]}
             for t in kept]

    data = {
        "title": "UNIVERSITY EXAM SCHEDULE",
        "task_label": "Exam",
        "slots": slots,
        "venues": venues,
        "groups": {g: group_sizes[g] for g in used_groups},
        "tasks": tasks,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print()
    print(f"Wrote {OUT_JSON}")
    print(f"  {len(tasks)} exams  ·  {len(used_groups)} groups  "
          f"·  {len(venues)} venues  ·  {len(slots)} slots")
    print(f"  exam sizes: {min(t['people'] for t in kept)}"
          f"..{max(t['people'] for t in kept)} students")
    print(f"  room sizes: {min(v['capacity'] for v in venues)}"
          f"..{max(v['capacity'] for v in venues)} seats")


if __name__ == "__main__":
    main()
