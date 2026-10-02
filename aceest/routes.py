"""HTTP routes for the ACEest Fitness & Gym service.

Each route is the web equivalent of a button in the desktop baseline:

    Save Client          -> POST   /clients
    Load Client          -> GET    /clients/<name>
    Client list          -> GET    /clients
    Client summary       -> GET    /clients/<name>/summary
    BMI info             -> GET    /clients/<name>/bmi
    Save Progress        -> POST   /clients/<name>/progress
    Progress chart data  -> GET    /clients/<name>/progress
    Log Workout          -> POST   /clients/<name>/workouts
    Workout history      -> GET    /clients/<name>/workouts
    Exercises per workout-> POST/GET /workouts/<id>/exercises
    Log Metrics          -> POST   /clients/<name>/metrics
    Weight chart data    -> GET    /clients/<name>/metrics
    Check Membership     -> GET    /clients/<name>/membership
"""

from datetime import date

from flask import Blueprint, current_app, jsonify, request

from aceest.programs import (
    WORKOUT_TYPES,
    bmi_category,
    calculate_bmi,
    calorie_target,
    current_week,
    get_program,
    list_programs,
)

bp = Blueprint("api", __name__)


def db():
    """Return the database attached to the running application."""
    return current_app.db


def error(message, status=400):
    return jsonify({"error": message}), status


def positive_number(value, field, errors, required=False):
    """Validate an optional positive number, collecting any error."""
    if value is None or value == "":
        if required:
            errors.append(f"Field '{field}' is required.")
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        errors.append(f"Field '{field}' must be a number.")
        return None
    if value <= 0:
        errors.append(f"Field '{field}' must be greater than zero.")
        return None
    return value


# ------------------------------------------------------------------
# Service endpoints
# ------------------------------------------------------------------
@bp.get("/")
def index():
    return jsonify(
        {
            "service": "ACEest Fitness & Gym",
            "version": "1.0.0",
            "description": (
                "Flask port of the ACEest desktop application; see "
                "legacy/ for the original Tkinter baseline."
            ),
            "endpoints": [
                "GET /health",
                "GET /programs",
                "POST /clients",
                "GET /clients",
                "GET /clients/<name>",
                "DELETE /clients/<name>",
                "GET /clients/<name>/summary",
                "GET /clients/<name>/bmi",
                "POST /clients/<name>/progress",
                "GET /clients/<name>/progress",
                "POST /clients/<name>/workouts",
                "GET /clients/<name>/workouts",
                "POST /workouts/<id>/exercises",
                "GET /workouts/<id>/exercises",
                "POST /clients/<name>/metrics",
                "GET /clients/<name>/metrics",
                "GET /clients/<name>/membership",
            ],
        }
    )


@bp.get("/health")
def health():
    """Liveness probe used by Docker, CI and the load balancer."""
    return jsonify({"status": "healthy"}), 200


@bp.get("/programs")
def programs():
    """The programme catalogue from the baseline's setup_data()."""
    return jsonify({"programs": list_programs()}), 200


# ------------------------------------------------------------------
# Clients
# ------------------------------------------------------------------
@bp.post("/clients")
def save_client():
    """Create or update a client - the 'Save Client' button."""
    payload = request.get_json(silent=True) or {}
    errors = []

    name = str(payload.get("name") or "").strip()
    if not name:
        errors.append("Field 'name' is required.")

    program_code = payload.get("program")
    program = get_program(program_code)
    if program is None:
        errors.append(
            "Field 'program' is required and must be one of: "
            + ", ".join(sorted(p["code"] for p in list_programs()))
            + "."
        )

    age = positive_number(payload.get("age"), "age", errors)
    height = positive_number(payload.get("height"), "height", errors)
    weight = positive_number(payload.get("weight"), "weight", errors)
    target_weight = positive_number(
        payload.get("target_weight"), "target_weight", errors
    )
    target_adherence = positive_number(
        payload.get("target_adherence"), "target_adherence", errors
    )

    if target_adherence is not None and target_adherence > 100:
        errors.append("Field 'target_adherence' must be between 1 and 100.")

    if errors:
        return error(" ".join(errors))

    record = {
        "name": name,
        "age": int(age) if age else None,
        "height": height,
        "weight": weight,
        "program": program["code"],
        "calories": calorie_target(weight, program["code"]),
        "target_weight": target_weight,
        "target_adherence": int(target_adherence) if target_adherence else None,
        "membership_status": str(
            payload.get("membership_status") or "Active"
        ).strip(),
        "membership_end": payload.get("membership_end"),
    }

    existed = db().get_client(name) is not None
    client = db().upsert_client(record)
    return jsonify(client), 200 if existed else 201


