/** pages/households.js — Quản lý Hộ/Phòng */
async function renderHouseholds() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="section-title" style="margin:0">Danh sách Hộ/Phòng</div>
      ${Auth.isAdmin() ? `<button class="btn btn-primary" onclick="openHouseholdModal()">➕ Thêm hộ</button>` : ""}
    </div>
    <div style="display:flex;gap:8px;margin-bottom:16px">
      <select id="filter-status" class="form-control" style="width:160px" onchange="renderHouseholds()">
        <option value="">Tất cả</option><option value="active">Đang hoạt động</option><option value="inactive">Ngừng</option>
      </select>
    </div>
    <div class="table-wrapper">
      <table><thead><tr>
        <th>Tên</th><th>Chủ hộ</th><th>SĐT</th><th>Trạng thái</th><th>Thao tác</th>
      </tr></thead>
      <tbody id="hh-tbody"><tr><td colspan="5" style="text-align:center;padding:24px;color:var(--text-muted)">Đang tải...</td></tr></tbody>
      </table>
    </div>
    <div id="hh-modal"></div>`;

  const status = document.getElementById("filter-status")?.value || "";
  try {
    const data = await Api.get(`/api/households${status ? `?status=${status}` : ""}`);
    const tbody = document.getElementById("hh-tbody");
    if (!data.length) { tbody.innerHTML = `<tr><td colspan="5" class="empty-state-text" style="padding:24px;text-align:center">Chưa có hộ nào</td></tr>`; return; }
    tbody.innerHTML = data.map(h => `
      <tr>
        <td><strong>${h.name}</strong><br><small style="color:var(--text-muted)">${h.address || ""}</small></td>
        <td>${h.owner_name || "—"}</td>
        <td>${h.phone || "—"}</td>
        <td><span class="badge ${h.status === "active" ? "badge-success" : "badge-info"}">${h.status === "active" ? "Hoạt động" : "Ngừng"}</span></td>
        <td style="display:flex;gap:6px">
          ${Auth.isAdmin() ? `<button class="btn btn-secondary btn-sm" onclick="openHouseholdModal(${JSON.stringify(h).replace(/"/g,"&quot;")})">✏️</button>
          <button class="btn btn-danger btn-sm" onclick="deleteHousehold(${h.id},'${h.name}')">🗑️</button>` : ""}
        </td>
      </tr>`).join("");
  } catch { showToast("Lỗi tải danh sách hộ", "error"); }
}

function openHouseholdModal(h = null) {
  const modal = document.getElementById("hh-modal");
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal">
        <div class="modal-title">${h ? "Sửa hộ/phòng" : "Thêm hộ/phòng mới"}</div>
        <div class="form-grid form-grid-2" style="gap:12px">
          <div class="form-group"><label class="form-label">Tên phòng *</label>
            <input id="hh-name" class="form-control" value="${h?.name||""}" placeholder="Phòng 101"></div>
          <div class="form-group"><label class="form-label">Chủ hộ</label>
            <input id="hh-owner" class="form-control" value="${h?.owner_name||""}" placeholder="Nguyễn Văn A"></div>
          <div class="form-group"><label class="form-label">SĐT</label>
            <input id="hh-phone" class="form-control" value="${h?.phone||""}" placeholder="09xxxxxxxx"></div>
          <div class="form-group"><label class="form-label">Trạng thái</label>
            <select id="hh-status" class="form-control">
              <option value="active" ${h?.status==="active"?"selected":""}>Hoạt động</option>
              <option value="inactive" ${h?.status==="inactive"?"selected":""}>Ngừng</option>
            </select></div>
          <div class="form-group" style="grid-column:1/-1"><label class="form-label">Địa chỉ</label>
            <input id="hh-addr" class="form-control" value="${h?.address||""}" placeholder="Số 12 Nguyễn Trãi..."></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="saveHousehold(${h?.id||"null"})">💾 Lưu</button>
        </div>
      </div>
    </div>`;
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
    renderHouseholds();
  } catch (e) { showToast(e.detail || "Lỗi lưu dữ liệu", "error"); }
}

async function deleteHousehold(id, name) {
  if (!confirm(`Xóa hộ "${name}"?`)) return;
  try {
    await Api.delete(`/api/households/${id}`);
    showToast("Đã xóa hộ", "success");
    renderHouseholds();
  } catch (e) { showToast(e.detail || "Không thể xóa", "error"); }
}
