/** pages/readings.js — Nhập & tra cứu chỉ số */
let _readingData = [];
let _readingMeters = [];
let _readingHouseholds = [];
let _readingState = { hh: "", period: "" };

async function renderReadings() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();
  const colCount = isAdmin ? 6 : 5;

  // Đổi vai trò trong cùng phiên → bỏ bộ lọc hộ còn sót lại
  if (!isAdmin) _readingState.hh = "";

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">📝 ${isAdmin ? "Nhập &amp; tra cứu chỉ số" : "Chỉ số của tôi"}</h2>
        <p class="page-head-sub">${isAdmin
          ? "Ghi chỉ số điện/nước theo kỳ tháng. Hệ thống tự tính mức tiêu thụ và kiểm tra bất thường."
          : "Tra cứu chỉ số điện nước của hộ theo từng kỳ tháng."}</p>
      </div>
    </div>

    <div class="layout-cols">
      ${isAdmin ? `
      <div class="form-panel">
        <div class="form-panel-title">➕ Nhập chỉ số mới</div>
        <div class="form-panel-sub">Chọn hộ và đồng hồ — chỉ số kỳ trước được điền tự động.</div>
        <div class="form-grid">
          <div class="form-group">
            <label class="form-label" for="r-hh">Hộ / Phòng</label>
            <select id="r-hh" class="form-control" onchange="loadMetersForReading()">
              <option value="">-- Chọn hộ --</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="r-meter">Đồng hồ</label>
            <select id="r-meter" class="form-control" onchange="prefillPrevReading()">
              <option value="">-- Chọn đồng hồ --</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="r-period">Kỳ tháng</label>
            <input id="r-period" class="form-control" type="month" value="${currentPeriod()}">
          </div>
          <div class="form-grid form-grid-2" style="gap:12px">
            <div class="form-group">
              <label class="form-label" for="r-prev">Chỉ số kỳ trước</label>
              <input id="r-prev" class="form-control" type="number" step="0.01" readonly placeholder="0">
            </div>
            <div class="form-group">
              <label class="form-label" for="r-curr">Chỉ số kỳ này *</label>
              <input id="r-curr" class="form-control" type="number" step="0.01" oninput="previewConsumption()" placeholder="Nhập số mới">
            </div>
          </div>
          <div class="reading-preview" id="r-preview-box">
            <span class="reading-preview-label">Tiêu thụ dự kiến</span>
            <span class="reading-preview-value" id="r-preview">—</span>
          </div>
        </div>
        <button class="btn btn-primary btn-block" type="button" style="margin-top:16px" onclick="submitReading()">✅ Nhập chỉ số</button>
      </div>` : ""}

      <div>
        <div class="toolbar" style="margin-bottom:12px">
          <div class="toolbar-group">
            ${isAdmin ? `
            <label class="filter-label" for="rf-hh">Hộ</label>
            <select id="rf-hh" class="form-control" style="width:170px" onchange="setReadingHousehold(this.value)" aria-label="Lọc theo hộ">
              <option value="">Tất cả hộ</option>
            </select>` : ""}
            <label class="filter-label" for="rf-period">Kỳ</label>
            <input id="rf-period" class="form-control" type="month" style="width:160px"
              value="${escapeHtml(_readingState.period)}"
              onchange="setReadingPeriod(this.value)" aria-label="Lọc theo kỳ">
            <button class="btn btn-ghost btn-sm" type="button" onclick="clearReadingFilters()">✕ Xóa lọc</button>
          </div>
          <span class="text-muted" id="reading-total" style="font-size:0.75rem"></span>
        </div>

        <div class="table-wrapper">
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  ${isAdmin ? "<th>Hộ / Phòng</th>" : ""}
                  <th>Đồng hồ</th>
                  <th>Kỳ</th>
                  <th class="num">Trước</th>
                  <th class="num">Sau</th>
                  <th class="num">Tiêu thụ</th>
                </tr>
              </thead>
              <tbody id="r-tbody">${loadingRow(colCount)}</tbody>
            </table>
          </div>
          <div class="table-foot">
            <span id="reading-table-foot">Đang tải…</span>
            <span>Chỉ số sắp xếp theo kỳ mới nhất</span>
          </div>
        </div>
      </div>
    </div>`;

  await loadReadingsPage();
}

async function loadReadingsPage() {
  const tbody = document.getElementById("r-tbody");
  if (!tbody) return;
  try {
    const [readings, meters, households] = await Promise.all([
      Api.get("/api/readings"),
      Api.get("/api/meters"),
      Api.get("/api/households"),
    ]);
    _readingData = Array.isArray(readings) ? readings : [];
    _readingMeters = Array.isArray(meters) ? meters : [];
    _readingHouseholds = Array.isArray(households) ? households : [];

    // Fill bộ lọc
    const filterHh = document.getElementById("rf-hh");
    if (filterHh) {
      filterHh.innerHTML = `<option value="">Tất cả hộ</option>` +
        _readingHouseholds.map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");
      filterHh.value = _readingState.hh;
    }

    // Fill form nhập
    const formHh = document.getElementById("r-hh");
    if (formHh) {
      formHh.innerHTML = `<option value="">-- Chọn hộ --</option>` +
        _readingHouseholds.filter(h => h.status === "active")
          .map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");
      if (_readingHouseholds.length === 1) {
        formHh.value = _readingHouseholds[0].id;
        await loadMetersForReading();
      }
    }

    renderReadingsTable();
  } catch {
    tbody.innerHTML = emptyRow(Auth.isAdmin() ? 6 : 5, "📝", "Không tải được dữ liệu chỉ số", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải chỉ số", "error");
  }
}

function readingMeter(id) {
  return _readingMeters.find(m => m.id === id) || null;
}

function readingHouseholdNameByMeter(meterId) {
  const meter = readingMeter(meterId);
  if (!meter) return `ĐH #${meterId}`;
  const hh = _readingHouseholds.find(h => h.id === meter.household_id);
  return hh?.name || `Hộ #${meter.household_id}`;
}

