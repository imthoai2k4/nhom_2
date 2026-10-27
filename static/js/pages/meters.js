/** pages/meters.js — Quản lý Đồng hồ */
async function renderMeters() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="section-title" style="margin:0">Danh sách Đồng hồ</div>
      ${Auth.isAdmin() ? `<button class="btn btn-primary" onclick="openMeterModal()">➕ Thêm đồng hồ</button>` : ""}
    </div>
    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
      <select id="mf-hh" class="form-control" style="flex:1;min-width:150px" onchange="loadMetersList()">
        <option value="">Tất cả hộ</option>
      </select>
      <select id="mf-type" class="form-control" style="width:140px" onchange="loadMetersList()">
        <option value="">Tất cả loại</option>
        <option value="electricity">⚡ Điện</option>
        <option value="water">💧 Nước</option>
      </select>
    </div>
    <div class="table-wrapper">
      <table><thead><tr>
        <th>Số đồng hồ</th><th>Loại</th><th>Hộ/Phòng</th><th>Đơn vị</th><th>Ngày lắp</th><th>Thao tác</th>
      </tr></thead>
      <tbody id="m-tbody"><tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted)">Đang tải...</td></tr></tbody>
      </table>
    </div>
    <div id="m-modal"></div>`;

  // Load households into filter
  try {
    const hhs = await Api.get("/api/households");
    const sel = document.getElementById("mf-hh");
    sel.innerHTML = `<option value="">Tất cả hộ</option>` + hhs.map(h => `<option value="${h.id}">${h.name}</option>`).join("");
  } catch {}
  loadMetersList();
}

async function loadMetersList() {
  const hhId = document.getElementById("mf-hh")?.value || "";
  const type = document.getElementById("mf-type")?.value || "";
  let url = "/api/meters?";
  if (hhId) url += `household_id=${hhId}&`;
  if (type) url += `meter_type=${type}`;
  try {
    const data = await Api.get(url);
    const tbody = document.getElementById("m-tbody");
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;padding:24px;color:var(--text-muted)">Chưa có đồng hồ nào</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(m => `<tr>
      <td><strong>${m.meter_number}</strong></td>
      <td><span class="badge ${m.meter_type === 'electricity' ? 'badge-warning' : 'badge-info'}">${m.meter_type === 'electricity' ? '⚡ Điện' : '💧 Nước'}</span></td>
      <td>HH #${m.household_id}</td>
      <td>${m.unit}</td>
      <td style="font-size:0.82rem;color:var(--text-secondary)">${m.installed_at ? m.installed_at.slice(0,10) : "—"}</td>
      <td style="display:flex;gap:6px">
        ${Auth.isAdmin() ? `<button class="btn btn-secondary btn-sm" onclick='openMeterModal(${JSON.stringify(m).replace(/'/g,"&#39;")})'>✏️</button>
        <button class="btn btn-danger btn-sm" onclick="deleteMeter(${m.id},'${m.meter_number}')">🗑️</button>` : ""}
      </td>
    </tr>`).join("");
  } catch { showToast("Lỗi tải danh sách đồng hồ", "error"); }
}

function openMeterModal(m = null) {
  const modal = document.getElementById("m-modal");
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal">
        <div class="modal-title">${m ? "Sửa đồng hồ" : "Thêm đồng hồ mới"}</div>
        <div class="form-grid form-grid-2" style="gap:12px">
          <div class="form-group"><label class="form-label">Hộ/Phòng *</label>
            <select id="m-hh" class="form-control"></select></div>
          <div class="form-group"><label class="form-label">Loại *</label>
            <select id="m-type" class="form-control">
              <option value="electricity" ${m?.meter_type==='electricity'?'selected':''}>⚡ Điện</option>
              <option value="water" ${m?.meter_type==='water'?'selected':''}>💧 Nước</option>
            </select></div>
          <div class="form-group"><label class="form-label">Số đồng hồ *</label>
            <input id="m-number" class="form-control" value="${m?.meter_number||''}" placeholder="EL-001"></div>
          <div class="form-group"><label class="form-label">Đơn vị</label>
            <input id="m-unit" class="form-control" value="${m?.unit||'kWh'}" placeholder="kWh / m³"></div>
          <div class="form-group"><label class="form-label">Ngày lắp đặt</label>
            <input id="m-install" class="form-control" type="date" value="${m?.installed_at?.slice(0,10)||''}"></div>
          <div class="form-group"><label class="form-label">Trạng thái</label>
            <select id="m-active" class="form-control">
              <option value="true" ${m?.is_active!==false?'selected':''}>Hoạt động</option>
              <option value="false" ${m?.is_active===false?'selected':''}>Ngừng</option>
            </select></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="saveMeter(${m?.id||'null'})">💾 Lưu</button>
        </div>
      </div>
    </div>`;

  // Load households into modal select
  Api.get("/api/households").then(data => {
    const sel = document.getElementById("m-hh");
    sel.innerHTML = data.map(h => `<option value="${h.id}" ${m?.household_id===h.id?'selected':''}>${h.name}</option>`).join("");
  });
}

async function saveMeter(id) {
  const body = {
    household_id: parseInt(document.getElementById("m-hh").value),
    meter_type: document.getElementById("m-type").value,
    meter_number: document.getElementById("m-number").value.trim(),
    unit: document.getElementById("m-unit").value.trim() || "kWh",
    installed_at: document.getElementById("m-install").value || null,
    is_active: document.getElementById("m-active").value === "true",
  };
  if (!body.meter_number) { showToast("Nhập số đồng hồ", "warning"); return; }
  try {
    if (id) await Api.put(`/api/meters/${id}`, body);
    else await Api.post("/api/meters", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast(id ? "Đã cập nhật đồng hồ" : "Đã thêm đồng hồ mới", "success");
    loadMetersList();
  } catch (e) { showToast(e.detail || "Lỗi lưu đồng hồ", "error"); }
}

async function deleteMeter(id, number) {
  if (!confirm(`Xóa đồng hồ "${number}"?`)) return;
  try {
    await Api.delete(`/api/meters/${id}`);
    showToast("Đã xóa đồng hồ", "success");
    loadMetersList();
  } catch (e) { showToast(e.detail || "Không thể xóa", "error"); }
}