@bp.get("/clients")
def list_clients():
    clients = db().list_clients()
    return jsonify({"count": len(clients), "clients": clients}), 200


@bp.get("/clients/<name>")
def get_client(name):
    """Load one client - the 'Load Client' button."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)
    return jsonify(client), 200


@bp.delete("/clients/<name>")
def delete_client(name):
    client = db().delete_client(name)
    if client is None:
        return error("Client not found.", 404)
    return jsonify({"deleted": client["name"]}), 200


@bp.get("/clients/<name>/summary")
def client_summary(name):
    """The summary panel: profile, programme, BMI and adherence to date."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    program = get_program(client["program"])
    progress = db().list_progress(client["name"])
    adherence_values = [row["adherence"] for row in progress]
    bmi = calculate_bmi(client["height"], client["weight"])
    category, _risk = bmi_category(bmi)

    return (
        jsonify(
            {
                "name": client["name"],
                "age": client["age"],
                "height": client["height"],
                "weight": client["weight"],
                "program": program["name"] if program else client["program"],
                "calories": client["calories"],
                "target_weight": client["target_weight"],
                "target_adherence": client["target_adherence"],
                "bmi": bmi,
                "bmi_category": category,
                "weeks_logged": len(adherence_values),
                "average_adherence": (
                    round(sum(adherence_values) / len(adherence_values), 1)
                    if adherence_values
                    else None
                ),
                "total_workouts": len(db().list_workouts(client["name"])),
            }
        ),
        200,
    )


@bp.get("/clients/<name>/bmi")
def client_bmi(name):
    """BMI with the band and risk note - the 'BMI Info' button."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    bmi = calculate_bmi(client["height"], client["weight"])
    if bmi is None:
        return error("Client has no valid height and weight recorded.", 400)

    category, risk = bmi_category(bmi)
    return (
        jsonify(
            {
                "client": client["name"],
                "bmi": bmi,
                "category": category,
                "risk_note": risk,
            }
        ),
        200,
    )


@bp.get("/clients/<name>/membership")
def client_membership(name):
    """The 'Check Membership' button."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)
    return (
        jsonify(
            {
                "client": client["name"],
                "membership_status": client["membership_status"],
                "renewal_date": client["membership_end"],
            }
        ),
        200,
    )


# ------------------------------------------------------------------
# Weekly adherence
# ------------------------------------------------------------------
@bp.post("/clients/<name>/progress")
def save_progress(name):
    """Log weekly adherence - the 'Save Progress' button."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    payload = request.get_json(silent=True) or {}
    adherence = payload.get("adherence")
    if isinstance(adherence, bool) or not isinstance(adherence, int):
        return error("Field 'adherence' must be an integer.")
    if adherence < 0 or adherence > 100:
        return error("Field 'adherence' must be between 0 and 100.")

    week = str(payload.get("week") or current_week()).strip()
    row = db().add_progress(client["name"], week, adherence)
    return jsonify(row), 201


@bp.get("/clients/<name>/progress")
def get_progress(name):
    """The data behind the weekly adherence chart."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    rows = db().list_progress(client["name"])
    return (
        jsonify(
            {
                "client": client["name"],
                "count": len(rows),
                "progress": rows,
            }
        ),
        200,
    )


