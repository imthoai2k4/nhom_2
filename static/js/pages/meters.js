/** pages/meters.js — Quản lý Đồng hồ */
let _meterData = [];
let _meterHouseholds = [];
let _meterState = { type: "", hh: "", q: "" };

async function renderMeters() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">Quản lý Đồng hồ</h2>
        <p class="page-head-sub">Theo dõi đồng hồ điện kế và đồng hồ nước đã lắp cho từng hộ.</p>
      </div>
      <div class="page-head-actions">
        ${isAdmin ? `<button class="btn btn-primary" type="button" onclick="openMeterModal()">➕ Thêm đồng hồ</button>` : ""}
      </div>
    </div>

    <div class="toolbar">
      <div class="search-field">
        <span class="search-icon" aria-hidden="true">🔎</span>
        <input id="meter-search" class="form-control" placeholder="Tìm theo số đồng hồ hoặc tên hộ…"
          value="${escapeHtml(_meterState.q)}" oninput="onMeterSearch(this.value)" aria-label="Tìm đồng hồ">
      </div>
      <div class="toolbar-group">
        <label class="filter-label" for="mf-hh">Hộ</label>
        <select id="mf-hh" class="form-control" style="width:170px" onchange="setMeterHousehold(this.value)" aria-label="Lọc theo hộ">
          <option value="">Tất cả hộ</option>
        </select>
        <div class="segmented" id="meter-type-filter" role="group" aria-label="Lọc theo loại đồng hồ">
          <button type="button" class="js-meter-type ${_meterState.type === "" ? "active" : ""}" onclick="setMeterType('')">Tất cả</button>
          <button type="button" class="js-meter-type ${_meterState.type === "electricity" ? "active" : ""}" onclick="setMeterType('electricity')">⚡ Điện</button>
          <button type="button" class="js-meter-type ${_meterState.type === "water" ? "active" : ""}" onclick="setMeterType('water')">💧 Nước</button>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" onclick="clearMeterFilters()">✕ Xóa lọc</button>
      </div>
    </div>

    <div class="table-wrapper">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Số đồng hồ</th>
              <th>Loại</th>
              <th>Hộ / Phòng</th>
              <th>Đơn vị</th>
              <th class="hide-md">Ngày lắp</th>
              <th>Trạng thái</th>
              ${isAdmin ? "<th>Thao tác</th>" : ""}
            </tr>
          </thead>
          <tbody id="m-tbody">${loadingRow(isAdmin ? 7 : 6)}</tbody>
        </table>
      </div>
      <div class="table-foot">
        <span id="meter-table-foot">Đang tải…</span>
        <span id="meter-split"></span>
      </div>
    </div>

    <div id="m-modal"></div>`;

  await loadMetersPage();
}

async function loadMetersPage() {
  const tbody = document.getElementById("m-tbody");
  if (!tbody) return;
  try {
    const [meters, households] = await Promise.all([
      Api.get("/api/meters"),
      Api.get("/api/households"),
    ]);
    _meterData = Array.isArray(meters) ? meters : [];
    _meterHouseholds = Array.isArray(households) ? households : [];

    const hhSel = document.getElementById("mf-hh");
    if (hhSel) {
      const current = _meterState.hh;
      hhSel.innerHTML = `<option value="">Tất cả hộ</option>` +
        _meterHouseholds.map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");
      hhSel.value = current;
    }
    renderMetersTable();
  } catch {
    tbody.innerHTML = emptyRow(Auth.isAdmin() ? 7 : 6, "🔌", "Không tải được danh sách đồng hồ", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải danh sách đồng hồ", "error");
  }
}

function meterHouseholdName(id) {
  return _meterHouseholds.find(h => h.id === id)?.name || `Hộ #${id}`;
}

