// Set to false once Flask is serving /api/* endpoints.
const USE_MOCK = false;

const $ = id => document.getElementById(id);
const IMAGE_COUNT = 200;

/* ---------- API layer (the only part that changes when the back-end is ready) ----------
   POST /api/run        {mode, workers, runs}  -> {job_id}
   POST /api/benchmark  {runs}                 -> {job_id}
   GET  /api/status/<id> -> {
       state: "running" | "done" | "error",
       progress: 0-100, message: "...", active_workers: 0-8,
       sequential_time: seconds | null,
       runs: [{workers, time}],        // average time per worker count
       verified: true | false | null,
       sample: "image_name.jpg" | null // for the image comparison
   }
*/
const api = {
  async start(kind, body) {
    if (USE_MOCK) return mock.start(kind, body);
    const url = kind === "benchmark" ? "/api/benchmark" : "/api/run";
    const res = await fetch(url, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "The server rejected the request.");
    return data;
  },
  async status(id) {
    if (USE_MOCK) return mock.status(id);
    const res = await fetch("/api/status/" + id);
    if (!res.ok) throw new Error("Could not read job status.");
    return res.json();
  }
};

/* ---------- Mock back-end: fake numbers shaped like a realistic run ---------- */
const mock = {
  jobs: {},
  SEQ: 120,
  TP: { 1: 124, 2: 63, 4: 33, 8: 20 },
  start(kind, body) {
    const id = "mock-" + Date.now();
    this.jobs[id] = { kind, body, t0: Date.now(), duration: 7000 };
    return { job_id: id };
  },
  status(id) {
    const j = this.jobs[id];
    const p = Math.min(1, (Date.now() - j.t0) / j.duration);
    const all = [1, 2, 4, 8];
    let runs = [], active = 1, seq = null;
    if (j.kind === "sequential") {
      if (p === 1) runs = [{ workers: 1, time: this.SEQ }];
      seq = p === 1 ? this.SEQ : null;
    } else if (j.kind === "parallel") {
      const w = Number(j.body.workers);
      active = w; seq = this.SEQ;
      if (p === 1) runs = [{ workers: w, time: this.TP[w] }];
    } else {
      const done = Math.floor(p * 4);
      runs = all.slice(0, done).map(w => ({ workers: w, time: this.TP[w] }));
      active = all[Math.min(done, 3)]; seq = this.SEQ;
    }
    return {
      state: p === 1 ? "done" : "running",
      progress: Math.round(p * 100),
      message: p === 1 ? "Finished." : "Processing " + Math.round(p * IMAGE_COUNT) + " of " + IMAGE_COUNT + " images",
      active_workers: p === 1 ? 0 : active,
      sequential_time: seq,
      runs,
      verified: p === 1 && j.kind !== "sequential" ? true : null,
      sample: null
    };
  }
};

/* ---------- UI ---------- */
const coresEl = $("cores");
for (let i = 1; i <= 8; i++) {
  const c = document.createElement("div");
  c.className = "core"; c.textContent = i;
  coresEl.appendChild(c);
}

function showCores(active) {
  [...coresEl.children].forEach((c, i) => c.classList.toggle("on", i < active));
}

function setState(text) { $("state").textContent = text; }

function setVerified(v) {
  const el = $("verify");
  el.className = "pill" + (v === true ? " ok" : v === false ? " bad" : "");
  el.textContent = v === true ? "Outputs match" : v === false ? "Outputs differ" : "Not verified yet";
}

function buildRows(status) {
  const seq = status.sequential_time;
  const n = status.image_count || IMAGE_COUNT; // IMAGE_COUNT is only a fallback for mock mode
  return status.runs.map(r => {
    const speedup = seq ? seq / r.time : null;
    return {
      workers: r.workers, time: r.time, speedup,
      efficiency: speedup ? speedup / r.workers : null,
      throughput: n / r.time
    };
  });
}

function renderTable(rows) {
  const body = $("rows");
  if (!rows.length) return;
  const f = (v, d) => (v == null ? "n/a" : v.toFixed(d));
  body.innerHTML = rows.map(r =>
    `<tr><td>${r.workers}</td><td>${f(r.time, 1)}</td><td>${f(r.speedup, 2)}x</td>` +
    `<td>${f(r.efficiency, 2)}</td><td>${f(r.throughput, 2)}</td></tr>`
  ).join("");
}

function showSample(name) {
  [["original", "original"], ["sequential", "sequential"], ["parallel", "parallel"]].forEach(([id, stage]) => {
    const el = $("img-" + id);
    el.innerHTML = name ? `<img alt="${stage} version of ${name}" src="/api/preview/${stage}/${encodeURIComponent(name)}">` : "No image yet";
  });
}

function syncSettings() {
  const kind = document.querySelector("input[name=kind]:checked").value;
  $("workers").disabled = kind !== "parallel";
  $("run").textContent = { sequential: "Run sequential", parallel: "Run parallel", benchmark: "Run benchmark" }[kind];
}
document.querySelectorAll("input[name=kind]").forEach(r => r.addEventListener("change", syncSettings));
syncSettings();
$("note").textContent = USE_MOCK ? "Using sample data. No images are processed yet." : "";

let timer = null;

async function poll(id) {
  try {
    const s = await api.status(id);
    $("bar-fill").style.width = s.progress + "%";
    $("message").textContent = s.message;
    showCores(s.active_workers);
    if (s.image_count) $("count").textContent = "Processed " + s.image_count + " images per test.";
    const rows = buildRows(s);
    renderTable(rows);
    if (rows.length && rows.every(r => r.speedup != null)) renderCharts(rows);
    if (s.sample) showSample(s.sample);

    if (s.state === "running") { timer = setTimeout(() => poll(id), USE_MOCK ? 300 : 1000); return; }
    setState(s.state === "done" ? "Done" : "Error");
    setVerified(s.verified);
    $("run").disabled = false;
  } catch (err) {
    setState("Error");
    $("message").textContent = err.message;
    showCores(0);
    $("run").disabled = false;
  }
}

$("run").addEventListener("click", async () => {
  const kind = document.querySelector("input[name=kind]:checked").value;
  const body = { mode: kind, workers: Number($("workers").value), runs: Number($("runs").value) };
  $("run").disabled = true;
  setState("Running"); setVerified(null);
  $("bar-fill").style.width = "0";
  $("message").textContent = "Starting...";
  clearTimeout(timer);
  try {
    const { job_id } = await api.start(kind, body);
    poll(job_id);
  } catch (err) {
    setState("Error");
    $("message").textContent = err.message;
    $("run").disabled = false;
  }
});