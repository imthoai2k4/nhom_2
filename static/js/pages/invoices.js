/** pages/invoices.js — Hóa đơn */
let _invoiceList = [];
let _invoiceHouseholds = [];
let _invoicePayments = [];
let _invoiceState = { status: "", hh: "", period: "", q: "" };

async function renderInvoices() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();
  const colCount = isAdmin ? 8 : 7;

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">${isAdmin ? "Hóa đơn" : "Hóa đơn của tôi"}</h2>
        <p class="page-head-sub">${isAdmin
          ? "Tạo hóa đơn theo kỳ từ chỉ số đã nhập và theo dõi tình trạng thanh toán."
          : "Tra cứu hóa đơn điện nước của hộ theo kỳ và tình trạng thanh toán."}</p>
      </div>
      <div class="page-head-actions">
        ${isAdmin ? `
          <button class="btn btn-primary" type="button" onclick="openGenModal()">➕ Tạo hóa đơn</button>
          <button class="btn btn-secondary" type="button" onclick="openGenAllModal()">📋 Tạo tất cả</button>` : ""}
      </div>
    </div>

    <div class="summary-chips" id="invoice-summary"></div>

    <div class="toolbar">
      ${isAdmin ? `
      <div class="search-field">
        <span class="search-icon" aria-hidden="true">🔎</span>
        <input id="if-search" class="form-control" placeholder="Tìm theo tên hộ / phòng…"
          value="${escapeHtml(_invoiceState.q)}" oninput="onInvoiceSearch(this.value)" aria-label="Tìm hóa đơn">
      </div>` : ""}
      <div class="toolbar-group">
        ${isAdmin ? `
        <label class="filter-label" for="if-hh">Hộ</label>
        <select id="if-hh" class="form-control" style="width:170px" onchange="setInvoiceHousehold(this.value)" aria-label="Lọc theo hộ">
          <option value="">Tất cả hộ</option>
        </select>` : ""}
        <label class="filter-label" for="if-period">Kỳ</label>
        <input id="if-period" class="form-control" type="month" style="width:160px"
          value="${escapeHtml(_invoiceState.period)}" onchange="setInvoicePeriod(this.value)" aria-label="Lọc theo kỳ">
        <button class="btn btn-ghost btn-sm" type="button" onclick="clearInvoiceFilters()">✕ Xóa lọc</button>
      </div>
    </div>

    <div class="toolbar" style="margin-top:-6px">
      <div class="segmented" role="group" aria-label="Lọc theo trạng thái">
        <button type="button" class="js-inv-status ${_invoiceState.status === "" ? "active" : ""}" onclick="setInvoiceStatus('')">Tất cả <span class="count" id="inv-count-all">–</span></button>
        <button type="button" class="js-inv-status ${_invoiceState.status === "unpaid" ? "active" : ""}" onclick="setInvoiceStatus('unpaid')">Chưa TT <span class="count" id="inv-count-unpaid">–</span></button>
        <button type="button" class="js-inv-status ${_invoiceState.status === "partial" ? "active" : ""}" onclick="setInvoiceStatus('partial')">Một phần <span class="count" id="inv-count-partial">–</span></button>
        <button type="button" class="js-inv-status ${_invoiceState.status === "paid" ? "active" : ""}" onclick="setInvoiceStatus('paid')">Đã TT <span class="count" id="inv-count-paid">–</span></button>
      </div>
      <span class="text-muted" id="invoice-total" style="font-size:0.75rem"></span>
    </div>

    <div class="table-wrapper">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              ${isAdmin ? "<th>Hộ / Phòng</th>" : ""}
              <th>Kỳ</th>
              <th class="num hide-md">Điện</th>
              <th class="num hide-md">Nước</th>
              <th class="num">Tổng tiền</th>
              <th>Trạng thái</th>
              <th>Hạn TT</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="inv-tbody">${loadingRow(colCount)}</tbody>
        </table>
      </div>
      <div class="table-foot">
        <span id="invoice-table-foot">Đang tải…</span>
        <span>Đơn vị: đồng (đ)</span>
      </div>
    </div>

    <div id="inv-modal"></div>`;

  await loadInvoicesPage();
}

async function loadInvoicesPage() {
  const tbody = document.getElementById("inv-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  try {
    const [invoices, households, payments] = await Promise.all([
      Api.get("/api/invoices"),
      Api.get("/api/households"),
      Api.get("/api/payments"),
    ]);
    _invoiceList = Array.isArray(invoices) ? invoices : [];
    _invoiceHouseholds = Array.isArray(households) ? households : [];
    _invoicePayments = Array.isArray(payments) ? payments : [];

    const hhSel = document.getElementById("if-hh");
    if (hhSel) {
      hhSel.innerHTML = `<option value="">Tất cả hộ</option>` +
        _invoiceHouseholds.map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("");
      hhSel.value = _invoiceState.hh;
    }
    renderInvoiceSummary();
    renderInvoicesTable();
  } catch {
    tbody.innerHTML = emptyRow(isAdmin ? 8 : 7, "🧾", "Không tải được danh sách hóa đơn", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải hóa đơn", "error");
  }
}

function invoiceHouseholdName(id) {
  return _invoiceHouseholds.find(h => h.id === id)?.name || `Hộ #${id}`;
}

