"""
app.py — Web interface for the AI Exam Timetable Scheduler
ST5001CMD Artificial Intelligence coursework — Shweta Bhandari

Run:  python app.py
Open: http://localhost:5000
"""

import os, sys, copy, time
from flask import Flask, render_template_string, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from engine import load_data, solve, verify, quality_score, explain_placement, attendance
from reschedule import apply_disruption, repair
from dataio import pretty_date, period_text

app = Flask(__name__)

DATASETS = {
    "exams":        "data/softwarica_exams.json",    # JSON input
    "classes":      "data/softwarica_classes.json",
    "exams_csv":    "data/data_exams_csv",           # same data, CSV input
    "classes_csv":  "data/data_classes_csv",
    "exams_xlsx":   "data/softwarica_exams.xlsx",    # same data, Excel input
    "classes_xlsx": "data/softwarica_classes.xlsx",
    "noisy":        "data/data_noisy_csv",           # recoverable noise, cleaned then solved
    "messy":        "data/data_messy_csv",           # unrecoverable errors, rejected
}

PALETTE = ["#4e79a7","#f28e2b","#59a14f","#e15759",
           "#76b7b2","#af7aa1","#edc948","#9c755f"]

def group_colors(data):
    return {g: PALETTE[i % len(PALETTE)]
            for i, g in enumerate(sorted(data["groups"]))}

def run_solver(dataset_key):
    path = DATASETS.get(dataset_key, DATASETS["exams"])
    data = load_data(path)                      # cleans + validates
    data["_by_name"] = {t["name"]: t for t in data["tasks"]}
    report = data.get("_report")

    if report is not None and not report.ok:    # unusable data — do not solve
        return data, None, {"attempts": 0, "backtracks": 0}, 0.0

    stats = {"attempts": 0, "backtracks": 0}
    t0 = time.time()
    result = solve({}, data["tasks"], data, stats)
    elapsed = round(time.time() - t0, 3)
    return data, result, stats, elapsed


# ── shared base ──────────────────────────────────────────────────────────────

