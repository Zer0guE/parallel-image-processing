"""Benchmark: sequential baseline plus parallel runs, each repeated and averaged."""
import argparse
import json
import os
import platform
from statistics import mean

import cv2

from src.metrics import summarize
from src.parallel import run_parallel
from src.sequential import run_sequential
from src.utils import RESULTS_DIR, ensure_dir, list_images
from src.verify import compare_outputs

DEFAULT_WORKERS = (1, 2, 4, 8)
DEFAULT_RUNS = 3


def run_benchmark(images, worker_counts=DEFAULT_WORKERS, runs=DEFAULT_RUNS, progress_callback=None, save=True):
    """Time sequential (Ts) and parallel (Tp) runs, then verify outputs.

    progress_callback(percent, message, active_workers) is optional; the
    web app uses it to drive the progress bar and the core squares.

    Returns {"image_count", "sequential_time", "runs": [metrics dicts],
             "verified", "verify_detail"}.
    """
    if not images:
        raise ValueError("No images to process. Add images to dataset/input/ first.")

    n = len(images)
    total_steps = runs * (1 + len(worker_counts))
    step = 0

    def report(message, active):
        if progress_callback:
            progress_callback(round(100 * step / total_steps), message, active)

    # Untimed warm-up. The first pass over the images reads them from disk and
    # the CPU may still be at a low clock speed. One throwaway pass first means
    # every timed run, sequential or parallel, starts from the same warm state.
    report("Warm-up pass (not timed)", 1)
    run_sequential(images)

    # Sequential baseline: plain loop, no Pool.
    seq_times = []
    for r in range(1, runs + 1):
        report(f"Sequential, run {r} of {runs}", 1)
        seq_times.append(run_sequential(images))
        step += 1
    ts = mean(seq_times)

    # Parallel runs for each worker count.
    results = []
    for p in worker_counts:
        par_times = []
        for r in range(1, runs + 1):
            report(f"{p} workers, run {r} of {runs}", p)
            par_times.append(run_parallel(images, workers=p))
            step += 1
        row = summarize(ts, mean(par_times), p, n)
        row["run_times"] = par_times
        results.append(row)

    # The output folders hold the last sequential and last parallel run.
    verify = compare_outputs()
    report("Finished.", 0)

    out = {
        "image_count": n,
        "sequential_time": ts,
        "sequential_run_times": seq_times,
        "runs": results,
        "verified": verify["match"],
        "verify_detail": verify,
    }
    if save:
        save_results(out)
    return out


def save_results(result):
    """Write benchmark_results.csv and system_info.json to output/results/."""
    import pandas as pd  # imported here, not at the top, so worker processes don't load it

    ensure_dir(RESULTS_DIR)
    n, ts = result["image_count"], result["sequential_time"]

    rows = [{
        "mode": "sequential", "workers": 1, "avg_time_s": ts, "speedup": 1.0,
        "efficiency": 1.0, "images_per_s": n / ts,
        "run_times_s": ";".join(f"{t:.3f}" for t in result["sequential_run_times"]),
    }]
    for r in result["runs"]:
        rows.append({
            "mode": "parallel", "workers": r["workers"], "avg_time_s": r["time"],
            "speedup": r["speedup"], "efficiency": r["efficiency"],
            "images_per_s": r["throughput"],
            "run_times_s": ";".join(f"{t:.3f}" for t in r["run_times"]),
        })
    pd.DataFrame(rows).to_csv(RESULTS_DIR / "benchmark_results.csv", index=False, float_format="%.4f")

    info = {
        "logical_cores": os.cpu_count(),
        "processor": platform.processor(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "image_count": n,
        "outputs_identical": result["verified"],
    }
    (RESULTS_DIR / "system_info.json").write_text(json.dumps(info, indent=2))


if __name__ == "__main__":
    # python -m src.benchmark            (3 runs each)
    # python -m src.benchmark --runs 1   (quick check)
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    args = ap.parse_args()

    imgs = list_images()
    result = run_benchmark(
        imgs, runs=args.runs,
        progress_callback=lambda pct, msg, active: print(f"[{pct:3d}%] {msg}"),
    )

    print(f"\nImages: {result['image_count']}   Ts = {result['sequential_time']:.3f}s")
    print(f"{'Workers':>7} {'Time(s)':>9} {'Speedup':>8} {'Effic.':>7} {'Img/s':>7}")
    for r in result["runs"]:
        print(f"{r['workers']:>7} {r['time']:>9.3f} {r['speedup']:>8.2f} {r['efficiency']:>7.2f} {r['throughput']:>7.2f}")
    print("Outputs identical:", result["verified"])
    print("Saved to output/results/")