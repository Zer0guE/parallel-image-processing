"""Filter pipeline: grayscale -> Gaussian blur -> Sobel edge detection.

Every worker (and the sequential loop) runs the same `process_image`
function on a different image. That is the SPMD idea from the proposal.
The worker function lives at module level so Windows can import it
when it starts worker processes.
"""
import cv2

from src.utils import load_image, output_path, save_image

# ---------- Fixed parameters (one place, used by both modes) ----------
GAUSSIAN_KSIZE = (5, 5)
GAUSSIAN_SIGMA = 1.4
SOBEL_KSIZE = 3


def init_worker():
    """Pool initializer: runs once inside each worker process.

    Turns off OpenCV's own multithreading so measured speedup comes only
    from our multiprocessing, not from OpenCV threads.
    """
    cv2.setNumThreads(1)
    cv2.ocl.setUseOpenCL(False)


def apply_pipeline(img):
    """Take a BGR image (NumPy array), return the Sobel edge map as 8-bit grayscale."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, GAUSSIAN_KSIZE, GAUSSIAN_SIGMA)
    gx = cv2.Sobel(blurred, cv2.CV_16S, 1, 0, ksize=SOBEL_KSIZE)
    gy = cv2.Sobel(blurred, cv2.CV_16S, 0, 1, ksize=SOBEL_KSIZE)
    return cv2.addWeighted(cv2.convertScaleAbs(gx), 0.5, cv2.convertScaleAbs(gy), 0.5, 0)


def process_image(task):
    """Load one image, filter it, save the result. Returns the output path as text.

    `task` is a tuple (input_path, output_dir). Only file paths cross the
    process boundary, so workers share no image data (shared-nothing design).
    """
    input_path, out_dir = task
    img = load_image(input_path)
    result = apply_pipeline(img)
    out_file = output_path(input_path, out_dir)
    save_image(out_file, result)
    return str(out_file)


if __name__ == "__main__":
    # Quick manual test: python -m src.filters
    from src.utils import OUTPUT_DIR, Timer, ensure_dir, list_images

    cv2.setNumThreads(1)
    images = list_images(limit=1)
    if not images:
        raise SystemExit("No images found in dataset/input/")
    test_dir = ensure_dir(OUTPUT_DIR / "test")
    with Timer() as t:
        out = process_image((images[0], test_dir))
    print(f"Filtered {images[0].name} in {t.elapsed:.3f}s -> {out}")