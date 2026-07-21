# Exam Timetable Scheduler

AI coursework (ST5001CMD) — a constraint satisfaction (CSP) based scheduling
engine that generates clash-free timetables for Softwarica College, with
rescheduling under uncertainty, explainable placements, and a visual output.

## What it does

Given subjects, rooms, teachers, student groups, and time slots, the system
produces a timetable where:

- no student group has two exams at the same time
- no room holds two exams at once, or more students than its capacity
- no teacher is double-booked, and unavailability is respected
- exams are spread across days to reduce student fatigue (soft constraints)

The engine is general purpose: swapping the data file makes it schedule
weekly classes instead of exams, with no code changes.

## AI techniques used

- **CSP modelling** — exams as variables, (slot, room) pairs as values,
  six hard constraints
- **Backtracking search** with the **MRV heuristic** (most constrained
  exam scheduled first) and **forward checking**
- **Soft constraints with value ordering** — kinder placements tried first,
  measured by a 0-100 quality score
- **Rescheduling under uncertainty** — minimal-disruption repair when a
  teacher or room suddenly becomes unavailable
- **Explainability** — the system justifies why each exam got its slot

## How to run

Requires Python 3 only (no external libraries).

```
python cli.py                          # exam timetable (default dataset)
python cli.py softwarica_classes.json  # weekly class timetable
python experiments.py                  # evaluation: baselines and ablations
python reschedule.py                   # rescheduling demo
```

The CLI menu offers: generate, simulate a disruption, data summary,
save to file, explain a placement, and open the visual timetable
in the browser.

## Files

| File | Role |
|------|------|
| `engine.py` | CSP solver: constraints, MRV, forward checking, scoring, explainer |
| `cli.py` | interactive menu interface |
| `reschedule.py` | disruption handling and minimal repair |
| `viz.py` | HTML visual timetable generator |
| `experiments.py` | evaluation: baselines, ablations, stress scenarios |
| `softwarica_exams.json` | main dataset: 20 exams, 6 groups, 8 staff |
| `softwarica_classes.json` | second dataset proving engine generality |

## Evaluation summary

Four methods compared over four scenarios (small / full / stress /
impossible). Key findings: the random baseline always produces clashes;
removing soft constraints drops schedule quality from 100 to 0; on an
over-constrained scenario the MRV heuristic proves infeasibility about
20x faster than naive ordering. Full table: run `python experiments.py`.

## Author

Shweta Bhandari — BSc (Hons) Computer Science with AI, Softwarica College of IT & E-Commerce.
Module: ST5001CMD Artificial Intelligence (Module leader: Er. Suman Shrestha).
