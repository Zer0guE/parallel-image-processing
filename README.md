# Parallel Image Processing

Batch image filtering in Python, compared in two modes: **sequential** (one CPU core) and **parallel** (a pool of worker processes using `multiprocessing`). The project measures how much faster the parallel version is and checks that both produce identical output images.

Course project for S-CSPE003LA, Parallel and Distributed Computing.

## What it does

Each image goes through the same pipeline: grayscale conversion, Gaussian blur (5x5, sigma 1.4), and Sobel edge detection (3x3). The result is saved as PNG.

- **Sequential mode:** one loop loads, filters, and saves each image on a single core.
- **Parallel mode:** the image list is divided among worker processes. Only file paths are sent to workers, so no image data is shared between processes. Small chunks give simple load balancing.
- **Verification:** every output image from the parallel run is compared pixel by pixel with the sequential output.
- **Metrics:** execution time, speedup (Ts / Tp), efficiency (S / p), and throughput (images per second) for 1, 2, 4, and 8 workers, each averaged over several runs.

PDC concepts used: data parallelism, SPMD, shared-nothing processes, and load balancing.

## Project structure

```
├── app.py              Flask server (web interface)
├── main.py             Command-line interface
├── requirements.txt
├── src/                Core processing code
│   ├── filters.py      Filter pipeline and worker function
│   ├── sequential.py   Sequential mode
│   ├── parallel.py     Parallel mode (multiprocessing.Pool)
│   ├── benchmark.py    Timed runs for 1, 2, 4, 8 workers
│   ├── metrics.py      Speedup, efficiency, throughput
│   ├── verify.py       Sequential vs. parallel output check
│   ├── plots.py        Charts from the benchmark CSV
│   └── utils.py        Paths, image I/O, timer
├── api/                Back-end for the web interface
├── webapp/             Front end (HTML, CSS, JavaScript)
├── dataset/input/      Input images (128 included)
├── output/             Generated results (not included)
└── docs/               Project proposal and saved results
```

## Setup

Requires Python 3.13 (the version used for development). Download it from python.org and tick "Add python.exe to PATH" during installation.

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate`.

## Dataset

The 128 test images are included in `dataset/input/`: 118 images (`0001.png` to `0118.png`) from the [Widescreen images 1920x1080 dataset on Kaggle](https://www.kaggle.com/datasets/trinquenta/imagens-widescreen-1920x1080), and 10 additional images (`img 1.jpg` to `img 10.jpg`). See the Kaggle page for that dataset's license terms.

To use your own images, replace the contents of that folder. Supported formats are JPG, PNG, BMP, and TIFF. Two images must not share the same file name, even with different extensions, because outputs are saved as `<name>.png`.

## Usage

Command line (run from the project root):

```
python main.py sequential
python main.py parallel --workers 4
python main.py benchmark            # 1, 2, 4, 8 workers, 3 runs each, then verify and plot
python main.py verify
python main.py plots
```

Add `--limit N` to `sequential`, `parallel`, or `benchmark` to use only the first N images, and `--runs N` to `benchmark` to change the number of runs.

Web interface:

```
python app.py
```

Then open http://127.0.0.1:5000. The page can run sequential, parallel, or the full benchmark, and shows progress, results, charts, and image previews.

## Results

The benchmark writes `output/results/benchmark_results.csv`, `system_info.json`, and three charts (`execution_time.png`, `speedup.png`, `efficiency.png`). Saved copies of the official run are in `docs/results/`.

## Benchmarking notes

- Official timings come from the command-line benchmark. Timings from the web page are for demonstration only.
- OpenCV's internal threading is disabled (`cv2.setNumThreads(1)`) in both modes, so measured differences come only from the program's own parallelism.
- An untimed warm-up pass runs before measuring, so every test starts with the images already in the operating system's file cache.
- Timings include loading, filtering, and saving each image. The parallel timings also include creating and closing the process pool.
- For stable results, close other programs, keep a laptop plugged in, and leave the machine alone while the benchmark runs.

## Authors

Demonteverde, Edwin Carl Jr · Delos Reyes, Dwyn Anthony V. · Perdito, Ma. Criselda S. · Rosales, John Leo M.
