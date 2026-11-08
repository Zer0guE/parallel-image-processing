"""Command-line entry point.

  python main.py sequential [--limit N]
  python main.py parallel --workers 4 [--limit N]
  python main.py benchmark [--runs 3] [--limit N]
  python main.py verify
  python main.py plots
"""
import argparse

from src.benchmark import DEFAULT_RUNS, run_benchmark
from src.parallel import run_parallel
from src.sequential import run_sequential
from src.utils import list_images
from src.verify import compare_outputs


def print_summary(images, elapsed, label):
    print(f"{label}: {elapsed:.3f}s for {len(images)} images ({len(images) / elapsed:.2f} images/s)")


def cmd_benchmark(args):
    from src.plots import make_plots  # lazy: matplotlib must not load in worker processes

    images = list_images(limit=args.limit)
    print(f"Benchmarking {len(images)} images, {args.runs} run(s) per test")
    result = run_benchmark(
        images, runs=args.runs,
        progress_callback=lambda pct, msg, active: print(f"[{pct:3d}%] {msg}"),
    )
    print(f"\nTs = {result['sequential_time']:.3f}s")
    print(f"{'Workers':>7} {'Time(s)':>9} {'Speedup':>8} {'Effic.':>7} {'Img/s':>7}")
    for r in result["runs"]:
        print(f"{r['workers']:>7} {r['time']:>9.3f} {r['speedup']:>8.2f} {r['efficiency']:>7.2f} {r['throughput']:>7.2f}")
    print("Outputs identical:", result["verified"])
    for path in make_plots():
        print("Saved", path)


def cmd_verify(args):
    r = compare_outputs()
    print(f"Matched {r['matched']} of {r['total']} images")
    for key in ("mismatched", "missing", "extra"):
        if r[key]:
            print(f"{key}: {r[key]}")
    print("RESULT:", "outputs are identical" if r["match"] else "outputs DIFFER")


def main():
    ap = argparse.ArgumentParser(description="Parallel image processing: sequential vs. multiprocessing")
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sequential", help="run the sequential baseline")
    p.add_argument("--limit", type=int, help="only use the first N images")

    p = sub.add_parser("parallel", help="run the parallel version")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--limit", type=int, help="only use the first N images")

    p = sub.add_parser("benchmark", help="run 1, 2, 4, 8 workers, then verify and plot")
    p.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    p.add_argument("--limit", type=int, help="only use the first N images")

    sub.add_parser("verify", help="compare sequential and parallel outputs")
    sub.add_parser("plots", help="redraw charts from the saved CSV")

    args = ap.parse_args()

    if args.command == "sequential":
        images = list_images(limit=args.limit)
        print_summary(images, run_sequential(images), "Sequential")
    elif args.command == "parallel":
        images = list_images(limit=args.limit)
        print_summary(images, run_parallel(images, workers=args.workers), f"Parallel ({args.workers} workers)")
    elif args.command == "benchmark":
        cmd_benchmark(args)
    elif args.command == "verify":
        cmd_verify(args)
    elif args.command == "plots":
        from src.plots import make_plots

        for path in make_plots():
            print("Saved", path)


if __name__ == "__main__":  # required on Windows for multiprocessing
    main()