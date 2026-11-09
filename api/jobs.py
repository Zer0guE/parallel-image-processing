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
from src.parallel import run_parallel
from src.sequential import run_sequential
from src.utils import list_images
from src.verify import compare_outputs


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
                "phase": None,            # compare only: warmup, sequential, parallel, verify, done
                "progress": 0,
                "seq_progress": 0,        # compare only: left column bar, 0-100
                "par_progress": 0,        # compare only: right column bar, 0-100
                "message": "Starting...",
                "active_workers": 0,
                "image_count": None,
                "sequential_time": None,
                "sequential_run_times": None,
                "parallel_workers": None,
                "parallel_time": None,
                "parallel_run_times": None,
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
            elif kind == "compare":
                result = self._run_compare(job_id, images, workers, runs)
            else:
                result = self._run_parallel(job_id, images, kind, workers, runs)

            self._update(job_id, state="done", phase="done", progress=100, message="Finished.",
                         active_workers=0, **result)
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

    def _run_compare(self, job_id, images, workers, runs):
        """One click: sequential first, then parallel, then verify.

        The two never overlap, so they do not compete for the CPU. The left
        column fills during the first half of the job, the right column during
        the second half.
        """
        n = len(images)
        self._update(job_id, image_count=n, phase="warmup", message="Warm-up pass (not timed)", active_workers=1)
        run_sequential(images)  # untimed: files get cached and the CPU wakes up, like in the benchmark

        # ----- Left column: sequential -----
        self._update(job_id, phase="sequential")
        seq_times = []
        for r in range(1, runs + 1):
            def on_seq(done, total, r=r):
                frac = ((r - 1) + done / total) / runs
                self._update(job_id, seq_progress=round(100 * frac), progress=round(50 * frac),
                             message=f"Sequential, run {r} of {runs}: {done} of {total} images",
                             active_workers=1)

            seq_times.append(run_sequential(images, progress_callback=on_seq))
        ts = mean(seq_times)
        self._update(job_id, sequential_time=ts, sequential_run_times=seq_times, seq_progress=100, progress=50)

        # ----- Right column: parallel -----
        self._update(job_id, phase="parallel", parallel_workers=workers)
        par_times = []
        for r in range(1, runs + 1):
            def on_par(done, total, r=r):
                frac = ((r - 1) + done / total) / runs
                self._update(job_id, par_progress=round(100 * frac), progress=50 + round(50 * frac),
                             message=f"Parallel ({workers} workers), run {r} of {runs}: {done} of {total} images",
                             active_workers=workers)

            par_times.append(run_parallel(images, workers=workers, progress_callback=on_par))
        tp = mean(par_times)
        self._update(job_id, parallel_time=tp, parallel_run_times=par_times, par_progress=100)

        # ----- Check that both outputs are identical -----
        self._update(job_id, phase="verify", message="Checking that both outputs are identical", active_workers=0)
        verify = compare_outputs()

        return {
            "image_count": n,
            "sequential_time": ts,
            "parallel_time": tp,
            "runs": [{"workers": workers, "time": tp}],
            "verified": verify["match"],
            "sample": images[0].name,
        }

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