function renderMetersTable() {
  const tbody = document.getElementById("m-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  const q = _meterState.q.trim().toLowerCase();

  const filtered = _meterData.filter(m => {
    if (_meterState.type && m.meter_type !== _meterState.type) return false;
    if (_meterState.hh && String(m.household_id) !== String(_meterState.hh)) return false;
    if (!q) return true;
    return String(m.meter_number || "").toLowerCase().includes(q)
      || meterHouseholdName(m.household_id).toLowerCase().includes(q);
  });

  if (!filtered.length) {
    tbody.innerHTML = emptyRow(
      isAdmin ? 7 : 6,
      "🔌",
      _meterData.length ? "Không tìm thấy đồng hồ phù hợp" : "Chưa có đồng hồ nào",
      _meterData.length ? "Thử từ khóa khác hoặc bỏ bộ lọc." : "Bấm “Thêm đồng hồ” để lắp đồng hồ mới."
    );
  } else {
    tbody.innerHTML = filtered.map(m => {
      const isElectricity = m.meter_type === "electricity";
      return `
      <tr>
        <td>
          <span class="cell-main">${escapeHtml(m.meter_number)}</span>
          <span class="cell-sub">ID #${m.id}</span>
        </td>
        <td><span class="badge ${isElectricity ? "badge-warning" : "badge-info"}">${isElectricity ? "⚡ Điện" : "💧 Nước"}</span></td>
        <td>${escapeHtml(meterHouseholdName(m.household_id))}</td>
        <td class="nowrap">${escapeHtml(m.unit)}</td>
        <td class="nowrap text-muted hide-md">${m.installed_at ? formatDateVN(m.installed_at) : "—"}</td>
        <td><span class="badge ${m.is_active ? "badge-success" : "badge-muted"}">${m.is_active ? "● Hoạt động" : "○ Ngừng"}</span></td>
        ${isAdmin ? `<td>
          <div class="row-actions">
            <button class="btn btn-secondary btn-sm" type="button" onclick="openMeterModal(${m.id})" title="Sửa đồng hồ" aria-label="Sửa ${escapeHtml(m.meter_number)}">✏️ Sửa</button>
            <button class="btn btn-danger btn-sm" type="button" onclick="deleteMeter(${m.id})" title="Xóa đồng hồ" aria-label="Xóa ${escapeHtml(m.meter_number)}">🗑️ Xóa</button>
          </div>
        </td>` : ""}
      </tr>`;
    }).join("");
  }

  const electricity = filtered.filter(m => m.meter_type === "electricity").length;
  const water = filtered.length - electricity;
  const foot = document.getElementById("meter-table-foot");
  if (foot) foot.innerHTML = `Hiển thị <strong>${filtered.length}</strong> / ${_meterData.length} đồng hồ`;
  const split = document.getElementById("meter-split");
  if (split) split.innerHTML = `⚡ ${electricity} điện · 💧 ${water} nước`;
}

function onMeterSearch(value) {
  _meterState.q = value;
  renderMetersTable();
}

function setMeterType(type) {
  _meterState.type = type;
  const index = type === "" ? 0 : type === "electricity" ? 1 : 2;
  document.querySelectorAll(".js-meter-type").forEach((btn, i) => btn.classList.toggle("active", i === index));
  renderMetersTable();
}

function setMeterHousehold(value) {
  _meterState.hh = value;
  renderMetersTable();
}

function clearMeterFilters() {
  _meterState = { type: "", hh: "", q: "" };
  const search = document.getElementById("meter-search");
  const hh = document.getElementById("mf-hh");
  if (search) search.value = "";
  if (hh) hh.value = "";
  document.querySelectorAll(".js-meter-type").forEach((btn, i) => btn.classList.toggle("active", i === 0));
  renderMetersTable();
}

function openMeterModal(idOrObject) {
  const m = typeof idOrObject === "object" && idOrObject
    ? idOrObject
    : _meterData.find(x => x.id === idOrObject) || null;
  const isEdit = !!m;

  const modal = document.getElementById("m-modal");
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" role="dialog" aria-modal="true" aria-label="${isEdit ? "Sửa đồng hồ" : "Thêm đồng hồ"}">
        <div class="modal-title">${isEdit ? "✏️ Sửa đồng hồ" : "➕ Thêm đồng hồ mới"}</div>
        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label class="form-label" for="m-hh">Hộ / Phòng ${isEdit ? "" : "*"}</label>
            <select id="m-hh" class="form-control" ${isEdit ? "disabled" : ""}></select>
            ${isEdit ? `<span class="form-hint">Không thể đổi hộ sau khi tạo đồng hồ.</span>` : ""}
          </div>
          <div class="form-group">
            <label class="form-label" for="m-type">Loại ${isEdit ? "" : "*"}</label>
            <select id="m-type" class="form-control" ${isEdit ? "disabled" : ""}>
              <option value="electricity" ${m?.meter_type === "electricity" ? "selected" : ""}>⚡ Điện</option>
              <option value="water" ${m?.meter_type === "water" ? "selected" : ""}>💧 Nước</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="m-number">Số đồng hồ *</label>
            <input id="m-number" class="form-control" value="${escapeHtml(m?.meter_number || "")}" placeholder="VD: EVN-2026-005">
          </div>
          <div class="form-group">
            <label class="form-label" for="m-unit">Đơn vị</label>
            <input id="m-unit" class="form-control" value="${escapeHtml(m?.unit || "kWh")}" placeholder="kWh / m³" ${isEdit ? "disabled" : ""}>
          </div>
          <div class="form-group">
            <label class="form-label" for="m-install">Ngày lắp đặt</label>
            <input id="m-install" class="form-control" type="date" value="${m?.installed_at ? String(m.installed_at).slice(0, 10) : ""}">
          </div>
          <div class="form-group">
            <label class="form-label" for="m-active">Trạng thái</label>
            <select id="m-active" class="form-control">
              <option value="true" ${m?.is_active !== false ? "selected" : ""}>Hoạt động</option>
              <option value="false" ${m?.is_active === false ? "selected" : ""}>Ngừng</option>
            </select>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="saveMeter(${m?.id || "null"})">💾 Lưu</button>
        </div>
      </div>
    </div>`;

  const sel = document.getElementById("m-hh");
  if (sel) {
    if (_meterHouseholds.length) {
      sel.innerHTML = _meterHouseholds.map(h =>
        `<option value="${h.id}" ${m?.household_id === h.id ? "selected" : ""}>${escapeHtml(h.name)}</option>`
      ).join("");
    } else {
      Api.get("/api/households").then(data => {
        _meterHouseholds = Array.isArray(data) ? data : [];
        sel.innerHTML = _meterHouseholds.map(h =>
          `<option value="${h.id}" ${m?.household_id === h.id ? "selected" : ""}>${escapeHtml(h.name)}</option>`
        ).join("");
      }).catch(() => {});
    }
  }
}

async function saveMeter(id) {
  const number = document.getElementById("m-number").value.trim();
  if (!number) { showToast("Nhập số đồng hồ", "warning"); return; }

  const body = {
    meter_number: number,
    installed_at: document.getElementById("m-install").value || null,
    is_active: document.getElementById("m-active").value === "true",
  };

  if (!id) {
    const householdId = parseInt(document.getElementById("m-hh").value);
    if (!householdId) { showToast("Chọn hộ/phòng cho đồng hồ", "warning"); return; }
    body.household_id = householdId;
    body.meter_type = document.getElementById("m-type").value;
    body.unit = document.getElementById("m-unit").value.trim() || "kWh";
  }

  try {
    if (id) await Api.put(`/api/meters/${id}`, body);
    else await Api.post("/api/meters", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast(id ? "Đã cập nhật đồng hồ" : "Đã thêm đồng hồ mới", "success");
    await loadMetersPage();
  } catch (e) { showToast(e.detail || "Lỗi lưu đồng hồ", "error"); }
}

async function deleteMeter(id) {
  const m = _meterData.find(x => x.id === id);
  if (!confirm(`Xóa đồng hồ "${m?.meter_number || id}"?`)) return;
  try {
    await Api.delete(`/api/meters/${id}`);
    showToast("Đã xóa đồng hồ", "success");
    await loadMetersPage();
  } catch (e) { showToast(e.detail || "Không thể xóa", "error"); }
}
