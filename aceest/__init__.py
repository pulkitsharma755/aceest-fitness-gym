"""ACEest Fitness & Gym - Flask application package.

This is the web port of the ACEest desktop application supplied with the
assignment. The original Tkinter source is kept in ``legacy/`` for
reference; the programme catalogue, calorie formula, BMI bands and
database schema here are taken from it unchanged.

The application is built with the factory pattern so that tests, the
development server and gunicorn each get an independent instance.
"""

import os

from flask import Flask, jsonify

from aceest.db import Database
from aceest.routes import bp

__version__ = "1.0.0"


def create_app(database=None, db_path=None):
    """Create and configure the Flask application.

    :param database: an existing Database instance (used by the tests)
    :param db_path:  path to the SQLite file; defaults to $ACEEST_DB
    """
    app = Flask(__name__)
    app.json.sort_keys = False

    if database is None:
        path = db_path or os.environ.get("ACEEST_DB", "aceest_fitness.db")
        database = Database(path)
    app.db = database

    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - defensive
        return jsonify({"error": "Internal server error."}), 500

    return app