# ------------------------------------------------------------------
# Workouts and exercises
# ------------------------------------------------------------------
@bp.post("/clients/<name>/workouts")
def log_workout(name):
    """Log a training session - the 'Log Workout' window."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    payload = request.get_json(silent=True) or {}
    errors = []

    workout_type = str(payload.get("workout_type") or "").strip().title()
    if workout_type not in WORKOUT_TYPES:
        errors.append(
            "Field 'workout_type' must be one of: " + ", ".join(WORKOUT_TYPES) + "."
        )

    duration = payload.get("duration_min")
    if isinstance(duration, bool) or not isinstance(duration, int):
        errors.append("Field 'duration_min' must be an integer.")
    elif duration <= 0 or duration > 480:
        errors.append("Field 'duration_min' must be between 1 and 480.")

    if errors:
        return error(" ".join(errors))

    workout_date = str(payload.get("date") or date.today().isoformat()).strip()
    notes = str(payload.get("notes") or "").strip()

    workout = db().add_workout(
        client["name"], workout_date, workout_type, duration, notes
    )
    return jsonify(workout), 201


@bp.get("/clients/<name>/workouts")
def workout_history(name):
    """The 'Workout History' window."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    workouts = db().list_workouts(client["name"])
    total_minutes = sum(w["duration_min"] or 0 for w in workouts)
    return (
        jsonify(
            {
                "client": client["name"],
                "count": len(workouts),
                "total_minutes": total_minutes,
                "workouts": workouts,
            }
        ),
        200,
    )


@bp.post("/workouts/<int:workout_id>/exercises")
def add_exercise(workout_id):
    """Add one exercise to a logged workout."""
    if db().get_workout(workout_id) is None:
        return error("Workout not found.", 404)

    payload = request.get_json(silent=True) or {}
    errors = []

    exercise_name = str(payload.get("name") or "").strip()
    if not exercise_name:
        errors.append("Field 'name' is required.")

    sets = positive_number(payload.get("sets"), "sets", errors, required=True)
    reps = positive_number(payload.get("reps"), "reps", errors, required=True)
    weight = positive_number(payload.get("weight"), "weight", errors)

    if errors:
        return error(" ".join(errors))

    exercise = db().add_exercise(
        workout_id, exercise_name, int(sets), int(reps), weight
    )
    return jsonify(exercise), 201


@bp.get("/workouts/<int:workout_id>/exercises")
def list_exercises(workout_id):
    if db().get_workout(workout_id) is None:
        return error("Workout not found.", 404)

    exercises = db().list_exercises(workout_id)
    volume = sum(
        (e["sets"] or 0) * (e["reps"] or 0) * (e["weight"] or 0) for e in exercises
    )
    return (
        jsonify(
            {
                "workout_id": workout_id,
                "count": len(exercises),
                "total_volume_kg": round(volume, 1),
                "exercises": exercises,
            }
        ),
        200,
    )


# ------------------------------------------------------------------
# Body metrics
# ------------------------------------------------------------------
@bp.post("/clients/<name>/metrics")
def log_metrics(name):
    """Log body metrics - the 'Log Metrics' window."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    payload = request.get_json(silent=True) or {}
    errors = []

    weight = positive_number(payload.get("weight"), "weight", errors, required=True)
    waist = positive_number(payload.get("waist"), "waist", errors)
    bodyfat = positive_number(payload.get("bodyfat"), "bodyfat", errors)

    if bodyfat is not None and bodyfat > 70:
        errors.append("Field 'bodyfat' must be a percentage below 70.")

    if errors:
        return error(" ".join(errors))

    metric_date = str(payload.get("date") or date.today().isoformat()).strip()
    row = db().add_metric(client["name"], metric_date, weight, waist, bodyfat)
    return jsonify(row), 201


@bp.get("/clients/<name>/metrics")
def metric_history(name):
    """The data behind the weight-trend chart."""
    client = db().get_client(name)
    if client is None:
        return error("Client not found.", 404)

    rows = db().list_metrics(client["name"])
    weights = [r["weight"] for r in rows if r["weight"]]
    return (
        jsonify(
            {
                "client": client["name"],
                "count": len(rows),
                "weight_change": (
                    round(weights[-1] - weights[0], 1) if len(weights) > 1 else None
                ),
                "metrics": rows,
            }
        ),
        200,
    )
