"""Parallel mode: images are divided among worker processes (data parallelism)."""
from multiprocessing import Pool

from src.filters import init_worker, process_image
from src.utils import PARALLEL_DIR, Timer, clear_dir, list_images


def default_chunksize(n_images, workers):
    """Small chunks so a worker that finishes early picks up more work (load balancing)."""
    return max(1, n_images // (workers * 8))


def run_parallel(images, workers, out_dir=PARALLEL_DIR, chunksize=None, progress_callback=None):
    """Filter every image using `workers` processes. Returns elapsed seconds (Tp).

    The timer includes creating and closing the pool, because process
    startup is part of the real cost of going parallel. Clearing the
    output folder is not timed.
    """
    if not images:
        raise ValueError("No images to process. Add images to dataset/input/ first.")

    clear_dir(out_dir)
    total = len(images)
    chunksize = chunksize or default_chunksize(total, workers)
    tasks = [(path, out_dir) for path in images]  # only file paths are sent to workers

    with Timer() as t:
        with Pool(processes=workers, initializer=init_worker) as pool:
            for done, _ in enumerate(pool.imap_unordered(process_image, tasks, chunksize), start=1):
                if progress_callback:
                    progress_callback(done, total)
    return t.elapsed


if __name__ == "__main__":
    # Quick manual test: python -m src.parallel
    # The __main__ guard is required on Windows, where workers re-import this module.
    images = list_images()
    for p in (1, 2, 4, 8):
        elapsed = run_parallel(images, workers=p)
        print(f"Tp({p} workers) = {elapsed:.3f}s  ({len(images) / elapsed:.2f} images/s)")