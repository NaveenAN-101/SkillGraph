# SkillGraph

SkillGraph is a skill intelligence platform that helps learners and professionals plan job transitions using a graph-based model of users, skills, job roles, prerequisites, and courses.

## Core Features

- Skill gap analysis between a user and a target job role
- Learning path generation using prerequisite depth
- Course recommendations for missing skills
- Progress tracking (`matched / total required`) with percent completion
- Career switch recommendations based on current profile
- Career transition advisor with missing skills + suggested courses
- Interactive D3 graph visualization for jobs, skills, prerequisites, and courses
- Admin panel for CRUD operations (users, skills, jobs, courses, relations)
- Skill Copilot roadmap generation (rule-based AI-style planning)
- Live Market Intelligence with free-source sync + fallback mode

## Tech Stack

- Backend: FastAPI (Python)
- Database: Neo4j
- Frontend: HTML, CSS, JavaScript, D3.js

## Project Structure

```text
SkillGraph/
  .env.example
  main.py
  db.py
  index.html
  requirements.txt
  start_app.bat
```

## Local Setup

### 1) Prerequisites

- Python 3.10+
- Neo4j running locally (or remotely)
- WSL installed (recommended for `start_app.bat` flow)

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure database

Update Neo4j connection values in `db.py`:

- `URI`
- `USERNAME`
- `PASSWORD`

### 4) Configure launcher (optional but recommended)

1. Copy `.env.example` to `.env`
2. Edit values only if needed

Important fields:
- `WSL_PROJECT_PATH` (leave blank for auto-detect)
- `API_PORT`
- `FRONTEND_PORT`
- `INDEX_FILE`
- `ENABLE_NEO4J_START`

`.env` is machine-specific and is ignored by git.

### 5) Run application

```bash
start_app.bat
```

This starts:
- Neo4j in WSL (if enabled)
- FastAPI backend in WSL
- Frontend static server in Windows
- Browser at `http://localhost:5500/index.html` (default)

Manual backend run (alternative):

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 6) Open frontend (manual mode)

If not using `start_app.bat`, serve frontend and open:
- `http://localhost:5500/index.html`

## Key API Endpoints

- `GET /learning-path/{job}`
- `GET /skill-gap/{user}/{job}`
- `GET /course-recommendations/{user}/{job}`
- `GET /progress/{user_id}/{job_title}`
- `GET /career-recommendations/{user_id}`
- `GET /career-transition/{user_id}`
- `POST /ai-roadmap`
- `POST /market/sync`
- `GET /market/intelligence`
- `GET /market/intelligence/{user_id}`

## Market Intelligence (Free Sources)

Market sync uses free/public sources with fallback support.

Example sync modes:
- All sources: `POST /market/sync?source=all&max_posts=220&allow_fallback=true`
- Remotive only: `POST /market/sync?source=remotive`
- Arbeitnow only: `POST /market/sync?source=arbeitnow`
- Offline fallback only: `POST /market/sync?source=fallback`

The UI supports:
- source selector
- max posts
- sync status + source errors
- trend confidence and source breakdown

## Dataset & Model Notes

- Data is modeled as a graph (Neo4j):
  - `User`, `Skill`, `JobRole`, `Course`, `MarketJobPost`
  - Relationships: `HAS_SKILL`, `REQUIRES`, `PREREQUISITE_OF`, `TEACHES`, `MARKET_REQUIRES`
- Market sync supports free/public feeds with fallback seed mode for offline demos.

## Submission Notes

- This repository is the main submission artifact.
- Report (PDF/Word) is prepared separately by teammate.

## Team

- Member 1 - A Naveen : Backend + Graph + APIs
- Member 2 - Arnav Dharmendra : Frontend + Report