function invoicePaidAmount(invoiceId) {
  return _invoicePayments
    .filter(p => p.invoice_id === invoiceId)
    .reduce((sum, p) => sum + (p.amount_paid || 0), 0);
}

function renderInvoiceSummary() {
  const el = document.getElementById("invoice-summary");
  if (!el) return;
  const total = _invoiceList.reduce((s, inv) => s + (inv.total_amount || 0), 0);
  const paid = _invoicePayments.reduce((s, p) => s + (p.amount_paid || 0), 0);
  const unpaidCount = _invoiceList.filter(i => i.status !== "paid").length;
  el.innerHTML = `
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(59,130,246,.12);border:1px solid rgba(59,130,246,.22)">🧾</span>
      <div style="min-width:0">
        <div class="summary-value">${fmtMoney(total)}</div>
        <div class="summary-label">Tổng phát sinh · ${_invoiceList.length} hóa đơn</div>
      </div>
    </div>
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.22)">💰</span>
      <div style="min-width:0">
        <div class="summary-value" style="color:var(--accent-green)">${fmtMoney(paid)}</div>
        <div class="summary-label">Đã thu</div>
      </div>
    </div>
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.22)">⏳</span>
      <div style="min-width:0">
        <div class="summary-value" style="color:var(--accent-red)">${fmtMoney(Math.max(total - paid, 0))}</div>
        <div class="summary-label">Còn nợ · ${unpaidCount} HĐ chưa TT</div>
      </div>
    </div>`;
}

