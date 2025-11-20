/* -----------------------------------------
   Base Device Metadata
----------------------------------------- */
const baseDevices = [
  { id: "TOTE001", name: "Tote001", status: "normal", temp: 0, tempRange: "-20°– -15°C", luxStatus: "CLOSE (OFF)", luxActive: false, lux: 0, location: "Warehouse A – Section 1", coords: "40.7128,-74.0060" },
  { id: "TOTE002", name: "Tote002", status: "warning", temp: 0, tempRange: "18°–25°C",    luxStatus: "OPEN (ON)",  luxActive: true,  lux: 0, location: "Warehouse B – Section 2", coords: "40.7589,-73.9851" },
  { id: "TOTE003", name: "Tote003", status: "critical",temp: 0, tempRange: "70°–80°C",    luxStatus: "CLOSE (OFF)", luxActive: false, lux: 0, location: "Warehouse C – Section 3", coords: "40.6892,-74.0445" },
  { id: "TOTE004", name: "Tote004", status: "normal", temp: 0, tempRange: "18°–25°C",    luxStatus: "OPEN (ON)",  luxActive: true,  lux: 0, location: "Warehouse D – Section 4", coords: "40.7505,-73.9934" },
];

let devices = JSON.parse(JSON.stringify(baseDevices));
let activeFilter = "all";
let activeToteId = null;
let selectedFile = null;

/* -----------------------------------------
   KPI Rendering
----------------------------------------- */
function renderKPIs(list) {
  document.getElementById("kpiSection").innerHTML = `
    <div class="bg-white rounded-2xl shadow p-4"><span class="text-xs">Total Totes</span><span class="text-2xl font-semibold">${list.length}</span></div>
    <div class="bg-white rounded-2xl shadow p-4"><span class="text-xs">Normal</span><span class="text-2xl font-semibold text-success">${list.filter(d=>d.status==="normal").length}</span></div>
    <div class="bg-white rounded-2xl shadow p-4"><span class="text-xs">Warning</span><span class="text-2xl font-semibold text-warning">${list.filter(d=>d.status==="warning").length}</span></div>
    <div class="bg-white rounded-2xl shadow p-4"><span class="text-xs">Critical</span><span class="text-2xl font-semibold text-critical">${list.filter(d=>d.status==="critical").length}</span></div>
    <div class="bg-white rounded-2xl shadow p-4"><span class="text-xs">Lux Active</span><span class="text-2xl font-semibold text-info">${list.filter(d=>d.luxActive).length}</span></div>
  `;
}

/* -----------------------------------------
   Filters + Search
----------------------------------------- */
function renderFilters() {
  document.getElementById("filterSection").innerHTML = `
    <input id="searchInput" type="text" placeholder="Search..." class="flex-1 px-4 py-2 rounded-xl border"/>
    <button id="filter-all" class="chip active">All</button>
    <button id="filter-normal" class="chip">Normal</button>
    <button id="filter-warning" class="chip">Warning</button>
    <button id="filter-critical" class="chip">Critical</button>
  `;

  document.querySelectorAll(".chip").forEach(btn => {
    btn.addEventListener("click", () => {
      activeFilter = btn.id.replace("filter-","");
      renderCards();
    });
  });

  document.getElementById("searchInput").addEventListener("input", renderCards);
}

/* -----------------------------------------
   Filter Logic
----------------------------------------- */
function filteredDevices() {
  const q = document.getElementById("searchInput").value.toLowerCase();

  return devices.filter(d => {
    const matchesFilter = activeFilter === "all" ? true : d.status === activeFilter;
    const matchesSearch =
      d.id.toLowerCase().includes(q) ||
      d.name.toLowerCase().includes(q) ||
      d.location.toLowerCase().includes(q);
    return matchesFilter && matchesSearch;
  });
}

