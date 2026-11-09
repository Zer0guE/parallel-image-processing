"""Endpoint definitions. create_app() builds the Flask app."""
import csv
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from api import config
from api.jobs import JobBusy, JobManager
from src.utils import list_images
from src.verify import compare_outputs


def create_app():
    app = Flask(__name__, static_folder=str(config.WEBAPP_DIR / "static"), static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
    manager = JobManager()

    def error(message, code=400):
        return jsonify({"error": message}), code

    def parse_runs(data):
        try:
            runs = int(data.get("runs", config.DEFAULT_RUNS))
        except (TypeError, ValueError):
            return None
        return runs if 1 <= runs <= config.MAX_RUNS else None

    def start_job(kind, workers, runs):
        try:
            return jsonify({"job_id": manager.start(kind, workers, runs)})
        except JobBusy as exc:
            return error(str(exc), 409)

    # ----- Front end -----
    @app.get("/")
    def index():
        return send_from_directory(config.WEBAPP_DIR, "index.html")

    # ----- Images -----
    @app.get("/api/images")
    def images():
        try:
            names = [p.name for p in list_images()]
        except ValueError as exc:
            return error(str(exc))
        return jsonify({"images": names, "count": len(names)})

    @app.post("/api/upload")
    def upload():
        if manager.is_busy():
            return error("A job is running. Upload after it finishes.", 409)
        saved, skipped = [], []
        for f in request.files.getlist("files"):
            name = secure_filename(f.filename or "")
            if Path(name).suffix.lower() not in config.IMAGE_EXTENSIONS:
                skipped.append(f.filename)
                continue
            f.save(config.INPUT_DIR / name)
            saved.append(name)
        return jsonify({"saved": saved, "skipped": skipped})

    # ----- Jobs -----
    @app.post("/api/run")
    def run():
        data = request.get_json(silent=True) or {}
        mode = data.get("mode")
        if mode not in ("sequential", "parallel", "compare"):
            return error("mode must be 'sequential', 'parallel' or 'compare'.")
        runs = parse_runs(data)
        if runs is None:
            return error(f"runs must be a whole number from 1 to {config.MAX_RUNS}.")
        try:
            workers = int(data.get("workers", 4))
        except (TypeError, ValueError):
            workers = None
        if mode in ("parallel", "compare") and workers not in config.ALLOWED_WORKERS:
            return error(f"workers must be one of {list(config.ALLOWED_WORKERS)}.")
        return start_job(mode, workers, runs)

    @app.post("/api/benchmark")
    def benchmark():
        data = request.get_json(silent=True) or {}
        runs = parse_runs(data)
        if runs is None:
            return error(f"runs must be a whole number from 1 to {config.MAX_RUNS}.")
        return start_job("benchmark", None, runs)

    @app.get("/api/status/<job_id>")
    def status(job_id):
        job = manager.status(job_id)
        return jsonify(job) if job else error("Unknown job id.", 404)

    # ----- Verification and results -----
    @app.post("/api/verify")
    def verify():
        if manager.is_busy():
            return error("A job is running. Verify after it finishes.", 409)
        return jsonify(compare_outputs())

    @app.get("/api/results")
    def results():
        path = config.RESULTS_DIR / "benchmark_results.csv"
        if not path.exists():
            return jsonify({"rows": []})
        with open(path, newline="") as f:
            return jsonify({"rows": list(csv.DictReader(f))})

    @app.get("/api/preview/<stage>/<path:name>")
    def preview(stage, name):
        if stage == "original":
            folder, filename = config.INPUT_DIR, name
        elif stage in ("sequential", "parallel"):
            folder = config.SEQUENTIAL_DIR if stage == "sequential" else config.PARALLEL_DIR
            filename = Path(name).stem + ".png"
        else:
            return error("stage must be original, sequential or parallel.", 404)
        response = send_from_directory(folder, filename)
        response.headers["Cache-Control"] = "no-store"
        return response

    return app