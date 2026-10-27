/** pages/payments.js — Thanh toán & Công nợ */
let _payInvoices = [];
let _payHouseholds = [];
let _payPayments = [];
let _payDebt = [];
let _paySelectedInvoice = null;

async function renderPayments() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();

  c.innerHTML = `
    <div class="page-head">
      <div>
        <h2 class="page-head-title">💳 ${isAdmin ? "Thanh toán &amp; Công nợ" : "Thanh toán của tôi"}</h2>
        <p class="page-head-sub">${isAdmin
          ? "Ghi nhận thanh toán hóa đơn và theo dõi công nợ của từng hộ."
          : "Theo dõi số tiền còn phải trả và lịch sử thanh toán của hộ."}</p>
      </div>
      <div class="page-head-actions">
        <a class="btn btn-secondary" href="#invoices">🧾 ${isAdmin ? "Danh sách hóa đơn" : "Hóa đơn của tôi"}</a>
      </div>
    </div>

    <div class="summary-chips" id="payment-summary"></div>

    <div class="layout-cols">
      ${isAdmin ? `
      <div class="form-panel">
        <div class="form-panel-title">➕ Ghi nhận thanh toán</div>
        <div class="form-panel-sub">Chọn hóa đơn còn nợ, hệ thống hiển thị số tiền cần thu.</div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label" for="p-inv">Hóa đơn chưa thanh toán</label>
            <select id="p-inv" class="form-control" onchange="loadRemainingDebt()">
              <option value="">-- Chọn hóa đơn --</option>
            </select>
          </div>

          <div class="finance-grid" id="p-invoice-info" style="margin:0">
            <div class="finance-item">
              <div class="finance-label">Tổng HĐ</div>
              <div class="finance-value" id="p-total" style="font-size:0.85rem">—</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">Đã trả</div>
              <div class="finance-value green" id="p-paid" style="font-size:0.85rem">—</div>
            </div>
            <div class="finance-item">
              <div class="finance-label">Còn nợ</div>
              <div class="finance-value red" id="p-remaining" style="font-size:0.85rem">—</div>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="p-amount">Số tiền thanh toán *</label>
            <input id="p-amount" class="form-control" type="number" min="1" step="1000" placeholder="Nhập số tiền (đ)" oninput="checkPaymentAmount()">
            <div class="meta-row" style="margin-top:2px">
              <button class="btn btn-ghost btn-sm" type="button" onclick="quickPaymentAmount(1)">Thu đủ</button>
              <button class="btn btn-ghost btn-sm" type="button" onclick="quickPaymentAmount(0.5)">50%</button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label" for="p-method">Hình thức thanh toán</label>
            <select id="p-method" class="form-control">
              <option value="cash">💵 Tiền mặt</option>
              <option value="transfer">🏦 Chuyển khoản</option>
              <option value="other">📄 Khác</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label" for="p-note">Ghi chú</label>
            <input id="p-note" class="form-control" placeholder="Ghi chú tùy chọn…">
          </div>
        </div>

        <button class="btn btn-primary btn-block" type="button" style="margin-top:16px" onclick="submitPayment()">✅ Ghi nhận thanh toán</button>
      </div>` : ""}

      <div class="stack-md">
        ${isAdmin ? `
        <div class="table-wrapper">
          <div class="table-header">
            <div>
              <div class="table-title">📊 Công nợ theo hộ</div>
              <div class="panel-sub">Sắp xếp theo số tiền còn nợ giảm dần</div>
            </div>
          </div>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Hộ / Phòng</th>
                  <th class="num">Tổng HĐ</th>
                  <th class="num">Đã TT</th>
                  <th class="num">Còn nợ</th>
                  <th style="width:130px">Tỷ lệ thu</th>
                </tr>
              </thead>
              <tbody id="debt-tbody">${loadingRow(5)}</tbody>
            </table>
          </div>
          <div class="table-foot">
            <span id="debt-table-foot">Đang tải…</span>
          </div>
        </div>` : `
        <div class="table-wrapper">
          <div class="table-header">
            <div>
              <div class="table-title">📌 Hóa đơn còn phải trả</div>
              <div class="panel-sub">Các hóa đơn chưa thanh toán đủ của hộ</div>
            </div>
            <a class="panel-link" href="#invoices">Tất cả hóa đơn →</a>
          </div>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Kỳ</th>
                  <th class="num">Tổng tiền</th>
                  <th class="num">Đã trả</th>
                  <th class="num">Còn nợ</th>
                  <th>Hạn TT</th>
                  <th></th>
                </tr>
              </thead>
              <tbody id="unpaid-tbody">${loadingRow(6)}</tbody>
            </table>
          </div>
        </div>`}

        <div class="table-wrapper">
          <div class="table-header">
            <div>
              <div class="table-title">🕘 Thanh toán gần đây</div>
              <div class="panel-sub">8 giao dịch mới nhất</div>
            </div>
          </div>
          <div class="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Ngày</th>
                  ${isAdmin ? "<th>Hộ / Phòng</th>" : ""}
                  <th>Kỳ</th>
                  <th>Hình thức</th>
                  <th class="num">Số tiền</th>
                </tr>
              </thead>
              <tbody id="payment-tbody">${loadingRow(isAdmin ? 5 : 4)}</tbody>
            </table>
          </div>
        </div>
      </div>
    </div>`;

  await loadPaymentsPage();
}

