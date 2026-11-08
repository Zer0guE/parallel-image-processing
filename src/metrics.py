"""Performance metrics from the proposal: speedup, efficiency, throughput."""


def speedup(ts, tp):
    """S = Ts / Tp"""
    return ts / tp


def efficiency(s, p):
    """E = S / p"""
    return s / p


def throughput(n_images, seconds):
    """Images processed per second."""
    return n_images / seconds


def summarize(ts, tp, p, n_images):
    """All metrics for one parallel configuration, as a dict."""
    s = speedup(ts, tp)
    return {
        "workers": p,
        "time": tp,
        "speedup": s,
        "efficiency": efficiency(s, p),
        "throughput": throughput(n_images, tp),
    }