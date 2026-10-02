# syntax=docker/dockerfile:1
# ---------------------------------------------------------------------
# ACEest Fitness & Gym - multi-stage build
#
#   base    shared Python layer with the runtime dependencies
#   test    adds dev dependencies and the test suite (CI target)
#   runtime final image: application only, no test tooling, non-root
#
# Build the production image : docker build -t aceest-fitness:latest .
# Build and run the tests    : docker build --target test -t aceest-fitness:test .
#                              docker run --rm aceest-fitness:test
# ---------------------------------------------------------------------

# ---------- base ----------
FROM python:3.12-slim AS base

# Keeps the image small and the logs unbuffered so `docker logs` is live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Requirements are copied first so this layer is cached and pip only
# re-runs when the dependency list itself changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------- test ----------
FROM base AS test

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY setup.cfg app.py ./
COPY aceest/ ./aceest/
COPY tests/ ./tests/

# Default command runs the full suite; CI overrides it when needed.
CMD ["python", "-m", "pytest", "-v"]

# ---------- runtime ----------
FROM base AS runtime

# Run as an unprivileged user: a container process should never be root.
RUN useradd --create-home --shell /usr/sbin/nologin appuser

COPY app.py .
COPY aceest/ ./aceest/

# SQLite file lives in a dedicated directory owned by the app user, so it
# can be mounted as a volume for persistence.
ENV ACEEST_DB=/data/aceest_fitness.db
RUN mkdir -p /data && chown appuser:appuser /data
VOLUME ["/data"]

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0) if urllib.request.urlopen('http://localhost:5000/health').status==200 else sys.exit(1)"

# gunicorn rather than the Flask development server: the dev server is
# single-threaded and explicitly not for production use.
# One worker with threads rather than multiple processes: the store is
# SQLite, and several processes writing one file invites lock contention.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", \
     "--timeout", "60", "app:app"]
