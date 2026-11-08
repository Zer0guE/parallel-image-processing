"""Charts for the report, drawn from output/results/benchmark_results.csv."""
import matplotlib

matplotlib.use("Agg")  # draw to files only; safe to call from a web server thread
import matplotlib.pyplot as plt
import pandas as pd

from src.utils import RESULTS_DIR

BLUE = "#2f5bea"
GREY = "#9aa7c7"


def make_plots(csv_path=None, out_dir=RESULTS_DIR):
    """Create execution_time.png, speedup.png and efficiency.png. Returns their paths."""
    csv_path = csv_path or (RESULTS_DIR / "benchmark_results.csv")
    df = pd.read_csv(csv_path)
    ts = float(df.loc[df["mode"] == "sequential", "avg_time_s"].iloc[0])
    par = df[df["mode"] == "parallel"].sort_values("workers")
    workers = par["workers"].astype(int).tolist()
    labels = [str(w) for w in workers]

    # Execution time
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(labels, par["avg_time_s"], color=BLUE, label="Parallel (Tp)")
    ax.axhline(ts, color=GREY, linestyle="--", label=f"Sequential (Ts = {ts:.1f}s)")
    ax.set_xlabel("Worker processes")
    ax.set_ylabel("Execution time (s)")
    ax.set_title("Execution time vs. workers")
    ax.legend()
    time_png = _save(fig, out_dir, "execution_time.png")

    # Speedup, measured vs. ideal
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(workers, par["speedup"], marker="o", color=BLUE, label="Measured")
    ax.plot(workers, workers, linestyle="--", color=GREY, label="Ideal (S = p)")
    ax.set_xticks(workers)
    ax.set_xlabel("Worker processes")
    ax.set_ylabel("Speedup (Ts / Tp)")
    ax.set_title("Speedup vs. workers")
    ax.legend()
    speed_png = _save(fig, out_dir, "speedup.png")

    # Efficiency
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(workers, par["efficiency"], marker="o", color=BLUE)
    ax.axhline(1.0, linestyle="--", color=GREY)
    ax.set_xticks(workers)
    ax.set_ylim(0, 1.1)
    ax.set_xlabel("Worker processes")
    ax.set_ylabel("Efficiency (S / p)")
    ax.set_title("Efficiency vs. workers")
    eff_png = _save(fig, out_dir, "efficiency.png")

    return [time_png, speed_png, eff_png]


def _save(fig, out_dir, name):
    path = out_dir / name
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


if __name__ == "__main__":
    # Run a benchmark first, then: python -m src.plots
    for p in make_plots():
        print("Saved", p)