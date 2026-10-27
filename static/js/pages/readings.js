/** pages/readings.js — Nhập & tra cứu chỉ số */
async function renderReadings() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
      ${Auth.isAdmin() ? `
      <div class="table-wrapper" style="flex:1;min-width:300px;padding:20px">
        <div class="table-title" style="margin-bottom:16px">📝 Nhập chỉ số mới</div>
        <div class="form-grid" style="gap:12px">
          <div class="form-group">
            <label class="form-label">Hộ/Phòng</label>
            <select id="r-hh" class="form-control" onchange="loadMetersForReading()"><option value="">-- Chọn hộ --</option></select>
          </div>
          <div class="form-group">
            <label class="form-label">Đồng hồ</label>
            <select id="r-meter" class="form-control" onchange="prefillPrevReading()"><option value="">-- Chọn đồng hồ --</option></select>
          </div>
          <div class="form-group">
            <label class="form-label">Kỳ (YYYY-MM)</label>
            <input id="r-period" class="form-control" placeholder="2026-07" maxlength="7">
          </div>
          <div class="form-group">
            <label class="form-label">Chỉ số kỳ trước</label>
            <input id="r-prev" class="form-control" type="number" step="0.01" readonly style="background:var(--bg-hover)">
          </div>
          <div class="form-group">
            <label class="form-label">Chỉ số kỳ này *</label>
            <input id="r-curr" class="form-control" type="number" step="0.01" oninput="previewConsumption()">
          </div>
          <div class="form-group">
            <label class="form-label">Tiêu thụ (preview)</label>
            <input id="r-preview" class="form-control" readonly style="background:var(--bg-hover);color:var(--accent-cyan)">
          </div>
        </div>
        <button class="btn btn-primary" style="margin-top:12px;width:100%" onclick="submitReading()">✅ Nhập chỉ số</button>
      </div>` : ""}
      <div style="flex:2;min-width:320px">
        <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
          <select id="rf-hh" class="form-control" style="flex:1" onchange="loadReadingsList()"><option value="">Tất cả hộ</option></select>
          <input id="rf-period" class="form-control" style="width:110px" placeholder="YYYY-MM" oninput="loadReadingsList()">
        </div>
        <div class="table-wrapper"><table>
          <thead><tr><th>Hộ/ĐH</th><th>Kỳ</th><th>Trước</th><th>Sau</th><th>Tiêu thụ</th></tr></thead>
          <tbody id="r-tbody"><tr><td colspan="5" style="padding:24px;text-align:center;color:var(--text-muted)">Đang tải...</td></tr></tbody>
        </table></div>
      </div>
    </div>`;

  await loadHouseholdsIntoSelect("r-hh");
  await loadHouseholdsIntoSelect("rf-hh", true);
  loadReadingsList();
}

async function loadHouseholdsIntoSelect(id, allOption = false) {
  try {
    const data = await Api.get("/api/households?status=active");
    const sel = document.getElementById(id);
    if (!sel) return;
    const extra = allOption ? `<option value="">Tất cả hộ</option>` : `<option value="">-- Chọn hộ --</option>`;
    sel.innerHTML = extra + data.map(h => `<option value="${h.id}">${h.name}</option>`).join("");
  } catch {}
}

async function loadMetersForReading() {
  const hhId = document.getElementById("r-hh")?.value;
  const sel = document.getElementById("r-meter");
  sel.innerHTML = `<option value="">-- Chọn đồng hồ --</option>`;
  if (!hhId) return;
  const data = await Api.get(`/api/meters?household_id=${hhId}`);
  sel.innerHTML += data.map(m => `<option value="${m.id}">${m.meter_type === "electricity" ? "⚡" : "💧"} ${m.meter_number} (${m.unit})</option>`).join("");
}

async function prefillPrevReading() {
  const meterId = document.getElementById("r-meter")?.value;
  document.getElementById("r-prev").value = "";
  document.getElementById("r-preview").value = "";
  if (!meterId) return;
  try {
    const last = await Api.get(`/api/readings/last/${meterId}`);
    document.getElementById("r-prev").value = last.curr_reading;
    previewConsumption();
  } catch {}
}

function previewConsumption() {
  const prev = parseFloat(document.getElementById("r-prev")?.value || 0);
  const curr = parseFloat(document.getElementById("r-curr")?.value || 0);
  const diff = curr - prev;
  const el = document.getElementById("r-preview");
  el.value = isNaN(diff) ? "" : diff.toFixed(2);
  document.getElementById("r-curr").style.borderColor = diff < 0 ? "var(--accent-red)" : "";
}

async function submitReading() {
  const body = {
    meter_id: parseInt(document.getElementById("r-meter").value),
    period: document.getElementById("r-period").value.trim(),
    prev_reading: parseFloat(document.getElementById("r-prev").value || 0),
    curr_reading: parseFloat(document.getElementById("r-curr").value),
  };
  if (!body.meter_id) { showToast("Chọn đồng hồ", "warning"); return; }
  if (!body.period) { showToast("Nhập kỳ tháng (YYYY-MM)", "warning"); return; }
  if (isNaN(body.curr_reading)) { showToast("Nhập chỉ số kỳ này", "warning"); return; }
  if (body.curr_reading < body.prev_reading) { showToast("Chỉ số mới không được nhỏ hơn kỳ trước", "error"); return; }
  try {
    await Api.post("/api/readings", body);
    showToast("Đã nhập chỉ số thành công!", "success");
    document.getElementById("r-curr").value = "";
    document.getElementById("r-preview").value = "";
    loadReadingsList();
  } catch (e) { showToast(e.detail || "Lỗi nhập chỉ số", "error"); }
}

async function loadReadingsList() {
  const hhId = document.getElementById("rf-hh")?.value || "";
  const period = document.getElementById("rf-period")?.value || "";
  let url = "/api/readings?";
  if (hhId) url += `household_id=${hhId}&`;
  if (period) url += `period=${period}`;
  try {
    const data = await Api.get(url);
    const tbody = document.getElementById("r-tbody");
    if (!data.length) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted)">Không có dữ liệu</td></tr>`; return; }
    tbody.innerHTML = data.map(r => `<tr>
      <td>ĐH #${r.meter_id}</td>
      <td><span class="badge badge-info">${r.period}</span></td>
      <td>${parseFloat(r.prev_reading).toLocaleString()}</td>
      <td>${parseFloat(r.curr_reading).toLocaleString()}</td>
      <td><strong style="color:var(--accent-cyan)">${parseFloat(r.consumption).toLocaleString()}</strong></td>
    </tr>`).join("");
  } catch { showToast("Lỗi tải chỉ số", "error"); }
}