async function loadPaymentsPage() {
  try {
    const [invoices, households, payments, debt] = await Promise.all([
      Api.get("/api/invoices"),
      Api.get("/api/households"),
      Api.get("/api/payments"),
      Api.get("/api/payments/reports/debt"),
    ]);
    _payInvoices = Array.isArray(invoices) ? invoices : [];
    _payHouseholds = Array.isArray(households) ? households : [];
    _payPayments = Array.isArray(payments) ? payments : [];
    _payDebt = Array.isArray(debt) ? debt : [];

    if (Auth.isAdmin()) loadUnpaidInvoicesSelect();
    renderPaymentSummary();
    if (Auth.isAdmin()) renderDebtTable();
    else renderUnpaidInvoices();
    renderPaymentHistory();
  } catch {
    const debtBody = document.getElementById("debt-tbody") || document.getElementById("unpaid-tbody");
    if (debtBody) debtBody.innerHTML = emptyRow(Auth.isAdmin() ? 5 : 6, "💳", "Không tải được dữ liệu thanh toán", "Kiểm tra kết nối server rồi thử lại.");
    showToast("Lỗi tải dữ liệu thanh toán", "error");
  }
}

function payHouseholdName(id) {
  return _payHouseholds.find(h => h.id === id)?.name || `Hộ #${id}`;
}

function invoicePaidTotal(invoiceId) {
  return _payPayments
    .filter(p => p.invoice_id === invoiceId)
    .reduce((sum, p) => sum + (p.amount_paid || 0), 0);
}

function renderPaymentSummary() {
  const el = document.getElementById("payment-summary");
  if (!el) return;
  const isAdmin = Auth.isAdmin();
  const totalDebt = _payDebt.reduce((s, r) => s + (r.outstanding_debt || 0), 0);
  const totalPaid = _payPayments.reduce((s, p) => s + (p.amount_paid || 0), 0);
  const debtors = _payDebt.filter(r => (r.outstanding_debt || 0) > 0).length;
  const unpaidCount = _payInvoices.filter(inv => inv.status !== "paid").length;
  el.innerHTML = `
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(248,113,113,.12);border:1px solid rgba(248,113,113,.22)">⏳</span>
      <div style="min-width:0">
        <div class="summary-value" style="color:var(--accent-red)">${fmtMoney(totalDebt)}</div>
        <div class="summary-label">${isAdmin ? "Tổng công nợ còn lại" : "Số tiền còn phải trả"}</div>
      </div>
    </div>
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.22)">💰</span>
      <div style="min-width:0">
        <div class="summary-value" style="color:var(--accent-green)">${fmtMoney(totalPaid)}</div>
        <div class="summary-label">${isAdmin ? "Tổng đã thu" : "Tổng đã thanh toán"} · ${_payPayments.length} giao dịch</div>
      </div>
    </div>
    <div class="summary-chip">
      <span class="stat-icon" style="width:34px;height:34px;font-size:1rem;background:rgba(251,191,36,.12);border:1px solid rgba(251,191,36,.22)">🧾</span>
      <div style="min-width:0">
        <div class="summary-value" style="color:var(--accent-yellow)">${isAdmin ? debtors : unpaidCount}</div>
        <div class="summary-label">${isAdmin ? "Hộ còn nợ" : "Hóa đơn chưa trả đủ"}</div>
      </div>
    </div>`;
}