/* -----------------------------------------
   Render Tote Cards
----------------------------------------- */
function renderCards() {
  const list = filteredDevices();
  renderKPIs(list);

  const container = document.getElementById("toteCards");
  container.innerHTML = "";

  list.forEach(d => {
    const [lat, lon] = d.coords.split(",");

    container.innerHTML += `
      <div class="rounded-2xl bg-white shadow border p-4 space-y-3">
        <div class="flex justify-between">
          <h2 class="font-semibold">${d.name}</h2>
          <span class="px-2 py-1 text-xs bg-gray-900 text-white rounded">${d.id}</span>
        </div>

        <div class="p-3 rounded-lg bg-cardGreen">
          <span class="text-xs">🌡 Temperature</span>
          <div class="text-xl font-bold">${d.temp}°C</div>
        </div>

        <div class="p-3 rounded-lg bg-cardBlue">
          <span class="text-xs">💡 Lux</span>
          <div class="text-md">${d.lux} lx</div>
        </div>

        <div class="p-3 rounded-lg bg-gray-100">
          <span class="text-xs">📍 Location</span>
          <div class="text-sm">${d.location}</div>
          <a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank"
             class="text-xs underline">Open</a>
        </div>

        <div class="p-3 rounded-lg bg-cardPurple">
          <span class="text-xs">🏷 Barcode Label</span>
          <div class="h-12 flex items-center justify-center bg-white border rounded">
            <img src="/label/${d.id}.png"
                 class="max-h-10"
                 onerror="this.style.display='none'; this.parentElement.innerHTML='No image'">
          </div>
          <button onclick="openLabelModal('${d.id}')"
                  class="mt-2 px-3 py-1 text-xs bg-white border rounded hover:bg-gray-100">
            View / Upload
          </button>
        </div>
      </div>
    `;
  });
}

/* -----------------------------------------
   MODAL LOGIC
----------------------------------------- */
function openLabelModal(toteId) {
  activeToteId = toteId;

  document.getElementById("modalTitle").innerText = "Barcode – " + toteId;
  document.getElementById("currentBarcodeImg").src = "/label/" + toteId + ".png?" + Date.now();
  document.getElementById("downloadBarcodeBtn").href = "/label/" + toteId + ".png";

  document.getElementById("labelModal").classList.remove("hidden");
  document.getElementById("labelModalBackdrop").classList.remove("hidden");
}

function closeLabelModal() {
  document.getElementById("labelModal").classList.add("hidden");
  document.getElementById("labelModalBackdrop").classList.add("hidden");
}

/* -----------------------------------------
   Upload Barcode
----------------------------------------- */
document.getElementById("uploadBtn").addEventListener("click", () => {
  if (!selectedFile) return alert("Choose a file!");

  const fd = new FormData();
  fd.append("file", selectedFile);

  fetch("/upload_label/" + activeToteId, { method: "POST", body: fd })
    .then(r => r.json())
    .then(() => {
      alert("Uploaded!");
      closeLabelModal();
      renderCards();
    });
});

document.getElementById("barcodeUpload").addEventListener("change", e => {
  selectedFile = e.target.files[0];
});

/* -----------------------------------------
   LIVE DATA POLLING
----------------------------------------- */
async function fetchLiveData() {
  try {
    const res = await fetch("/iot/live");
    const data = await res.json();

    devices = JSON.parse(JSON.stringify(baseDevices));

    devices.forEach(d => {
      const live = data[d.id];
      if (!live) return;

      d.temp = live.temperature ?? d.temp;
      d.lux = live.lux ?? d.lux;
      d.status = live.status ?? d.status;

      if (live.location?.lat && live.location?.lon) {
        d.coords = `${live.location.lat},${live.location.lon}`;
      }
    });

    renderCards();
  } catch (err) {
    console.error(err);
  }
}

document.getElementById("refreshBtn").onclick = fetchLiveData;

// Live update every 5 seconds
setInterval(fetchLiveData, 5000);

// Initial render
renderFilters();
renderCards();
fetchLiveData();
