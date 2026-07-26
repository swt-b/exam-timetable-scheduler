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

## Data handling

A dataset can be supplied three ways, all producing identical timetables
because the input format is separated from the engine:

- an **Excel workbook** with one tab per table (tidiest for office staff)
- a folder of **CSV** files, one per table
- a single **JSON** file

The six tables are `meta`, `slots`, `venues`, `groups`, `tasks` and
`unavailable`. The Excel workbook also carries a `readme` tab explaining
what belongs in each sheet.

Incoming data is cleaned and validated before the solver runs:

- **repaired automatically** — stray whitespace, inconsistent capitalisation,
  duplicate rows, numbers stored as text, group names that differ only by case
- **rejected with reasons** — missing room capacity, a task with no staff
  member, references to groups or rooms that do not exist, or a dataset that
  is provably unschedulable (more tasks than slot/room combinations, a group
  with more exams than there are slots)

Every repair and rejection is reported to the user rather than applied
silently, so a timetable is never built on data the system had to guess about.

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
pip install -r requirements.txt        # web interface, Excel input, notebook

python app.py                              # web interface at http://localhost:5000
python cli.py                              # terminal interface (exam timetable)
python cli.py softwarica_classes.json      # terminal: weekly class timetable
python engine.py softwarica_exams.xlsx     # same timetable, loaded from Excel
python engine.py data_exams_csv            # same timetable, loaded from CSV
python dataio.py data_noisy_csv            # data cleaning report only
python experiments.py                      # evaluation: baselines and ablations
python charts.py                           # evaluation charts in popup windows
python reschedule.py                       # rescheduling demo

jupyter notebook notebooks/data_exploration.ipynb   # data analysis and charts
```

Dataset names are resolved against the `data/` folder, so
`python engine.py softwarica_exams.xlsx` and
`python engine.py data/softwarica_exams.xlsx` both work.

The solver itself uses no external libraries. Flask is only for the web
interface and openpyxl only for reading Excel files; the CLI runs on JSON
or CSV with a plain Python 3 install.

The web interface has four working pages: generate a timetable (filterable
to a single student group), simulate a staff absence and repair, ask why an
exam was placed where it was, and **build your own scenario** by adding an
exam, closing rooms or removing time slots and regenerating.

The CLI offers the same core functions in a terminal menu: generate, simulate
a disruption, data summary, save to file, explain a placement, and open the
visual timetable in the browser.

## Files

| File | Role |
|------|------|
| `engine.py` | CSP solver: constraints, MRV, forward checking, scoring, explainer |
| `cli.py` | interactive menu interface |
| `reschedule.py` | disruption handling and minimal repair |
| `viz.py` | HTML visual timetable generator |
| `experiments.py` | evaluation: baselines, ablations, stress scenarios |
| `app.py` | Flask web interface — run and open http://localhost:5000 |
| `dataio.py` | dataset loading (Excel + CSV + JSON), cleaning, validation |
| `charts.py` | runs the solver and shows the evaluation charts |
| `notebooks/data_exploration.ipynb` | pandas analysis and charts of the data and results |
| `data/` | all datasets (see below) |

### Inside `data/`

| File | Role |
|------|------|
| `softwarica_exams.json` | main dataset: 20 exams, 6 groups, 7 staff |
| `softwarica_classes.json` | second dataset proving engine generality |
| `softwarica_exams.xlsx` | the exam dataset as an Excel workbook |
| `softwarica_classes.xlsx` | the class dataset as an Excel workbook |
| `data_exams_csv/` | the exam dataset in CSV form |
| `data_classes_csv/` | the class dataset in CSV form |
| `data_noisy_csv/` | recoverable noise: cleaned, then scheduled |
| `data_messy_csv/` | unrecoverable errors: rejected with reasons |

## Evaluation summary

Four methods compared over four scenarios (small / full / stress /
impossible). Key findings: the random baseline always produces clashes;
removing soft constraints drops schedule quality from 100 to 0; on an
over-constrained scenario the MRV heuristic proves infeasibility about
20x faster than naive ordering. Full table: run `python experiments.py`.

## Author

Shweta Bhandari — BSc (Hons) Computer Science with AI, Softwarica College of IT & E-Commerce.
Module: ST5001CMD Artificial Intelligence (Module leader: Er. Suman Shrestha).
