"""Tests for the service endpoints and client management."""

import pytest


# -- service endpoints ---------------------------------------------
def test_index_describes_the_service(client):
    body = client.get("/").get_json()

    assert body["service"] == "ACEest Fitness & Gym"
    assert "GET /health" in body["endpoints"]


def test_health_reports_healthy(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_programs_endpoint_returns_the_catalogue(client):
    body = client.get("/programs").get_json()

    assert len(body["programs"]) == 4
    assert {p["code"] for p in body["programs"]} == {"BG", "FL3", "FL5", "MGPPL"}


def test_unknown_route_returns_json_404(client):
    response = client.get("/not-a-route")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Resource not found."


def test_wrong_method_returns_json_405(client):
    response = client.delete("/health")

    assert response.status_code == 405
    assert response.get_json()["error"] == "Method not allowed."


# -- saving clients ------------------------------------------------
def test_client_is_saved_with_a_calculated_calorie_target(saved_client):
    # 80 kg on Muscle Gain (factor 35)
    assert saved_client["name"] == "Agam"
    assert saved_client["program"] == "MGPPL"
    assert saved_client["calories"] == 2800
    assert saved_client["membership_status"] == "Active"


def test_saving_the_same_name_again_updates_the_record(client, saved_client):
    response = client.post(
        "/clients",
        json={"name": "Agam", "weight": 76, "program": "FL5", "height": 178},
    )
    body = response.get_json()

    assert response.status_code == 200  # updated, not created
    assert body["weight"] == 76
    assert body["calories"] == 76 * 24
    assert client.get("/clients").get_json()["count"] == 1


def test_client_without_weight_has_no_calorie_target(client):
    response = client.post("/clients", json={"name": "Nisha", "program": "BG"})

    assert response.status_code == 201
    assert response.get_json()["calories"] is None


def test_client_name_is_trimmed(client):
    response = client.post("/clients", json={"name": "  Rahul  ", "program": "BG"})

    assert response.get_json()["name"] == "Rahul"


@pytest.mark.parametrize(
    "payload,expected_field",
    [
        ({"program": "BG"}, "name"),
        ({"name": "   ", "program": "BG"}, "name"),
        ({"name": "Rahul"}, "program"),
        ({"name": "Rahul", "program": "CROSSFIT"}, "program"),
        ({"name": "Rahul", "program": "BG", "weight": -10}, "weight"),
        ({"name": "Rahul", "program": "BG", "weight": "eighty"}, "weight"),
        ({"name": "Rahul", "program": "BG", "age": 0}, "age"),
        ({"name": "Rahul", "program": "BG", "height": -170}, "height"),
        ({"name": "Rahul", "program": "BG", "target_adherence": 150}, "target_adherence"),
    ],
)
def test_invalid_client_payloads_are_rejected(client, payload, expected_field):
    response = client.post("/clients", json=payload)

    assert response.status_code == 400
    assert expected_field in response.get_json()["error"]


# -- reading and deleting clients ----------------------------------
def test_client_can_be_loaded_by_name(client, saved_client):
    response = client.get("/clients/Agam")

    assert response.status_code == 200
    assert response.get_json()["name"] == "Agam"


def test_client_lookup_is_case_insensitive(client, saved_client):
    assert client.get("/clients/agam").status_code == 200


def test_missing_client_returns_404(client):
    response = client.get("/clients/Nobody")

    assert response.status_code == 404
    assert response.get_json()["error"] == "Client not found."


def test_clients_can_be_listed(client, saved_client):
    client.post("/clients", json={"name": "Priya", "program": "FL3"})

    body = client.get("/clients").get_json()

    assert body["count"] == 2
    assert [c["name"] for c in body["clients"]] == ["Agam", "Priya"]


def test_client_can_be_deleted(client, saved_client):
    deleted = client.delete("/clients/Agam")

    assert deleted.status_code == 200
    assert deleted.get_json() == {"deleted": "Agam"}
    assert client.get("/clients/Agam").status_code == 404


def test_deleting_a_missing_client_returns_404(client):
    assert client.delete("/clients/Nobody").status_code == 404


# -- BMI, membership and summary -----------------------------------
def test_bmi_endpoint_returns_the_band_and_risk_note(client, saved_client):
    body = client.get("/clients/Agam/bmi").get_json()

    assert body["bmi"] == 25.2
    assert body["category"] == "Overweight"
    assert "Moderate risk" in body["risk_note"]


def test_bmi_requires_height_and_weight(client):
    client.post("/clients", json={"name": "Nisha", "program": "BG"})

    response = client.get("/clients/Nisha/bmi")

    assert response.status_code == 400
    assert "height and weight" in response.get_json()["error"]


def test_membership_defaults_to_active(client, saved_client):
    body = client.get("/clients/Agam/membership").get_json()

    assert body["membership_status"] == "Active"
    assert body["renewal_date"] is None


def test_membership_can_be_set_explicitly(client):
    client.post(
        "/clients",
        json={
            "name": "Priya",
            "program": "FL3",
            "membership_status": "Expired",
            "membership_end": "2026-01-31",
        },
    )

    body = client.get("/clients/Priya/membership").get_json()

    assert body["membership_status"] == "Expired"
    assert body["renewal_date"] == "2026-01-31"


def test_summary_combines_profile_bmi_and_activity(client, saved_client):
    client.post("/clients/Agam/progress", json={"adherence": 80, "week": "Week 10 - 2026"})
    client.post("/clients/Agam/progress", json={"adherence": 90, "week": "Week 11 - 2026"})
    client.post(
        "/clients/Agam/workouts",
        json={"workout_type": "Strength", "duration_min": 60},
    )

    body = client.get("/clients/Agam/summary").get_json()

    assert body["program"] == "Muscle Gain (MG) - PPL"
    assert body["calories"] == 2800
    assert body["bmi"] == 25.2
    assert body["bmi_category"] == "Overweight"
    assert body["weeks_logged"] == 2
    assert body["average_adherence"] == 85.0
    assert body["total_workouts"] == 1


def test_summary_for_a_missing_client_returns_404(client):
    assert client.get("/clients/Nobody/summary").status_code == 404
