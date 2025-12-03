document.addEventListener("DOMContentLoaded", () => {

  let totes = {};
  let activeId = null;
  let modalOpen = false;

  const cardsSection = document.getElementById("toteCards");
  const kpiSection = document.getElementById("kpiSection");
  const searchInput = document.getElementById("searchInput");
  const refreshBtn = document.getElementById("refreshBtn");

  const modal = document.getElementById("labelModal");
  const backdrop = document.getElementById("modalBackdrop");
  const labelPreview = document.getElementById("labelPreview");
  const noLabelMessage = document.getElementById("noLabelMessage");
  const downloadBtn = document.getElementById("downloadBtn");
  const labelFileInput = document.getElementById("labelFile");
  const uploadBtn = document.getElementById("uploadBtn");

  /* ---------------- MAP ---------------- */
  let map = L.map("toteMap").setView([20.5, 78.9], 5);
  let toteMarkers = {};

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

  function updateMap() {
    Object.values(totes).forEach(t => {
      const lat = t.location?.lat;
      const lon = t.location?.lon;
      if (!lat || !lon) return;

      if (!toteMarkers[t.id]) {
        toteMarkers[t.id] = L.marker([lat, lon]).addTo(map);
      } else {
        toteMarkers[t.id].setLatLng([lat, lon]);
      }
    });
  }

  /* ---------------- LIVE DATA ---------------- */
  async function fetchLiveData() {
    try {
      const res = await fetch("/iot/live");
      totes = await res.json();

      renderKPIs();
      renderCards();
      updateMap();
    } catch (err) {
      console.error("Live fetch error:", err);
    }
  }

  /* ---------------- KPIs ---------------- */
  function renderKPIs() {
    const values = Object.values(totes);

    const normal = values.filter(t => t.status === "normal").length;
    const warn = values.filter(t => t.status === "warning").length;
    const crit = values.filter(t => t.status === "critical").length;

    kpiSection.innerHTML = `
      <div class="bg-white p-4 rounded-2xl shadow">
        <p class="text-xs text-gray-500">Total</p>
        <p class="text-2xl font-semibold">${values.length}</p>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow">
        <p class="text-xs text-gray-500">Normal</p>
        <p class="text-2xl font-semibold text-green-600">${normal}</p>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow">
        <p class="text-xs text-gray-500">Warning</p>
        <p class="text-2xl font-semibold text-amber-600">${warn}</p>
      </div>
      <div class="bg-white p-4 rounded-2xl shadow">
        <p class="text-xs text-gray-500">Critical</p>
        <p class="text-2xl font-semibold text-red-600">${crit}</p>
      </div>
    `;
  }

  /* ---------------- CARDS ---------------- */
  function renderCards() {
    const query = searchInput.value.toLowerCase().trim();
    const values = Object.values(totes);

    cardsSection.innerHTML = "";

    values
      .filter(t => {
        return (
          t.id.toLowerCase().includes(query) ||
          (t.location?.label || "").toLowerCase().includes(query)
        );
      })
      .forEach(t => {
        const lat = t.location?.lat ?? "";
        const lon = t.location?.lon ?? "";
        const ts = t.timestamp ? new Date(t.timestamp * 1000).toLocaleString() : "—";

        let statusColor = "bg-green-100 text-green-700";
        if (t.status === "warning") statusColor = "bg-amber-100 text-amber-700";
        if (t.status === "critical") statusColor = "bg-red-100 text-red-700";

        cardsSection.innerHTML += `
          <div class="bg-white rounded-2xl p-5 shadow border space-y-3">
            <div class="flex justify-between items-start">
              <div>
                <h2 class="font-semibold text-gray-900">${t.id}</h2>
              </div>
              <span class="px-2 py-1 text-xs rounded ${statusColor}">
                ${t.status}
              </span>
            </div>

            <div class="p-3 rounded-lg bg-cardGreen">
              <p class="text-xs text-gray-600">🌡 Temperature</p>
              <p class="text-xl font-bold">${t.temperature ?? "--"}°C</p>
            </div>

            <div class="p-3 rounded-lg bg-cardPurple">
              <p class="text-xs text-gray-600">💧 Humidity</p>
              <p class="text-md font-medium">${t.humidity ?? "--"}%</p>
            </div>

            <div class="p-3 rounded-lg bg-cardBlue">
              <p class="text-xs text-gray-600">💡 Lux</p>
              <p class="text-md font-medium">${t.lux ?? "--"} lx</p>
            </div>

            <div class="bg-gray-100 p-3 rounded-lg">
              <p class="text-xs text-gray-600">📍 Location</p>
              <p class="text-sm">${lat}, ${lon}</p>
              ${
                lat && lon
                  ? `<a href="https://www.google.com/maps?q=${lat},${lon}" target="_blank"
                       class="text-xs underline text-blue-700">Open in Maps</a>`
                  : ""
              }
            </div>

            <p class="text-xs text-gray-500">⏱ Last updated: ${ts}</p>

            <button onclick="openModal('${t.id}')"
              class="w-full py-2 text-xs bg-white border rounded-lg hover:bg-gray-100">
              Manage Label
            </button>
          </div>
        `;
      });
  }

  /* ---------------- LABEL MODAL ---------------- */
  window.openModal = function (id) {
    activeId = id;
    modalOpen = true;

    labelPreview.classList.add("hidden");
    noLabelMessage.classList.remove("hidden");

    const url = `/label/${id}.png?cb=${Date.now()}`;
    labelPreview.src = url;
    labelPreview.onload = () => {
      labelPreview.classList.remove("hidden");
      noLabelMessage.classList.add("hidden");
    };

    downloadBtn.href = url;

    modal.classList.remove("hidden");
    backdrop.classList.remove("hidden");
  };

  window.closeModal = function () {
    modalOpen = false;
    modal.classList.add("hidden");
    backdrop.classList.add("hidden");
  };

  uploadBtn.addEventListener("click", async () => {
    const file = labelFileInput.files[0];
    if (!file) return alert("Select a PNG file first");

    const fd = new FormData();
    fd.append("file", file);

    const res = await fetch(`/upload_label/${activeId}`, {
      method: "POST",
      body: fd
    });

    const data = await res.json();
    if (data.ok) {
      alert("Label uploaded!");
      openModal(activeId);
    }
  });

  /* ---------------- EVENTS ---------------- */
  searchInput.addEventListener("input", renderCards);
  refreshBtn.addEventListener("click", fetchLiveData);

  setInterval(fetchLiveData, 5000);
  fetchLiveData();

});
