document.addEventListener("DOMContentLoaded", () => {
  let totes = {};         // live data from /iot/live
  let activeId = null;    // currently selected tote ID in modal
  let selectedFile = null;
  let modalOpen = false;

  const kpiSection = document.getElementById("kpiSection");
  const cardsSection = document.getElementById("toteCards");
  const searchInput = document.getElementById("searchInput");

  const modal = document.getElementById("labelModal");
  const backdrop = document.getElementById("modalBackdrop");
  const modalTitle = document.getElementById("modalTitle");
  const labelPreview = document.getElementById("labelPreview");
  const noLabelMessage = document.getElementById("noLabelMessage");
  const downloadBtn = document.getElementById("downloadBtn");
  const labelFileInput = document.getElementById("labelFile");
  const uploadBtn = document.getElementById("uploadBtn");
  const refreshBtn = document.getElementById("refreshBtn");

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
    } catch (err) {
      console.error("Error fetching live data", err);
    }
  }

  /* -----------------------------
     KPI RENDERING
  ----------------------------- */
  function renderKPIs() {
    const values = Object.values(totes);

    const total = values.length;
    const normal = values.filter(t => t.status === "normal").length;
    const warning = values.filter(t => t.status === "warning").length;
    const critical = values.filter(t => t.status === "critical").length;

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
      .filter(t => {
        if (!query) return true;
        return (
          (t.id || "").toLowerCase().includes(query) ||
          (t.name || "").toLowerCase().includes(query) ||
          (t.location || "").toLowerCase().includes(query)
        );
      })
      .forEach(t => {
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

            <div class="bg-purple-100 p-3 rounded-lg">
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
              View / Upload Label
            </button>
          </div>
        `;
      });
  }

  /* -----------------------------
     MODAL LOGIC
  ----------------------------- */
  window.openModal = function (toteId) {
    activeId = toteId;
    modalOpen = true;

    modalTitle.textContent = `Label – ${toteId}`;

    // Reset preview state
    labelPreview.classList.remove("hidden");
    noLabelMessage.classList.add("hidden");
    labelPreview.src = `/label/${toteId}.png?${Date.now()}`;

    // If image not found or fails to load
    labelPreview.onerror = () => {
      labelPreview.classList.add("hidden");
      noLabelMessage.classList.remove("hidden");
    };

    downloadBtn.href = `/label/${toteId}.png`;

    modal.classList.remove("hidden");
    backdrop.classList.remove("hidden");
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

  uploadBtn.addEventListener("click", () => {
    if (!activeId) {
      alert("No tote selected.");
      return;
    }
    if (!selectedFile) {
      alert("Please select an image file.");
      return;
    }

    const fd = new FormData();
    fd.append("file", selectedFile);

    fetch(`/upload_label/${activeId}`, {
      method: "POST",
      body: fd,
    })
      .then((r) => r.json())
      .then((res) => {
        if (!res.ok) {
          console.error("Upload failed", res);
          alert("Upload failed");
          return;
        }
        alert("Label uploaded!");
        // Refresh label preview
        labelPreview.classList.remove("hidden");
        noLabelMessage.classList.add("hidden");
        labelPreview.src = `/label/${activeId}.png?${Date.now()}`;
      })
      .catch((err) => {
        console.error("Upload error", err);
        alert("Upload error");
      });
  });

  /* -----------------------------
     SEARCH + REFRESH
  ----------------------------- */
  searchInput.addEventListener("input", renderCards);
  refreshBtn.addEventListener("click", fetchLiveData);

  // Poll every 5s for live data
  setInterval(fetchLiveData, 5000);

  // Initial load
  fetchLiveData();
});
