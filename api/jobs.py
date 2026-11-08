"""Runs benchmarks in a background thread and tracks their progress.

Only one job may run at a time. Two jobs at once would compete for the same
CPU cores and ruin the timings, so a second request is rejected.
"""
import copy
import threading
import uuid
from statistics import mean

from api import config
from src.benchmark import run_benchmark
from src.sequential import run_sequential
from src.utils import list_images


class JobBusy(Exception):
    """Raised when a job is requested while another is still running."""


class JobManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._jobs = {}
        self._active = None

    def is_busy(self):
        with self._lock:
            return self._active is not None

    def start(self, kind, workers, runs):
        """Start a job in a background thread and return its id."""
        with self._lock:
            if self._active is not None:
                raise JobBusy("A job is already running. Wait for it to finish.")
            job_id = uuid.uuid4().hex[:8]
            self._jobs[job_id] = {
                "state": "running",
                "progress": 0,
                "message": "Starting...",
                "active_workers": 0,
                "image_count": None,
                "sequential_time": None,
                "runs": [],
                "verified": None,
                "sample": None,
            }
            self._active = job_id
        threading.Thread(target=self._run, args=(job_id, kind, workers, runs), daemon=True).start()
        return job_id

    def status(self, job_id):
        with self._lock:
            job = self._jobs.get(job_id)
            return copy.deepcopy(job) if job else None

    def _update(self, job_id, **fields):
        with self._lock:
            self._jobs[job_id].update(fields)

    def _run(self, job_id, kind, workers, runs):
        try:
            images = list_images()
            if not images:
                raise ValueError("No images found. Add images to dataset/input/ first.")

            if kind == "sequential":
                result = self._run_sequential(job_id, images, runs)
            else:
                result = self._run_parallel(job_id, images, kind, workers, runs)

            self._update(job_id, state="done", progress=100, message="Finished.", active_workers=0, **result)
        except Exception as exc:  # shown on the page instead of crashing the thread silently
            self._update(job_id, state="error", message=str(exc), active_workers=0)
        finally:
            with self._lock:
                self._active = None

    def _run_sequential(self, job_id, images, runs):
        times = []
        for r in range(1, runs + 1):
            def on_image(done, total, r=r):
                pct = round(100 * ((r - 1) + done / total) / runs)
                self._update(job_id, progress=pct, message=f"Run {r} of {runs}: {done} of {total} images", active_workers=1)

            times.append(run_sequential(images, progress_callback=on_image))
        ts = mean(times)
        return {"image_count": len(images), "sequential_time": ts,
                "runs": [{"workers": 1, "time": ts}], "verified": None, "sample": None}

    def _run_parallel(self, job_id, images, kind, workers, runs):
        counts = config.BENCHMARK_WORKERS if kind == "benchmark" else (workers,)

        def on_progress(pct, message, active):
            self._update(job_id, progress=pct, message=message, active_workers=active)

        # Only the full benchmark overwrites benchmark_results.csv.
        res = run_benchmark(images, worker_counts=counts, runs=runs,
                            progress_callback=on_progress, save=(kind == "benchmark"))

        if kind == "benchmark":
            try:
                from src.plots import make_plots  # lazy: keep matplotlib out of worker start-up
                make_plots()
            except Exception:
                pass  # charts are a bonus; the page draws its own

        return {
            "image_count": res["image_count"],
            "sequential_time": res["sequential_time"],
            "runs": [{"workers": r["workers"], "time": r["time"]} for r in res["runs"]],
            "verified": res["verified"],
            "sample": images[0].name,
        }