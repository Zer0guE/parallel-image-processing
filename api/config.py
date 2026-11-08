"""Settings for the web API. Paths come from src.utils so the CLI and web app agree."""
from src.utils import (  # noqa: F401  (re-exported for the rest of the api package)
    IMAGE_EXTENSIONS,
    INPUT_DIR,
    OUTPUT_DIR,
    PARALLEL_DIR,
    PROJECT_ROOT,
    RESULTS_DIR,
    SEQUENTIAL_DIR,
)

WEBAPP_DIR = PROJECT_ROOT / "webapp"

ALLOWED_WORKERS = (1, 2, 4, 8)   # worker counts the page may request
BENCHMARK_WORKERS = (1, 2, 4, 8)
MAX_RUNS = 5
DEFAULT_RUNS = 3
MAX_UPLOAD_MB = 200

HOST = "127.0.0.1"
PORT = 5000