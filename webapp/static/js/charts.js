// Draws the three charts. rows = [{workers, time, speedup, efficiency}]
const charts = {};
Chart.defaults.color = "#9e9e9e";        // axis text and legends
Chart.defaults.borderColor = "#4d4d4d";  // grid lines

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
    [{ label: "Time (s)", data: rows.map(r => r.time), backgroundColor: "#028300" }],
    "Execution time (s)");
  drawChart("chart-speedup", "line", labels, [
    { label: "Measured", data: rows.map(r => r.speedup), borderColor: "#028300", backgroundColor: "#028300" },
    { label: "Ideal", data: rows.map(r => r.workers), borderColor: "#9e9e9e", borderDash: [6, 4], pointRadius: 0 }
  ], "Speedup");
  drawChart("chart-eff", "line", labels,
    [{ label: "Efficiency", data: rows.map(r => r.efficiency), borderColor: "#028300", backgroundColor: "#028300" }],
    "Efficiency (S / p)");
}