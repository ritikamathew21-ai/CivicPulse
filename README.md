# CivicPulse

**Cross-signal urban incident intelligence.** Team Nexora, BUiLDX 2026, CivicTech track.

CivicPulse takes separate city signals (rainfall, traffic slowdowns, road incidents), works out which
belong to the same event in space and time, and gives an operator a ranked, explained hypothesis.

**Live project:** <https://civicpulse-seven-vert.vercel.app> ([API docs](https://civicpulse-seven-vert.vercel.app/docs)).
Choose **Load one event** to start.

## Problem statement

Cities produce signals all the time, but weather, traffic and incident reports are usually viewed in
separate systems. An operator has to connect them by hand, and it is hard to tell which signals matter
and which are unrelated.

## Proposed solution

An analytical layer that sits on top of existing systems rather than replacing them. It aligns signals by
place and time, scores each group with fixed, visible weights, and shows the evidence for every
hypothesis **and** the reason each other signal was left out.

## Key features

- **Alignment** with an adjustable radius (default 1 km) and time window (default 15 min).
- **Deterministic reasoning**: the same signals always give the same result.
- **Explanations for every signal**, aligned or excluded.
- **Infrastructure context**: the nearest hospital, fire station, railway station and major road within
  500 m of an event, from OpenStreetMap.
- **Rainfall anomaly detection**: flags rain that is unusual for that place and month, compared with ten
  years of hourly history.
- **Ranked hypotheses** when several events happen at once, ordered by priority.
- **Operator alerts**: acknowledge, resolve, reopen. An alert keeps its status as its event grows, and
  shows how many signals arrived since the last decision.
- **Interactive map**: select an insight to highlight its signals and fade the rest.
- **Live mode**: rainfall from Open-Meteo at five Mumbai points and at recently reported locations.
- **Signal reporting** from the map, or through the API.

### What is simulated, and current limits

- **Demo mode uses simulated signals.** Every result shown is calculated from them.
- Live rainfall is a weather model value, not a rain gauge reading. **No live traffic feed is connected**;
  live traffic and incidents come from reports.
- The score is an engineering score (maximum 95%), not a probability and not machine learning.
- There is no sign-in. Everyone using the hosted site shares the same data and can change it.
- Each analysis covers the newest 500 signals from the last 24 hours.
- Rain history is gridded hourly data, so comparing it with a point reading is approximate. A fixed
  percentile test is used, not machine learning. Traffic and incidents have no history, so no anomaly check.
- Infrastructure is a bundled OpenStreetMap snapshot, and may be incomplete.
- Not built yet: PostGIS, live traffic, historical pattern analysis, response workflows.

## How the reasoning works

1. **Filter.** Readings below 2.5 mm/h rain or 30% slowdown are background, not evidence.
2. **Pair.** Two signals align if they are within the radius *and* the time window.
3. **Group.** The signal with the most signal types around it, then the most neighbours, then the most
   central position, becomes an anchor. Members must align with the anchor, so a chain of neighbours
   cannot merge distant events.
4. **Require two types.** One type alone is not cross-signal evidence.
5. **Score.**

| Factor | Weight |
|---|---|
| Rainfall present | 0.30 |
| Traffic slowdown present | 0.25 |
| Road incident present | 0.20 |
| Spatial alignment | 0.10 × share of pairs within the radius |
| Temporal alignment | 0.10 × share of pairs within the window |

### Priority

Priority decides the order operators see. It starts from the score and **never changes it**: +0.05 for each
kind of infrastructure nearby, +0.05 for unusual rain (above 99% of that month's hours in 2016–2025) or
+0.10 for extreme rain (above 99.9%). High is 1.00 or more, medium 0.75 or more. These values are design
choices, not learned from data.

The "one event" demo has 9 signals: 8 aligned, 1 excluded, 28 aligned pairs, score 95%. A test checks this.

## Technologies used

| Part | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Map | Leaflet, OpenStreetMap |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy |
| Hosting | Vercel, with Neon PostgreSQL |
| Live weather | [Open-Meteo](https://open-meteo.com/) (no API key) |
| Tests | pytest |

## Installation and setup

Needs **Python 3.11 or 3.12** and Node.js 22 or newer. Python 3.13+ does not work, because the
bundled PostgreSQL package has no build for it. PostgreSQL itself does not have to be installed: the development
requirements include its binaries, and data is kept in `.civicpulse` in your home folder.

Windows (PowerShell):

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
cd ../frontend
npm install
```

On macOS or Linux, use `python3.12 -m venv .venv`, then `.venv/bin/python` instead of `.venv\Scripts\python`.

To use your own PostgreSQL, set `DATABASE_URL=postgresql://user:password@host:5432/dbname`.

## How to run the project

Terminal 1:

```powershell
cd backend
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

Terminal 2:

```powershell
cd frontend
npm run dev
```

Open <http://localhost:5173> and choose **Load one event** or **Load several events**.
API documentation is at <http://localhost:8000/docs>.

Tests use a separate temporary database:

```powershell
cd backend
.venv\Scripts\python -m pytest
```

## Deployment

`vercel.json` deploys the dashboard and API as one Vercel project. It needs a PostgreSQL `DATABASE_URL`
(Neon, from the Vercel Marketplace). Pushes to `main` deploy automatically.

## Project architecture

```mermaid
flowchart LR
  D[Demo scenarios] --> API
  W[Open-Meteo rainfall] --> API
  O[Operator reports] --> API
  API[FastAPI] <--> DB[(PostgreSQL)]
  C[OpenStreetMap + rainfall history] --> P
  API --> A[Space + time alignment] --> R[Cross-signal scoring] --> H[Explained hypotheses] --> P[Priority]
  P --> UI[React + Leaflet dashboard]
  UI -- decisions --> API
```

| Path | Purpose |
|---|---|
| `backend/app/reasoning.py` | Alignment, grouping, scoring, explanations (pure functions) |
| `backend/app/service.py` | Database reads and writes around the engine |
| `backend/app/main.py`, `schemas.py` | API routes and input validation |
| `backend/app/context.py`, `data/` | Infrastructure, rainfall history and priority |
| `backend/scripts/build_context.py` | Rebuilds the files in `data/` |
| `backend/app/weather.py` | Open-Meteo client |
| `backend/app/demo.py` | Simulated scenarios |
| `backend/app/dev_db.py` | Local PostgreSQL for development |
| `backend/tests/` | Engine and API tests |
| `frontend/src/` | Dashboard |

## Team members and contributions

Team **Nexora** (solo participant)

| Member | Contribution |
|---|---|
| Ritika Mathew | Project concept and proposal, scope and product decisions, and development with Claude Code as the AI coding assistant |

## AI tools and third-party work

Built during BUiLDX 2026 with Claude Code (Anthropic) as an AI coding assistant, under the event's AI
Tools Policy. No earlier project code was reused. Third-party libraries are listed in
`backend/requirements.txt` and `frontend/package.json`. Map and infrastructure data © OpenStreetMap contributors, available under the
[ODbL](https://www.openstreetmap.org/copyright). Weather data by Open-Meteo.com (CC BY 4.0).
