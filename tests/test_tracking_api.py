"""Tests for weekly adherence, workouts, exercises and body metrics."""

from datetime import date

import pytest


# -- weekly adherence ----------------------------------------------
def test_progress_is_logged_against_the_client(client, saved_client):
    response = client.post("/clients/Agam/progress", json={"adherence": 75})
    body = response.get_json()

    assert response.status_code == 201
    assert body["client_name"] == "Agam"
    assert body["adherence"] == 75
    assert body["week"].startswith("Week ")


def test_progress_accepts_an_explicit_week(client, saved_client):
    response = client.post(
        "/clients/Agam/progress", json={"adherence": 60, "week": "Week 09 - 2026"}
    )

    assert response.get_json()["week"] == "Week 09 - 2026"


@pytest.mark.parametrize("adherence", [-1, 101, "high", None, True])
def test_invalid_adherence_is_rejected(client, saved_client, adherence):
    response = client.post("/clients/Agam/progress", json={"adherence": adherence})

    assert response.status_code == 400
    assert "adherence" in response.get_json()["error"]


def test_progress_for_a_missing_client_returns_404(client):
    response = client.post("/clients/Nobody/progress", json={"adherence": 50})

    assert response.status_code == 404


def test_progress_history_is_returned_in_order(client, saved_client):
    for week, value in [("Week 09 - 2026", 60), ("Week 10 - 2026", 70)]:
        client.post("/clients/Agam/progress", json={"week": week, "adherence": value})

    body = client.get("/clients/Agam/progress").get_json()

    assert body["count"] == 2
    assert [row["adherence"] for row in body["progress"]] == [60, 70]


# -- workouts ------------------------------------------------------
def test_workout_is_logged_with_todays_date_by_default(client, saved_client):
    response = client.post(
        "/clients/Agam/workouts",
        json={"workout_type": "Cardio", "duration_min": 45, "notes": "Zone 2"},
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body["workout_type"] == "Cardio"
    assert body["duration_min"] == 45
    assert body["notes"] == "Zone 2"
    assert body["date"] == date.today().isoformat()


def test_workout_type_is_normalised(client, saved_client):
    response = client.post(
        "/clients/Agam/workouts", json={"workout_type": "strength", "duration_min": 30}
    )

    assert response.get_json()["workout_type"] == "Strength"


@pytest.mark.parametrize(
    "payload,expected_field",
    [
        ({"duration_min": 60}, "workout_type"),
        ({"workout_type": "Pilates", "duration_min": 60}, "workout_type"),
        ({"workout_type": "Cardio"}, "duration_min"),
        ({"workout_type": "Cardio", "duration_min": 0}, "duration_min"),
        ({"workout_type": "Cardio", "duration_min": 600}, "duration_min"),
        ({"workout_type": "Cardio", "duration_min": "sixty"}, "duration_min"),
    ],
)
def test_invalid_workout_payloads_are_rejected(
    client, saved_client, payload, expected_field
):
    response = client.post("/clients/Agam/workouts", json=payload)

    assert response.status_code == 400
    assert expected_field in response.get_json()["error"]


def test_workout_history_totals_the_minutes(client, saved_client):
    client.post(
        "/clients/Agam/workouts",
        json={"workout_type": "Strength", "duration_min": 60, "date": "2026-03-01"},
    )
    client.post(
        "/clients/Agam/workouts",
        json={"workout_type": "Mobility", "duration_min": 30, "date": "2026-03-02"},
    )

    body = client.get("/clients/Agam/workouts").get_json()

    assert body["count"] == 2
    assert body["total_minutes"] == 90
    # newest session first
    assert body["workouts"][0]["date"] == "2026-03-02"


def test_workout_history_for_a_missing_client_returns_404(client):
    assert client.get("/clients/Nobody/workouts").status_code == 404


# -- exercises -----------------------------------------------------
@pytest.fixture
def workout(client, saved_client):
    response = client.post(
        "/clients/Agam/workouts",
        json={"workout_type": "Hypertrophy", "duration_min": 75},
    )
    return response.get_json()


def test_exercise_is_attached_to_a_workout(client, workout):
    response = client.post(
        f"/workouts/{workout['id']}/exercises",
        json={"name": "Back Squat", "sets": 5, "reps": 5, "weight": 100},
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body["workout_id"] == workout["id"]
    assert body["name"] == "Back Squat"


def test_exercise_volume_is_totalled(client, workout):
    client.post(
        f"/workouts/{workout['id']}/exercises",
        json={"name": "Back Squat", "sets": 5, "reps": 5, "weight": 100},
    )
    client.post(
        f"/workouts/{workout['id']}/exercises",
        json={"name": "Bench Press", "sets": 4, "reps": 8, "weight": 60},
    )

    body = client.get(f"/workouts/{workout['id']}/exercises").get_json()

    # (5 * 5 * 100) + (4 * 8 * 60) = 2500 + 1920
    assert body["count"] == 2
    assert body["total_volume_kg"] == 4420.0


@pytest.mark.parametrize(
    "payload,expected_field",
    [
        ({"sets": 5, "reps": 5}, "name"),
        ({"name": "Deadlift", "reps": 5}, "sets"),
        ({"name": "Deadlift", "sets": 5}, "reps"),
        ({"name": "Deadlift", "sets": 0, "reps": 5}, "sets"),
        ({"name": "Deadlift", "sets": 5, "reps": 5, "weight": -20}, "weight"),
    ],
)
def test_invalid_exercise_payloads_are_rejected(
    client, workout, payload, expected_field
):
    response = client.post(f"/workouts/{workout['id']}/exercises", json=payload)

    assert response.status_code == 400
    assert expected_field in response.get_json()["error"]


def test_exercise_on_a_missing_workout_returns_404(client):
    response = client.post(
        "/workouts/999/exercises", json={"name": "Squat", "sets": 3, "reps": 10}
    )

    assert response.status_code == 404
    assert response.get_json()["error"] == "Workout not found."


# -- body metrics --------------------------------------------------
def test_metrics_are_logged(client, saved_client):
    response = client.post(
        "/clients/Agam/metrics",
        json={"weight": 79.5, "waist": 86, "bodyfat": 19.5, "date": "2026-03-01"},
    )
    body = response.get_json()

    assert response.status_code == 201
    assert body["weight"] == 79.5
    assert body["waist"] == 86
    assert body["bodyfat"] == 19.5


def test_metric_weight_change_is_reported(client, saved_client):
    client.post("/clients/Agam/metrics", json={"weight": 80, "date": "2026-03-01"})
    client.post("/clients/Agam/metrics", json={"weight": 77.5, "date": "2026-03-29"})

    body = client.get("/clients/Agam/metrics").get_json()

    assert body["count"] == 2
    assert body["weight_change"] == -2.5


def test_single_metric_has_no_weight_change(client, saved_client):
    client.post("/clients/Agam/metrics", json={"weight": 80})

    assert client.get("/clients/Agam/metrics").get_json()["weight_change"] is None


@pytest.mark.parametrize(
    "payload,expected_field",
    [
        ({}, "weight"),
        ({"weight": 0}, "weight"),
        ({"weight": 80, "waist": -5}, "waist"),
        ({"weight": 80, "bodyfat": 95}, "bodyfat"),
    ],
)
def test_invalid_metric_payloads_are_rejected(
    client, saved_client, payload, expected_field
):
    response = client.post("/clients/Agam/metrics", json=payload)

    assert response.status_code == 400
    assert expected_field in response.get_json()["error"]


def test_metrics_for_a_missing_client_returns_404(client):
    assert client.get("/clients/Nobody/metrics").status_code == 404
