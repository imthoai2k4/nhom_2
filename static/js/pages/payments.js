/** pages/payments.js — Thanh toán & Công nợ */
async function renderPayments() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
      ${Auth.isAdmin() ? `
      <div class="table-wrapper" style="flex:1;min-width:280px;padding:20px">
        <div class="table-title" style="margin-bottom:16px">💳 Ghi nhận thanh toán</div>
        <div class="form-grid" style="gap:12px">
          <div class="form-group"><label class="form-label">Hóa đơn chưa TT</label>
            <select id="p-inv" class="form-control" onchange="loadRemainingDebt()"><option value="">-- Chọn hóa đơn --</option></select></div>
          <div class="form-group"><label class="form-label">Còn nợ</label>
            <input id="p-remaining" class="form-control" readonly style="background:var(--bg-hover);color:var(--accent-yellow)"></div>
          <div class="form-group"><label class="form-label">Số tiền thanh toán *</label>
            <input id="p-amount" class="form-control" type="number" oninput="checkPaymentAmount()"></div>
          <div class="form-group"><label class="form-label">Hình thức</label>
            <select id="p-method" class="form-control">
              <option value="cash">Tiền mặt</option><option value="transfer">Chuyển khoản</option><option value="other">Khác</option>
            </select></div>
          <div class="form-group" style="grid-column:1/-1"><label class="form-label">Ghi chú</label>
            <input id="p-note" class="form-control" placeholder="Ghi chú tùy chọn..."></div>
        </div>
        <button class="btn btn-primary" style="width:100%;margin-top:12px" onclick="submitPayment()">✅ Ghi nhận</button>
      </div>` : ""}
      <div style="flex:2;min-width:300px">
        <div class="section-title">📊 Công nợ theo hộ</div>
        <div class="table-wrapper"><table>
          <thead><tr><th>Hộ/Phòng</th><th>Chủ hộ</th><th>Tổng HĐ</th><th>Đã TT</th><th>Còn nợ</th></tr></thead>
          <tbody id="debt-tbody"><tr><td colspan="5" style="padding:24px;text-align:center;color:var(--text-muted)">Đang tải...</td></tr></tbody>
        </table></div>
      </div>
    </div>`;

  loadDebtReport();
  if (Auth.isAdmin()) loadUnpaidInvoicesSelect();
}

async function loadUnpaidInvoicesSelect() {
  try {
    const data = await Api.get("/api/invoices?status=unpaid");
    const partial = await Api.get("/api/invoices?status=partial");
    const all = [...data, ...partial];
    const sel = document.getElementById("p-inv");
    sel.innerHTML = `<option value="">-- Chọn hóa đơn --</option>` +
      all.map(inv => `<option value="${inv.id}" data-total="${inv.total_amount}">HH#${inv.household_id} — Kỳ ${inv.period} — ${inv.total_amount.toLocaleString()}đ</option>`).join("");
  } catch {}
}

async function loadRemainingDebt() {
  const invId = document.getElementById("p-inv")?.value;
  document.getElementById("p-remaining").value = "";
  if (!invId) return;
  try {
    const payments = await Api.get(`/api/payments?invoice_id=${invId}`);
    const opt = document.querySelector(`#p-inv option[value="${invId}"]`);
    const total = parseInt(opt?.dataset.total || 0);
    const paid = payments.reduce((s, p) => s + p.amount_paid, 0);
    const remaining = total - paid;
    document.getElementById("p-remaining").value = remaining.toLocaleString() + "đ";
    document.getElementById("p-amount").max = remaining;
  } catch {}
}

function checkPaymentAmount() {
  const amount = parseInt(document.getElementById("p-amount").value || 0);
  const max = parseInt(document.getElementById("p-amount").max || 999999999);
  document.getElementById("p-amount").style.borderColor = amount > max ? "var(--accent-yellow)" : "";
}

async function submitPayment() {
  const body = {
    invoice_id: parseInt(document.getElementById("p-inv").value),
    amount_paid: parseInt(document.getElementById("p-amount").value),
    method: document.getElementById("p-method").value,
    note: document.getElementById("p-note").value.trim() || null,
  };
  if (!body.invoice_id) { showToast("Chọn hóa đơn", "warning"); return; }
  if (!body.amount_paid || body.amount_paid <= 0) { showToast("Nhập số tiền hợp lệ", "warning"); return; }
  try {
    await Api.post("/api/payments", body);
    showToast("Ghi nhận thanh toán thành công!", "success");
    document.getElementById("p-amount").value = "";
    document.getElementById("p-note").value = "";
    loadDebtReport();
    loadUnpaidInvoicesSelect();
  } catch (e) { showToast(e.detail || "Lỗi ghi nhận", "error"); }
}

async function loadDebtReport() {
  try {
    const data = await Api.get("/api/payments/reports/debt");
    const tbody = document.getElementById("debt-tbody");
    if (!data.length) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted)">Không có dữ liệu</td></tr>`; return; }
    tbody.innerHTML = data.sort((a,b) => b.outstanding_debt - a.outstanding_debt).map(r => `<tr>
      <td><strong>${r.household_name}</strong></td>
      <td>${r.owner_name || "—"}</td>
      <td>${(r.total_invoiced||0).toLocaleString()}đ</td>
      <td style="color:var(--accent-green)">${(r.total_paid||0).toLocaleString()}đ</td>
      <td><strong style="color:${r.outstanding_debt > 0 ? "var(--accent-red)" : "var(--accent-green)"}">${(r.outstanding_debt||0).toLocaleString()}đ</strong></td>
    </tr>`).join("");
  } catch { showToast("Lỗi tải công nợ", "error"); }
}
