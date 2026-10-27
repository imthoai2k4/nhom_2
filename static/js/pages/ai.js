/** pages/ai.js — Phân tích AI tiêu thụ điện nước (Gemini) */
async function renderAI() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="margin-bottom:16px">
      <div class="section-title" style="margin:0 0 4px 0">🤖 Phân tích AI — Tiêu thụ Điện Nước</div>
      <div style="font-size:0.82rem;color:var(--text-secondary)">Sử dụng Gemini AI phân tích hóa đơn, cảnh báo bất thường và gợi ý tiết kiệm</div>
    </div>
    <div style="display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap;align-items:end">
      <div class="form-group" style="flex:1;min-width:180px;margin:0">
        <label class="form-label">Chọn hộ / phòng</label>
        <select id="ai-hh" class="form-control"><option value="">— Chọn hộ —</option></select>
      </div>
      <div class="form-group" style="width:120px;margin:0">
        <label class="form-label">Số tháng</label>
        <select id="ai-months" class="form-control">
          <option value="3">3 tháng</option>
          <option value="6" selected>6 tháng</option>
          <option value="12">12 tháng</option>
        </select>
      </div>
      <button class="btn btn-primary" onclick="runAIAnalysis()" id="ai-btn" style="height:40px">
        🤖 Phân tích
      </button>
    </div>
    <div id="ai-result"></div>`;

  // Load danh sách hộ (đã filter theo quyền ở backend)
  try {
    const hhs = await Api.get("/api/households");
    const sel = document.getElementById("ai-hh");
    hhs.forEach(h => {
      sel.innerHTML += `<option value="${h.id}">${h.name} — ${h.owner_name || ""}</option>`;
    });
    // Nếu user chỉ có 1 hộ → tự chọn
    if (hhs.length === 1) {
      sel.value = hhs[0].id;
    }
  } catch {
    showToast("Không thể tải danh sách hộ", "error");
  }
}

async function runAIAnalysis() {
  const hhId = document.getElementById("ai-hh").value;
  const months = document.getElementById("ai-months").value;
  const resultDiv = document.getElementById("ai-result");
  const btn = document.getElementById("ai-btn");

  if (!hhId) { showToast("Vui lòng chọn hộ", "warning"); return; }

  // Loading state
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px"></span> Đang phân tích...';
  resultDiv.innerHTML = `
    <div class="table-wrapper" style="padding:40px;text-align:center">
      <div class="spinner" style="margin:0 auto 12px"></div>
      <div style="color:var(--text-secondary);font-size:0.88rem">🤖 AI Gemini đang phân tích dữ liệu tiêu thụ...</div>
      <div style="color:var(--text-muted);font-size:0.78rem;margin-top:6px">Quá trình này có thể mất vài giây</div>
    </div>`;

  try {
    const res = await Api.post("/api/ai/analyze", {
      household_id: parseInt(hhId),
      months: parseInt(months),
    });

    // Render kết quả (markdown-like → HTML đơn giản)
    const htmlContent = simpleMarkdown(res.analysis);

    resultDiv.innerHTML = `
      <div class="table-wrapper" style="padding:24px">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:8px">
          <div>
            <div style="font-size:1.05rem;font-weight:700;color:var(--text-primary)">
              🤖 Kết quả phân tích — ${res.household_name}
            </div>
            <div style="font-size:0.78rem;color:var(--text-muted);margin-top:2px">
              Dữ liệu: ${res.data_points} điểm | Mô hình: Gemini AI
            </div>
          </div>
          <span class="badge badge-success">✅ Hoàn tất</span>
        </div>
        <div class="ai-content" style="line-height:1.7;font-size:0.88rem;color:var(--text-primary)">
          ${htmlContent}
        </div>
      </div>`;

  } catch (e) {
    resultDiv.innerHTML = `
      <div class="table-wrapper" style="padding:24px;text-align:center">
        <div style="font-size:2rem;margin-bottom:8px">❌</div>
        <div style="color:var(--accent-red);font-weight:600;margin-bottom:4px">Lỗi phân tích</div>
        <div style="color:var(--text-secondary);font-size:0.83rem">${e.detail || e.message || "Không thể kết nối AI"}</div>
      </div>`;
    showToast("Lỗi phân tích AI", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "🤖 Phân tích";
  }
}

/**
 * Chuyển markdown đơn giản thành HTML
 */
function simpleMarkdown(text) {
  if (!text) return "";
  return text
    // Headers
    .replace(/^### (.+)$/gm, '<h4 style="color:var(--accent-blue);margin:16px 0 6px;font-size:0.95rem">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 style="color:var(--text-primary);margin:18px 0 8px;font-size:1.05rem">$1</h3>')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong style="color:var(--text-primary)">$1</strong>')
    // Italic
    .replace(/\*(.+?)\*/g, '<em style="color:var(--text-secondary)">$1</em>')
    // Blockquote
    .replace(/^> (.+)$/gm, '<blockquote style="border-left:3px solid var(--accent-blue);padding:6px 12px;margin:8px 0;color:var(--text-secondary);font-size:0.83rem;background:var(--bg-secondary);border-radius:4px">$1</blockquote>')
    // List items
    .replace(/^- (.+)$/gm, '<div style="padding:3px 0 3px 16px;position:relative"><span style="position:absolute;left:0">•</span> $1</div>')
    // Line breaks
    .replace(/\n\n/g, '<div style="height:8px"></div>')
    .replace(/\n/g, '<br>');
}
