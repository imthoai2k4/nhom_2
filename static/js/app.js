/**
 * app.js — SPA router KT2 — đầy đủ 7 pages + auth + prices
 */

// ── Auth state ───────────────────────────────────────────────
const Auth = {
  get role()     { return localStorage.getItem("role") || ""; },
  get username() { return localStorage.getItem("username") || ""; },
  isLoggedIn()   { return !!localStorage.getItem("username"); },
  isAdmin()      { return this.role === "admin"; },
  save(data)     { localStorage.setItem("username", data.username); localStorage.setItem("role", data.role); Api.setCredentials(data.username, localStorage.getItem("pwd") || ""); },
  clear()        { localStorage.clear(); },
};

// Sync credentials from storage on load
const _savedUser = localStorage.getItem("username");
const _savedPwd  = localStorage.getItem("pwd");
if (_savedUser && _savedPwd) Api.setCredentials(_savedUser, _savedPwd);

// ── Toast notifications ─────────────────────────────────────
function showToast(message, type = "info") {
  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || "ℹ️"}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "none";
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ── Toggle sidebar (mobile) ──────────────────────────────────
function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("open");
}

// ── Navigation ───────────────────────────────────────────────
const pages = {
  dashboard:  renderDashboard,
  login:      renderLogin,
  households: renderHouseholds,
  meters:     renderMeters,
  readings:   renderReadings,
  prices:     renderPrices,
  invoices:   renderInvoices,
  payments:   renderPayments,
  ai:         renderAI,
};

const pageTitles = {
  dashboard:  "Dashboard",
  login:      "Đăng nhập",
  households: "Hộ / Phòng",
  meters:     "Đồng hồ",
  readings:   "Nhập Chỉ số",
  prices:     "Đơn giá",
  invoices:   "Hóa đơn",
  payments:   "Thanh toán",
  ai:         "Phân tích AI",
};

function navigate(page) {
  // Cập nhật active nav
  document.querySelectorAll(".nav-item").forEach(el => el.classList.remove("active"));
  const navEl = document.getElementById(`nav-${page}`);
  if (navEl) navEl.classList.add("active");

  // Cập nhật tiêu đề
  document.getElementById("page-title").textContent = pageTitles[page] || page;

  // Render trang
  const container = document.getElementById("page-container");
  if (pages[page]) {
    pages[page](container);
  }
}

// ── Hash-based routing ───────────────────────────────────────
function handleRoute() {
  const hash = location.hash.replace("#", "") || "dashboard";
  navigate(hash);
}

window.addEventListener("hashchange", handleRoute);

document.querySelectorAll(".nav-item").forEach(el => {
  el.addEventListener("click", () => {
    // Đóng sidebar trên mobile
    document.getElementById("sidebar").classList.remove("open");
  });
});

// ── Coming soon placeholder ──────────────────────────────────
function renderComingSoon(title, phase) {
  const container = document.getElementById("page-container");
  container.innerHTML = `
    <div class="empty-state" style="margin-top: 60px;">
      <div class="empty-state-icon">${title.split(" ")[0]}</div>
      <div style="font-size:1.2rem;font-weight:700;color:var(--text-primary);margin-bottom:8px;">
        ${title}
      </div>
      <div class="empty-state-text" style="margin-bottom:20px;">
        Tính năng này sẽ được xây dựng trong giai đoạn <strong>${phase}</strong>
      </div>
      <span class="badge badge-info">${phase} — Coming Soon</span>
    </div>`;
}

