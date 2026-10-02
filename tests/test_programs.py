"""Unit tests for the fitness calculations.

These test the rules ported from the desktop baseline without touching
Flask or the database, so a failure points at the logic itself.
"""

from datetime import datetime

import pytest

from aceest.programs import (
    PROGRAMS,
    bmi_category,
    calculate_bmi,
    calorie_target,
    current_week,
    get_program,
    list_programs,
)


# -- programme catalogue -------------------------------------------
def test_catalogue_matches_the_baseline_factors():
    """The calorie factors must stay identical to the desktop version."""
    assert PROGRAMS["FL3"]["factor"] == 22
    assert PROGRAMS["FL5"]["factor"] == 24
    assert PROGRAMS["MGPPL"]["factor"] == 35
    assert PROGRAMS["BG"]["factor"] == 26


def test_list_programs_returns_every_programme_sorted():
    codes = [p["code"] for p in list_programs()]

    assert codes == ["BG", "FL3", "FL5", "MGPPL"]


def test_get_program_is_case_insensitive():
    assert get_program("mgppl")["name"] == "Muscle Gain (MG) - PPL"


@pytest.mark.parametrize("code", [None, "", "UNKNOWN", "   "])
def test_get_program_rejects_unknown_codes(code):
    assert get_program(code) is None


# -- calorie target ------------------------------------------------
def test_calorie_target_multiplies_weight_by_the_factor():
    # 80 kg on Muscle Gain (factor 35) = 2800 kcal
    assert calorie_target(80, "MGPPL") == 2800


def test_calorie_target_truncates_to_a_whole_number():
    # 72.5 kg on Fat Loss 3-day (factor 22) = 1595.0
    assert calorie_target(72.5, "FL3") == 1595


@pytest.mark.parametrize(
    "weight,program",
    [(None, "FL3"), (0, "FL3"), (-5, "FL3"), (80, "NOPE"), (80, None)],
)
def test_calorie_target_returns_none_for_invalid_input(weight, program):
    assert calorie_target(weight, program) is None


# -- BMI -----------------------------------------------------------
def test_bmi_is_calculated_from_height_in_centimetres():
    # 80 kg at 178 cm -> 80 / 1.78^2 = 25.2
    assert calculate_bmi(178, 80) == 25.2


def test_bmi_is_rounded_to_one_decimal():
    assert calculate_bmi(170, 65) == 22.5


@pytest.mark.parametrize(
    "height,weight", [(0, 80), (178, 0), (None, 80), (178, None), (-178, 80)]
)
def test_bmi_returns_none_for_invalid_input(height, weight):
    assert calculate_bmi(height, weight) is None


@pytest.mark.parametrize(
    "bmi,expected",
    [
        (17.0, "Underweight"),
        (18.4, "Underweight"),
        (18.5, "Normal"),
        (24.9, "Normal"),
        (25.0, "Overweight"),
        (29.9, "Overweight"),
        (30.0, "Obese"),
        (41.2, "Obese"),
    ],
)
def test_bmi_bands_match_the_baseline_thresholds(bmi, expected):
    category, risk = bmi_category(bmi)

    assert category == expected
    assert risk  # every band carries a risk note


def test_bmi_category_handles_a_missing_value():
    assert bmi_category(None) == (None, None)


# -- week label ----------------------------------------------------
def test_current_week_uses_the_baseline_format():
    label = current_week(datetime(2026, 3, 15))

    assert label.startswith("Week ")
    assert label.endswith(" - 2026")


def test_current_week_defaults_to_now():
    assert current_week().startswith("Week ")
