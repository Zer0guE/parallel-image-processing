"""Verify that the parallel output is identical to the sequential output."""
import cv2
import numpy as np

from src.utils import PARALLEL_DIR, SEQUENTIAL_DIR


def _load_unchanged(path):
    """Read a PNG exactly as saved (no colour conversion)."""
    img = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Could not read image: {path}")
    return img


def compare_outputs(seq_dir=SEQUENTIAL_DIR, par_dir=PARALLEL_DIR):
    """Compare every PNG in both folders pixel by pixel.

    Returns a dict:
      match      True only if both folders hold the same files and every pixel is equal
      total      number of images in the sequential folder
      matched    images that are pixel-identical
      mismatched file names whose pixels differ
      missing    in sequential but not in parallel
      extra      in parallel but not in sequential
    """
    seq_files = {p.name: p for p in seq_dir.glob("*.png")}
    par_files = {p.name: p for p in par_dir.glob("*.png")}

    missing = sorted(set(seq_files) - set(par_files))
    extra = sorted(set(par_files) - set(seq_files))

    matched, mismatched = 0, []
    for name in sorted(set(seq_files) & set(par_files)):
        a, b = _load_unchanged(seq_files[name]), _load_unchanged(par_files[name])
        if a.shape == b.shape and np.array_equal(a, b):
            matched += 1
        else:
            mismatched.append(name)

    return {
        "match": bool(seq_files) and not missing and not extra and not mismatched,
        "total": len(seq_files),
        "matched": matched,
        "mismatched": mismatched,
        "missing": missing,
        "extra": extra,
    }


if __name__ == "__main__":
    # Run sequential and parallel first, then: python -m src.verify
    r = compare_outputs()
    if r["total"] == 0:
        raise SystemExit("No sequential output found. Run src.sequential first.")
    print(f"Matched {r['matched']} of {r['total']} images")
    for key in ("mismatched", "missing", "extra"):
        if r[key]:
            print(f"{key}: {r[key]}")
    print("RESULT:", "outputs are identical" if r["match"] else "outputs DIFFER")