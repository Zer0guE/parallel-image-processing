"""Sequential mode: one loop, one process, one core. This is the baseline (Ts)."""
import cv2

from src.filters import process_image
from src.utils import SEQUENTIAL_DIR, Timer, clear_dir, list_images


def run_sequential(images, out_dir=SEQUENTIAL_DIR, progress_callback=None):
    """Filter every image in order. Returns elapsed seconds (Ts).

    The timer covers load + filter + save for all images, the same work
    the parallel version does. Clearing the output folder is not timed.
    """
    if not images:
        raise ValueError("No images to process. Add images to dataset/input/ first.")

    cv2.setNumThreads(1)  # same OpenCV setting the workers use
    clear_dir(out_dir)
    total = len(images)

    with Timer() as t:
        for i, path in enumerate(images, start=1):
            process_image((path, out_dir))
            if progress_callback:
                progress_callback(i, total)
    return t.elapsed


if __name__ == "__main__":
    # Quick manual test: python -m src.sequential
    images = list_images()
    print(f"Running sequential on {len(images)} images...")
    elapsed = run_sequential(images)
    print(f"Ts = {elapsed:.3f}s  ({len(images) / elapsed:.2f} images/s)")