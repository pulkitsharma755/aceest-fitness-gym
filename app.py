"""Entry point for the ACEest Fitness & Gym service.

Development:  python app.py
Production:   gunicorn --bind 0.0.0.0:5000 app:app
"""

from aceest import create_app

app = create_app()


if __name__ == "__main__":  # pragma: no cover
    app.run(host="0.0.0.0", port=5000, debug=False)
