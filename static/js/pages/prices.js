/** pages/prices.js — Quản lý Đơn giá */
async function renderPrices() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
      <div class="section-title" style="margin:0">Bảng Đơn giá</div>
      ${Auth.isAdmin() ? `<button class="btn btn-primary" onclick="openPriceModal()">➕ Thêm đơn giá</button>` : ""}
    </div>
    <div style="display:flex;gap:8px;margin-bottom:16px">
      <button class="btn btn-secondary price-tab active" id="tab-electricity" onclick="switchPriceTab('electricity')">⚡ Điện</button>
      <button class="btn btn-secondary price-tab" id="tab-water" onclick="switchPriceTab('water')">💧 Nước</button>
    </div>
    <div class="table-wrapper">
      <table><thead><tr>
        <th>Bậc</th><th>Từ</th><th>Đến</th><th>Đơn giá (đ)</th><th>Áp dụng từ</th><th>Đến ngày</th>
        ${Auth.isAdmin() ? '<th>Thao tác</th>' : ''}
      </tr></thead>
      <tbody id="pr-tbody"><tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-muted)">Đang tải...</td></tr></tbody>
      </table>
    </div>
    <div id="pr-modal"></div>`;

  loadPricesTable("electricity");
}

let _currentPriceTab = "electricity";

function switchPriceTab(type) {
  _currentPriceTab = type;
  document.querySelectorAll(".price-tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`tab-${type}`)?.classList.add("active");
  loadPricesTable(type);
}

async function loadPricesTable(type) {
  try {
    const data = await Api.get(`/api/prices?meter_type=${type}&active_only=false`);
    const tbody = document.getElementById("pr-tbody");
    if (!data.length) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:24px;color:var(--text-muted)">Chưa có đơn giá</td></tr>`;
      return;
    }
    tbody.innerHTML = data.map(p => {
      const isActive = !p.effective_to || new Date(p.effective_to) >= new Date();
      return `<tr style="${!isActive ? 'opacity:0.5' : ''}">
        <td><span class="badge badge-info">Bậc ${p.tier}</span></td>
        <td>${p.min_unit != null ? parseFloat(p.min_unit).toLocaleString() : '0'}</td>
        <td>${p.max_unit != null ? parseFloat(p.max_unit).toLocaleString() : '∞'}</td>
        <td><strong>${p.price_per_unit.toLocaleString()}</strong></td>
        <td style="font-size:0.82rem">${p.effective_from}</td>
        <td style="font-size:0.82rem">${p.effective_to || '<span style="color:var(--accent-green)">Đang áp dụng</span>'}</td>
        ${Auth.isAdmin() ? `<td>${isActive ? `<button class="btn btn-secondary btn-sm" onclick="closePriceModal(${p.id})">🔒 Đóng</button>` : '<span style="color:var(--text-muted);font-size:0.8rem">Đã đóng</span>'}</td>` : ''}
      </tr>`;
    }).join("");
  } catch { showToast("Lỗi tải đơn giá", "error"); }
}

function openPriceModal() {
  document.getElementById("pr-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal">
        <div class="modal-title">Thêm đơn giá mới</div>
        <div class="form-grid form-grid-2" style="gap:12px">
          <div class="form-group"><label class="form-label">Loại *</label>
            <select id="np-type" class="form-control">
              <option value="electricity">⚡ Điện</option>
              <option value="water">💧 Nước</option>
            </select></div>
          <div class="form-group"><label class="form-label">Bậc *</label>
            <input id="np-tier" class="form-control" type="number" min="1" value="1"></div>
          <div class="form-group"><label class="form-label">Từ (kWh/m³)</label>
            <input id="np-start" class="form-control" type="number" step="0.01" value="0"></div>
          <div class="form-group"><label class="form-label">Đến (kWh/m³)</label>
            <input id="np-end" class="form-control" type="number" step="0.01" placeholder="Để trống = ∞"></div>
          <div class="form-group"><label class="form-label">Đơn giá (đ) *</label>
            <input id="np-price" class="form-control" type="number" min="0"></div>
          <div class="form-group"><label class="form-label">Áp dụng từ *</label>
            <input id="np-from" class="form-control" type="date"></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="saveNewPrice()">💾 Lưu</button>
        </div>
      </div>
    </div>`;
}

async function saveNewPrice() {
  const body = {
    meter_type: document.getElementById("np-type").value,
    tier: parseInt(document.getElementById("np-tier").value),
    min_unit: parseFloat(document.getElementById("np-start").value) || 0,
    max_unit: document.getElementById("np-end").value ? parseFloat(document.getElementById("np-end").value) : null,
    price_per_unit: parseInt(document.getElementById("np-price").value),
    effective_from: document.getElementById("np-from").value,
  };
  if (!body.effective_from) { showToast("Nhập ngày áp dụng", "warning"); return; }
  if (!body.price_per_unit) { showToast("Nhập đơn giá", "warning"); return; }
  try {
    await Api.post("/api/prices", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast("Đã thêm đơn giá mới", "success");
    loadPricesTable(_currentPriceTab);
  } catch (e) { showToast(e.detail || "Lỗi thêm đơn giá", "error"); }
}

function closePriceModal(priceId) {
  document.getElementById("pr-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" style="max-width:360px">
        <div class="modal-title">🔒 Đóng đơn giá</div>
        <div class="form-group">
          <label class="form-label">Ngày kết thúc *</label>
          <input id="cp-date" class="form-control" type="date">
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="closePrice(${priceId})">✅ Xác nhận</button>
        </div>
      </div>
    </div>`;
}

async function closePrice(priceId) {
  const d = document.getElementById("cp-date").value;
  if (!d) { showToast("Nhập ngày kết thúc", "warning"); return; }
  try {
    await Api.put(`/api/prices/${priceId}?effective_to=${d}`, {});
    document.querySelector(".modal-overlay")?.remove();
    showToast("Đã đóng đơn giá", "success");
    loadPricesTable(_currentPriceTab);
  } catch (e) { showToast(e.detail || "Lỗi", "error"); }
}
