"""Shared helpers: project paths, image listing, image I/O and timing."""
import shutil
import time
from pathlib import Path

import cv2
import numpy as np

# ---------- Paths ----------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "dataset" / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
SEQUENTIAL_DIR = OUTPUT_DIR / "sequential"
PARALLEL_DIR = OUTPUT_DIR / "parallel"
RESULTS_DIR = OUTPUT_DIR / "results"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

# Output is always PNG (lossless), with one fixed compression level in
# every mode so sequential and parallel outputs can be compared exactly.
PNG_COMPRESSION = 3


# ---------- Files and folders ----------
def list_images(folder=INPUT_DIR, limit=None):
    """Return a sorted list of image paths in `folder` (optionally only the first `limit`)."""
    folder = Path(folder)
    paths = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS)

    # Outputs are saved as <name>.png, so two inputs with the same name but
    # different extensions would overwrite each other.
    seen = {}
    for p in paths:
        if p.stem in seen:
            raise ValueError(f"Duplicate image name '{p.stem}': {seen[p.stem].name} and {p.name}. Rename one.")
        seen[p.stem] = p

    return paths[:limit] if limit else paths


def ensure_dir(folder):
    Path(folder).mkdir(parents=True, exist_ok=True)
    return Path(folder)


def clear_dir(folder):
    """Delete and recreate a folder so every run starts from empty output."""
    folder = Path(folder)
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def output_path(input_path, out_dir):
    """Where the filtered version of `input_path` is saved: <out_dir>/<name>.png"""
    return Path(out_dir) / (Path(input_path).stem + ".png")


# ---------- Image I/O ----------
# np.fromfile / tofile are used instead of cv2.imread / cv2.imwrite because
# the OpenCV versions fail on Windows paths with non-ASCII characters.
def load_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


def save_image(path, img):
    ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, PNG_COMPRESSION])
    if not ok:
        raise ValueError(f"Could not encode image: {path}")
    buf.tofile(str(path))


# ---------- Timing ----------
class Timer:
    """Usage:  with Timer() as t: ...work...   then read t.elapsed (seconds)."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed = time.perf_counter() - self.start
        return False