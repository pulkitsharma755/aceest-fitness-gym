"""SQLite data access for the ACEest service.

The schema is the one created by the desktop baseline
(``legacy/Aceestver-3_2_4.py``): clients, progress, workouts, exercises
and metrics. The ``users`` table is deliberately not carried over - see
the README section "What was left out of the port and why".

Wrapping the connection in a class keeps the route handlers free of SQL
and lets each test run against its own private ``:memory:`` database.
"""

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    age INTEGER,
    height REAL,
    weight REAL,
    program TEXT,
    calories INTEGER,
    target_weight REAL,
    target_adherence INTEGER,
    membership_status TEXT DEFAULT 'Active',
    membership_end TEXT
);

CREATE TABLE IF NOT EXISTS progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    week TEXT NOT NULL,
    adherence INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS workouts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    workout_type TEXT,
    duration_min INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS exercises (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workout_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    sets INTEGER,
    reps INTEGER,
    weight REAL
);

CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    date TEXT NOT NULL,
    weight REAL,
    waist REAL,
    bodyfat REAL
);
"""


class Database:
    """A thin wrapper around one SQLite connection."""

    def __init__(self, path=":memory:"):
        self.path = path
        # check_same_thread=False because gunicorn serves requests from
        # worker threads; the connection is used behind Flask's request
        # handling, one statement at a time.
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_schema()

    def create_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- generic helpers -------------------------------------------
    def query(self, sql, params=()):
        """Return all matching rows as a list of dictionaries."""
        cur = self.conn.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]

    def query_one(self, sql, params=()):
        """Return the first matching row as a dictionary, or None."""
        cur = self.conn.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def execute(self, sql, params=()):
        """Run a write statement and return the new row id."""
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.lastrowid

    def close(self):
        self.conn.close()

    # -- clients ---------------------------------------------------
    def upsert_client(self, client):
        """Insert or replace a client, mirroring the baseline's
        ``INSERT OR REPLACE INTO clients``."""
        self.execute(
            """
            INSERT INTO clients
                (name, age, height, weight, program, calories,
                 target_weight, target_adherence, membership_status,
                 membership_end)
            VALUES (:name, :age, :height, :weight, :program, :calories,
                    :target_weight, :target_adherence, :membership_status,
                    :membership_end)
            ON CONFLICT(name) DO UPDATE SET
                age = excluded.age,
                height = excluded.height,
                weight = excluded.weight,
                program = excluded.program,
                calories = excluded.calories,
                target_weight = excluded.target_weight,
                target_adherence = excluded.target_adherence,
                membership_status = excluded.membership_status,
                membership_end = excluded.membership_end
            """,
            client,
        )
        return self.get_client(client["name"])

    def get_client(self, name):
        return self.query_one(
            "SELECT * FROM clients WHERE name = ? COLLATE NOCASE", (name,)
        )

    def list_clients(self):
        return self.query("SELECT * FROM clients ORDER BY name")

    def delete_client(self, name):
        client = self.get_client(name)
        if client is None:
            return None
        self.execute("DELETE FROM clients WHERE name = ? COLLATE NOCASE", (name,))
        return client

    # -- progress --------------------------------------------------
    def add_progress(self, client_name, week, adherence):
        row_id = self.execute(
            """
            INSERT INTO progress (client_name, week, adherence)
            VALUES (?, ?, ?)
            """,
            (client_name, week, adherence),
        )
        return self.query_one("SELECT * FROM progress WHERE id = ?", (row_id,))

    def list_progress(self, client_name):
        return self.query(
            "SELECT * FROM progress WHERE client_name = ? COLLATE NOCASE ORDER BY id",
            (client_name,),
        )

    # -- workouts and exercises ------------------------------------
    def add_workout(self, client_name, workout_date, workout_type, duration, notes):
        row_id = self.execute(
            """
            INSERT INTO workouts (client_name, date, workout_type, duration_min, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (client_name, workout_date, workout_type, duration, notes),
        )
        return self.get_workout(row_id)

    def get_workout(self, workout_id):
        return self.query_one("SELECT * FROM workouts WHERE id = ?", (workout_id,))

    def list_workouts(self, client_name):
        return self.query(
            """
            SELECT * FROM workouts
            WHERE client_name = ? COLLATE NOCASE
            ORDER BY date DESC, id DESC
            """,
            (client_name,),
        )

    def add_exercise(self, workout_id, name, sets, reps, weight):
        row_id = self.execute(
            """
            INSERT INTO exercises (workout_id, name, sets, reps, weight)
            VALUES (?, ?, ?, ?, ?)
            """,
            (workout_id, name, sets, reps, weight),
        )
        return self.query_one("SELECT * FROM exercises WHERE id = ?", (row_id,))

    def list_exercises(self, workout_id):
        return self.query(
            "SELECT * FROM exercises WHERE workout_id = ? ORDER BY id", (workout_id,)
        )

    # -- body metrics ----------------------------------------------
    def add_metric(self, client_name, metric_date, weight, waist, bodyfat):
        row_id = self.execute(
            """
            INSERT INTO metrics (client_name, date, weight, waist, bodyfat)
            VALUES (?, ?, ?, ?, ?)
            """,
            (client_name, metric_date, weight, waist, bodyfat),
        )
        return self.query_one("SELECT * FROM metrics WHERE id = ?", (row_id,))

    def list_metrics(self, client_name):
        return self.query(
            """
            SELECT * FROM metrics
            WHERE client_name = ? COLLATE NOCASE
            ORDER BY date, id
            """,
            (client_name,),
        )