/** Dành cho user: danh sách hóa đơn còn nợ thay cho bảng công nợ theo hộ. */
function renderUnpaidInvoices() {
  const tbody = document.getElementById("unpaid-tbody");
  if (!tbody) return;
  const rows = _payInvoices
    .filter(inv => inv.status !== "paid")
    .sort((a, b) => String(b.period).localeCompare(String(a.period)) || b.id - a.id);

  if (!rows.length) {
    tbody.innerHTML = emptyRow(6, "✅", "Không còn khoản nào phải trả", "Tất cả hóa đơn của hộ đã được thanh toán đủ.");
    return;
  }

  tbody.innerHTML = rows.map(inv => {
    const paid = invoicePaidTotal(inv.id);
    const remaining = Math.max((inv.total_amount || 0) - paid, 0);
    return `
    <tr>
      <td><span class="badge badge-info">${escapeHtml(inv.period)}</span>
        <span class="cell-sub">Hóa đơn #${inv.id}</span></td>
      <td class="num">${fmtMoney(inv.total_amount)}</td>
      <td class="num money green">${fmtMoney(paid)}</td>
      <td class="num"><strong class="money red">${fmtMoney(remaining)}</strong></td>
      <td class="nowrap text-muted">${inv.due_date ? formatDateVN(inv.due_date) : "—"}</td>
      <td class="text-right">
        <button class="btn btn-secondary btn-sm" type="button" onclick="viewInvoiceDetail(${inv.id})">Chi tiết</button>
      </td>
    </tr>`;
  }).join("");
}

function loadUnpaidInvoicesSelect() {
  const sel = document.getElementById("p-inv");
  if (!sel) return;

  const pending = _payInvoices
    .filter(inv => inv.status !== "paid")
    .sort((a, b) => String(b.period).localeCompare(String(a.period)) || b.id - a.id);

  sel.innerHTML = `<option value="">-- Chọn hóa đơn --</option>` +
    pending.map(inv => {
      const remaining = Math.max((inv.total_amount || 0) - invoicePaidTotal(inv.id), 0);
      return `<option value="${inv.id}">
        ${escapeHtml(payHouseholdName(inv.household_id))} · Kỳ ${escapeHtml(inv.period)} · còn ${fmtMoney(remaining)}
      </option>`;
    }).join("");

  if (!pending.length) {
    sel.innerHTML = `<option value="">Không có hóa đơn cần thu</option>`;
  }
  _paySelectedInvoice = null;
  updatePaymentInvoiceInfo(null);
}

function loadRemainingDebt() {
  const invId = parseInt(document.getElementById("p-inv")?.value);
  const inv = _payInvoices.find(x => x.id === invId) || null;
  _paySelectedInvoice = inv;
  updatePaymentInvoiceInfo(inv);
}

function updatePaymentInvoiceInfo(inv) {
  const totalEl = document.getElementById("p-total");
  const paidEl = document.getElementById("p-paid");
  const remainEl = document.getElementById("p-remaining");
  const amountEl = document.getElementById("p-amount");
  if (!totalEl) return;

  if (!inv) {
    totalEl.textContent = "—";
    paidEl.textContent = "—";
    remainEl.textContent = "—";
    if (amountEl) {
      amountEl.value = "";
      amountEl.removeAttribute("max");
      amountEl.style.borderColor = "";
    }
    return;
  }

  const paid = invoicePaidTotal(inv.id);
  const remaining = Math.max((inv.total_amount || 0) - paid, 0);
  totalEl.textContent = fmtMoney(inv.total_amount);
  paidEl.textContent = fmtMoney(paid);
  remainEl.textContent = fmtMoney(remaining);
  if (amountEl) {
    amountEl.value = remaining > 0 ? remaining : "";
    amountEl.max = remaining;
    amountEl.style.borderColor = "";
  }
}

function quickPaymentAmount(ratio) {
  if (!_paySelectedInvoice) { showToast("Chọn hóa đơn trước", "warning"); return; }
  const remaining = Math.max((_paySelectedInvoice.total_amount || 0) - invoicePaidTotal(_paySelectedInvoice.id), 0);
  const value = Math.max(0, Math.round(remaining * ratio));
  const input = document.getElementById("p-amount");
  if (input) {
    input.value = value;
    checkPaymentAmount();
  }
}

function checkPaymentAmount() {
  const input = document.getElementById("p-amount");
  if (!input) return;
  const amount = Number(input.value || 0);
  const max = Number(input.max || 0);
  input.style.borderColor = max && amount > max ? "var(--accent-yellow)" : "";
}

