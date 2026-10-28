/** pages/prices.js — Quản lý Đơn giá */
let _currentPriceTab = "electricity";

async function renderPrices() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">Bảng đơn giá</h2>
        <p class="page-head-sub">Đơn giá điện và nước tính theo bậc lũy tiến, áp dụng theo khoảng thời gian.</p>
      </div>
      <div class="page-head-actions">
        ${isAdmin ? `<button class="btn btn-primary" type="button" onclick="openPriceModal()">➕ Thêm đơn giá</button>` : ""}
      </div>
    </div>

    <div class="toolbar">
      <div class="segmented" role="group" aria-label="Chọn loại đơn giá">
        <button type="button" class="price-tab ${_currentPriceTab === "electricity" ? "active" : ""}" id="tab-electricity" onclick="switchPriceTab('electricity')">⚡ Điện</button>
        <button type="button" class="price-tab ${_currentPriceTab === "water" ? "active" : ""}" id="tab-water" onclick="switchPriceTab('water')">💧 Nước</button>
      </div>
      <span class="text-muted" style="font-size:0.75rem" id="price-note"></span>
    </div>

    <div class="table-wrapper">
      <div class="table-header">
        <div>
          <div class="table-title" id="price-table-title">⚡ Biểu giá điện</div>
          <div class="panel-sub">Bậc càng cao, đơn giá áp dụng cho phần vượt định mức càng lớn</div>
        </div>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Bậc</th>
              <th class="num">Từ</th>
              <th class="num">Đến</th>
              <th class="num">Đơn giá</th>
              <th>Áp dụng từ</th>
              <th>Đến ngày</th>
              <th>Trạng thái</th>
              ${isAdmin ? "<th>Thao tác</th>" : ""}
            </tr>
          </thead>
          <tbody id="pr-tbody">${loadingRow(isAdmin ? 8 : 7)}</tbody>
        </table>
      </div>
      <div class="table-foot">
        <span id="price-table-foot">Đang tải…</span>
        <span>Đơn giá tính bằng đồng trên kWh hoặc m³</span>
      </div>
    </div>

    <div id="pr-modal"></div>`;

  await loadPricesTable(_currentPriceTab);
}

function switchPriceTab(type) {
  _currentPriceTab = type;
  document.querySelectorAll(".price-tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`tab-${type}`)?.classList.add("active");

  const title = document.getElementById("price-table-title");
  if (title) title.textContent = type === "electricity" ? "⚡ Biểu giá điện" : "💧 Biểu giá nước";
  loadPricesTable(type);
}

async function loadPricesTable(type) {
  const tbody = document.getElementById("pr-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();

  try {
    const data = await Api.get(`/api/prices?meter_type=${type}&active_only=false`);
    const rows = Array.isArray(data) ? data : [];
    const unit = type === "electricity" ? "kWh" : "m³";

    if (!rows.length) {
      tbody.innerHTML = emptyRow(isAdmin ? 8 : 7, "💰", "Chưa có đơn giá", "Thêm đơn giá đầu tiên để có thể tạo hóa đơn.");
    } else {
      tbody.innerHTML = rows.map(p => {
        const isActive = !p.effective_to || new Date(p.effective_to) >= new Date(new Date().toDateString());
        return `
          <tr style="${!isActive ? "opacity:0.55" : ""}">
            <td><span class="badge badge-info">Bậc ${p.tier}</span></td>
            <td class="num">${fmtNumber(p.min_unit, 0)}</td>
            <td class="num">${p.max_unit != null ? fmtNumber(p.max_unit, 0) : `<span class="text-muted">∞</span>`}</td>
            <td class="num"><strong>${fmtMoney(p.price_per_unit, " đ/" + unit)}</strong></td>
            <td class="nowrap text-muted">${formatDateVN(p.effective_from)}</td>
            <td class="nowrap text-muted">${p.effective_to ? formatDateVN(p.effective_to) : "—"}</td>
            <td><span class="badge ${isActive ? "badge-success" : "badge-muted"}">${isActive ? "● Đang áp dụng" : "○ Đã đóng"}</span></td>
            ${isAdmin ? `<td>
              <div class="row-actions">
                ${isActive
                  ? `<button class="btn btn-secondary btn-sm" type="button" onclick="closePriceModal(${p.id})">🔒 Đóng</button>`
                  : `<span class="text-muted" style="font-size:0.74rem">Không còn hiệu lực</span>`}
              </div>
            </td>` : ""}
          </tr>`;
      }).join("");
    }

    const activeCount = rows.filter(p => !p.effective_to || new Date(p.effective_to) >= new Date(new Date().toDateString())).length;
    const foot = document.getElementById("price-table-foot");
    if (foot) foot.innerHTML = `Hiển thị <strong>${rows.length}</strong> bậc giá · ${activeCount} đang áp dụng`;
    const note = document.getElementById("price-note");
    if (note) note.textContent = `${rows.length} bậc · đơn vị ${unit}`;
  } catch {
    tbody.innerHTML = emptyRow(isAdmin ? 8 : 7, "💰", "Không tải được bảng đơn giá", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải đơn giá", "error");
  }
}

function openPriceModal() {
  document.getElementById("pr-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Thêm đơn giá">
        <div class="modal-title">➕ Thêm đơn giá mới</div>
        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label class="form-label" for="np-type">Loại *</label>
            <select id="np-type" class="form-control">
              <option value="electricity" ${_currentPriceTab === "electricity" ? "selected" : ""}>⚡ Điện</option>
              <option value="water" ${_currentPriceTab === "water" ? "selected" : ""}>💧 Nước</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label" for="np-tier">Bậc *</label>
            <input id="np-tier" class="form-control" type="number" min="1" value="1">
          </div>
          <div class="form-group">
            <label class="form-label" for="np-start">Từ (kWh/m³)</label>
            <input id="np-start" class="form-control" type="number" step="0.01" value="0">
          </div>
          <div class="form-group">
            <label class="form-label" for="np-end">Đến (kWh/m³)</label>
            <input id="np-end" class="form-control" type="number" step="0.01" placeholder="Để trống = không giới hạn">
          </div>
          <div class="form-group">
            <label class="form-label" for="np-price">Đơn giá (đ) *</label>
            <input id="np-price" class="form-control" type="number" min="0" placeholder="VD: 1728">
          </div>
          <div class="form-group">
            <label class="form-label" for="np-from">Áp dụng từ *</label>
            <input id="np-from" class="form-control" type="date" value="${new Date().toISOString().slice(0, 10)}">
          </div>
        </div>
        <div class="form-hint" style="margin-top:10px">Đơn giá mới sẽ được dùng khi tạo hóa đơn có kỳ nằm trong khoảng hiệu lực.</div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="saveNewPrice()">💾 Lưu</button>
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
  if (!body.effective_from) { showToast("Chọn ngày áp dụng", "warning"); return; }
  if (!body.price_per_unit) { showToast("Nhập đơn giá", "warning"); return; }
  try {
    await Api.post("/api/prices", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast("Đã thêm đơn giá mới", "success");
    _currentPriceTab = body.meter_type;
    document.querySelectorAll(".price-tab").forEach(t => t.classList.remove("active"));
    document.getElementById(`tab-${body.meter_type}`)?.classList.add("active");
    document.getElementById("price-table-title").textContent =
      body.meter_type === "electricity" ? "⚡ Biểu giá điện" : "💧 Biểu giá nước";
    await loadPricesTable(_currentPriceTab);
  } catch (e) { showToast(e.detail || "Lỗi thêm đơn giá", "error"); }
}

function closePriceModal(priceId) {
  document.getElementById("pr-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" style="max-width:380px" role="dialog" aria-modal="true" aria-label="Đóng đơn giá">
        <div class="modal-title">🔒 Đóng đơn giá</div>
        <div class="form-group">
          <label class="form-label" for="cp-date">Ngày kết thúc *</label>
          <input id="cp-date" class="form-control" type="date" value="${new Date().toISOString().slice(0, 10)}">
        </div>
        <div class="form-hint" style="margin-top:8px">Đơn giá sẽ không được áp dụng cho các kỳ sau ngày này.</div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="closePrice(${priceId})">✅ Xác nhận</button>
        </div>
      </div>
    </div>`;
}

async function closePrice(priceId) {
  const d = document.getElementById("cp-date").value;
  if (!d) { showToast("Chọn ngày kết thúc", "warning"); return; }
  try {
    await Api.put(`/api/prices/${priceId}?effective_to=${encodeURIComponent(d)}`, {});
    document.querySelector(".modal-overlay")?.remove();
    showToast("Đã đóng đơn giá", "success");
    await loadPricesTable(_currentPriceTab);
  } catch (e) { showToast(e.detail || "Lỗi đóng đơn giá", "error"); }
}
