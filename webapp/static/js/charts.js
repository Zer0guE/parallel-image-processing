// Draws the three charts. rows = [{workers, time, speedup, efficiency}]
const charts = {};

function drawChart(id, type, labels, datasets, yTitle) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart(document.getElementById(id), {
    type,
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: { legend: { display: datasets.length > 1, position: "bottom" } },
      scales: {
        x: { title: { display: true, text: "Worker processes" } },
        y: { beginAtZero: true, title: { display: true, text: yTitle } }
      }
    }
  });
}

function renderCharts(rows) {
  const labels = rows.map(r => String(r.workers));
  drawChart("chart-time", "bar", labels,
    [{ label: "Time (s)", data: rows.map(r => r.time), backgroundColor: "#2f5bea" }],
    "Execution time (s)");
  drawChart("chart-speedup", "line", labels, [
    { label: "Measured", data: rows.map(r => r.speedup), borderColor: "#2f5bea", backgroundColor: "#2f5bea" },
    { label: "Ideal", data: rows.map(r => r.workers), borderColor: "#9aa7c7", borderDash: [6, 4], pointRadius: 0 }
  ], "Speedup");
  drawChart("chart-eff", "line", labels,
    [{ label: "Efficiency", data: rows.map(r => r.efficiency), borderColor: "#2f5bea", backgroundColor: "#2f5bea" }],
    "Efficiency (S / p)");
}