async function submitPayment() {
  const invoiceId = parseInt(document.getElementById("p-inv")?.value);
  const amountInput = document.getElementById("p-amount");
  const amount = Math.round(Number(amountInput?.value || 0));
  const body = {
    invoice_id: invoiceId,
    amount_paid: amount,
    method: document.getElementById("p-method").value,
    note: document.getElementById("p-note").value.trim() || null,
  };
  if (!body.invoice_id) { showToast("Chọn hóa đơn cần thu", "warning"); return; }
  if (!body.amount_paid || body.amount_paid <= 0) { showToast("Nhập số tiền hợp lệ", "warning"); return; }
  if (amountInput?.max && body.amount_paid > Number(amountInput.max)) {
    showToast("Số tiền vượt quá số còn nợ", "warning");
    return;
  }

  try {
    await Api.post("/api/payments", body);
    showToast("Ghi nhận thanh toán thành công!", "success");
    await loadPaymentsPage();
  } catch (e) { showToast(e.detail || "Lỗi ghi nhận thanh toán", "error"); }
}

function renderDebtTable() {
  const tbody = document.getElementById("debt-tbody");
  if (!tbody) return;

  const rows = [..._payDebt].sort((a, b) => (b.outstanding_debt || 0) - (a.outstanding_debt || 0));
  if (!rows.length) {
    tbody.innerHTML = emptyRow(5, "📊", "Chưa có dữ liệu công nợ", "Công nợ sẽ xuất hiện sau khi tạo hóa đơn.");
  } else {
    tbody.innerHTML = rows.map(r => {
      const invoiced = r.total_invoiced || 0;
      const paid = r.total_paid || 0;
      const debt = r.outstanding_debt || 0;
      const rate = invoiced > 0 ? Math.min(100, Math.round((paid / invoiced) * 100)) : 0;
      return `
      <tr>
        <td>
          <div class="cell-user">
            <span class="avatar" aria-hidden="true">${escapeHtml(initials(r.household_name))}</span>
            <div>
              <span class="cell-main">${escapeHtml(r.household_name)}</span>
              <span class="cell-sub">${escapeHtml(r.owner_name || "Chưa cập nhật chủ hộ")}</span>
            </div>
          </div>
        </td>
        <td class="num">${fmtMoney(invoiced)}</td>
        <td class="num money green">${fmtMoney(paid)}</td>
        <td class="num"><strong class="${debt > 0 ? "money red" : "money green"}">${fmtMoney(debt)}</strong></td>
        <td class="pay-progress">
          <div class="progress"><div class="progress-bar ${rate >= 100 ? "" : rate >= 50 ? "blue" : "yellow"}" style="width:${rate}%"></div></div>
          <span class="cell-sub">${rate}%</span>
        </td>
      </tr>`;
    }).join("");
  }

  const foot = document.getElementById("debt-table-foot");
  if (foot) foot.innerHTML = `Hiển thị <strong>${rows.length}</strong> hộ · Tổng còn nợ <strong>${fmtMoney(rows.reduce((s, r) => s + (r.outstanding_debt || 0), 0))}</strong>`;
}

function renderPaymentHistory() {
  const tbody = document.getElementById("payment-tbody");
  if (!tbody) return;
  const isAdmin = Auth.isAdmin();
  const invoiceMap = new Map(_payInvoices.map(inv => [inv.id, inv]));
  const rows = [..._payPayments]
    .sort((a, b) => new Date(b.paid_at) - new Date(a.paid_at))
    .slice(0, 8);

  if (!rows.length) {
    tbody.innerHTML = emptyRow(isAdmin ? 5 : 4, "🕘", "Chưa có giao dịch nào", "Các khoản thu sẽ được lưu tại đây.");
    return;
  }

  tbody.innerHTML = rows.map(p => {
    const inv = invoiceMap.get(p.invoice_id);
    return `
    <tr>
      <td class="nowrap text-muted">${formatDateVN(p.paid_at)}</td>
      ${isAdmin ? `<td>${escapeHtml(inv ? payHouseholdName(inv.household_id) : `HĐ #${p.invoice_id}`)}</td>` : ""}
      <td>${inv ? `<span class="badge badge-muted">${escapeHtml(inv.period)}</span>` : "—"}</td>
      <td>${escapeHtml(PAYMENT_METHOD_LABEL[p.method] || p.method)}</td>
      <td class="num"><strong class="money green">+${fmtMoney(p.amount_paid)}</strong></td>
    </tr>`;
  }).join("");
}
