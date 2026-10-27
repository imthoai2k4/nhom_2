/** pages/invoices.js — Hóa đơn */
async function renderInvoices() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px">
      <div class="section-title" style="margin:0">Danh sách Hóa đơn</div>
      ${Auth.isAdmin() ? `
      <div style="display:flex;gap:8px">
        <button class="btn btn-primary" onclick="openGenModal()">🧾 Tạo hóa đơn</button>
        <button class="btn btn-secondary" onclick="openGenAllModal()">📋 Tạo tất cả</button>
      </div>` : ""}
    </div>
    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <select id="if-hh" class="form-control" style="flex:1;min-width:140px" onchange="loadInvoices()"><option value="">Tất cả hộ</option></select>
      <input id="if-period" class="form-control" style="width:110px" placeholder="YYYY-MM" oninput="loadInvoices()">
      <select id="if-status" class="form-control" style="width:130px" onchange="loadInvoices()">
        <option value="">Tất cả</option><option value="unpaid">Chưa TT</option>
        <option value="partial">Một phần</option><option value="paid">Đã TT</option>
      </select>
    </div>
    <div class="table-wrapper"><table>
      <thead><tr><th>Hộ</th><th>Kỳ</th><th>Điện</th><th>Nước</th><th>Tổng</th><th>Trạng thái</th><th>Hạn TT</th><th></th></tr></thead>
      <tbody id="inv-tbody"><tr><td colspan="8" style="padding:24px;text-align:center;color:var(--text-muted)">Đang tải...</td></tr></tbody>
    </table></div>
    <div id="inv-modal"></div>`;

  const hhs = await Api.get("/api/households").catch(() => []);
  const sel = document.getElementById("if-hh");
  sel.innerHTML = `<option value="">Tất cả hộ</option>` + hhs.map(h => `<option value="${h.id}">${h.name}</option>`).join("");
  loadInvoices();
}

const STATUS_BADGE = { unpaid: "badge-danger", partial: "badge-warning", paid: "badge-success" };
const STATUS_LABEL = { unpaid: "Chưa TT", partial: "Một phần", paid: "Đã TT" };

async function loadInvoices() {
  const hhId = document.getElementById("if-hh")?.value || "";
  const period = document.getElementById("if-period")?.value || "";
  const status = document.getElementById("if-status")?.value || "";
  let url = "/api/invoices?";
  if (hhId) url += `household_id=${hhId}&`;
  if (period) url += `period=${period}&`;
  if (status) url += `status=${status}`;
  try {
    const data = await Api.get(url);
    const tbody = document.getElementById("inv-tbody");
    if (!data.length) { tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:20px;color:var(--text-muted)">Không có hóa đơn</td></tr>`; return; }
    tbody.innerHTML = data.map(inv => `<tr>
      <td>HH #${inv.household_id}</td>
      <td><span class="badge badge-info">${inv.period}</span></td>
      <td>${inv.electricity_amount.toLocaleString()}đ</td>
      <td>${inv.water_amount.toLocaleString()}đ</td>
      <td><strong>${inv.total_amount.toLocaleString()}đ</strong></td>
      <td><span class="badge ${STATUS_BADGE[inv.status]}">${STATUS_LABEL[inv.status]}</span></td>
      <td style="font-size:0.78rem;color:var(--text-secondary)">${inv.due_date ? inv.due_date.slice(0,10) : "—"}</td>
      <td><button class="btn btn-secondary btn-sm" onclick="viewInvoiceDetail(${inv.id})">👁️</button></td>
    </tr>`).join("");
  } catch { showToast("Lỗi tải hóa đơn", "error"); }
}