async function loadMetersForReading() {
  const hhId = document.getElementById("r-hh")?.value;
  const sel = document.getElementById("r-meter");
  if (!sel) return;
  sel.innerHTML = `<option value="">-- Chọn đồng hồ --</option>`;
  document.getElementById("r-prev").value = "";
  previewConsumption();
  if (!hhId) return;

  try {
    const data = _readingMeters.filter(m => String(m.household_id) === String(hhId));
    if (!data.length) {
      sel.innerHTML = `<option value="">Hộ này chưa có đồng hồ</option>`;
      return;
    }
    sel.innerHTML += data.map(m =>
      `<option value="${m.id}">${m.meter_type === "electricity" ? "⚡" : "💧"} ${escapeHtml(m.meter_number)} (${escapeHtml(m.unit)})</option>`
    ).join("");
    if (data.length === 1) {
      sel.value = data[0].id;
      await prefillPrevReading();
    }
  } catch {
    showToast("Không tải được đồng hồ", "error");
  }
}

async function prefillPrevReading() {
  const meterId = document.getElementById("r-meter")?.value;
  const prevEl = document.getElementById("r-prev");
  if (!prevEl) return;
  prevEl.value = "";
  previewConsumption();
  if (!meterId) return;
  try {
    const last = await Api.get(`/api/readings/last/${meterId}`);
    prevEl.value = last.curr_reading;
  } catch {
    prevEl.value = 0; // chưa có chỉ số trước đó
  }
  previewConsumption();
}

function previewConsumption() {
  const prev = parseFloat(document.getElementById("r-prev")?.value || 0);
  const currRaw = document.getElementById("r-curr")?.value;
  const curr = currRaw === "" ? NaN : parseFloat(currRaw);
  const meter = readingMeter(parseInt(document.getElementById("r-meter")?.value));
  const unit = meter?.unit ? ` ${meter.unit}` : "";
  const preview = document.getElementById("r-preview");
  const box = document.getElementById("r-preview-box");
  const input = document.getElementById("r-curr");
  if (!preview) return;
  if (isNaN(curr)) {
    preview.textContent = "—";
    box?.classList.remove("negative");
    if (input) input.style.borderColor = "";
    return;
  }
  const diff = curr - prev;
  preview.textContent = `${fmtNumber(diff, 2)}${unit}`;
  box?.classList.toggle("negative", diff < 0);
  if (input) input.style.borderColor = diff < 0 ? "var(--accent-red)" : "";
}

