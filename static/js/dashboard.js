document.addEventListener("DOMContentLoaded", () => {
  let totes = {};         // live data from /iot/live
  let activeId = null;    // currently selected tote ID in modal
  let selectedFile = null;
  let modalOpen = false;

  const kpiSection   = document.getElementById("kpiSection");
  const cardsSection = document.getElementById("toteCards");
  const searchInput  = document.getElementById("searchInput");

  const modal        = document.getElementById("labelModal");
  const backdrop     = document.getElementById("modalBackdrop");
  const modalTitle   = document.getElementById("modalTitle");
  const labelPreview = document.getElementById("labelPreview");
  const noLabelMessage = document.getElementById("noLabelMessage");
  const downloadBtn  = document.getElementById("downloadBtn");
  const labelFileInput = document.getElementById("labelFile");
  const uploadBtn    = document.getElementById("uploadBtn");
  const refreshBtn   = document.getElementById("refreshBtn");

  // MAP
  const mapContainer = document.getElementById("toteMap");
  let map = null;
  let toteMarkers = {};

  function initMap() {
    if (!mapContainer || typeof L === "undefined") return;
    if (map) return; // already initialised

    map = L.map("toteMap").setView([20.5937, 78.9629], 5); // Center on India by default

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19
    }).addTo(map);
  }

  function renderMap() {
    if (!map) return;

    const values = Object.values(totes || {});
    const latLngs = [];

    values.forEach((t) => {
      if (!t.coords) return;

      const parts = String(t.coords).split(",");
      if (parts.length < 2) return;

      const lat = parseFloat(parts[0]);
      const lon = parseFloat(parts[1]);
      if (Number.isNaN(lat) || Number.isNaN(lon)) return;

      latLngs.push([lat, lon]);

      if (!toteMarkers[t.id]) {
        toteMarkers[t.id] = L.marker([lat, lon])
          .addTo(map)
          .bindPopup(
            `<div style="min-width:160px;">
               <strong>${t.name || t.id}</strong><br/>
               ${t.location || ""}<br/>
               <small>Status: ${t.status || "unknown"}</small>
             </div>`
          );
      } else {
        toteMarkers[t.id].setLatLng([lat, lon]);
      }
    });

    // Remove markers for totes that no longer exist
    Object.keys(toteMarkers).forEach((id) => {
      if (!totes[id] || !totes[id].coords) {
        map.removeLayer(toteMarkers[id]);
        delete toteMarkers[id];
      }
    });

    if (latLngs.length) {
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }

  /* -----------------------------
     LIVE DATA FETCH
  ----------------------------- */
  async function fetchLiveData() {
    if (modalOpen) {
      // Optional: don't refresh while modal open
      return;
    }

    try {
      const res = await fetch("/iot/live");
      const data = await res.json();

      totes = data || {};
      renderKPIs();
      renderCards();
      renderMap();
    } catch (err) {
      console.error("Error fetching live data", err);
    }
  }

  /* -----------------------------
     KPI RENDERING
  ----------------------------- */
  function renderKPIs() {
    const values = Object.values(totes);

    const total    = values.length;
    const normal   = values.filter((t) => t.status === "normal").length;
    const warning  = values.filter((t) => t.status === "warning").length;
    const critical = values.filter((t) => t.status === "critical").length;

    kpiSection.innerHTML = `
      <div class="bg-white p-4 rounded-2xl shadow flex flex-col">
        <span class="text-xs text-gray-500 mb-1">Total Totes</span>
        <span class="text-2xl font-semibold">${total}</span>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow flex flex-col">
        <span class="text-xs text-gray-500 mb-1">Normal</span>
        <span class="text-2xl font-semibold text-green-600">${normal}</span>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow flex flex-col">
        <span class="text-xs text-gray-500 mb-1">Warning</span>
        <span class="text-2xl font-semibold text-amber-500">${warning}</span>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow flex flex-col">
        <span class="text-xs text-gray-500 mb-1">Critical</span>
        <span class="text-2xl font-semibold text-red-500">${critical}</span>
      </div>
    `;
  }

  /* -----------------------------
     CARD RENDERING
  ----------------------------- */
  function renderCards() {
    const query = (searchInput.value || "").toLowerCase().trim();
    const values = Object.values(totes);

    cardsSection.innerHTML = "";

    values
      .filter((t) => {
        if (!query) return true;
        return (
          (t.id || "").toLowerCase().includes(query) ||
          (t.name || "").toLowerCase().includes(query) ||
          (t.location || "").toLowerCase().includes(query)
        );
      })
      .forEach((t) => {
        const coords = (t.coords || "").split(",");
        const lat = coords[0] || "";
        const lon = coords[1] || "";

        let statusBadge = "";
        if (t.status === "critical") {
          statusBadge = `<span class="px-2 py-1 text-xs rounded bg-red-100 text-red-700">Critical</span>`;
        } else if (t.status === "warning") {
          statusBadge = `<span class="px-2 py-1 text-xs rounded bg-amber-100 text-amber-700">Warning</span>`;
        } else {
          statusBadge = `<span class="px-2 py-1 text-xs rounded bg-green-100 text-green-700">Normal</span>`;
        }

        cardsSection.innerHTML += `
          <div class="bg-white rounded-2xl p-5 shadow border space-y-3">
            <div class="flex justify-between items-start">
              <div>
                <h2 class="font-semibold text-gray-900">${t.name || t.id}</h2>
                <p class="text-xs text-gray-500">${t.id}</p>
              </div>
              ${statusBadge}
            </div>

            <div class="bg-cardGreen p-3 rounded-lg">
              <p class="text-xs text-gray-600">🌡 Temperature</p>
              <p class="text-xl font-bold">${t.temp ?? "--"}°C</p>
            </div>

            <div class="bg-cardPurple p-3 rounded-lg">
              <p class="text-xs text-gray-600">💧 Humidity</p>
              <p class="text-md font-medium">${t.humidity ?? "--"}%</p>
            </div>

            <div class="bg-cardBlue p-3 rounded-lg">
              <p class="text-xs text-gray-600">💡 Lux</p>
              <p class="text-md font-medium">${t.lux ?? "--"} lx</p>
            </div>

            <div class="bg-gray-100 p-3 rounded-lg">
              <p class="text-xs text-gray-600">📍 Location</p>
              <p class="text-sm text-gray-800">${t.location || "Unknown"}</p>
              ${
                lat && lon
                  ? `<a href="https://www.google.com/maps?q=${lat},${lon}"
                        target="_blank"
                        class="text-xs underline text-blue-700">
                       Open in Maps
                     </a>`
                  : ""
              }
            </div>

            <button
              class="w-full py-2 text-xs bg-white border rounded-lg hover:bg-gray-100"
              onclick="openModal('${t.id}')">
              Manage Label
            </button>
          </div>
        `;
      });
  }

  /* -----------------------------
     MODAL LOGIC
  ----------------------------- */
  function updateModalLabelPreview(id) {
    if (!id) return;
    const url = `/label/${id}.png?cacheBust=${Date.now()}`;

    labelPreview.onload = () => {
      labelPreview.classList.remove("hidden");
      noLabelMessage.classList.add("hidden");
    };
    labelPreview.onerror = () => {
      labelPreview.classList.add("hidden");
      noLabelMessage.classList.remove("hidden");
    };

    labelPreview.src = url;
    downloadBtn.href = url;
  }

  window.openModal = function (id) {
    activeId = id;
    modalOpen = true;

    modalTitle.textContent = `Label for ${id}`;
    modal.classList.remove("hidden");
    backdrop.classList.remove("hidden");

    updateModalLabelPreview(id);
  };

  window.closeModal = function () {
    modalOpen = false;
    modal.classList.add("hidden");
    backdrop.classList.add("hidden");
  };

  /* -----------------------------
     LABEL UPLOAD
  ----------------------------- */
  labelFileInput.addEventListener("change", (e) => {
    selectedFile = e.target.files[0] || null;
  });

  uploadBtn.addEventListener("click", async () => {
    if (!activeId) {
      alert("No tote selected.");
      return;
    }
    if (!selectedFile) {
      alert("Please select a PNG file first.");
      return;
    }

    const fd = new FormData();
    fd.append("file", selectedFile);

    try {
      const res = await fetch(`/upload_label/${activeId}`, {
        method: "POST",
        body: fd,
      });
      const data = await res.json();

      if (!res.ok || !data.ok) {
        console.error("Upload failed", data);
        alert("Upload failed");
        return;
      }

      alert("Label uploaded!");
      updateModalLabelPreview(activeId);
    } catch (err) {
      console.error("Upload error", err);
      alert("Upload error");
    }
  });

  /* -----------------------------
     SEARCH + REFRESH
  ----------------------------- */
  searchInput.addEventListener("input", renderCards);
  refreshBtn.addEventListener("click", fetchLiveData);

  // Poll every 5s for live data
  setInterval(fetchLiveData, 5000);

  // Initial load
  initMap();
  fetchLiveData();
});