function renderInvoicesTable() {
  const tbody = document.getElementById("inv-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  const colCount = isAdmin ? 8 : 7;
  const q = _invoiceState.q.trim().toLowerCase();

  const filtered = _invoiceList.filter(inv => {
    if (_invoiceState.status && inv.status !== _invoiceState.status) return false;
    if (_invoiceState.hh && String(inv.household_id) !== String(_invoiceState.hh)) return false;
    if (_invoiceState.period && inv.period !== _invoiceState.period) return false;
    if (q && !invoiceHouseholdName(inv.household_id).toLowerCase().includes(q)) return false;
    return true;
  });

  const counts = {
    all: _invoiceList.length,
    unpaid: _invoiceList.filter(i => i.status === "unpaid").length,
    partial: _invoiceList.filter(i => i.status === "partial").length,
    paid: _invoiceList.filter(i => i.status === "paid").length,
  };
  const allEl = document.getElementById("inv-count-all");
  if (allEl) {
    allEl.textContent = counts.all;
    document.getElementById("inv-count-unpaid").textContent = counts.unpaid;
    document.getElementById("inv-count-partial").textContent = counts.partial;
    document.getElementById("inv-count-paid").textContent = counts.paid;
  }

  if (!filtered.length) {
    tbody.innerHTML = emptyRow(
      colCount,
      "🧾",
      _invoiceList.length ? "Không tìm thấy hóa đơn phù hợp" : "Chưa có hóa đơn nào",
      _invoiceList.length
        ? "Thử bỏ bộ lọc hoặc chọn kỳ khác."
        : (isAdmin ? "Bấm “Tạo hóa đơn” để phát hành hóa đơn đầu tiên." : "Hóa đơn sẽ xuất hiện khi quản trị viên phát hành.")
    );
  } else {
    tbody.innerHTML = filtered.map(inv => {
      const remaining = (inv.total_amount || 0) - invoicePaidAmount(inv.id);
      return `
      <tr>
        ${isAdmin ? `<td>
          <span class="cell-main">${escapeHtml(invoiceHouseholdName(inv.household_id))}</span>
          <span class="cell-sub">Hóa đơn #${inv.id}</span>
        </td>` : ""}
        <td><span class="badge badge-info">${escapeHtml(inv.period)}</span>
          ${isAdmin ? "" : `<span class="cell-sub">Hóa đơn #${inv.id}</span>`}</td>
        <td class="num hide-md">${fmtMoney(inv.electricity_amount)}</td>
        <td class="num hide-md">${fmtMoney(inv.water_amount)}</td>
        <td class="num">
          <strong>${fmtMoney(inv.total_amount)}</strong>
          ${inv.status !== "paid" && remaining > 0 && remaining < inv.total_amount ? `<span class="cell-sub text-right">còn ${fmtMoney(remaining)}</span>` : ""}
        </td>
        <td>${invoiceStatusBadge(inv.status)}</td>
        <td class="nowrap text-muted">${inv.due_date ? formatDateVN(inv.due_date) : "—"}</td>
        <td>
          <button class="btn btn-secondary btn-sm" type="button" onclick="viewInvoiceDetail(${inv.id})" title="Xem chi tiết hóa đơn" aria-label="Chi tiết hóa đơn ${inv.id}">👁️ Xem</button>
          ${isAdmin ? `<button class="btn btn-ghost btn-sm" type="button" onclick="deleteInvoice(${inv.id})" title="Xóa hóa đơn" aria-label="Xóa hóa đơn ${inv.id}">🗑️ Xóa</button>` : ""}
        </td>
      </tr>`;
    }).join("");
  }

  const totalFiltered = filtered.reduce((s, inv) => s + (inv.total_amount || 0), 0);
  const foot = document.getElementById("invoice-table-foot");
  if (foot) foot.innerHTML = `Hiển thị <strong>${filtered.length}</strong> / ${_invoiceList.length} hóa đơn`;
  const totalEl = document.getElementById("invoice-total");
  if (totalEl) totalEl.textContent = filtered.length ? `Tổng đang lọc: ${fmtMoney(totalFiltered)}` : "";
}

async function deleteInvoice(id) {
  const inv = _invoiceList.find(item => item.id === id);
  if (!inv || !Auth.isAdmin()) return;
  if (!window.confirm(`Xóa hóa đơn kỳ ${inv.period} của ${invoiceHouseholdName(inv.household_id)}?`)) return;
  try {
    await Api.delete(`/api/invoices/${id}`);
    showToast("Đã xóa hóa đơn", "success");
    await loadInvoicesPage();
  } catch (e) { showToast(e.detail || "Lỗi xóa hóa đơn", "error"); }
}

function onInvoiceSearch(value) {
  _invoiceState.q = value;
  renderInvoicesTable();
}

function setInvoiceStatus(status) {
  _invoiceState.status = status;
  const order = ["", "unpaid", "partial", "paid"];
  const index = order.indexOf(status);
  document.querySelectorAll(".js-inv-status").forEach((btn, i) => btn.classList.toggle("active", i === index));
  renderInvoicesTable();
}

function setInvoiceHousehold(value) {
  _invoiceState.hh = value;
  renderInvoicesTable();
}

function setInvoicePeriod(value) {
  _invoiceState.period = value;
  renderInvoicesTable();
}

function clearInvoiceFilters() {
  _invoiceState = { status: "", hh: "", period: "", q: "" };
  const search = document.getElementById("if-search");
  const hh = document.getElementById("if-hh");
  const period = document.getElementById("if-period");
  if (search) search.value = "";
  if (hh) hh.value = "";
  if (period) period.value = "";
  document.querySelectorAll(".js-inv-status").forEach((btn, i) => btn.classList.toggle("active", i === 0));
  renderInvoicesTable();
}

async function viewInvoiceDetail(id) {
  const inv = _invoiceList.find(x => x.id === id) || await Api.get(`/api/invoices/${id}`).catch(() => null);
  if (!inv) return;

  // Trang hiện tại có thể chưa tải danh sách hộ (dashboard, thanh toán…) → bổ sung để hiện đúng tên hộ
  if (!_invoiceHouseholds.length) {
    const hhs = await Api.get("/api/households").catch(() => []);
    _invoiceHouseholds = Array.isArray(hhs) ? hhs : [];
  }

  let payments = _invoicePayments.filter(p => p.invoice_id === id);
  if (!payments.length) {
    payments = await Api.get(`/api/payments?invoice_id=${id}`).catch(() => []);
  }
  const totalPaid = payments.reduce((s, p) => s + (p.amount_paid || 0), 0);
  const remaining = Math.max((inv.total_amount || 0) - totalPaid, 0);

  const modal = document.getElementById("app-modal");
  if (!modal) return;
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" style="max-width:680px" role="dialog" aria-modal="true" aria-label="Chi tiết hóa đơn">
        <div class="modal-title">🧾 Chi tiết hóa đơn · Kỳ ${escapeHtml(inv.period)}</div>

        <div class="finance-grid" style="margin-bottom:16px">
          <div class="finance-item">
            <div class="finance-label">Hộ / Phòng</div>
            <div class="finance-value" style="font-size:0.88rem">${escapeHtml(invoiceHouseholdName(inv.household_id))}</div>
          </div>
          <div class="finance-item">
            <div class="finance-label">Đã thanh toán</div>
            <div class="finance-value green">${fmtMoney(totalPaid)}</div>
          </div>
          <div class="finance-item">
            <div class="finance-label">Còn nợ</div>
            <div class="finance-value ${remaining > 0 ? "red" : "green"}">${fmtMoney(remaining)}</div>
          </div>
        </div>

        <div class="divider"></div>
        <div class="section-title">Chi tiết tính tiền</div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr><th>Mô tả</th><th class="num">Tiêu thụ</th><th class="num">Đơn giá</th><th class="num">Thành tiền</th></tr>
            </thead>
            <tbody>
              ${(inv.items || []).length
                ? inv.items.map(it => `
                    <tr>
                      <td>${escapeHtml(it.description || "—")}</td>
                      <td class="num">${fmtNumber(it.consumption, 2)}</td>
                      <td class="num">${fmtMoney(it.unit_price)}</td>
                      <td class="num"><strong>${fmtMoney(it.total)}</strong></td>
                    </tr>`).join("")
                : `<tr><td colspan="4" class="text-muted" style="text-align:center;padding:16px">Chưa có chi tiết</td></tr>`}
            </tbody>
          </table>
        </div>

        <div class="divider"></div>
        <div class="section-title">Lịch sử thanh toán</div>
        ${payments.length
          ? `<div class="stack-sm">${payments.map(p => `
              <div class="meta-row" style="justify-content:space-between;font-size:0.8rem;padding:7px 0;border-bottom:1px solid var(--border-soft)">
                <span class="text-muted">${formatDateVN(p.paid_at)} · ${escapeHtml(PAYMENT_METHOD_LABEL[p.method] || p.method)}</span>
                <strong style="color:var(--accent-green)">+${fmtMoney(p.amount_paid)}</strong>
              </div>`).join("")}</div>`
          : `<div class="empty-state" style="padding:18px"><div class="empty-state-text">Chưa có thanh toán nào cho hóa đơn này.</div></div>`}

        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Đóng</button>
          ${remaining > 0 && Auth.isAdmin()
            ? `<a class="btn btn-primary" href="#payments" onclick="this.closest('.modal-overlay')?.remove()">💳 Ghi thanh toán</a>`
            : ""}
        </div>
      </div>
    </div>`;
}

function openGenModal() {
  document.getElementById("inv-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Tạo hóa đơn">
        <div class="modal-title">➕ Tạo hóa đơn</div>
        <div class="form-grid form-grid-2">
          <div class="form-group">
            <label class="form-label" for="gen-hh">Hộ / Phòng *</label>
            <select id="gen-hh" class="form-control"></select>
          </div>
          <div class="form-group">
            <label class="form-label" for="gen-period">Kỳ tháng *</label>
            <input id="gen-period" class="form-control" type="month" value="${currentPeriod()}">
          </div>
        </div>
        <div class="form-hint" style="margin-top:10px">Hóa đơn được tính từ chỉ số đã nhập trong kỳ và bảng đơn giá đang áp dụng.</div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="generateInvoice()">🧾 Tạo hóa đơn</button>
        </div>
      </div>
    </div>`;

  const sel = document.getElementById("gen-hh");
  const fill = (data) => {
    sel.innerHTML = data.length
      ? data.map(h => `<option value="${h.id}">${escapeHtml(h.name)}</option>`).join("")
      : `<option value="">Chưa có hộ hoạt động</option>`;
  };
  const active = _invoiceHouseholds.filter(h => h.status === "active");
  if (active.length) fill(active);
  else Api.get("/api/households?status=active").then(fill).catch(() => fill([]));

  setTimeout(() => document.getElementById("gen-period")?.focus(), 50);
}

async function generateInvoice() {
  const hhValue = document.getElementById("gen-hh").value;
  const period = document.getElementById("gen-period").value.trim();
  if (!hhValue) { showToast("Chưa có hộ để tạo hóa đơn", "warning"); return; }
  if (!period) { showToast("Chọn kỳ tháng", "warning"); return; }
  const body = { household_id: parseInt(hhValue), period };
  try {
    await Api.post("/api/invoices/generate", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast("Tạo hóa đơn thành công!", "success");
    await loadInvoicesPage();
  } catch (e) { showToast(e.detail || "Lỗi tạo hóa đơn", "error"); }
}

function openGenAllModal() {
  document.getElementById("inv-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" role="dialog" aria-modal="true" aria-label="Tạo hóa đơn cho tất cả hộ">
        <div class="modal-title">📋 Tạo hóa đơn cho tất cả hộ</div>
        <div class="form-group">
          <label class="form-label" for="ga-period">Kỳ tháng *</label>
          <input id="ga-period" class="form-control" type="month" value="${currentPeriod()}">
        </div>
        <div class="form-hint" style="margin-top:10px">Hộ đã có hóa đơn trong kỳ hoặc chưa nhập chỉ số sẽ được bỏ qua tự động.</div>
        <div class="modal-actions">
          <button class="btn btn-secondary" type="button" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" type="button" onclick="generateAll()">Tạo tất cả</button>
        </div>
      </div>
    </div>`;
}

async function generateAll() {
  const period = document.getElementById("ga-period").value.trim();
  if (!period) { showToast("Chọn kỳ tháng", "warning"); return; }
  try {
    const res = await Api.post(`/api/invoices/generate-all?period=${encodeURIComponent(period)}`, {});
    document.querySelector(".modal-overlay")?.remove();
    const created = res.created?.length || 0;
    const skipped = res.skipped?.length || 0;
    showToast(`Đã tạo ${created} hóa đơn, bỏ qua ${skipped} hộ`, created ? "success" : "warning");
    await loadInvoicesPage();
  } catch (e) { showToast(e.detail || "Lỗi tạo hóa đơn", "error"); }
}