async function submitReading() {
  const meterId = parseInt(document.getElementById("r-meter").value);
  const period = document.getElementById("r-period").value.trim();
  const currRaw = document.getElementById("r-curr").value;
  const body = {
    meter_id: meterId,
    period,
    prev_reading: parseFloat(document.getElementById("r-prev").value || 0),
    curr_reading: parseFloat(currRaw),
  };
  if (!body.meter_id) { showToast("Chọn đồng hồ", "warning"); return; }
  if (!body.period) { showToast("Chọn kỳ tháng", "warning"); return; }
  if (currRaw === "" || isNaN(body.curr_reading)) { showToast("Nhập chỉ số kỳ này", "warning"); return; }
  if (body.curr_reading < body.prev_reading) { showToast("Chỉ số mới không được nhỏ hơn kỳ trước", "error"); return; }

  try {
    await Api.post("/api/readings", body);
    showToast("Đã nhập chỉ số thành công!", "success");
    document.getElementById("r-curr").value = "";
    await prefillPrevReading();
    // Tải lại danh sách (giữ nguyên bộ lọc)
    const readings = await Api.get("/api/readings").catch(() => _readingData);
    _readingData = Array.isArray(readings) ? readings : _readingData;
    renderReadingsTable();
  } catch (e) { showToast(e.detail || "Lỗi nhập chỉ số", "error"); }
}

function renderReadingsTable() {
  const tbody = document.getElementById("r-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  const colCount = isAdmin ? 6 : 5;

  const filtered = _readingData.filter(r => {
    const meter = readingMeter(r.meter_id);
    if (_readingState.hh && String(meter?.household_id) !== String(_readingState.hh)) return false;
    if (_readingState.period && r.period !== _readingState.period) return false;
    return true;
  });

  if (!filtered.length) {
    tbody.innerHTML = emptyRow(
      colCount,
      "📝",
      _readingData.length ? "Không có chỉ số phù hợp" : "Chưa có chỉ số nào",
      _readingData.length
        ? "Thử chọn hộ hoặc kỳ khác."
        : (isAdmin ? "Nhập chỉ số đầu tiên ở biểu mẫu bên cạnh." : "Chỉ số sẽ xuất hiện khi quản trị viên cập nhật.")
    );
  } else {
    tbody.innerHTML = filtered.map(r => {
      const meter = readingMeter(r.meter_id);
      const isElectricity = meter?.meter_type === "electricity";
      return `
      <tr>
        ${isAdmin ? `<td>
          <span class="cell-main">${escapeHtml(readingHouseholdNameByMeter(r.meter_id))}</span>
          <span class="cell-sub">ĐH #${r.meter_id}</span>
        </td>` : ""}
        <td>
          <span class="badge ${isElectricity ? "badge-warning" : "badge-info"}">${isElectricity ? "⚡" : "💧"} ${escapeHtml(meter?.meter_number || "—")}</span>
        </td>
        <td><span class="badge badge-muted">${escapeHtml(r.period)}</span></td>
        <td class="num">${fmtNumber(r.prev_reading, 2)}</td>
        <td class="num">${fmtNumber(r.curr_reading, 2)}</td>
        <td class="num"><strong style="color:var(--accent-cyan)">${fmtNumber(r.consumption, 2)}</strong> <span class="text-muted" style="font-size:0.7rem">${escapeHtml(meter?.unit || "")}</span></td>
      </tr>`;
    }).join("");
  }

  const totalConsumption = filtered.reduce((sum, r) => sum + (Number(r.consumption) || 0), 0);
  const foot = document.getElementById("reading-table-foot");
  if (foot) foot.innerHTML = `Hiển thị <strong>${filtered.length}</strong> / ${_readingData.length} bản ghi chỉ số`;

  const total = document.getElementById("reading-total");
  if (total) {
    if (!filtered.length) {
      total.textContent = "";
    } else {
      // Tổng tiêu thụ theo từng đơn vị (kWh / m³) để tránh cộng sai đơn vị
      const byUnit = new Map();
      filtered.forEach(r => {
        const meter = readingMeter(r.meter_id);
        const unit = meter?.unit || "—";
        byUnit.set(unit, (byUnit.get(unit) || 0) + (Number(r.consumption) || 0));
      });
      const parts = [...byUnit.entries()].map(([unit, value]) => {
        const icon = unit === "kWh" ? "⚡" : unit === "m3" || unit === "m³" ? "💧" : "";
        return `${icon} ${fmtNumber(value, 2)} ${unit}`.trim();
      });
      total.textContent = `Tổng tiêu thụ: ${parts.join(" · ")}`;
    }
  }
}

function clearReadingFilters() {
  _readingState = { hh: "", period: "" };
  const hh = document.getElementById("rf-hh");
  const period = document.getElementById("rf-period");
  if (hh) hh.value = "";
  if (period) period.value = "";
  renderReadingsTable();
}

function setReadingHousehold(value) {
  _readingState.hh = value;
  renderReadingsTable();
}

function setReadingPeriod(value) {
  _readingState.period = value;
  renderReadingsTable();
}