BASE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TimetableAI: {{ title }}</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;background:#f0f2f5;color:#1a1a2e}
nav{background:#1a1f36;display:flex;align-items:center;gap:6px;padding:0 28px;height:54px}
.logo{font-size:17px;font-weight:700;color:#818cf8;margin-right:12px}
nav a{color:#9ca3af;text-decoration:none;font-size:13.5px;padding:5px 10px;border-radius:6px;transition:.15s}
nav a:hover,nav a.on{color:#fff;background:#2d3561}
.wrap{max-width:1180px;margin:28px auto;padding:0 20px}
.back{display:inline-flex;align-items:center;gap:5px;color:#818cf8;text-decoration:none;font-size:13px;margin-bottom:18px}
.back:hover{text-decoration:underline}

/* stats row */
.stats{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:22px}
.stat{background:#fff;border-radius:10px;padding:14px 22px;box-shadow:0 2px 8px rgba(0,0,0,.06);flex:1;min-width:110px;text-align:center}
.stat .v{font-size:26px;font-weight:700}.stat .l{font-size:11px;color:#888;margin-top:3px}
.green .v{color:#059669}.blue .v{color:#818cf8}.amber .v{color:#d97706}.red .v{color:#dc2626}

/* cards on home */
.cards{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:28px}
.card{background:#fff;border-radius:14px;padding:28px;box-shadow:0 2px 10px rgba(0,0,0,.07);
      border:2px solid transparent;transition:.2s}
.card:hover{border-color:#818cf8;transform:translateY(-2px);box-shadow:0 8px 24px rgba(129,140,248,.15)}
.card h3{font-size:18px;margin-bottom:8px}
.card p{color:#555;font-size:13.5px;line-height:1.6;margin-bottom:18px}
.pills{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:18px}
.pill{background:#ede9fe;color:#6d28d9;padding:3px 10px;border-radius:20px;font-size:12px}

/* hero */
.hero{background:linear-gradient(135deg,#1a1f36,#2d3561);color:#fff;
      border-radius:16px;padding:44px;margin-bottom:28px}
.hero h1{font-size:30px;margin-bottom:8px}
.hero p{color:#a5b4fc;font-size:15px;margin-bottom:26px;line-height:1.6}
.powered{color:#6b7699;font-size:10.5px;text-transform:uppercase;
         letter-spacing:1.4px;font-weight:600;margin-bottom:9px}
.tags{display:flex;gap:7px;flex-wrap:wrap}
.tag{background:rgba(129,140,248,.13);color:#8b93b8;border:1px solid #3d4570;
     padding:3px 11px;border-radius:20px;font-size:11.5px}

/* buttons */
.btn{display:inline-block;padding:9px 22px;border-radius:8px;font-size:13.5px;
     font-weight:600;cursor:pointer;border:none;text-decoration:none;transition:.15s}
.btn-primary{background:#818cf8;color:#fff}.btn-primary:hover{background:#6366f1}
.btn-danger{background:#ef4444;color:#fff}.btn-danger:hover{background:#dc2626}
.btn-green{background:#059669;color:#fff}.btn-green:hover{background:#047857}
.btn-sm{padding:6px 14px;font-size:12.5px}

/* timetable */
.tt-wrap{background:#fff;border-radius:14px;padding:22px;
         box-shadow:0 2px 10px rgba(0,0,0,.07);overflow-x:auto}
.tt-wrap h2{font-size:17px;margin-bottom:14px}
.legend{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}
.litem{padding:3px 12px;border-radius:20px;color:#fff;font-size:12px}
.viewbar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.vlabel{font-size:11px;text-transform:uppercase;letter-spacing:1px;
        color:#9ca3af;font-weight:600;margin-right:4px}
.vopt{padding:4px 13px;border-radius:20px;font-size:12.5px;text-decoration:none;
      color:#555;border:1px solid #ddd;background:#fff;transition:.15s}
.vopt:hover{border-color:#818cf8;color:#4f46e5}
.vopt.on{background:#1a1f36;border-color:#1a1f36;color:#fff;font-weight:600}
table{border-collapse:collapse;width:100%;min-width:500px}
th{background:#1a1f36;color:#fff;padding:9px 11px;font-size:12.5px;text-align:left}
td{border:1px solid #eee;padding:5px 7px;vertical-align:top}
td.sc{background:#1a1f36;color:#fff;font-weight:600;font-size:12.5px;white-space:nowrap;width:105px}
td.sc .sd{display:block;font-weight:400;font-size:10.5px;color:#8b93b8;margin-top:2px}
td.em{background:#fafafa}
.ec{border-radius:6px;padding:7px 9px;color:#fff;font-size:12px;cursor:pointer;transition:.15s}
.ec:hover{opacity:.85}
.ec b{display:block;font-size:13px;margin-bottom:2px}

/* forms */
.panel{background:#fff;border-radius:14px;padding:28px;box-shadow:0 2px 10px rgba(0,0,0,.07);margin-bottom:20px}
.panel h2{font-size:17px;margin-bottom:6px}
.panel .sub{color:#666;font-size:13.5px;margin-bottom:20px}
.frow{display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;margin-bottom:16px}
.fg{flex:1;min-width:160px}
label{display:block;font-size:12.5px;color:#555;font-weight:500;margin-bottom:5px}
select,input[type=text]{width:100%;padding:8px 11px;border:1px solid #ddd;
                         border-radius:7px;font-size:13.5px;background:#fafafa}
select:focus,input:focus{outline:2px solid #818cf8;border-color:#818cf8;background:#fff}

/* scenario builder */
.bsec{border-top:1px solid #f0f0f3;padding-top:18px;margin-top:18px}
.bsec:first-of-type{border-top:none;padding-top:0;margin-top:8px}
.bsec h3{font-size:13.5px;margin-bottom:3px}
.bhint{font-size:12.5px;color:#777;margin-bottom:11px;line-height:1.5}
.chips{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:6px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;
      border:1px solid #ddd;border-radius:20px;font-size:12.5px;color:#666;
      background:#fafafa;cursor:pointer;user-select:none;transition:.12s}
.chip:hover{border-color:#818cf8}
.chip.on{background:#eef2ff;border-color:#818cf8;color:#3730a3;font-weight:500}
.chip input{margin:0;cursor:pointer;accent-color:#6366f1}
.chip .cap{color:#9ca3af;font-size:11px}

/* alerts & moved */
.alert{padding:13px 16px;border-radius:8px;margin-bottom:14px;font-size:13.5px}
.a-green{background:#d1fae5;color:#065f46;border-left:4px solid #059669}
.a-amber{background:#fef3c7;color:#92400e;border-left:4px solid #d97706}
.a-red{background:#fee2e2;color:#991b1b;border-left:4px solid #dc2626}
.moved{background:#fef9c3;border-radius:8px;padding:14px;margin:14px 0;border-left:4px solid #ca8a04}
.moved h4{color:#92400e;margin-bottom:8px;font-size:14px}
.mi{font-size:13px;padding:3px 0}
.arr{color:#818cf8;font-weight:700}

/* explain */
.xpre{background:#f5f3ff;border-radius:8px;padding:16px;font-size:13.5px;
      line-height:1.75;border-left:4px solid #818cf8;white-space:pre-wrap;
      font-family:'Segoe UI',sans-serif}

/* summary */
.sg{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}
.sc2{background:#fff;border-radius:10px;padding:18px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.sc2 h4{font-size:12px;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.sc2 ul{list-style:none}.sc2 li{font-size:13px;padding:4px 0;border-bottom:1px solid #f3f4f6}
.sc2 li:last-child{border:none}

@media(max-width:640px){.cards{grid-template-columns:1fr}}
</style>
</head>
<body>
<nav>
  <span class="logo">🗓 TimetableAI</span>
  <a href="/" class="{{ 'on' if active=='home' else '' }}">Home</a>
  <a href="/build" class="{{ 'on' if active=='build' else '' }}">Build your own</a>
  <a href="/about" class="{{ 'on' if active=='about' else '' }}">About</a>
  {% if ds %}
  <a href="/timetable?dataset={{ ds }}" class="{{ 'on' if active=='tt' else '' }}">Timetable</a>
  <a href="/disrupt?dataset={{ ds }}" class="{{ 'on' if active=='dis' else '' }}">Disruption Sim</a>
  <a href="/explain?dataset={{ ds }}" class="{{ 'on' if active=='exp' else '' }}">Explain</a>
  <a href="/summary?dataset={{ ds }}" class="{{ 'on' if active=='sum' else '' }}">Data Summary</a>
  {% endif %}
</nav>
<div class="wrap">
{% block body %}{% endblock %}
</div>
</body></html>"""


# ── home ─────────────────────────────────────────────────────────────────────

HOME = BASE.replace("{% block body %}{% endblock %}", """
<div class="hero">
  <h1>Exam Timetable Scheduler</h1>
  <p>Generate a complete, clash-free timetable in under a second.<br>
     No student sits two exams at once. No room is overbooked. No teacher is double-booked.</p>
</div>

<div class="cards">
  <div class="card">
    <h3>📋 Exam Timetable</h3>
    <p>End-of-semester exams for all student groups, scheduled across the
       college's exam halls and rooms.</p>
    <div class="pills">
      <span class="pill">20 exams</span>
      <span class="pill">6 groups</span>
      <span class="pill">5 venues</span>
      <span class="pill">10 slots</span>
    </div>
    <a href="/timetable?dataset=exams" class="btn btn-primary">Generate Timetable →</a>
  </div>
  <div class="card">
    <h3>🏫 Weekly Class Timetable</h3>
    <p>Regular weekly lectures and labs across Softwarica's lecture rooms
       (Lr 1–16), ICR labs and the Seminar Hall.</p>
    <div class="pills">
      <span class="pill">19 classes</span>
      <span class="pill">4 groups</span>
      <span class="pill">23 rooms</span>
      <span class="pill">15 slots</span>
    </div>
    <a href="/timetable?dataset=classes" class="btn btn-primary">Generate Timetable →</a>
  </div>
</div>

<p style="text-align:center;color:#999;font-size:12.5px;margin-top:26px">
  Every timetable is checked for clashes, room capacity and staff availability
  before it is shown. <a href="/about" style="color:#818cf8">How it works →</a>
</p>
""")


@app.route("/")
def home():
    return render_template_string(HOME, title="Home", active="home", ds=None)


# ── about / how it works ──────────────────────────────────────────────────────

ABOUT = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/">← Back to Home</a>

<div class="hero" style="padding:34px">
  <h1 style="font-size:25px">About this system</h1>
  <p style="margin-bottom:0">Building an exam timetable by hand takes days and mistakes
     slip through. This system does it in under a second, and shows its reasoning.</p>
</div>

<div class="panel">
  <h2>What it does</h2>
  <p style="font-size:13.5px;line-height:1.8;color:#333;margin-top:6px">
    You give it your exams, rooms, teachers and student groups. It works out a
    complete timetable where nothing clashes, then lets you ask why any exam
    ended up where it did, and repair the timetable if someone becomes unavailable.
  </p>

  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px;margin-top:20px">
    <div style="padding:14px 16px;background:#f0fdf4;border-radius:10px;border-left:3px solid #059669">
      <b style="font-size:13.5px">No student clashes</b>
      <p style="font-size:12.5px;color:#555;margin-top:4px;line-height:1.5">
        A student group is never scheduled for two exams at the same time.</p>
    </div>
    <div style="padding:14px 16px;background:#f0fdf4;border-radius:10px;border-left:3px solid #059669">
      <b style="font-size:13.5px">Rooms always fit</b>
      <p style="font-size:12.5px;color:#555;margin-top:4px;line-height:1.5">
        No room is double-booked, and every room is big enough for the group.</p>
    </div>
    <div style="padding:14px 16px;background:#f0fdf4;border-radius:10px;border-left:3px solid #059669">
      <b style="font-size:13.5px">Teacher availability respected</b>
      <p style="font-size:12.5px;color:#555;margin-top:4px;line-height:1.5">
        Teachers are never double-booked or scheduled when unavailable.</p>
    </div>
    <div style="padding:14px 16px;background:#f0fdf4;border-radius:10px;border-left:3px solid #059669">
      <b style="font-size:13.5px">Exams spread fairly</b>
      <p style="font-size:12.5px;color:#555;margin-top:4px;line-height:1.5">
        Where possible, no group sits two exams on the same day.</p>
    </div>
  </div>
</div>

<div class="panel">
  <h2>Three things you can do</h2>
  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px;margin-top:10px">
    <div style="padding:16px;background:#f5f3ff;border-radius:10px">
      <b style="color:#6d28d9;font-size:13.5px">Generate a timetable</b>
      <p style="font-size:12.5px;color:#555;margin-top:6px;line-height:1.6">
        A complete, checked timetable in under a second, or a clear answer that
        no valid timetable is possible with your current rooms and slots.</p>
      <a href="/" class="btn btn-primary btn-sm" style="margin-top:10px">Generate →</a>
    </div>
    <div style="padding:16px;background:#fff7ed;border-radius:10px">
      <b style="color:#c2410c;font-size:13.5px">Handle a disruption</b>
      <p style="font-size:12.5px;color:#555;margin-top:6px;line-height:1.6">
        If a teacher falls ill, only the affected exams are moved. The rest of the
        timetable stays exactly where students already saw it.</p>
      <a href="/disrupt?dataset=exams" class="btn btn-danger btn-sm" style="margin-top:10px">Try it →</a>
    </div>
    <div style="padding:16px;background:#ecfdf5;border-radius:10px">
      <b style="color:#065f46;font-size:13.5px">Ask why</b>
      <p style="font-size:12.5px;color:#555;margin-top:6px;line-height:1.6">
        Pick any exam and the system explains its placement: what ruled out every
        other slot and room, and whether a better option existed.</p>
      <a href="/explain?dataset=exams" class="btn btn-green btn-sm" style="margin-top:10px">Try it →</a>
    </div>
    <div style="padding:16px;background:#eef2ff;border-radius:10px">
      <b style="color:#3730a3;font-size:13.5px">Change the problem</b>
      <p style="font-size:12.5px;color:#555;margin-top:6px;line-height:1.6">
        Add an exam, close a room, or cut time slots, then generate again. Take
        away enough and the system will prove no valid timetable exists.</p>
      <a href="/build" class="btn btn-primary btn-sm" style="margin-top:10px">Build your own →</a>
    </div>
  </div>
</div>

<div class="panel">
  <h2>Data</h2>
  <p style="font-size:13.5px;line-height:1.8;color:#333;margin-top:6px">
    Your data can be an Excel workbook, a set of CSV files, or a JSON file. All three
    produce the same timetable. Before scheduling, the data is checked: obvious problems
    like extra spaces, inconsistent capitalisation and duplicate rows are repaired and
    reported. Problems that cannot be guessed safely, such as a room with no capacity or
    an exam with no teacher, stop the process with an explanation, rather than producing
    a timetable that looks right but isn't.
  </p>
  <div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:16px">
    <a href="/timetable?dataset=exams_xlsx" class="btn btn-sm"
       style="background:#e5e7eb;color:#374151">Loaded from Excel</a>
    <a href="/timetable?dataset=exams_csv" class="btn btn-sm"
       style="background:#e5e7eb;color:#374151">Loaded from CSV</a>
    <a href="/timetable?dataset=noisy" class="btn btn-sm"
       style="background:#fef3c7;color:#92400e">Example: messy data, repaired</a>
    <a href="/timetable?dataset=messy" class="btn btn-sm btn-danger">Example: broken data, refused</a>
  </div>
</div>

<hr style="border:none;border-top:1px solid #e5e7eb;margin:34px 0 26px">
<p style="font-size:11px;text-transform:uppercase;letter-spacing:1.3px;
          color:#9ca3af;font-weight:600;margin-bottom:14px">Technical details</p>

<div class="panel">
  <h2>How it decides</h2>
  <p class="sub">Timetabling is modelled as a Constraint Satisfaction Problem (CSP)
     and solved with backtracking search.</p>
  <p style="font-size:13.5px;line-height:1.8;color:#333">
    Each exam is a <b>variable</b>; every possible (time slot, room) pair is a
    <b>value</b> it could take; six <b>hard constraints</b> define which combinations
    are legal. The solver assigns one legal value to every variable at once.
  </p>

  <div style="background:#f5f3ff;border-radius:10px;padding:16px;margin-top:16px">
    <b style="font-size:13px;color:#6d28d9">Hard constraints</b>
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:8px;margin-top:10px;font-size:13px;color:#444">
      <div><b>C1</b>: a group cannot sit two exams in one slot</div>
      <div><b>C2</b>: a room hosts only one exam per slot</div>
      <div><b>C3</b>: room capacity must be at least the number of students</div>
      <div><b>C4</b>: staff cannot invigilate two exams at once</div>
      <div><b>C5</b>: staff unavailability is respected</div>
      <div><b>C6</b>: room unavailability is respected</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:14px;margin-top:18px">
    <div style="padding:16px;background:#ecfdf5;border-radius:10px">
      <b style="color:#065f46;font-size:13.5px">Backtracking search</b>
      <p style="font-size:13px;color:#444;margin-top:6px;line-height:1.6">
        Place one exam at a time; if a placement makes the rest impossible, undo it
        and try the next option. Guarantees a valid timetable if one exists, and
        proves none exists if it doesn't.</p>
    </div>
    <div style="padding:16px;background:#ecfdf5;border-radius:10px">
      <b style="color:#065f46;font-size:13.5px">MRV heuristic</b>
      <p style="font-size:13px;color:#444;margin-top:6px;line-height:1.6">
        <i>Minimum Remaining Values</i>. Always schedule the exam with the fewest
        legal options left. Handling the hardest case while the timetable is still
        mostly empty avoids painting yourself into a corner.</p>
    </div>
    <div style="padding:16px;background:#ecfdf5;border-radius:10px">
      <b style="color:#065f46;font-size:13.5px">Forward checking</b>
      <p style="font-size:13px;color:#444;margin-top:6px;line-height:1.6">
        After each placement, check whether any unscheduled exam now has zero legal
        options. If so, abandon the branch immediately rather than discovering the
        dead end many steps later.</p>
    </div>
    <div style="padding:16px;background:#ecfdf5;border-radius:10px">
      <b style="color:#065f46;font-size:13.5px">Soft constraint ordering</b>
      <p style="font-size:13px;color:#444;margin-top:6px;line-height:1.6">
        Among legal options the kindest is tried first: penalties discourage giving a
        group two exams in one day (−10) or overloading a staff member (−5).
        The result is scored 0–100 for quality.</p>
    </div>
  </div>
</div>

<div class="panel">
  <h2>Uncertainty and explainability</h2>
  <p style="font-size:13.5px;line-height:1.8;color:#333;margin-top:6px">
    <b>Minimal-disruption repair.</b> When a teacher falls ill, rebuilding everything
    would disrupt students unnecessarily. Instead the system finds only the exams that
    now break a constraint, un-places those, and re-solves for them while every other
    exam stays fixed. In the built-in demo a staff absence moves 2 exams and leaves
    18 untouched.
  </p>
  <p style="font-size:13.5px;line-height:1.8;color:#333;margin-top:12px">
    <b>Explainable placements.</b> For any exam the system re-examines every
    alternative slot and room and reports why each was rejected: room too small,
    group already busy, staff unavailable, or room taken. It also reports whether
    a kinder placement existed. This turns the solver from a black box into something an
    exam officer can question.
  </p>
</div>

<div class="panel">
  <h2>General purpose by design</h2>
  <p style="font-size:13.5px;line-height:1.8;color:#333;margin-top:6px">
    The engine has no concept of "exams", only tasks, venues, staff and groups.
    Swapping the data file makes the same code schedule weekly lectures and labs,
    with no changes to the solver.
  </p>
  <p style="font-size:13px;color:#666;margin-top:16px;margin-bottom:8px">
    Six tables make up a dataset. In Excel each is a tab; in CSV each is a file.</p>
  <table style="min-width:auto">
    <tr><th>Table</th><th>Columns</th></tr>
    <tr><td><code>meta</code></td><td>title, task_label</td></tr>
    <tr><td><code>slots</code></td><td>slot</td></tr>
    <tr><td><code>venues</code></td><td>name, capacity</td></tr>
    <tr><td><code>groups</code></td><td>group, size</td></tr>
    <tr><td><code>tasks</code></td><td>name, staff, groups <i>(pipe-separated)</i></td></tr>
    <tr><td><code>unavailable</code></td><td>kind, who, slot</td></tr>
  </table>
</div>

<div class="panel" style="background:#fafafa">
  <h2 style="font-size:15px">Coursework information</h2>
  <p style="font-size:13px;color:#555;line-height:1.7;margin-top:6px">
    ST5001CMD Artificial Intelligence · Softwarica College of IT &amp; E-Commerce<br>
    Built in Python 3. The solver uses no external AI libraries and is implemented
    from first principles following Russell &amp; Norvig (2021),
    <i>Artificial Intelligence: A Modern Approach</i> (4th ed.), Chapter 6.
  </p>
</div>
""")


@app.route("/about")
def about():
    return render_template_string(ABOUT, title="How it works", active="about", ds=None)


# ── build your own timetable ─────────────────────────────────────────────────

BUILD_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/">← Back to Home</a>

<div class="panel">
  <h2>🛠 Build your own timetable</h2>
  <p class="sub">Change the problem and watch the AI solve it again. Add an exam,
     close rooms, remove time slots, or make a teacher unavailable, then generate.</p>

  <form method="POST" action="/build">
    <input type="hidden" name="base" value="{{ base }}">

    <div class="bsec">
      <h3>Rooms available</h3>
      <p class="bhint">Untick a room to close it, for example for maintenance.</p>
      <div class="chips">
        {% for v in all_venues %}
        <label class="chip {{ 'on' if v.name in venues_on else '' }}">
          <input type="checkbox" name="venue" value="{{ v.name }}"
                 {{ 'checked' if v.name in venues_on else '' }}>
          {{ v.name }} <span class="cap">{{ v.capacity }}</span>
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="bsec">
      <h3>Time slots available</h3>
      <p class="bhint">Remove slots to squeeze the timetable. Remove enough and no
         valid answer will exist, which the system will prove rather than guess.</p>
      <div class="chips">
        {% for s in all_slots %}
        <label class="chip {{ 'on' if s in slots_on else '' }}">
          <input type="checkbox" name="slot" value="{{ s }}"
                 {{ 'checked' if s in slots_on else '' }}>
          {{ s }}
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="bsec">
      <h3>Exams to schedule</h3>
      <p class="bhint">Untick any exam to leave it out.</p>
      <div class="chips">
        {% for t in all_tasks %}
        <label class="chip {{ 'on' if t.name in tasks_on else '' }}">
          <input type="checkbox" name="task" value="{{ t.name }}"
                 {{ 'checked' if t.name in tasks_on else '' }}>
          {{ t.name }}
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="bsec">
      <h3>Add a new exam</h3>
      <p class="bhint">Leave the name blank to skip.</p>
      <div class="frow">
        <div class="fg">
          <label>Exam name</label>
          <input type="text" name="new_name" placeholder="e.g. Computer Networks"
                 value="{{ form.new_name }}">
        </div>
        <div class="fg">
          <label>Teacher</label>
          <select name="new_staff">
            {% for s in all_staff %}
            <option {{ 'selected' if form.new_staff == s else '' }}>{{ s }}</option>
            {% endfor %}
          </select>
        </div>
      </div>
      <label>Which groups sit it</label>
      <div class="chips">
        {% for g, n in all_groups.items() %}
        <label class="chip {{ 'on' if g in form.new_groups else '' }}">
          <input type="checkbox" name="new_group" value="{{ g }}"
                 {{ 'checked' if g in form.new_groups else '' }}>
          {{ g }} <span class="cap">{{ n }}</span>
        </label>
        {% endfor %}
      </div>
    </div>

    <div class="bsec">
      <h3>Make a teacher unavailable</h3>
      <div class="frow">
        <div class="fg">
          <label>Teacher</label>
          <select name="block_staff">
            <option value="">nobody</option>
            {% for s in all_staff %}
            <option {{ 'selected' if form.block_staff == s else '' }}>{{ s }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="fg">
          <label>Unavailable slots (comma separated)</label>
          <input type="text" name="block_slots" placeholder="Mon 9AM, Mon 1PM"
                 value="{{ form.block_slots }}">
        </div>
      </div>
    </div>

    <div style="display:flex;gap:10px;margin-top:6px">
      <button class="btn btn-primary" type="submit">Generate timetable →</button>
      <a href="/build?base={{ base }}" class="btn btn-sm"
         style="background:#e5e7eb;color:#374151;padding:9px 22px">Reset</a>
    </div>
  </form>
</div>

{% if attempted %}
  {% if error %}
  <div class="alert a-red"><b>Cannot schedule.</b> {{ error }}</div>
  {% elif result is none %}
  <div class="panel">
    <h2>❌ No valid timetable exists</h2>
    <p class="sub">The search explored every possibility and proved these constraints
       cannot all be satisfied at the same time.</p>
    <p style="font-size:13.5px;line-height:1.8;color:#333">
      You asked for <b>{{ n_tasks }} exams</b> in <b>{{ n_slots }} slots</b> across
      <b>{{ n_venues }} rooms</b>, which is {{ n_slots * n_venues }} possible sittings.
      This is a definite answer, not a failure to find one. Add a slot or reopen a room
      and try again.
    </p>
    <p style="font-size:13px;color:#666;margin-top:10px">
      Proved in {{ elapsed }}s after {{ tried }} placement attempts.
    </p>
  </div>
  {% else %}
  <div class="stats">
    <div class="stat blue"><div class="v">{{ n_tasks }}</div><div class="l">Exams scheduled</div></div>
    <div class="stat {{ 'green' if clashes==0 else 'red' }}">
      <div class="v">{{ clashes }}</div><div class="l">Clashes</div></div>
    <div class="stat {{ 'green' if quality==100 else 'amber' }}">
      <div class="v">{{ quality }}/100</div><div class="l">Quality score</div></div>
    <div class="stat amber"><div class="v">{{ elapsed }}s</div><div class="l">Solve time</div></div>
    <div class="stat {{ 'green' if backtracks==0 else 'amber' }}">
      <div class="v">{{ backtracks }}</div><div class="l">Backtracks</div></div>
  </div>

  <div class="tt-wrap">
    <h2>Your timetable</h2>
    <div class="legend">
      {% for g, c in colors.items() %}
      <span class="litem" style="background:{{ c }}">{{ g }}</span>
      {% endfor %}
    </div>
    <table>
      <tr><th></th>
        {% for v in shown_venues %}<th>{{ v.name }}<br>
          <small style="opacity:.7">cap {{ v.capacity }}</small></th>{% endfor %}
      </tr>
      {% for slot in slots %}
      <tr>
        <td class="sc">{{ slot }}</td>
        {% for v in shown_venues %}
          {% set key = slot + '|||' + v.name %}
          {% if key in by_cell %}
            {% set item = by_cell[key] %}
            <td><div class="ec" style="background:{{ colors[item.group1] }};
                 {% if item.is_new %}outline:3px solid #fbbf24;{% endif %}">
              <b>{{ item.name }}</b>{% if item.is_new %} ✨{% endif %}
              <small>{{ item.groups }} · {{ item.people }} ppl · {{ item.staff }}</small>
            </div></td>
          {% else %}<td class="em"></td>{% endif %}
        {% endfor %}
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}
{% endif %}
""")


def _build_defaults(data):
    return {
        "venues_on": [v["name"] for v in data["venues"]],
        "slots_on": list(data["slots"]),
        "tasks_on": [t["name"] for t in data["tasks"]],
    }


@app.route("/build", methods=["GET", "POST"])
def build():
    base = (request.values.get("base") or "exams")
    if base not in ("exams", "classes"):
        base = "exams"

    data = load_data(DATASETS[base])
    all_staff = sorted({t["staff"] for t in data["tasks"]})

    ctx = {
        "base": base,
        "all_venues": data["venues"],
        "all_slots": list(data["slots"]),
        "all_tasks": data["tasks"],
        "all_groups": data["groups"],
        "all_staff": all_staff,
        "form": {"new_name": "", "new_staff": all_staff[0] if all_staff else "",
                 "new_groups": [], "block_staff": "", "block_slots": ""},
        "attempted": False, "error": None, "result": None,
    }
    ctx.update(_build_defaults(data))

    if request.method == "GET":
        return render_template_string(BUILD_PAGE, title="Build your own",
                                      active="build", ds=None, **ctx)

    # ---- read the form ----
    f = request.form
    venues_on = f.getlist("venue")
    slots_on = f.getlist("slot")
    tasks_on = f.getlist("task")
    new_name = (f.get("new_name") or "").strip()
    new_staff = f.get("new_staff") or ""
    new_groups = f.getlist("new_group")
    block_staff = f.get("block_staff") or ""
    block_slots = [s.strip() for s in (f.get("block_slots") or "").split(",") if s.strip()]

    ctx.update({
        "venues_on": venues_on, "slots_on": slots_on, "tasks_on": tasks_on,
        "attempted": True,
        "form": {"new_name": new_name, "new_staff": new_staff,
                 "new_groups": new_groups, "block_staff": block_staff,
                 "block_slots": ", ".join(block_slots)},
    })

    # ---- assemble the scenario ----
    scenario = copy.deepcopy(data)
    scenario["venues"] = [v for v in data["venues"] if v["name"] in venues_on]
    scenario["slots"] = [s for s in data["slots"] if s in slots_on]
    scenario["tasks"] = [t for t in data["tasks"] if t["name"] in tasks_on]

    if new_name:
        if not new_groups:
            ctx["error"] = "Choose at least one group for the new exam."
            return render_template_string(BUILD_PAGE, title="Build your own",
                                          active="build", ds=None, **ctx)
        if any(t["name"].lower() == new_name.lower() for t in scenario["tasks"]):
            ctx["error"] = f"There is already an exam called '{new_name}'."
            return render_template_string(BUILD_PAGE, title="Build your own",
                                          active="build", ds=None, **ctx)
        scenario["tasks"].append({"name": new_name, "staff": new_staff,
                                  "groups": new_groups})

    if block_staff and block_slots:
        scenario.setdefault("staff_unavailable", {})
        scenario["staff_unavailable"] = dict(scenario.get("staff_unavailable") or {})
        scenario["staff_unavailable"][block_staff] = list(
            scenario["staff_unavailable"].get(block_staff, [])) + block_slots

    # slot dates no longer apply once slots are edited by hand
    scenario["slot_dates"] = {s: d for s, d in (data.get("slot_dates") or {}).items()
                              if s in scenario["slots"]}
    scenario["_by_name"] = {t["name"]: t for t in scenario["tasks"]}

    # ---- sanity checks before searching ----
    if not scenario["slots"]:
        ctx["error"] = "Keep at least one time slot."
    elif not scenario["venues"]:
        ctx["error"] = "Keep at least one room open."
    elif not scenario["tasks"]:
        ctx["error"] = "Keep at least one exam to schedule."
    else:
        biggest = max(v["capacity"] for v in scenario["venues"])
        toobig = [t["name"] for t in scenario["tasks"]
                  if attendance(t, scenario) > biggest]
        if toobig:
            ctx["error"] = (f"No open room is large enough for: "
                            f"{', '.join(toobig)}. Reopen a bigger room.")
    if ctx["error"]:
        return render_template_string(BUILD_PAGE, title="Build your own",
                                      active="build", ds=None, **ctx)

    # ---- solve ----
    stats = {"attempts": 0, "backtracks": 0}
    t0 = time.time()
    result = solve({}, scenario["tasks"], scenario, stats)
    elapsed = round(time.time() - t0, 3)

    ctx.update({
        "result": result, "elapsed": elapsed, "tried": stats["attempts"],
        "backtracks": stats["backtracks"],
        "n_tasks": len(scenario["tasks"]), "n_slots": len(scenario["slots"]),
        "n_venues": len(scenario["venues"]),
    })

    if result is not None:
        colors = group_colors(scenario)
        used = {v for _s, v in result.values()}
        by_cell = {}
        for name, (slot, venue) in result.items():
            task = scenario["_by_name"][name]
            by_cell[slot + "|||" + venue] = {
                "name": name, "group1": task["groups"][0],
                "groups": ", ".join(task["groups"]),
                "people": attendance(task, scenario), "staff": task["staff"],
                "is_new": bool(new_name) and name == new_name,
            }
        ctx.update({
            "colors": colors,
            "shown_venues": [v for v in scenario["venues"] if v["name"] in used],
            "slots": scenario["slots"], "by_cell": by_cell,
            "clashes": len(verify(result, scenario)),
            "quality": quality_score(result, scenario),
        })

    return render_template_string(BUILD_PAGE, title="Build your own",
                                  active="build", ds=None, **ctx)




# ── timetable ─────────────────────────────────────────────────────────────────

TT_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/">← Back to Home</a>

{% if report and not report.clean %}
<div class="panel" style="padding:20px 24px;margin-bottom:20px">
  <h2 style="font-size:15px">🧹 Data quality report
    <span style="font-weight:400;color:#888;font-size:12.5px">
      ({{ report.source }}, {{ report.format|upper }})</span></h2>
  <p class="sub" style="margin-bottom:14px">
    The dataset was checked and cleaned before scheduling.</p>
  {% for m in report.repairs %}
  <div style="font-size:13px;padding:5px 0;color:#065f46">
    <b style="color:#059669">repaired</b> &nbsp;{{ m }}</div>
  {% endfor %}
  {% for m in report.warnings %}
  <div style="font-size:13px;padding:5px 0;color:#92400e">
    <b style="color:#d97706">warning</b> &nbsp;&nbsp;{{ m }}</div>
  {% endfor %}
</div>
{% endif %}

<div class="stats">
  <div class="stat blue"><div class="v">{{ ntasks }}</div><div class="l">Tasks scheduled</div></div>
  <div class="stat {{ 'green' if clashes==0 else 'red' }}">
    <div class="v">{{ clashes }}</div><div class="l">Clashes</div></div>
  <div class="stat {{ 'green' if quality==100 else 'amber' }}">
    <div class="v">{{ quality }}/100</div><div class="l">Quality score</div></div>
  <div class="stat amber"><div class="v">{{ elapsed }}s</div><div class="l">Solve time</div></div>
  <div class="stat blue"><div class="v">{{ backtracks }}</div><div class="l">Backtracks</div></div>
</div>

<div class="tt-wrap">
  <h2>{{ tt_title }}
    {% if date_range %}<span style="font-weight:400;color:#666;font-size:14px">
      &nbsp;·&nbsp; {{ date_range }}</span>{% endif %}
  </h2>

  <div class="viewbar">
    <span class="vlabel">Showing</span>
    <a href="/timetable?dataset={{ ds }}"
       class="vopt {{ 'on' if not group else '' }}">Everyone</a>
    {% for g in groups %}
    <a href="/timetable?dataset={{ ds }}&group={{ g|urlencode }}"
       class="vopt {{ 'on' if group == g else '' }}"
       style="{{ 'background:' ~ colors[g] ~ ';border-color:' ~ colors[g] ~ ';color:#fff' if group == g else '' }}">
      {{ g }}</a>
    {% endfor %}
  </div>

  {% if group %}
  <p style="font-size:13px;color:#666;margin-bottom:14px">
    {{ mine }} of {{ ntasks }} shown &nbsp;·&nbsp;
    {{ group }} has {{ groups[group] }} students
    {% if my_days %}&nbsp;·&nbsp; across {{ my_days }} day{{ '' if my_days == 1 else 's' }}{% endif %}
  </p>
  {% else %}
  <div class="legend">
    {% for g, c in colors.items() %}
    <span class="litem" style="background:{{ c }}">{{ g }} ({{ groups[g] }})</span>
    {% endfor %}
  </div>
  {% endif %}
  <table>
    <tr>
      <th></th>
      {% for v in shown_venues %}<th>{{ v.name }}<br><small style="opacity:.7">cap {{ v.capacity }}</small></th>{% endfor %}
    </tr>
    {% for slot in slots %}
    <tr>
      <td class="sc">{{ slot }}
        {% if slot_dates.get(slot) %}<span class="sd">{{ slot_dates[slot] }}</span>{% endif %}
      </td>
      {% for v in shown_venues %}
        {% set key = slot + '|||' + v.name %}
        {% if key in by_cell %}
          {% set item = by_cell[key] %}
          <td>
            <div class="ec" style="background:{{ colors[item.group1] }}"
                 title="Click to explain this placement"
                 onclick="location.href='/explain?dataset={{ ds }}&exam={{ item.name|urlencode }}'">
              <b>{{ item.name }}</b>
              <small>{{ item.groups }} · {{ item.people }} ppl · {{ item.staff }}</small>
            </div>
          </td>
        {% else %}
          <td class="em"></td>
        {% endif %}
      {% endfor %}
    </tr>
    {% endfor %}
  </table>
</div>

{% if group and mine == 0 %}
<p style="text-align:center;color:#888;font-size:13.5px;padding:26px 0">
  {{ group }} has nothing scheduled.</p>
{% endif %}

<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap">
  <a href="/disrupt?dataset={{ ds }}" class="btn btn-danger">⚡ Simulate Disruption</a>
  <a href="/explain?dataset={{ ds }}" class="btn btn-primary">💬 Explain a Placement</a>
  <a href="/summary?dataset={{ ds }}" class="btn" style="background:#e5e7eb;color:#374151">📊 Data Summary</a>
</div>
""")


FAIL_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/">← Back to Home</a>

<div class="panel">
  <h2>{{ heading }}</h2>
  <p class="sub">{{ subtitle }}</p>

  {% if report %}
    {% for m in report.errors %}
    <div class="alert a-red">✕ {{ m }}</div>
    {% endfor %}
    {% if report.repairs %}
      <h2 style="font-size:14px;margin-top:20px">Automatically repaired first</h2>
      {% for m in report.repairs %}
      <div style="font-size:13px;padding:5px 0;color:#065f46">
        <b style="color:#059669">repaired</b> &nbsp;{{ m }}</div>
      {% endfor %}
    {% endif %}
    {% if report.warnings %}
      <h2 style="font-size:14px;margin-top:20px">Warnings</h2>
      {% for m in report.warnings %}
      <div style="font-size:13px;padding:5px 0;color:#92400e">
        <b style="color:#d97706">warning</b> &nbsp;&nbsp;{{ m }}</div>
      {% endfor %}
    {% endif %}
  {% endif %}

  <p style="margin-top:22px;font-size:13.5px;color:#555;line-height:1.7">
    {{ footnote }}
  </p>
  <a href="/" class="btn btn-primary btn-sm" style="margin-top:12px">← Choose another dataset</a>
</div>
""")


def _rejected(report, active):
    """Page shown when a dataset is too broken to schedule."""
    return render_template_string(
        FAIL_PAGE, title="Dataset rejected", active=active, ds=None,
        report=report,
        heading="⚠ Dataset rejected",
        subtitle="The data contains problems that make scheduling impossible. "
                 "Fix these and try again.",
        footnote="The system refuses to build a timetable from invalid data "
                 "rather than producing one that looks correct but is not. "
                 "Recoverable noise (extra spaces, wrong capitalisation, "
                 "duplicate rows) is repaired automatically; the issues above "
                 "need a human decision.",
    ), 400


def _no_solution(active):
    """Page shown when the data is valid but no legal timetable exists."""
    return render_template_string(
        FAIL_PAGE, title="No solution", active=active, ds=None,
        report=None,
        heading="No valid timetable exists",
        subtitle="The search proved that these constraints cannot all be "
                 "satisfied at the same time.",
        footnote="This is a definite answer, not a failure to find one. "
                 "Backtracking search explored the space exhaustively. "
                 "To make it solvable, add time slots or venues, or relax "
                 "a staff availability restriction.",
    ), 200


@app.route("/timetable")
def timetable():
    ds = request.args.get("dataset", "exams")
    data, result, stats, elapsed = run_solver(ds)
    report = data.get("_report")

    if report is not None and not report.ok:
        return _rejected(report, "tt")
    if result is None:
        return _no_solution("tt")

    colors = group_colors(data)

    # optional filter: show only one student group's timetable
    group = request.args.get("group", "")
    if group not in data["groups"]:
        group = ""

    visible = {n: p for n, p in result.items()
               if not group or group in data["_by_name"][n]["groups"]}

    # only show rooms and days that the visible tasks actually use
    used = {v for _, v in visible.values()}
    shown = [v for v in data["venues"] if v["name"] in used]

    if group:
        busy_days = {s.split()[0] for s, _v in visible.values()}
        rows = [s for s in data["slots"] if s.split()[0] in busy_days]
    else:
        busy_days = set()
        rows = data["slots"]

    # build cell lookup: "slot|||venue" -> item dict
    by_cell = {}
    for name, (slot, venue) in visible.items():
        task = data["_by_name"][name]
        by_cell[slot + "|||" + venue] = {
            "name": name,
            "group1": task["groups"][0],
            "groups": ", ".join(task["groups"]),
            "people": attendance(task, data),
            "staff": task["staff"],
        }

    from urllib.parse import quote
    for k in by_cell:
        by_cell[k]["name_url"] = quote(by_cell[k]["name"])

    # dated exam week, or the term a recurring timetable applies to
    slot_dates = {s: pretty_date(iso)
                  for s, iso in (data.get("slot_dates") or {}).items()}
    date_range = period_text(data)

    return render_template_string(
        TT_PAGE,
        title=data.get("title", "Timetable"),
        active="tt", ds=ds,
        tt_title=data.get("title", "TIMETABLE"),
        ntasks=len(result),
        clashes=len(verify(result, data)),
        quality=quality_score(result, data),
        elapsed=elapsed,
        backtracks=stats["backtracks"],
        colors=colors,
        groups=data["groups"],
        slots=rows,
        shown_venues=shown,
        by_cell=by_cell,
        report=report,
        slot_dates=slot_dates,
        date_range=date_range,
        group=group,
        mine=len(visible),
        my_days=len(busy_days),
    )


# ── disruption simulator ──────────────────────────────────────────────────────

DIS_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/timetable?dataset={{ ds }}">← Back to Timetable</a>

<div class="panel">
  <h2>⚡ Disruption Simulator</h2>
  <p class="sub">Mark a staff member as unavailable for certain slots.
     The engine repairs only the affected exams. Everything else stays fixed.</p>
  <form method="POST" action="/disrupt">
    <input type="hidden" name="dataset" value="{{ ds }}">
    <div class="frow">
      <div class="fg">
        <label>Staff member</label>
        <select name="staff">
          {% for s in staff_list %}<option>{{ s }}</option>{% endfor %}
        </select>
      </div>
      <div class="fg">
        <label>Unavailable slots (comma-separated, e.g. Mon 9AM, Mon 1PM)</label>
        <input type="text" name="slots" placeholder="Mon 9AM, Mon 1PM">
      </div>
      <div>
        <button class="btn btn-danger" type="submit">Apply Disruption</button>
      </div>
    </div>
  </form>
</div>

{% if result %}
  {% if moved %}
  <div class="alert a-amber">
    ⚡ Disruption applied. <strong>{{ moved|length }} exam(s) rescheduled</strong>,
    {{ untouched }} untouched. 0 clashes in repaired timetable.
  </div>
  <div class="moved">
    <h4>Moved exams:</h4>
    {% for m in moved %}
    <div class="mi">📌 <b>{{ m.name }}</b>:
      <span style="color:#dc2626">{{ m.old_slot }} / {{ m.old_venue }}</span>
      <span class="arr"> → </span>
      <span style="color:#059669">{{ m.new_slot }} / {{ m.new_venue }}</span>
    </div>
    {% endfor %}
  </div>
  {% else %}
  <div class="alert a-green">✅ No exams affected. The timetable is already valid after this disruption.</div>
  {% endif %}

  <div class="tt-wrap">
    <h2>Repaired Timetable</h2>
    <div class="legend">
      {% for g, c in colors.items() %}
      <span class="litem" style="background:{{ c }}">{{ g }}</span>
      {% endfor %}
    </div>
    <table>
      <tr>
        <th></th>
        {% for v in shown_venues %}<th>{{ v.name }}</th>{% endfor %}
      </tr>
      {% for slot in slots %}
      <tr>
        <td class="sc">{{ slot }}
          {% if slot_dates.get(slot) %}<span class="sd">{{ slot_dates[slot] }}</span>{% endif %}
        </td>
        {% for v in shown_venues %}
          {% set key = slot + '|||' + v.name %}
          {% if key in by_cell %}
            {% set item = by_cell[key] %}
            <td><div class="ec" style="background:{{ colors[item.group1] }};
                 {% if item.moved %}outline:3px solid #fbbf24;{% endif %}">
              <b>{{ item.name }}</b>{% if item.moved %} ⚡{% endif %}
              <small>{{ item.staff }}</small>
            </div></td>
          {% else %}
            <td class="em"></td>
          {% endif %}
        {% endfor %}
      </tr>
      {% endfor %}
    </table>
  </div>
{% endif %}
""")


@app.route("/disrupt", methods=["GET", "POST"])
def disrupt():
    ds = request.args.get("dataset") or request.form.get("dataset", "exams")
    data, original, _, _ = run_solver(ds)

    report = data.get("_report")
    if report is not None and not report.ok:
        return _rejected(report, "dis")
    if original is None:
        return _no_solution("dis")

    staff_list = sorted({t["staff"] for t in data["tasks"]})

    result_ctx = {}
    if request.method == "POST":
        staff = request.form.get("staff", "")
        raw = request.form.get("slots", "")
        slots_list = [s.strip() for s in raw.split(",") if s.strip()]

        disrupted = copy.deepcopy(data)
        disrupted["_by_name"] = {t["name"]: t for t in disrupted["tasks"]}
        apply_disruption(disrupted, "staff", staff, slots_list)
        repaired, moved_info = repair(dict(original), disrupted)

        if repaired is None:
            result_ctx = {"error": True}
        else:
            moved_names = {m[0] for m in moved_info}
            colors = group_colors(data)
            used = {v for _, v in repaired.values()}
            shown = [v for v in data["venues"] if v["name"] in used]

            by_cell = {}
            for name, (slot, venue) in repaired.items():
                task = data["_by_name"][name]
                by_cell[slot + "|||" + venue] = {
                    "name": name,
                    "group1": task["groups"][0],
                    "staff": task["staff"],
                    "moved": name in moved_names,
                }

            moved_list = [
                {"name": n, "old_slot": os_, "old_venue": ov,
                 "new_slot": ns, "new_venue": nv}
                for n, (os_, ov), (ns, nv) in moved_info
            ]

            result_ctx = {
                "result": True,
                "moved": moved_list,
                "untouched": len(repaired) - len(moved_list),
                "colors": colors,
                "slots": data["slots"],
                "shown_venues": shown,
                "by_cell": by_cell,
                "slot_dates": {s: pretty_date(iso)
                               for s, iso in (data.get("slot_dates") or {}).items()},
            }

    result_ctx.setdefault("slot_dates", {})
    return render_template_string(
        DIS_PAGE,
        title="Disruption Simulator",
        active="dis", ds=ds,
        staff_list=staff_list,
        **result_ctx,
    )


# ── explain ───────────────────────────────────────────────────────────────────

EXP_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/timetable?dataset={{ ds }}">← Back to Timetable</a>

<div class="panel">
  <h2>💬 Explain a Placement</h2>
  <p class="sub">The system explains why a task was placed in its slot and room,
     and what ruled out every other option.</p>
  <form method="GET" action="/explain">
    <input type="hidden" name="dataset" value="{{ ds }}">
    <div class="frow">
      <div class="fg">
        <label>Select exam / class</label>
        <select name="exam">
          {% for name in task_names %}
          <option value="{{ name }}" {{ 'selected' if name == selected else '' }}>{{ name }}</option>
          {% endfor %}
        </select>
      </div>
      <div><button class="btn btn-primary" type="submit">Explain →</button></div>
    </div>
  </form>
</div>

{% if explanation %}
<div class="panel">
  <h2>Explanation</h2>
  <div style="margin-top:12px">
    <pre class="xpre">{{ explanation }}</pre>
  </div>
</div>
{% endif %}
""")


@app.route("/explain")
def explain():
    ds = request.args.get("dataset", "exams")
    exam = request.args.get("exam", "")
    data, result, _, _ = run_solver(ds)

    report = data.get("_report")
    if report is not None and not report.ok:
        return _rejected(report, "exp")
    if result is None:
        return _no_solution("exp")

    task_names = sorted(result.keys())
    explanation = ""
    if exam and exam in result:
        explanation = explain_placement(exam, result, data)
    elif task_names:
        exam = task_names[0]
        explanation = explain_placement(exam, result, data)

    return render_template_string(
        EXP_PAGE,
        title="Explain",
        active="exp", ds=ds,
        task_names=task_names,
        selected=exam,
        explanation=explanation,
    )


# ── data summary ──────────────────────────────────────────────────────────────

SUM_PAGE = BASE.replace("{% block body %}{% endblock %}", """
<a class="back" href="/timetable?dataset={{ ds }}">← Back to Timetable</a>

<div class="panel" style="margin-bottom:20px">
  <h2>📊 Dataset Summary: {{ dstitle }}</h2>
  <p class="sub">Everything the scheduler knows about this problem.</p>
</div>

<div class="sg">
  <div class="sc2">
    <h4>📚 Tasks ({{ tasks|length }})</h4>
    <ul>{% for t in tasks %}<li>{{ t.name }}</li>{% endfor %}</ul>
  </div>
  <div class="sc2">
    <h4>👥 Student Groups</h4>
    <ul>{% for g, n in groups.items() %}<li>{{ g }}: {{ n }} students</li>{% endfor %}</ul>
  </div>
  <div class="sc2">
    <h4>👩‍🏫 Staff ({{ staff|length }})</h4>
    <ul>{% for s in staff %}<li>{{ s }}</li>{% endfor %}</ul>
  </div>
  <div class="sc2">
    <h4>🏛 Venues ({{ venues|length }})</h4>
    <ul>{% for v in venues %}<li>{{ v.name }}: capacity {{ v.capacity }}</li>{% endfor %}</ul>
  </div>
  <div class="sc2">
    <h4>🕐 Time Slots ({{ slots|length }})</h4>
    <ul>{% for s in slots %}
      <li>{{ s }}{% if slot_dates.get(s) %}
        <span style="color:#888;font-size:12px"> · {{ slot_dates[s] }}</span>{% endif %}</li>
    {% endfor %}</ul>
  </div>
  <div class="sc2">
    <h4>🚫 Staff Unavailability</h4>
    <ul>
    {% if unavail %}
      {% for person, slist in unavail.items() %}
      <li>{{ person }}: {{ slist|join(', ') }}</li>
      {% endfor %}
    {% else %}
      <li>None defined</li>
    {% endif %}
    </ul>
  </div>
  <div class="sc2">
    <h4>⚖️ Hard Constraints</h4>
    <ul>
      <li>C1 No group double-booked</li>
      <li>C2 No venue double-booked</li>
      <li>C3 Venue capacity respected</li>
      <li>C4 No staff double-booked</li>
      <li>C5 Staff unavailability respected</li>
      <li>C6 Venue unavailability respected</li>
    </ul>
  </div>
  <div class="sc2">
    <h4>✨ AI Techniques</h4>
    <ul>
      <li>CSP modelling</li>
      <li>Backtracking search</li>
      <li>MRV heuristic</li>
      <li>Forward checking</li>
      <li>Soft constraint value ordering</li>
      <li>Minimal-disruption repair</li>
      <li>Explainable placements</li>
    </ul>
  </div>
</div>
""")


@app.route("/summary")
def summary():
    ds = request.args.get("dataset", "exams")
    data, _, _, _ = run_solver(ds)

    report = data.get("_report")
    if report is not None and not report.ok:
        return _rejected(report, "sum")

    staff = sorted({t["staff"] for t in data["tasks"]})
    return render_template_string(
        SUM_PAGE,
        title="Summary",
        active="sum", ds=ds,
        dstitle=data.get("title", "Dataset"),
        tasks=data["tasks"],
        groups=data["groups"],
        staff=staff,
        venues=data["venues"],
        slots=data["slots"],
        slot_dates={s: pretty_date(iso)
                    for s, iso in (data.get("slot_dates") or {}).items()},
        unavail=data.get("staff_unavailable", {}),
    )


# ── run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import threading, webbrowser
    URL = "http://localhost:5000"
    print("\n  TimetableAI is running.")
    print(f"  Opening in your browser:  {URL}")
    print("  (press CTRL+C here to stop the server)\n")
    threading.Timer(1.2, lambda: webbrowser.open(URL)).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
