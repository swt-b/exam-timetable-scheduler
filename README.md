# Exam Timetable Scheduler

An AI coursework project (ST5001CMD): a constraint satisfaction (CSP) based
scheduling engine that generates clash-free university exam timetables,
repairs them when a teacher becomes unavailable, and explains every placement
it makes.

## Dataset

**University Exam Scheduling** by Rezwanul Azad (2024), downloaded from Kaggle:
https://www.kaggle.com/datasets/smrezwanulazad/exam-schedule

The raw dataset is six CSV files (classrooms, courses, instructors, students,
timeslots, schedule) in `data/exam_schedule/`. They describe the *inputs*
of the problem, students enrolled on courses, rooms with capacities, and
available time slots.

A small preprocessing step (`import_kaggle.py`) joins these six tables into
one file, `data/exam_schedule.json`, which is what the solver reads. That
file already exists in the repository, so you do not need to regenerate it.

After preprocessing the working dataset has 22 exam sessions across 5 student
cohorts, 8 lecture rooms and 12 weekly time slots.

## What the AI does

Given exams, rooms, teachers, cohorts and time slots, the system produces a
timetable where:

- no student cohort has two exams at the same time
- no room is double-booked or overcrowded
- no teacher is in two places at once
- exams are spread across days to reduce student fatigue (soft constraint)

If a teacher goes sick after the timetable is published, only the affected
exams are moved; everything else stays where it was. For any exam, the
system explains why it went where it did.

## AI techniques

- **CSP modelling** — exams as variables, (slot, room) pairs as values,
  six hard constraints
- **Backtracking search** with the **MRV heuristic** (schedule the most
  constrained exam first) and **forward checking**
- **Value ordering by soft constraints** — kinder placements are tried first,
  measured by a 0-100 quality score
- **Rescheduling under uncertainty** — minimal-disruption repair when a
  teacher or room becomes unavailable
- **Explainability** — the system justifies every placement it makes

## How to run

Install the libraries once:

```
pip install -r requirements.txt
```

Then any of these, from the project root:

```
python app.py                 # web interface at http://localhost:5000
python src/cli.py             # menu-based terminal interface
python src/engine.py          # one shot: print the timetable
python src/reschedule.py      # rescheduling demo
python src/charts.py          # evaluation charts in popup windows
python src/experiments.py     # baselines and ablations table
```

Optional (only if `data/exam_schedule.json` gets deleted):

```
python src/import_kaggle.py   # rebuild the JSON from the six Kaggle CSVs
```

## Files

| Path | Role |
|------|------|
| `app.py` | Flask web interface (entry point) |
| `src/engine.py` | CSP solver, constraints, MRV, forward checking, scoring, explainer |
| `src/dataio.py` | dataset loading and validation |
| `src/import_kaggle.py` | joins the six Kaggle CSVs into one JSON |
| `src/reschedule.py` | disruption handling and minimal repair |
| `src/viz.py` | HTML visual timetable |
| `src/experiments.py` | baselines and ablations |
| `src/charts.py` | evaluation charts in popup windows |
| `src/cli.py` | interactive terminal menu |
| `notebooks/data_exploration.ipynb` | pandas analysis and charts |
| `data/exam_schedule/` | the six Kaggle CSVs |
| `data/exam_schedule.json` | preprocessed dataset the solver reads |
| `figures/` | charts saved by `charts.py` and the notebook |

## Evaluation summary

Four methods compared across four scenarios (small, full, stress, impossible).
Key findings:

- the random baseline is invalid in every scenario (6 to 20 clashes), so the
  problem genuinely needs a search algorithm
- the solver produces a correct, fair timetable instantly (0 clashes,
  0 backtracks, about 0.05s on the full dataset)
- on the over-constrained scenario the solver correctly proves that no
  timetable exists rather than returning an invalid one
- on this loosely constrained real instance MRV and value ordering leave the
  result unchanged; they are safeguards whose benefit grows as instances tighten

Full table: `python src/experiments.py`.

## Author

Shweta Bhandari, BSc (Hons) Computer Science with AI, Softwarica College of
IT & E-Commerce. Module: ST5001CMD Artificial Intelligence
(Module leader: Er. Suman Shrestha).