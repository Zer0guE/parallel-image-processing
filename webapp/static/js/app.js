const $ = id => document.getElementById(id);
const kindNow = () => document.querySelector("input[name=kind]:checked").value;
const fmt = (v, d) => (v == null || Number.isNaN(v) ? "–" : v.toFixed(d));
const runList = list => (list || []).map(t => t.toFixed(1)).join(", ") + " s";

/* ---------- API layer ----------
   POST /api/run        {mode: "compare", workers, runs} -> {job_id}
   POST /api/benchmark  {runs}                            -> {job_id}
   GET  /api/status/<id> -> state, phase, progress, seq_progress, par_progress, message,
        active_workers, image_count, sequential_time, parallel_time, parallel_workers,
        sequential_run_times, parallel_run_times, runs, verified
   GET  /api/images     -> {images: [names]}
*/
const api = {
  async start(kind, body) {
    const res = await fetch(kind === "benchmark" ? "/api/benchmark" : "/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "The server rejected the request.");
    return data;
  },
  async status(id) {
    const res = await fetch("/api/status/" + id);
    if (!res.ok) throw new Error("Could not read job status.");
    return res.json();
  },
  async images() {
    const res = await fetch("/api/images");
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Could not list the images.");
    return data.images;
  }
};

/* ---------- Small UI helpers ---------- */
["seq-cores", "par-cores", "bench-cores"].forEach(id => {
  for (let i = 1; i <= 8; i++) {
    const c = document.createElement("div");
    c.className = "core"; c.textContent = i;
    $(id).appendChild(c);
  }
});

function lit(id, n) {
  [...$(id).children].forEach((c, i) => c.classList.toggle("on", i < (n || 0)));
}

function setPill(id, text, cls = "") {
  const el = $(id);
  el.className = "pill " + cls;
  el.textContent = text;
}

function setVerified(v) {
  const [text, cls] = v === true ? ["Outputs match", "ok"] : v === false ? ["Outputs differ", "bad"] : ["Not verified yet", ""];
  setPill("verify", text, cls);
  setPill("bench-verify", text, cls);
}

function lock(on) {
  $("run").disabled = on;
  $("modes").disabled = on;
  $("runs").disabled = on;
  $("workers").disabled = on || kindNow() !== "compare";
}

function syncMode() {
  const kind = kindNow();
  $("view-compare").hidden = kind !== "compare";
  $("view-bench").hidden = kind !== "benchmark";
  $("run").textContent = kind === "compare" ? "Run comparison" : "Run full benchmark";
  lock(false);
}
document.querySelectorAll("input[name=kind]").forEach(r => r.addEventListener("change", syncMode));

/* ---------- Compare view (two columns + combined metrics) ---------- */
function renderCompare(s) {
  const phase = s.phase, n = s.image_count, p = s.parallel_workers;
  const ts = s.sequential_time, tp = s.parallel_time;
  const seqRunning = phase === "warmup" || phase === "sequential";

  $("seq-bar").style.width = (s.seq_progress || 0) + "%";
  $("par-bar").style.width = (s.par_progress || 0) + "%";
  lit("seq-cores", seqRunning ? 1 : 0);
  lit("par-cores", phase === "parallel" ? s.active_workers : 0);

  setPill("seq-state", ts != null ? "Done" : phase === "warmup" ? "Warming up" : seqRunning ? "Running" : "Waiting", ts != null ? "ok" : "");
  setPill("par-state", tp != null ? "Done" : phase === "parallel" ? "Running" : "Waiting", tp != null ? "ok" : "");

  $("seq-time").textContent = ts != null ? ts.toFixed(2) + " s" : "–";
  $("par-time").textContent = tp != null ? tp.toFixed(2) + " s" : "–";
  $("seq-detail").textContent = ts != null ? `${fmt(n / ts, 2)} images per second. Runs: ${runList(s.sequential_run_times)}` : "";
  $("par-detail").textContent = tp != null ? `${p} workers, ${fmt(n / tp, 2)} images per second. Runs: ${runList(s.parallel_run_times)}` : "";

  const speed = ts != null && tp != null ? ts / tp : null;
  const eff = speed != null && p ? speed / p : null;
  const rows = [
    ["Workers", "1", p != null ? p : "–"],
    ["Time (s)", fmt(ts, 2), fmt(tp, 2)],
    ["Images per second", ts != null ? fmt(n / ts, 2) : "–", tp != null ? fmt(n / tp, 2) : "–"],
    ["Speedup (Ts / Tp)", ts != null ? "1.00x" : "–", speed != null ? fmt(speed, 2) + "x" : "–"],
    ["Efficiency (speedup / workers)", ts != null ? "1.00" : "–", eff != null ? fmt(eff, 2) : "–"]
  ];
  $("metrics").innerHTML = rows.map(r => `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join("");

  $("summary").textContent = speed == null ? "" : speed >= 1
    ? `Parallel finished ${speed.toFixed(2)}x faster than sequential. With ${p} workers the ideal is ${p}x, so efficiency is ${eff.toFixed(2)} (1.00 would be perfect).`
    : `Parallel was slower this time. With few workers, the cost of starting the processes can outweigh the gain.`;
}

/* ---------- Full benchmark view ---------- */
function renderBench(s) {
  $("bench-bar").style.width = (s.progress || 0) + "%";
  lit("bench-cores", s.active_workers);
  const ts = s.sequential_time, n = s.image_count;
  if (ts == null || !s.runs.length) return;

  const rows = s.runs.map(r => {
    const speedup = ts / r.time;
    return { workers: r.workers, time: r.time, speedup, efficiency: speedup / r.workers, throughput: n / r.time };
  });
  $("rows").innerHTML =
    `<tr><td>Sequential</td><td>${ts.toFixed(1)}</td><td>1.00x</td><td>1.00</td><td>${(n / ts).toFixed(2)}</td></tr>` +
    rows.map(r => `<tr><td>${r.workers} workers</td><td>${r.time.toFixed(1)}</td><td>${r.speedup.toFixed(2)}x</td>` +
      `<td>${r.efficiency.toFixed(2)}</td><td>${r.throughput.toFixed(2)}</td></tr>`).join("");
  $("count").textContent = `Processed ${n} images per test.`;
  renderCharts(rows);
}

/* ---------- Image browser ---------- */
let names = [], idx = 0;

async function loadBrowser() {
  try {
    names = await api.images();
  } catch (err) {
    $("message").textContent = err.message;
    return;
  }
  if (!names.length) return;
  const pick = $("pick");
  pick.replaceChildren();
  names.forEach((name, i) => pick.add(new Option(name, i)));
  $("browser").hidden = false;
  show(0);
}

function show(i) {
  if (!names.length) return;
  idx = (i + names.length) % names.length;
  $("pick").value = idx;
  const name = names[idx];
  ["original", "sequential", "parallel"].forEach(stage => {
    const img = new Image();
    img.alt = `${stage} version of ${name}`;
    img.src = `/api/preview/${stage}/${encodeURIComponent(name)}`;
    $("img-" + stage).replaceChildren(img);
  });
  $("pos").textContent = `Image ${idx + 1} of ${names.length}: ${name}`;
}

$("prev").addEventListener("click", () => show(idx - 1));
$("next").addEventListener("click", () => show(idx + 1));
$("pick").addEventListener("change", e => show(Number(e.target.value)));
document.addEventListener("keydown", e => {
  if (!names.length || /SELECT|INPUT/.test(document.activeElement.tagName)) return;
  if (e.key === "ArrowRight") show(idx + 1);
  if (e.key === "ArrowLeft") show(idx - 1);
});

/* ---------- Running a job ---------- */
let timer = null;

async function poll(id, kind) {
  try {
    const s = await api.status(id);
    $("message").textContent = s.message;
    (kind === "compare" ? renderCompare : renderBench)(s);
    if (s.state === "running") { timer = setTimeout(() => poll(id, kind), 700); return; }
    setVerified(s.verified);
    lock(false);
    if (s.state === "done") await loadBrowser();
  } catch (err) {
    $("message").textContent = err.message;
    lock(false);
  }
}

$("run").addEventListener("click", async () => {
  const kind = kindNow();
  const body = { mode: kind, workers: Number($("workers").value), runs: Number($("runs").value) };
  clearTimeout(timer);
  lock(true);
  renderCompare({});
  $("bench-bar").style.width = "0";
  lit("bench-cores", 0);
  $("rows").innerHTML = '<tr><td colspan="5" class="empty">Running. Results appear when the benchmark finishes.</td></tr>';
  $("count").textContent = "";
  setVerified(null);
  $("browser").hidden = true;
  names = [];
  $("message").textContent = "Starting...";
  try {
    const { job_id } = await api.start(kind, body);
    poll(job_id, kind);
  } catch (err) {
    $("message").textContent = err.message;
    lock(false);
  }
});

renderCompare({});
syncMode();