// ── Dashboard ────────────────────────────────────────────────
async function renderDashboard(container) {
  container.innerHTML = `
    <div class="loading-screen">
      <div class="spinner"></div>
      <p>Đang tải dữ liệu...</p>
    </div>`;

  try {
    const info = await Api.get("/api/info");
    const health = await Api.get("/api/health");

    // Fetch summary stats
    let hhCount = 0, meterCount = 0, invCount = 0;
    try {
      const hhs = await Api.get("/api/households");
      hhCount = hhs.length;
    } catch {}
    try {
      const meters = await Api.get("/api/meters");
      meterCount = meters.length;
    } catch {}
    try {
      const invs = await Api.get("/api/invoices");
      invCount = invs.length;
    } catch {}

    container.innerHTML = `
      <!-- Welcome banner -->
      <div style="margin-bottom:24px;">
        <h2 style="font-size:1.3rem;font-weight:700;margin-bottom:6px;">
          Chào mừng đến với UtilityAI 👋
        </h2>
        <p style="color:var(--text-secondary);font-size:0.875rem;">
          ${info.name} — Phiên bản ${info.version} — Giai đoạn: <strong style="color:var(--accent-blue)">${info.phase}</strong>
        </p>
      </div>

      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card blue">
          <div class="stat-icon">⚡</div>
          <div class="stat-info">
            <div class="stat-label">Trạng thái hệ thống</div>
            <div class="stat-value" style="font-size:1rem;">${health.status === 'ok' ? '🟢 Hoạt động' : '🔴 Lỗi'}</div>
            <div class="stat-sub">${health.message}</div>
          </div>
        </div>
        <div class="stat-card green">
          <div class="stat-icon">🏠</div>
          <div class="stat-info">
            <div class="stat-label">Hộ / Phòng</div>
            <div class="stat-value">${hhCount}</div>
            <div class="stat-sub">hộ đang quản lý</div>
          </div>
        </div>
        <div class="stat-card yellow">
          <div class="stat-icon">🔌</div>
          <div class="stat-info">
            <div class="stat-label">Đồng hồ</div>
            <div class="stat-value">${meterCount}</div>
            <div class="stat-sub">đồng hồ đã lắp</div>
          </div>
        </div>
        <div class="stat-card red">
          <div class="stat-icon">🧾</div>
          <div class="stat-info">
            <div class="stat-label">Hóa đơn</div>
            <div class="stat-value">${invCount}</div>
            <div class="stat-sub">hóa đơn đã tạo</div>
          </div>
        </div>
      </div>

      <!-- Quick actions -->
      <div class="section-title" style="margin-top:24px;">Truy cập nhanh</div>
      <div class="stats-grid" style="grid-template-columns: repeat(auto-fill, minmax(180px,1fr));">
        <a href="#households" class="stat-card blue" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">🏠</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Quản lý Hộ</div>
        </a>
        <a href="#meters" class="stat-card green" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">🔌</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Đồng hồ</div>
        </a>
        <a href="#readings" class="stat-card yellow" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">📝</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Nhập Chỉ số</div>
        </a>
        <a href="#prices" class="stat-card blue" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">💰</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Đơn giá</div>
        </a>
        <a href="#invoices" class="stat-card red" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">🧾</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Hóa đơn</div>
        </a>
        <a href="#payments" class="stat-card green" style="cursor:pointer;text-decoration:none">
          <div style="font-size:1.6rem">💳</div>
          <div style="font-size:0.85rem;font-weight:600;margin-top:6px">Thanh toán</div>
        </a>
      </div>

      <!-- Roadmap -->
      <div class="section-title" style="margin-top:24px;">Lộ trình xây dựng</div>
      <div class="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Giai đoạn</th>
              <th>Mô tả</th>
              <th>AI hỗ trợ</th>
              <th>Trạng thái</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>KT1</strong></td>
              <td>Phân tích nghiệp vụ, thiết kế CSDL, tạo models & seed data</td>
              <td>Phân tích chỉ số, hóa đơn, thanh toán</td>
              <td><span class="badge badge-success">✅ Hoàn thành</span></td>
            </tr>
            <tr>
              <td><strong>KT2</strong></td>
              <td>CRUD API hộ, chỉ số, hóa đơn, thanh toán; frontend pages</td>
              <td>Sinh CRUD, debug công thức tính</td>
              <td><span class="badge badge-success">✅ Hoàn thành</span></td>
            </tr>
            <tr>
              <td><strong>KT3</strong></td>
              <td>Tích hợp Gemini AI; test dữ liệu âm/mâu thuẫn</td>
              <td>Thiết kế prompt phân tích tiêu thụ</td>
              <td><span class="badge badge-info">🔜 KT3</span></td>
            </tr>
          </tbody>
        </table>
      </div>`;
  } catch (err) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">❌</div>
        <div class="empty-state-text">Không thể kết nối đến server. Hãy chắc chắn <code>python main.py</code> đang chạy.</div>
      </div>`;
  }
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // Update user display from localStorage
  if (Auth.isLoggedIn()) {
    document.getElementById("display-username").textContent = Auth.username;
    document.getElementById("display-role").textContent = Auth.isAdmin() ? "Quản trị viên" : "Người dùng";
  }

  // Kiểm tra health
  try {
    await Api.get("/api/health");
    showToast("Kết nối hệ thống thành công!", "success");
  } catch {
    showToast("Không kết nối được server!", "error");
  }

  handleRoute();
});
