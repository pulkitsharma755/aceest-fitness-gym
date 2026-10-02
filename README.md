# ACEest Fitness \& Gym — Flask service with an automated CI/CD pipeline

A Flask web service for gym client, training and progress management, delivered
through an automated pipeline: Git for version control, Pytest for validation,
Docker for environment consistency, Jenkins for the controlled BUILD, and GitHub
Actions for continuous integration on every push and pull request.

!\[CI/CD Pipeline](https://github.com/pulkitsharma755/aceest-fitness-gym/actions/workflows/main.yml/badge.svg)

\---

## 1\. Relationship to the supplied baseline

The course supplied a baseline **Tkinter desktop application** (`ACEestApp`,
versions 1.0 through 3.2.4). Two of those files are kept unchanged in `legacy/`
for reference:

|File|What it contributed|
|-|-|
|`legacy/Aceestver-2\_2\_4.py`|The SQLite schema, the programme catalogue and calorie factors, the BMI bands and risk notes, the weekly-adherence week label|
|`legacy/Aceestver-3\_2\_4.py`|The membership fields and the workout / exercise / metrics tables|

**Why the application was re-platformed rather than containerised as it stands.**
Tkinter is a desktop GUI toolkit: it requires a display server. A Docker container
and a GitHub Actions runner are both headless, so `tkinter.Tk()` raises
`TclError: no display name and no $DISPLAY environment variable` and the process
exits before any test can run. The same applies to `matplotlib.pyplot.show()` and
the modal `messagebox` dialogs — all three block waiting for a human, which is the
opposite of what an automated pipeline needs. Assignment phase 1 therefore calls
for a **Flask** application, and this repository is the faithful port of the
baseline's business logic onto an HTTP interface that *can* be built, tested and
deployed with nobody at a screen.

**Carried across unchanged**

* The programme catalogue and its calorie factors — Fat Loss 3-day (22),
Fat Loss 5-day (24), Muscle Gain PPL (35), Beginner (26)
* The calorie formula `calories = int(weight × factor)`
* The BMI calculation and its four bands, with the original risk wording
* The week label `Week %U - %Y` used for weekly adherence
* The database schema: `clients`, `progress`, `workouts`, `exercises`, `metrics`

**Left out of the port, and why**

|Baseline feature|Decision|
|-|-|
|`users` table and login window|Out of scope here, and a plaintext-password table should not be carried into a web service; authentication belongs behind a proper mechanism|
|PDF report (`fpdf`)|Adds a dependency producing a binary artefact that no test can meaningfully assert on|
|"Generate AI Program" (`random.choice`)|Non-deterministic by construction, so it cannot be unit tested; a real recommendation rule would replace it|
|Matplotlib charts|The service returns the **data** behind each chart as JSON (`/progress`, `/metrics`); rendering is a client concern|

Every button in the baseline has a corresponding endpoint — the mapping is in the
docstring of `aceest/routes.py` and in the table below.

\---

## 2\. API reference

|Method|Endpoint|Baseline equivalent|
|-|-|-|
|`GET`|`/`|— service banner and endpoint list|
|`GET`|`/health`|— liveness probe for Docker, CI and load balancers|
|`GET`|`/programs`|`setup\_data()` — the programme catalogue|
|`POST`|`/clients`|**Save Client**|
|`GET`|`/clients`|the client dropdown (`refresh\_client\_list`)|
|`GET`|`/clients/<name>`|**Load Client**|
|`DELETE`|`/clients/<name>`|—|
|`GET`|`/clients/<name>/summary`|the summary panel (`refresh\_summary`)|
|`GET`|`/clients/<name>/bmi`|**BMI Info**|
|`GET`|`/clients/<name>/membership`|**Check Membership**|
|`POST`|`/clients/<name>/progress`|**Save Progress**|
|`GET`|`/clients/<name>/progress`|data behind the adherence chart|
|`POST`|`/clients/<name>/workouts`|**Log Workout**|
|`GET`|`/clients/<name>/workouts`|**Workout History**|
|`POST`|`/workouts/<id>/exercises`|the exercise rows of a session|
|`GET`|`/workouts/<id>/exercises`|— with total training volume|
|`POST`|`/clients/<name>/metrics`|**Log Metrics**|
|`GET`|`/clients/<name>/metrics`|data behind the weight chart|

### Example

```bash
# Register a client on the Muscle Gain programme
curl -X POST http://localhost:5000/clients \\
  -H "Content-Type: application/json" \\
  -d '{"name":"Agam","age":34,"height":178,"weight":80,"program":"MGPPL"}'
```

```json
{
  "id": 1,
  "name": "Agam",
  "age": 34,
  "height": 178.0,
  "weight": 80.0,
  "program": "MGPPL",
  "calories": 2800,
  "membership\_status": "Active"
}
```

`calories` is `80 × 35`, exactly as the desktop application calculated it.

```bash
curl http://localhost:5000/clients/Agam/bmi
# {"client":"Agam","bmi":25.2,"category":"Overweight","risk\_note":"Moderate risk; ..."}
```

\---

## 3\. Project structure

```
aceest-fitness-gym/
├── app.py                      # Entry point for the dev server and gunicorn
├── aceest/                     # Application package
│   ├── \_\_init\_\_.py             #   create\_app() factory and error handlers
│   ├── programs.py             #   Programmes, calories, BMI  (no Flask, no SQL)
│   ├── db.py                   #   SQLite schema and all data access
│   └── routes.py               #   HTTP routes — one per baseline button
├── tests/
│   ├── conftest.py             #   Fixtures: an in-memory database per test
│   ├── test\_programs.py        #   Domain logic, tested without Flask
│   ├── test\_clients\_api.py     #   Service endpoints and client management
│   └── test\_tracking\_api.py    #   Progress, workouts, exercises, metrics
├── legacy/                     # The supplied Tkinter baseline, unchanged
├── Dockerfile                  # Multi-stage: base → test → runtime
├── Jenkinsfile                 # Jenkins BUILD pipeline
├── .github/workflows/main.yml  # GitHub Actions CI/CD pipeline
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Test and lint dependencies
└── setup.cfg                   # flake8 and pytest configuration
```

The split is deliberate: `programs.py` holds the fitness rules with no Flask and no
SQL in sight, which is why those rules can be unit tested directly, and `db.py`
keeps every SQL statement out of the route handlers.

\---

## 4\. Local setup and execution

**Prerequisites:** Python 3.12+, Git, and Docker Desktop for the container steps.

```bash
git clone https://github.com/pulkitsharma755/aceest-fitness-gym.git
cd aceest-fitness-gym

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate

pip install -r requirements-dev.txt
python app.py
```

The service starts on [http://localhost:5000](http://localhost:5000) and creates `aceest\_fitness.db` in
the working directory. Override the location with the `ACEEST\_DB` environment
variable.

```bash
curl http://localhost:5000/health
# {"status":"healthy"}
```

\---

## 5\. Running the tests manually

```bash
pytest -v                                      # the full suite — 97 tests
pytest --cov=aceest --cov-report=term-missing  # with coverage
pytest tests/test\_programs.py -v               # domain logic only
pytest -k bmi -v                               # everything about BMI
flake8 .                                       # lint
```

Each test runs against its own `:memory:` SQLite database created by the
`database` fixture in `conftest.py`, so tests are isolated, leave no files behind,
and can run in any order.

Coverage spans the programme rules (catalogue, calorie formula, BMI bands and
thresholds, week label), client create/update/read/delete with validation, the
summary and membership views, weekly adherence, workout logging and history,
exercises with training-volume totals, body metrics with weight change, and the
JSON error handling for 400, 404 and 405.

\---

## 6\. Docker

The Dockerfile is **multi-stage**, so the shipped image contains no test tooling:

|Stage|Contents|Purpose|
|-|-|-|
|`base`|Python 3.12 slim + runtime dependencies|Shared cached layer|
|`test`|`base` + dev dependencies + the test suite|Running Pytest in a container|
|`runtime`|`base` + the application only, non-root, gunicorn|The production image|

```bash
# Production image
docker build -t aceest-fitness:latest .
docker run -d -p 5000:5000 -v aceest\_data:/data --name aceest aceest-fitness:latest
curl http://localhost:5000/health

# Tests inside the container
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test

docker rm -f aceest
```

**Efficiency and security choices:** `python:3.12-slim` rather than the full image;
`requirements.txt` copied before the source so the dependency layer stays cached;
`--no-cache-dir` on pip; a `.dockerignore` that keeps Git history, the virtual
environment and the `legacy/` desktop sources out of the build context; the
container runs as the unprivileged `appuser`; the SQLite file lives in `/data`,
declared as a volume so data survives a container replacement; `HEALTHCHECK` lets
Docker report container health; and gunicorn serves the application rather than
the Flask development server. Gunicorn runs **one worker with four threads** —
several processes writing a single SQLite file would contend for the write lock.

\---

## 7\. CI/CD integration logic

### 7.1 GitHub Actions — continuous integration on every change

`.github/workflows/main.yml` runs on **every push and every pull request**, as two
jobs, the second gated on the first.

**Job 1 — Build \& Lint** (fast feedback, under a minute)

1. Check out the code; set up Python 3.12 with a pip cache.
2. Install from `requirements-dev.txt`.
3. `flake8` for syntax errors and undefined names — a hard failure.
4. `flake8` full style check.
5. Build check: import the package and construct the app through the factory.
6. Run the Pytest suite with coverage.

**Job 2 — Docker Build \& Containerised Tests** (only if Job 1 passed)

1. Build the `test` image stage with Buildx layer caching.
2. **Run the Pytest suite inside the container.**
3. Build the slim `runtime` image.
4. Smoke test: start the container, poll `/health`, register a client through the
live API and assert the calorie target is 2800, then confirm the BMI endpoint
returns the expected band.
5. Report the image size and remove the container.

Splitting the jobs means a syntax error costs seconds instead of a full Docker
build, and nothing reaches the image stage without passing tests first.

### 7.2 Jenkins — the controlled BUILD phase

`Jenkinsfile` is a declarative pipeline that Jenkins runs after pulling the latest
code from GitHub (SCM polling every five minutes; a webhook replaces this wherever
Jenkins is reachable from the internet).

|Stage|What it proves|
|-|-|
|Checkout|The exact commit under test is recorded in the build log|
|Clean Build Environment|A fresh virtual environment — nothing survives from the last build|
|Lint|The source is syntactically valid and consistently styled|
|Build Check|The application imports and constructs in a clean environment|
|Unit Tests|Pytest passes; results published to Jenkins as a JUnit report|
|Docker Image|The image builds and is tagged with the Jenkins build number|

**Why both Jenkins and GitHub Actions?** They answer different questions. GitHub
Actions is the hosted gate attached to the repository: it blocks a bad pull request
before it can be merged. Jenkins is the self-managed build server inside the
organisation's own environment, with its own agents, credentials and retention
policy — the arrangement most enterprises use when hosted runners cannot reach
internal systems. Jenkins is the **secondary validation layer** the assignment
describes.

#### Setting up the Jenkins job

1. Install Jenkins LTS with the **Pipeline**, **Git** and **JUnit** plugins.
2. **New Item → Pipeline**, named `aceest-fitness-build`.
3. **Pipeline → Pipeline script from SCM → Git**.
4. Repository URL: this repository. Branch: `\*/main`. Script path: `Jenkinsfile`.
5. **Build Triggers → Poll SCM**, schedule `H/5 \* \* \* \*`.
6. **Save → Build Now**.

Python 3 must be present on the Jenkins agent for the virtual-environment stage.

\---

## 8\. Branching and commit strategy

`main` holds releasable code. Work happens on short-lived branches and reaches
`main` through a pull request, so GitHub Actions validates it before the merge.

|Branch|Purpose|
|-|-|
|`chore/baseline`|The supplied desktop baseline, recorded before any change|
|`feature/flask-app`|The Flask port of the baseline logic|
|`feature/unit-tests`|The Pytest suite|
|`feature/docker`|Containerisation|
|`ci/github-actions`|The GitHub Actions workflow|
|`ci/jenkins`|The Jenkins pipeline|
|`docs/readme`|Documentation|

Commit messages use conventional prefixes — `feat:`, `test:`, `ci:`, `docs:`,
`fix:`, `chore:` — so the history reads as a record of intent.

\---

## 9\. Troubleshooting

|Symptom|Fix|
|-|-|
|`ModuleNotFoundError: No module named 'aceest'`|Run `pytest` from the repository root, not from inside `tests/`|
|`TclError: no display name`|You are running a file from `legacy/` — those are the desktop baseline and need a GUI; run `python app.py` instead|
|Port 5000 already in use|`docker run -p 5001:5000 ...`, or stop the other process|
|`docker: permission denied`|Start Docker Desktop; on Linux add your user to the `docker` group|
|`database is locked`|Another process holds the SQLite file; stop it, or point `ACEEST\_DB` elsewhere|
|GitHub Actions badge shows "no status"|Replace `pulkitsharma755` in the badge URL|

\---

## 10\. Author

Prepared for **Introduction to DevOps (CSI ZG514 / SE ZG514)**, Assignment 1 —
BITS Pilani Work Integrated Learning Programmes.