async function viewInvoiceDetail(id) {
  const inv = await Api.get(`/api/invoices/${id}`).catch(() => null);
  if (!inv) return;
  const payments = await Api.get(`/api/payments?invoice_id=${id}`).catch(() => []);
  const totalPaid = payments.reduce((s, p) => s + p.amount_paid, 0);
  const modal = document.getElementById("inv-modal");
  modal.innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal" style="max-width:640px">
        <div class="modal-title">🧾 Chi tiết hóa đơn — Kỳ ${inv.period}</div>
        <div style="font-size:0.85rem;margin-bottom:12px;color:var(--text-secondary)">Tổng: <strong style="color:var(--text-primary)">${inv.total_amount.toLocaleString()}đ</strong> | Đã TT: <strong style="color:var(--accent-green)">${totalPaid.toLocaleString()}đ</strong> | Còn nợ: <strong style="color:var(--accent-red)">${(inv.total_amount-totalPaid).toLocaleString()}đ</strong></div>
        <table style="margin-bottom:12px"><thead><tr><th>Mô tả</th><th>Tiêu thụ</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
        <tbody>${(inv.items||[]).map(it=>`<tr><td>${it.description}</td><td>${parseFloat(it.consumption).toLocaleString()}</td><td>${it.unit_price.toLocaleString()}đ</td><td>${it.total.toLocaleString()}đ</td></tr>`).join("")}</tbody></table>
        <div class="section-title">Lịch sử thanh toán</div>
        ${payments.length ? payments.map(p=>`<div style="font-size:0.83rem;padding:6px 0;border-bottom:1px solid var(--border-color)">${p.paid_at?.slice(0,10)} — ${p.amount_paid.toLocaleString()}đ — ${p.method}</div>`).join("") : `<div style="color:var(--text-muted);font-size:0.83rem">Chưa có thanh toán</div>`}
        <div class="modal-actions"><button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Đóng</button></div>
      </div>
    </div>`;
}

function openGenModal() {
  document.getElementById("inv-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal">
        <div class="modal-title">Tạo hóa đơn</div>
        <div class="form-grid form-grid-2" style="gap:12px">
          <div class="form-group"><label class="form-label">Hộ *</label>
            <select id="gen-hh" class="form-control"></select></div>
          <div class="form-group"><label class="form-label">Kỳ (YYYY-MM) *</label>
            <input id="gen-period" class="form-control" placeholder="2026-07"></div>
        </div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="generateInvoice()">Tạo</button>
        </div>
      </div>
    </div>`;
  Api.get("/api/households?status=active").then(data => {
    document.getElementById("gen-hh").innerHTML = data.map(h=>`<option value="${h.id}">${h.name}</option>`).join("");
  });
}

async function generateInvoice() {
  const body = { household_id: parseInt(document.getElementById("gen-hh").value), period: document.getElementById("gen-period").value.trim() };
  if (!body.period) { showToast("Nhập kỳ tháng", "warning"); return; }
  try {
    await Api.post("/api/invoices/generate", body);
    document.querySelector(".modal-overlay")?.remove();
    showToast("Tạo hóa đơn thành công!", "success");
    loadInvoices();
  } catch (e) { showToast(e.detail || "Lỗi tạo hóa đơn", "error"); }
}

function openGenAllModal() {
  document.getElementById("inv-modal").innerHTML = `
    <div class="modal-overlay" onclick="if(event.target===this)this.remove()">
      <div class="modal">
        <div class="modal-title">Tạo hóa đơn cho tất cả hộ</div>
        <div class="form-group"><label class="form-label">Kỳ (YYYY-MM) *</label>
          <input id="ga-period" class="form-control" placeholder="2026-07"></div>
        <div class="modal-actions">
          <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()">Hủy</button>
          <button class="btn btn-primary" onclick="generateAll()">Tạo tất cả</button>
        </div>
      </div>
    </div>`;
}

async function generateAll() {
  const period = document.getElementById("ga-period").value.trim();
  if (!period) { showToast("Nhập kỳ tháng", "warning"); return; }
  try {
    const res = await Api.post(`/api/invoices/generate-all?period=${period}`, {});
    document.querySelector(".modal-overlay")?.remove();
    showToast(`Tạo ${res.created.length} hóa đơn, bỏ qua ${res.skipped.length}`, "success");
    loadInvoices();
  } catch (e) { showToast(e.detail || "Lỗi", "error"); }
}
