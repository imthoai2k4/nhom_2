/** pages/ai.js — Phân tích AI tiêu thụ điện nước (Gemini) */
let _aiResultText = "";
let _aiHouseholdId = null;

async function renderAI() {
  const c = document.getElementById("page-container");
  const isAdmin = Auth.isAdmin();

  c.innerHTML = `
    <div class="ai-hero">
      <div class="ai-hero-icon" aria-hidden="true">🤖</div>
      <div>
        <div class="ai-hero-title">Phân tích tiêu thụ bằng AI</div>
        <div class="ai-hero-sub">Gemini AI đọc dữ liệu hóa đơn để phát hiện bất thường, giải thích biến động và gợi ý cách tiết kiệm điện nước.</div>
      </div>
    </div>

    <div class="panel ai-panel">
      <div class="ai-form-row">
        ${isAdmin ? `
        <div class="form-group">
          <label class="form-label" for="ai-hh">Hộ / Phòng cần phân tích</label>
          <select id="ai-hh" class="form-control">
            <option value="">— Chọn hộ —</option>
          </select>
        </div>` : `
        <div class="form-group">
          <label class="form-label">Hộ / Phòng được phân tích</label>
          <input id="ai-hh-display" class="form-control" readonly value="Đang tải…">
        </div>`}
        <div class="form-group ai-months">
          <label class="form-label" for="ai-months">Khoảng thời gian</label>
          <select id="ai-months" class="form-control">
            <option value="3">3 tháng</option>
            <option value="6" selected>6 tháng</option>
            <option value="12">12 tháng</option>
          </select>
        </div>
        <button class="btn btn-primary" type="button" onclick="runAIAnalysis()" id="ai-btn" style="height:38px">
          ✨ Phân tích ngay
        </button>
      </div>
      <div class="form-hint" style="margin-top:10px">${isAdmin
        ? "Mẹo: chọn khoảng 6–12 tháng để AI so sánh xu hướng chính xác hơn."
        : "AI chỉ phân tích dữ liệu của hộ bạn. Chọn 6–12 tháng để so sánh xu hướng chính xác hơn."}</div>
    </div>

    <div class="ai-feature-grid">
      <div class="ai-feature">
        <span class="ai-feature-icon" aria-hidden="true">🔍</span>
        <div>
          <div class="ai-feature-title">Phát hiện bất thường</div>
          <div class="ai-feature-desc">So sánh chỉ số từng kỳ và cảnh báo khi mức tiêu thụ tăng đột biến.</div>
        </div>
      </div>
      <div class="ai-feature">
        <span class="ai-feature-icon" aria-hidden="true">📈</span>
        <div>
          <div class="ai-feature-title">Xu hướng tiêu thụ</div>
          <div class="ai-feature-desc">Nhìn rõ điện và nước đang tăng hay giảm qua từng tháng.</div>
        </div>
      </div>
      <div class="ai-feature">
        <span class="ai-feature-icon" aria-hidden="true">💡</span>
        <div>
          <div class="ai-feature-title">Gợi ý tiết kiệm</div>
          <div class="ai-feature-desc">Đề xuất hành động cụ thể, phù hợp với mức sử dụng thực tế.</div>
        </div>
      </div>
    </div>

    <div id="ai-result" aria-live="polite"></div>`;

  try {
    const hhs = await Api.get("/api/households");
    const list = Array.isArray(hhs) ? hhs : [];
    const active = isAdmin ? list.filter(h => h.status !== "inactive") : list;

    if (isAdmin) {
      const sel = document.getElementById("ai-hh");
      if (!sel) return;
      sel.innerHTML = `<option value="">— Chọn hộ —</option>` +
        active.map(h => `<option value="${h.id}">${escapeHtml(h.name)} — ${escapeHtml(h.owner_name || "chưa có chủ hộ")}</option>`).join("");
      if (active.length === 1) sel.value = active[0].id;
    } else {
      const hh = active[0] || null;
      _aiHouseholdId = hh?.id || null;
      const display = document.getElementById("ai-hh-display");
      if (display) display.value = hh ? `${hh.name} — ${hh.owner_name || "chưa có chủ hộ"}` : "Chưa gắn hộ/phòng";
    }
  } catch {
    showToast("Không thể tải danh sách hộ", "error");
  }
}

async function runAIAnalysis() {
  const hhId = document.getElementById("ai-hh")?.value || _aiHouseholdId;
  const months = document.getElementById("ai-months").value;
  const resultDiv = document.getElementById("ai-result");
  const btn = document.getElementById("ai-btn");

  if (!hhId) { showToast("Vui lòng chọn hộ", "warning"); return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:15px;height:15px;border-width:2px;display:inline-block;vertical-align:middle;margin-right:6px"></span> Đang phân tích…';
  resultDiv.innerHTML = `
    <div class="ai-loading-card">
      <div class="spinner" style="margin:0 auto 14px"></div>
      <div style="color:var(--text-secondary);font-size:0.88rem">🤖 Gemini AI đang đọc dữ liệu tiêu thụ…</div>
      <div style="color:var(--text-muted);font-size:0.76rem;margin-top:6px">Quá trình này có thể mất vài giây</div>
    </div>`;

  try {
    const res = await Api.post("/api/ai/analyze", {
      household_id: parseInt(hhId),
      months: parseInt(months),
    });

    _aiResultText = res.analysis || "";
    const htmlContent = simpleMarkdown(_aiResultText);

    resultDiv.innerHTML = `
      <div class="ai-response-card">
        <div class="ai-response-header">
          <div>
            <div class="ai-response-title">🤖 Kết quả phân tích · ${escapeHtml(res.household_name || "")}</div>
            <div class="ai-response-meta">${res.data_points || 0} điểm dữ liệu · ${months} tháng · Gemini AI</div>
          </div>
          <div class="meta-row">
            <span class="badge badge-success">✅ Hoàn tất</span>
            <button class="btn btn-secondary btn-sm" type="button" onclick="copyAIResult()">📋 Sao chép</button>
          </div>
        </div>
        <div class="ai-content" id="ai-content">${htmlContent}</div>
      </div>`;
  } catch (e) {
    resultDiv.innerHTML = `
      <div class="panel" style="border-color:rgba(248,113,113,.28)">
        <div class="empty-state">
          <div class="empty-state-icon" style="background:rgba(248,113,113,.1);border-color:rgba(248,113,113,.24)">⚠️</div>
          <div class="empty-state-title" style="color:var(--accent-red)">Không thể phân tích</div>
          <div class="empty-state-text">${escapeHtml(e.detail || e.message || "Không thể kết nối AI. Kiểm tra GEMINI_API_KEY trong .env.")}</div>
          <button class="btn btn-secondary" type="button" onclick="runAIAnalysis()">🔄 Thử lại</button>
        </div>
      </div>`;
    showToast("Lỗi phân tích AI", "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = "✨ Phân tích ngay";
  }
}

async function copyAIResult() {
  if (!_aiResultText) return;
  try {
    await navigator.clipboard.writeText(_aiResultText);
    showToast("Đã sao chép kết quả phân tích", "success");
  } catch {
    showToast("Trình duyệt không cho phép sao chép", "warning");
  }
}

/**
 * Chuyển markdown đơn giản thành HTML (đã escape để an toàn)
 */
function simpleMarkdown(text) {
  if (!text) return "";
  return escapeHtml(text)
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>')
    .replace(/^- (.+)$/gm, '<div class="ai-list-item">$1</div>')
    .replace(/\n\n/g, '<div class="ai-spacer"></div>')
    .replace(/\n/g, '<br>');
}
