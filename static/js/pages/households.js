/** pages/households.js — Quản lý Hộ/Phòng */
let _hhData = [];
let _hhState = { status: "", q: "" };

async function renderHouseholds() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">Danh sách Hộ / Phòng</h2>
        <p class="page-head-sub">Quản lý thông tin hộ gia đình, chủ hộ và trạng thái hoạt động.</p>
      </div>
      <div class="page-head-actions">
        ${isAdmin ? `<button class="btn btn-primary" type="button" onclick="openHouseholdModal()">➕ Thêm hộ / phòng</button>` : ""}
      </div>
    </div>

    <div class="toolbar">
      <div class="search-field">
        <span class="search-icon" aria-hidden="true">🔎</span>
        <input id="hh-search" class="form-control" placeholder="Tìm theo tên, chủ hộ, SĐT, địa chỉ…"
          value="${escapeHtml(_hhState.q)}" oninput="onHouseholdSearch(this.value)" aria-label="Tìm hộ/phòng">
      </div>
      <div class="segmented" id="hh-status-filter" role="group" aria-label="Lọc theo trạng thái">
        <button type="button" class="js-hh-status ${_hhState.status === "" ? "active" : ""}" onclick="setHouseholdStatus('')">
          Tất cả <span class="count" id="hh-count-all">–</span>
        </button>
        <button type="button" class="js-hh-status ${_hhState.status === "active" ? "active" : ""}" onclick="setHouseholdStatus('active')">
          Hoạt động <span class="count" id="hh-count-active">–</span>
        </button>
        <button type="button" class="js-hh-status ${_hhState.status === "inactive" ? "active" : ""}" onclick="setHouseholdStatus('inactive')">
          Ngừng <span class="count" id="hh-count-inactive">–</span>
        </button>
      </div>
    </div>

    <div class="table-wrapper">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Hộ / Phòng</th>
              <th>Chủ hộ</th>
              <th>Số điện thoại</th>
              <th>Trạng thái</th>
              ${isAdmin ? "<th>Thao tác</th>" : ""}
            </tr>
          </thead>
          <tbody id="hh-tbody">${loadingRow(isAdmin ? 5 : 4)}</tbody>
        </table>
      </div>
      <div class="table-foot">
        <span id="hh-table-foot">Đang tải…</span>
        <span>Dữ liệu cập nhật theo thời gian thực</span>
      </div>
    </div>

    <div id="hh-modal"></div>`;

  await refreshHouseholds();
}

async function refreshHouseholds() {
  const tbody = document.getElementById("hh-tbody");
  if (!tbody) return;
  try {
    const data = await Api.get("/api/households");
    _hhData = Array.isArray(data) ? data : [];
    renderHouseholdsTable();
  } catch {
    tbody.innerHTML = emptyRow(Auth.isAdmin() ? 5 : 4, "🔌", "Không tải được danh sách hộ", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải danh sách hộ", "error");
  }
}

function filterHouseholds() {
  const q = _hhState.q.trim().toLowerCase();
  return _hhData.filter(h => {
    if (_hhState.status && h.status !== _hhState.status) return false;
    if (!q) return true;
    return [h.name, h.owner_name, h.phone, h.address]
      .some(v => String(v || "").toLowerCase().includes(q));
  });
}

function renderHouseholdsTable() {
  const tbody = document.getElementById("hh-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  const filtered = filterHouseholds();

  // Cập nhật số lượng trên bộ lọc
  const counts = {
    all: _hhData.length,
    active: _hhData.filter(h => h.status === "active").length,
    inactive: _hhData.filter(h => h.status === "inactive").length,
  };
  const countAll = document.getElementById("hh-count-all");
  if (countAll) {
    countAll.textContent = counts.all;
    document.getElementById("hh-count-active").textContent = counts.active;
    document.getElementById("hh-count-inactive").textContent = counts.inactive;
  }

  if (!filtered.length) {
    tbody.innerHTML = emptyRow(
      isAdmin ? 5 : 4,
      "🏠",
      _hhData.length ? "Không tìm thấy hộ phù hợp" : "Chưa có hộ nào",
      _hhData.length ? "Thử từ khóa khác hoặc bỏ bộ lọc." : "Bấm “Thêm hộ / phòng” để bắt đầu."
    );
  } else {
    tbody.innerHTML = filtered.map(h => `
      <tr>
        <td>
          <div class="cell-user">
            <span class="avatar" aria-hidden="true">${escapeHtml(initials(h.name))}</span>
            <div>
              <span class="cell-main">${escapeHtml(h.name)}</span>
              <span class="cell-sub">${escapeHtml(h.address || "Chưa cập nhật địa chỉ")}</span>
            </div>
          </div>
        </td>
        <td>${escapeHtml(h.owner_name || "—")}</td>
        <td class="nowrap">${escapeHtml(h.phone || "—")}</td>
        <td>
          <span class="badge ${h.status === "active" ? "badge-success" : "badge-muted"}">
            ${h.status === "active" ? "● Hoạt động" : "○ Ngừng"}
          </span>
        </td>
        ${isAdmin ? `<td>
          <div class="row-actions">
            <button class="btn btn-secondary btn-sm" type="button" onclick="openHouseholdModal(${h.id})" title="Sửa hộ" aria-label="Sửa ${escapeHtml(h.name)}">✏️ Sửa</button>
            <button class="btn btn-danger btn-sm" type="button" onclick="deleteHousehold(${h.id})" title="Xóa hộ" aria-label="Xóa ${escapeHtml(h.name)}">🗑️ Xóa</button>
          </div>
        </td>` : ""}
      </tr>`).join("");
  }

  const foot = document.getElementById("hh-table-foot");
  if (foot) {
    foot.innerHTML = `Hiển thị <strong>${filtered.length}</strong> / ${_hhData.length} hộ`;
  }
}

function onHouseholdSearch(value) {
  _hhState.q = value;
  renderHouseholdsTable();
}

function setHouseholdStatus(status) {
  _hhState.status = status;
  document.querySelectorAll(".js-hh-status").forEach(btn => btn.classList.remove("active"));
  const index = status === "" ? 0 : status === "active" ? 1 : 2;
  document.querySelectorAll(".js-hh-status")[index]?.classList.add("active");
  renderHouseholdsTable();
}

function openHouseholdModal(idOrObject) {
  const h = typeof idOrObject === "object" && idOrObject
    ? idOrObject
    : _hhData.find(x => x.id === idOrObject) || null;

  const modal = document.getElementById("hh-modal");
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" role="dialog" aria-modal="true" aria-label="${h ? "Sửa hộ/phòng" : "Thêm hộ/phòng"}">
        <div class="modal-title">${h ? "✏️ Sửa hộ / phòng" : "➕ Thêm hộ / phòng mới"}</div>
        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label class="form-label" for="hh-name">Tên phòng *</label>
            <input id="hh-name" class="form-control" value="${escapeHtml(h?.name || "")}" placeholder="VD: Phòng 101" autofocus>
          </div>
          <div class="form-group">
            <label class="form-label" for="hh-owner">Chủ hộ</label>
            <input id="hh-owner" class="form-control" value="${escapeHtml(h?.owner_name || "")}" placeholder="VD: Nguyễn Văn A">
          </div>
          <div class="form-group">
            <label class="form-label" for="hh-phone">Số điện thoại</label>
            <input id="hh-phone" class="form-control" value="${escapeHtml(h?.phone || "")}" placeholder="09xxxxxxxx">
          </div>
          <div class="form-group">
            <label class="form-label" for="hh-status">Trạng thái</label>
            <select id="hh-status" class="form-control">
              <option value="active" ${h?.status === "active" ? "selected" : ""}>Hoạt động</option>
              <option value="inactive" ${h?.status === "inactive" ? "selected" : ""}>Ngừng</option>
            </select>
          </div>
          <div class="form-group" style="grid-column:1/-1">
            <label class="form-label" for="hh-addr">Địa chỉ</label>
            <input id="hh-addr" class="form-control" value="${escapeHtml(h?.address || "")}" placeholder="Số 12 Nguyễn Trãi, Q.1…">
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="saveHousehold(${h?.id || "null"})">💾 Lưu</button>
        </div>
      </div>
    </div>`;

  setTimeout(() => document.getElementById("hh-name")?.focus(), 50);
}

async function saveHousehold(id) {
  const body = {
    name: document.getElementById("hh-name").value.trim(),
    owner_name: document.getElementById("hh-owner").value.trim() || null,
    phone: document.getElementById("hh-phone").value.trim() || null,
    address: document.getElementById("hh-addr").value.trim() || null,
    status: document.getElementById("hh-status").value,
  };
  if (!body.name) { showToast("Vui lòng nhập tên hộ/phòng", "warning"); return; }
  try {
    if (id) await Api.put(`/api/households/${id}`, body);
    else await Api.post("/api/households", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast(id ? "Đã cập nhật hộ" : "Đã thêm hộ mới", "success");
    await refreshHouseholds();
  } catch (e) { showToast(e.detail || "Lỗi lưu dữ liệu", "error"); }
}

async function deleteHousehold(id) {
  const h = _hhData.find(x => x.id === id);
  if (!confirm(`Xóa hộ "${h?.name || id}"?`)) return;
  try {
    await Api.delete(`/api/households/${id}`);
    showToast("Đã xóa hộ", "success");
    await refreshHouseholds();
  } catch (e) { showToast(e.detail || "Không thể xóa", "error"); }
}
