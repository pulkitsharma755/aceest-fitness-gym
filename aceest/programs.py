"""Training programmes and the fitness calculations.

Every rule in this module is ported directly from the ACEest desktop
baseline supplied with the assignment (``legacy/Aceestver-2_2_4.py`` and
``legacy/Aceestver-3_2_4.py``):

* the programme catalogue and calorie factors come from ``setup_data()``
* the calorie formula comes from ``save_client()``
* the BMI bands and risk notes come from ``show_bmi_info()``
* the week label format comes from ``save_progress()``

The logic is kept free of Flask and of the database so it can be unit
tested on its own, exactly as the assignment asks for tests that
"validate the internal logic".
"""

from datetime import datetime

# Programme catalogue. ``code`` is the URL-safe identifier used by the
# API; ``name`` is the label the desktop application displayed.
PROGRAMS = {
    "FL3": {
        "code": "FL3",
        "name": "Fat Loss (FL) - 3 day",
        "factor": 22,
        "description": "3-day full-body fat loss",
    },
    "FL5": {
        "code": "FL5",
        "name": "Fat Loss (FL) - 5 day",
        "factor": 24,
        "description": "5-day split, higher volume fat loss",
    },
    "MGPPL": {
        "code": "MGPPL",
        "name": "Muscle Gain (MG) - PPL",
        "factor": 35,
        "description": "Push/Pull/Legs hypertrophy",
    },
    "BG": {
        "code": "BG",
        "name": "Beginner (BG)",
        "factor": 26,
        "description": "3-day simple beginner full-body",
    },
}

WORKOUT_TYPES = ("Strength", "Hypertrophy", "Cardio", "Mobility")


def get_program(code):
    """Return the programme for ``code``, or None when it is unknown."""
    if not code:
        return None
    return PROGRAMS.get(str(code).strip().upper())


def list_programs():
    """Return the catalogue as a list, ordered by code."""
    return [PROGRAMS[code] for code in sorted(PROGRAMS)]


def calorie_target(weight_kg, program_code):
    """Daily calorie target: body weight multiplied by the programme factor.

    Mirrors ``calories = int(weight * factor)`` in the baseline. Returns
    None when either input is missing, as the baseline also stored NULL.
    """
    program = get_program(program_code)
    if program is None or not weight_kg or weight_kg <= 0:
        return None
    return int(weight_kg * program["factor"])


def calculate_bmi(height_cm, weight_kg):
    """Return BMI rounded to one decimal, or None when inputs are invalid."""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def bmi_category(bmi):
    """Return the band and risk note for a BMI value.

    The thresholds and wording are taken from the baseline's
    ``show_bmi_info()`` so the web service classifies a client exactly as
    the desktop application did.
    """
    if bmi is None:
        return None, None
    if bmi < 18.5:
        return "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return "Normal", "Low risk if active and strong."
    if bmi < 30:
        return (
            "Overweight",
            "Moderate risk; focus on adherence and progressive activity.",
        )
    return (
        "Obese",
        "Higher risk; prioritize fat loss, consistency, and supervision.",
    )


def current_week(now=None):
    """Return the week label used for weekly adherence, e.g. 'Week 11 - 2026'.

    The baseline used ``datetime.now().strftime("Week %U - %Y")``; the
    optional ``now`` argument makes the function testable.
    """
    moment = now or datetime.now()
    return moment.strftime("Week %U - %Y")
