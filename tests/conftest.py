"""Shared pytest fixtures.

Every test gets its own in-memory SQLite database, so tests are isolated
and leave nothing behind on disk.
"""

import pytest

from aceest import create_app
from aceest.db import Database


@pytest.fixture
def database():
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def app(database):
    application = create_app(database=database)
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def saved_client(client):
    """A client already stored in the database, used by most tests."""
    response = client.post(
        "/clients",
        json={
            "name": "Agam",
            "age": 34,
            "height": 178,
            "weight": 80,
            "program": "MGPPL",
            "target_weight": 76,
            "target_adherence": 85,
        },
    )
    assert response.status_code == 201
    return response.get_json()
