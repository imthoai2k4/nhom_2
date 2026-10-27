/**
 * app.js — SPA router + shared UI helpers
 * UtilityAI · Hệ thống quản lý hóa đơn điện nước
 *
 * Điểm chính:
 *  - Điều hướng & nội dung thay đổi theo vai trò (admin / user)
 *  - Dashboard riêng: admin quản lý toàn hệ thống, user chỉ thấy hộ của mình
 *  - Các helper hiển thị dùng chung cho mọi trang
 */

// ── Auth state ───────────────────────────────────────────────
const Auth = {
  get role()         { return localStorage.getItem("role") || ""; },
  get username()     { return localStorage.getItem("username") || ""; },
  get householdId()  { return localStorage.getItem("household_id") || ""; },
  get householdName(){ return localStorage.getItem("household_name") || ""; },
  isLoggedIn()       { return !!localStorage.getItem("username") && !!localStorage.getItem("pwd"); },
  isAdmin()          { return this.role === "admin"; },

  saveSession(data, password) {
    localStorage.setItem("username", data.username);
    localStorage.setItem("role", data.role);
    localStorage.setItem("pwd", password);
    if (data.household_id) localStorage.setItem("household_id", data.household_id);
    else localStorage.removeItem("household_id");
    Api.setCredentials(data.username, password);
  },

  setHouseholdName(name) {
    if (!name) return;
    if (localStorage.getItem("household_name") !== name) {
      localStorage.setItem("household_name", name);
    }
    updateScopeChip();
  },

  clear() {
    ["username", "role", "pwd", "household_id", "household_name"].forEach(k => localStorage.removeItem(k));
  },
};

// Sync credentials from storage on load
if (Auth.isLoggedIn()) Api.setCredentials(Auth.username, localStorage.getItem("pwd") || "");

// ── Formatting helpers ───────────────────────────────────────
const VND = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 0 });

function fmtMoney(value, suffix = " đ") {
  const n = Number(value) || 0;
  return VND.format(n) + suffix;
}

function fmtNumber(value, digits = 0) {
  const n = Number(value);
  if (isNaN(n)) return "—";
  return n.toLocaleString("vi-VN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function escapeHtml(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatDateVN(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value).slice(0, 10);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function formatDateShort(value) {
  if (!value) return "—";
  const d = new Date(value);
  if (isNaN(d.getTime())) return String(value).slice(0, 10);
  return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
}

function currentPeriod() {
  return new Date().toISOString().slice(0, 7);
}

function periodLabel(period) {
  if (!period) return "—";
  const [year, month] = String(period).split("-");
  return `T${Number(month)}/${String(year).slice(2)}`;
}

function initials(name) {
  const value = String(name || "").trim();
  if (!value) return "?";
  const words = value.split(/\s+/);
  const last = words[words.length - 1];
  if (/^\d+$/.test(last)) return last.slice(0, 3);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + last[0]).toUpperCase();
}

function debounce(fn, delay = 220) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

function okValue(result, fallback) {
  return result && result.status === "fulfilled" ? result.value : fallback;
}

// ── Shared markup helpers ────────────────────────────────────
const INVOICE_STATUS = {
  unpaid:  { label: "Chưa thanh toán", cls: "badge-danger" },
  partial: { label: "Một phần",        cls: "badge-warning" },
  paid:    { label: "Đã thanh toán",   cls: "badge-success" },
};

const PAYMENT_METHOD_LABEL = { cash: "Tiền mặt", transfer: "Chuyển khoản", other: "Khác" };

function invoiceStatusBadge(status) {
  const meta = INVOICE_STATUS[status] || { label: status || "—", cls: "badge-muted" };
  return `<span class="badge ${meta.cls}">${meta.label}</span>`;
}

function loadingRow(colspan) {
  return `<tr><td colspan="${colspan}"><div class="table-loading"><span class="spinner"></span> Đang tải dữ liệu…</div></td></tr>`;
}

function emptyRow(colspan, icon, title, text = "") {
  return `<tr><td colspan="${colspan}">
    <div class="empty-state">
      <div class="empty-state-icon">${icon}</div>
      <div class="empty-state-title">${title}</div>
      <div class="empty-state-text">${text}</div>
    </div>
  </td></tr>`;
}

// ── Toast notifications ─────────────────────────────────────
function showToast(message, type = "info") {
  const icons = { success: "✅", error: "❌", info: "ℹ️", warning: "⚠️" };
  const container = document.getElementById("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.setAttribute("role", type === "error" ? "alert" : "status");
  toast.innerHTML = `<span aria-hidden="true">${icons[type] || "ℹ️"}</span><span>${escapeHtml(message)}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "none";
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ── Toggle sidebar (mobile) ──────────────────────────────────
function toggleSidebar(force) {
  const sidebar = document.getElementById("sidebar");
  const overlay = document.getElementById("sidebar-overlay");
  if (!sidebar) return;
  const open = typeof force === "boolean" ? force : !sidebar.classList.contains("open");
  sidebar.classList.toggle("open", open);
  if (overlay) overlay.classList.toggle("open", open);
}

function closeSidebar() {
  document.getElementById("sidebar")?.classList.remove("open");
  document.getElementById("sidebar-overlay")?.classList.remove("open");
}

// ── Phân quyền giao diện ─────────────────────────────────────
const ADMIN_PAGES = new Set(["households", "meters", "prices"]);

function updateScopeChip() {
  const chip = document.getElementById("scope-chip");
  if (!chip) return;
  if (Auth.isAdmin()) {
    chip.hidden = true;
    chip.textContent = "";
    return;
  }
  const name = Auth.householdName;
  if (!name) {
    chip.hidden = true;
    chip.textContent = "";
    return;
  }
  chip.hidden = false;
  chip.textContent = `🏠 ${name}`;
}

/** Áp dụng trạng thái đăng nhập/vai trò cho toàn bộ khung giao diện. */
function applyRoleUI() {
  const isAdmin = Auth.isAdmin();

  // Ẩn/hiện các mục chỉ dành cho admin
  document.querySelectorAll("[data-admin-only]").forEach(el => { el.hidden = !isAdmin; });

  // Nhãn nhóm điều hướng theo vai trò
  document.querySelectorAll("[data-label-admin]").forEach(el => {
    el.textContent = isAdmin ? el.dataset.labelAdmin : el.dataset.labelUser;
  });

  // Nhóm điều hướng rỗng thì ẩn luôn
  document.querySelectorAll(".sidebar-nav .nav-group").forEach(group => {
    const items = [...group.querySelectorAll(".nav-item")];
    group.hidden = items.length > 0 && items.every(item => item.hidden);
  });

  // Thông tin người dùng ở sidebar
  const usernameEl = document.getElementById("display-username");
  const roleEl = document.getElementById("display-role");
  const avatar = document.getElementById("user-avatar");
  if (usernameEl) usernameEl.textContent = Auth.username || "—";
  if (roleEl) roleEl.textContent = !Auth.isLoggedIn() ? "Chưa đăng nhập" : (isAdmin ? "Quản trị viên" : "Người dùng");
  if (avatar) avatar.textContent = initials(Auth.username || Auth.householdName);

  updateScopeChip();
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

let _currentPage = "dashboard";
function isPageActive(page) { return _currentPage === page; }

const pageTitles = {
  dashboard:  "Tổng quan",
  login:      "Đăng nhập",
  households: "Hộ / Phòng",
  meters:     "Đồng hồ",
  readings:   "Chỉ số",
  prices:     "Đơn giá",
  invoices:   "Hóa đơn",
  payments:   "Thanh toán",
  ai:         "Phân tích AI",
};

/** Tiêu đề trang phù hợp với vai trò hiện tại. */
function pageTitle(page) {
  if (Auth.isAdmin()) return pageTitles[page] || page;
  const userTitles = {
    dashboard: "Tổng quan",
    invoices:  "Hóa đơn của tôi",
    readings:  "Chỉ số của tôi",
    payments:  "Thanh toán của tôi",
    ai:        "Phân tích AI",
  };
  return userTitles[page] || pageTitles[page] || page;
}

function navigate(page) {
  if (!pages[page]) page = "dashboard";

  // Chặn truy cập trang quản trị bằng đường dẫn trực tiếp
  if (ADMIN_PAGES.has(page) && !Auth.isAdmin()) {
    showToast("Trang này chỉ dành cho quản trị viên", "warning");
    page = "dashboard";
    if (location.hash !== "#dashboard") history.replaceState(null, "", "#dashboard");
  }

  _currentPage = page;
  const isLogin = page === "login";

  document.body.classList.toggle("auth-mode", isLogin);

  // Đóng modal dùng chung khi chuyển trang
  const appModal = document.getElementById("app-modal");
  if (appModal) appModal.innerHTML = "";

  document.querySelectorAll(".nav-item").forEach(el => {
    const active = el.id === `nav-${page}`;
    el.classList.toggle("active", active);
    if (active) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });

  const title = pageTitle(page);
  const titleEl = document.getElementById("page-title");
  const crumbEl = document.getElementById("breadcrumb-current");
  if (titleEl) titleEl.textContent = title;
  if (crumbEl) crumbEl.textContent = title;
  document.title = `${title} · UtilityAI`;

  applyRoleUI();
  closeSidebar();

  const container = document.getElementById("page-container");
  if (container && pages[page]) pages[page](container);
  window.scrollTo(0, 0);
}

// ── Hash-based routing ───────────────────────────────────────
function handleRoute() {
  const hash = location.hash.replace("#", "") || "dashboard";

  // Chưa đăng nhập → chỉ cho vào trang đăng nhập
  if (!Auth.isLoggedIn() && hash !== "login") {
    history.replaceState(null, "", "#login");
    navigate("login");
    return;
  }
  // Đã đăng nhập → không cần quay lại trang đăng nhập
  if (Auth.isLoggedIn() && hash === "login") {
    history.replaceState(null, "", "#dashboard");
    navigate("dashboard");
    return;
  }
  navigate(hash);
}

window.addEventListener("hashchange", handleRoute);

document.querySelectorAll(".nav-item").forEach(el => {
  el.addEventListener("click", () => closeSidebar());
});

// Close modal / sidebar / chat on Escape
document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (document.body.classList.contains("chat-open") && typeof Chat !== "undefined") {
    Chat.close();
    return;
  }
  document.querySelector(".modal-overlay")?.remove();
  closeSidebar();
});

// ── Dashboard ────────────────────────────────────────────────
async function renderDashboard(container) {
  container.innerHTML = `
    <div class="loading-screen">
      <div class="spinner"></div>
      <p>Đang tải dữ liệu tổng quan…</p>
    </div>`;

  const [hhRes, meterRes, invRes, payRes, debtRes, alertRes, readingRes, healthRes] =
    await Promise.allSettled([
      Api.get("/api/households"),
      Api.get("/api/meters"),
      Api.get("/api/invoices"),
      Api.get("/api/payments"),
      Api.get("/api/payments/reports/debt"),
      Api.get("/api/payments/reports/alerts?resolved=false"),
      Api.get("/api/readings"),
      Api.get("/api/health"),
    ]);

  // Người dùng đã chuyển trang trong lúc chờ dữ liệu → bỏ qua kết quả cũ
  if (!isPageActive("dashboard")) return;

  const health = okValue(healthRes, null);
  const allFailed = [hhRes, meterRes, invRes, payRes, debtRes, alertRes, readingRes]
    .every(r => r.status === "rejected");

  if (allFailed && !health) {
    container.innerHTML = `
      <div class="panel">
        <div class="empty-state">
          <div class="empty-state-icon">🔌</div>
          <div class="empty-state-title">Không thể kết nối đến server</div>
          <div class="empty-state-text">Hãy chắc chắn <code>python main.py</code> đang chạy trên cổng 8000.</div>
          <button class="btn btn-primary" type="button" onclick="renderDashboard(document.getElementById('page-container'))">🔄 Thử lại</button>
        </div>
      </div>`;
    return;
  }

  const data = {
    households: okValue(hhRes, []),
    meters:     okValue(meterRes, []),
    invoices:   okValue(invRes, []),
    payments:   okValue(payRes, []),
    debts:      okValue(debtRes, []),
    alerts:     okValue(alertRes, []),
    readings:   okValue(readingRes, []),
    health,
  };

  if (Auth.isAdmin()) {
    renderAdminDashboard(container, data);
  } else {
    const household = data.households[0] || null;
    if (household) Auth.setHouseholdName(household.name);
    renderUserDashboard(container, data, household);
  }
}

/** Hero dùng chung — gọn, tập trung vào hành động chính. */
function dashboardHero({ eyebrow, title, sub, contact = "", actions, sideLabel, sideValue, sideBadge, sideBadgeClass = "badge-info" }) {
  return `
    <section class="hero compact">
      <div class="hero-content">
        <span class="hero-eyebrow">${eyebrow}</span>
        <h2 class="hero-title">${title}</h2>
        <p class="hero-sub">${sub}</p>
        ${contact ? `<div class="hero-contact">${contact}</div>` : ""}
        <div class="hero-actions">${actions}</div>
      </div>
      <div class="hero-side">
        <span class="hero-side-label">${sideLabel}</span>
        <span class="hero-side-date">${sideValue}</span>
        <span class="badge ${sideBadgeClass}">${sideBadge}</span>
      </div>
    </section>`;
}

function recentInvoiceRows(invoices, hhMap) {
  return invoices.map(inv => `
    <tr>
      <td><span class="cell-main">${escapeHtml(hhMap.get(inv.household_id)?.name || `Hộ #${inv.household_id}`)}</span>
        <span class="cell-sub">Hóa đơn #${inv.id}</span></td>
      <td><span class="badge badge-info">${escapeHtml(inv.period)}</span></td>
      <td class="num"><strong>${fmtMoney(inv.total_amount)}</strong></td>
      <td>${invoiceStatusBadge(inv.status)}</td>
      <td class="nowrap text-muted">${inv.due_date ? formatDateVN(inv.due_date) : "—"}</td>
    </tr>`).join("");
}

// ── Dashboard: ADMIN ─────────────────────────────────────────
function renderAdminDashboard(container, data) {
  const { households, meters, invoices, payments, debts, alerts, health } = data;
  const hhMap = new Map(households.map(h => [h.id, h]));

  const activeHouseholds = households.filter(h => h.status === "active").length;
  const electricityMeters = meters.filter(m => m.meter_type === "electricity").length;
  const waterMeters = meters.length - electricityMeters;

  const totalInvoiced = invoices.reduce((sum, inv) => sum + (inv.total_amount || 0), 0);
  const totalCollected = payments.reduce((sum, p) => sum + (p.amount_paid || 0), 0);
  const outstanding = Math.max(totalInvoiced - totalCollected, 0);
  const unpaidInvoices = invoices.filter(inv => inv.status !== "paid");
  const debtHouseholds = debts.filter(d => (d.outstanding_debt || 0) > 0).length;
  const collectionRate = totalInvoiced > 0 ? Math.min(100, Math.round((totalCollected / totalInvoiced) * 100)) : 0;

  // Phát sinh theo kỳ (6 kỳ gần nhất)
  const byPeriod = new Map();
  invoices.forEach(inv => {
    if (!inv.period) return;
    byPeriod.set(inv.period, (byPeriod.get(inv.period) || 0) + (inv.total_amount || 0));
  });
  const chartPeriods = [...byPeriod.keys()].sort().slice(-6);
  const chartMax = Math.max(1, ...chartPeriods.map(p => byPeriod.get(p) || 0));

  const chartHtml = chartPeriods.length
    ? `<div class="chart${chartPeriods.length === 1 ? " single" : ""}" role="img" aria-label="Biểu đồ phát sinh theo kỳ">
        ${chartPeriods.map(period => {
          const value = byPeriod.get(period) || 0;
          const height = Math.max(4, Math.round((value / chartMax) * 100));
          return `<div class="chart-col" title="${periodLabel(period)}: ${fmtMoney(value)}">
            <div class="chart-track"><div class="chart-bar" style="height:${height}%"></div></div>
            <span class="chart-label">${periodLabel(period)}</span>
          </div>`;
        }).join("")}
      </div>`
    : `<div class="empty-state" style="padding:26px 16px">
        <div class="empty-state-icon">📈</div>
        <div class="empty-state-title">Chưa có dữ liệu hóa đơn</div>
        <div class="empty-state-text">Tạo hóa đơn để xem biểu đồ phát sinh theo kỳ.</div>
      </div>`;

  const recentInvoices = [...invoices]
    .sort((a, b) => String(b.period).localeCompare(String(a.period)) || b.id - a.id)
    .slice(0, 5);

  const recentRows = recentInvoices.length
    ? recentInvoiceRows(recentInvoices, hhMap)
    : emptyRow(5, "🧾", "Chưa có hóa đơn nào", "Tạo hóa đơn từ trang Hóa đơn để bắt đầu.");

  const alertItems = alerts.slice(0, 4).map(a => `
    <div class="alert-item">
      <div class="alert-icon">⚠️</div>
      <div class="alert-body">
        <div class="alert-title">${escapeHtml(a.message)}</div>
        <div class="alert-meta">${escapeHtml(hhMap.get(a.household_id)?.name || `Hộ #${a.household_id}`)} · Kỳ ${escapeHtml(a.period)}</div>
      </div>
    </div>`).join("");

  const alertsHtml = alerts.length
    ? `<div class="alert-list">${alertItems}</div>`
    : `<div class="empty-state" style="padding:26px 16px">
        <div class="empty-state-icon">✅</div>
        <div class="empty-state-title">Không có cảnh báo</div>
        <div class="empty-state-text">Tiêu thụ của các hộ đang ở mức bình thường.</div>
      </div>`;

  const username = Auth.username || "bạn";
  const today = new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });

  const quickActions = [
    { href: "#readings",  icon: "📝", tone: "blue",   title: "Nhập chỉ số", desc: "Ghi chỉ số điện / nước" },
    { href: "#invoices",  icon: "🧾", tone: "purple", title: "Hóa đơn",     desc: "Tạo & theo dõi hóa đơn" },
    { href: "#payments",  icon: "💳", tone: "green",  title: "Thanh toán",  desc: "Thu tiền & công nợ" },
    { href: "#households",icon: "🏠", tone: "cyan",   title: "Hộ / Phòng",  desc: "Quản lý hộ gia đình" },
  ].map(item => `
    <a class="quick-card" href="${item.href}">
      <span class="quick-icon ${item.tone}">${item.icon}</span>
      <span class="quick-text">
        <span class="quick-title">${item.title}</span>
        <span class="quick-desc">${item.desc}</span>
      </span>
    </a>`).join("");

  container.innerHTML = `
    ${dashboardHero({
      eyebrow: "● Tổng quan vận hành",
      title: `Xin chào, ${escapeHtml(username)} 👋`,
      sub: "Theo dõi hộ, đồng hồ, hóa đơn và công nợ của toàn hệ thống trong một màn hình.",
      contact: `<span>🏠 ${households.length} hộ</span><span>🔌 ${meters.length} đồng hồ</span><span>🧾 ${invoices.length} hóa đơn</span>`,
      actions: `
        <a class="btn btn-primary" href="#readings">📝 Nhập chỉ số</a>
        <a class="btn btn-secondary" href="#invoices">🧾 Xem hóa đơn</a>
        <button class="btn btn-ghost" type="button" onclick="Chat.togglePanel()">🤖 Hỏi trợ lý AI</button>`,
      sideLabel: "Hôm nay",
      sideValue: escapeHtml(today),
      sideBadge: health && health.status === "ok" ? "● Kết nối ổn định" : "● Mất kết nối",
      sideBadgeClass: health && health.status === "ok" ? "badge-success" : "badge-danger",
    })}

    <div class="stats-grid">
      <a class="stat-card blue" href="#households">
        <div class="stat-icon">🏠</div>
        <div class="stat-info">
          <div class="stat-label">Hộ / Phòng</div>
          <div class="stat-value">${households.length}</div>
          <div class="stat-sub">${activeHouseholds} đang hoạt động</div>
        </div>
      </a>
      <a class="stat-card yellow" href="#meters">
        <div class="stat-icon">🔌</div>
        <div class="stat-info">
          <div class="stat-label">Đồng hồ</div>
          <div class="stat-value">${meters.length}</div>
          <div class="stat-sub">${electricityMeters} điện · ${waterMeters} nước</div>
        </div>
      </a>
      <a class="stat-card purple" href="#invoices">
        <div class="stat-icon">🧾</div>
        <div class="stat-info">
          <div class="stat-label">Hóa đơn</div>
          <div class="stat-value">${invoices.length}</div>
          <div class="stat-sub">${unpaidInvoices.length} chưa thanh toán</div>
        </div>
      </a>
      <a class="stat-card red" href="#payments">
        <div class="stat-icon">💳</div>
        <div class="stat-info">
          <div class="stat-label">Công nợ còn lại</div>
          <div class="stat-value sm">${fmtMoney(outstanding)}</div>
          <div class="stat-sub">${debtHouseholds} hộ còn nợ</div>
        </div>
      </a>
    </div>

    <div class="dashboard-grid">
      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">💰 Tổng quan tài chính</div>
            <div class="panel-sub">Số liệu trên toàn bộ hóa đơn đã phát hành</div>
          </div>
          <a class="panel-link" href="#payments">Chi tiết →</a>
        </div>

        <div class="finance-grid">
          <div class="finance-item">
            <div class="finance-label">Tổng phát sinh</div>
            <div class="finance-value">${fmtMoney(totalInvoiced)}</div>
          </div>
          <div class="finance-item">
            <div class="finance-label">Đã thu</div>
            <div class="finance-value green">${fmtMoney(totalCollected)}</div>
          </div>
          <div class="finance-item">
            <div class="finance-label">Còn nợ</div>
            <div class="finance-value red">${fmtMoney(outstanding)}</div>
          </div>
        </div>

        <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${collectionRate}">
          <div class="progress-bar" style="width:${collectionRate}%"></div>
        </div>
        <div class="progress-meta">
          <span>Tỷ lệ thu tiền</span>
          <strong>${collectionRate}%</strong>
        </div>

        <div class="section-title" style="margin:20px 0 2px">Phát sinh theo kỳ</div>
        ${chartHtml}
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">⚠️ Cảnh báo tiêu thụ</div>
            <div class="panel-sub">${alerts.length ? `${alerts.length} cảnh báo chưa xử lý` : "Không có bất thường"}</div>
          </div>
          <a class="panel-link" href="#ai">Phân tích →</a>
        </div>
        ${alertsHtml}
      </div>
    </div>

    <div class="section-title">Truy cập nhanh</div>
    <div class="quick-grid cols-4">${quickActions}</div>

    <div class="table-wrapper">
      <div class="table-header">
        <div>
          <div class="table-title">🧾 Hóa đơn gần đây</div>
          <div class="panel-sub">5 hóa đơn mới nhất theo kỳ</div>
        </div>
        <a class="panel-link" href="#invoices">Xem tất cả →</a>
      </div>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Hộ / Phòng</th>
              <th>Kỳ</th>
              <th class="num">Tổng tiền</th>
              <th>Trạng thái</th>
              <th>Hạn thanh toán</th>
            </tr>
          </thead>
          <tbody>${recentRows}</tbody>
        </table>
      </div>
    </div>`;
}

// ── Dashboard: USER (hộ gia đình) ────────────────────────────
function renderUserDashboard(container, data, household) {
  const { meters, invoices, payments, debts, alerts, readings } = data;

  if (!household) {
    container.innerHTML = `
      <div class="panel">
        <div class="empty-state">
          <div class="empty-state-icon">🏠</div>
          <div class="empty-state-title">Tài khoản chưa được gắn với hộ/phòng</div>
          <div class="empty-state-text">Vui lòng liên hệ quản trị viên để được cấp quyền xem dữ liệu hộ.</div>
          <button class="btn btn-secondary" type="button" onclick="doLogout()">Đăng xuất</button>
        </div>
      </div>`;
    return;
  }

  const hhMap = new Map([[household.id, household]]);
  const myDebt = debts.find(d => d.household_id === household.id);
  const outstanding = Math.max(myDebt?.outstanding_debt || 0, 0);
  const unpaidInvoices = invoices.filter(inv => inv.status !== "paid");
  const nextDue = invoices
    .filter(inv => inv.status !== "paid" && inv.due_date)
    .map(inv => inv.due_date)
    .sort()[0];

  // Kỳ có chỉ số mới nhất + mức tiêu thụ điện/nước của kỳ đó
  const periods = [...new Set(readings.map(r => r.period))].sort();
  const latestPeriod = periods[periods.length - 1] || "";
  const latestReadings = readings.filter(r => r.period === latestPeriod);
  const meterMap = new Map(meters.map(m => [m.id, m]));
  let electricity = 0, water = 0;
  latestReadings.forEach(r => {
    const meter = meterMap.get(r.meter_id);
    const value = Number(r.consumption) || 0;
    if (meter?.meter_type === "electricity") electricity += value;
    else if (meter?.meter_type === "water") water += value;
  });

  const today = new Date().toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit", year: "numeric" });
  const owner = household.owner_name || Auth.username;

  const recentInvoices = [...invoices]
    .sort((a, b) => String(b.period).localeCompare(String(a.period)) || b.id - a.id)
    .slice(0, 6);

  const recentRows = recentInvoices.length
    ? recentInvoices.map(inv => `
        <tr>
          <td><span class="badge badge-info">${escapeHtml(inv.period)}</span>
            <span class="cell-sub">Hóa đơn #${inv.id}</span></td>
          <td class="num"><strong>${fmtMoney(inv.total_amount)}</strong></td>
          <td>${invoiceStatusBadge(inv.status)}</td>
          <td class="nowrap text-muted">${inv.due_date ? formatDateVN(inv.due_date) : "—"}</td>
          <td class="text-right">
            <button class="btn btn-secondary btn-sm" type="button" onclick="viewInvoiceDetail(${inv.id})">Chi tiết</button>
          </td>
        </tr>`).join("")
    : emptyRow(5, "🧾", "Chưa có hóa đơn", "Hóa đơn của hộ sẽ xuất hiện tại đây khi được phát hành.");

  const alertItems = alerts.slice(0, 4).map(a => `
    <div class="alert-item">
      <div class="alert-icon">⚠️</div>
      <div class="alert-body">
        <div class="alert-title">${escapeHtml(a.message)}</div>
        <div class="alert-meta">Kỳ ${escapeHtml(a.period)}</div>
      </div>
    </div>`).join("");

  const alertsHtml = alerts.length
    ? `<div class="alert-list">${alertItems}</div>`
    : `<div class="empty-state" style="padding:26px 16px">
        <div class="empty-state-icon">✅</div>
        <div class="empty-state-title">Không có cảnh báo</div>
        <div class="empty-state-text">Mức tiêu thụ của hộ đang bình thường.</div>
      </div>`;

  const quickActions = [
    { href: "#invoices", icon: "🧾", tone: "purple", title: "Hóa đơn", desc: "Xem hóa đơn của hộ" },
    { href: "#payments", icon: "💳", tone: "green",  title: "Thanh toán", desc: "Công nợ & lịch sử thu" },
    { href: "#readings", icon: "📝", tone: "blue",   title: "Chỉ số", desc: "Tra cứu điện / nước" },
    { href: "#ai",       icon: "✨", tone: "red",    title: "Phân tích AI", desc: "Gợi ý tiết kiệm" },
  ].map(item => `
    <a class="quick-card" href="${item.href}">
      <span class="quick-icon ${item.tone}">${item.icon}</span>
      <span class="quick-text">
        <span class="quick-title">${item.title}</span>
        <span class="quick-desc">${item.desc}</span>
      </span>
    </a>`).join("");

  container.innerHTML = `
    ${dashboardHero({
      eyebrow: "🏠 Không gian của hộ",
      title: `Xin chào, ${escapeHtml(owner)} 👋`,
      sub: `${escapeHtml(household.name)}${household.address ? " · " + escapeHtml(household.address) : ""}`,
      contact: [
        household.phone ? `<span>📞 ${escapeHtml(household.phone)}</span>` : "",
        `<span>🔌 ${meters.length} đồng hồ</span>`,
        latestPeriod ? `<span>🗓️ Kỳ mới nhất ${escapeHtml(latestPeriod)}</span>` : "",
      ].filter(Boolean).join(""),
      actions: `
        <a class="btn btn-primary" href="#invoices">🧾 Hóa đơn của tôi</a>
        <a class="btn btn-secondary" href="#payments">💳 Thanh toán</a>
        <button class="btn btn-ghost" type="button" onclick="Chat.togglePanel()">🤖 Hỏi trợ lý AI</button>`,
      sideLabel: "Công nợ hiện tại",
      sideValue: fmtMoney(outstanding),
      sideBadge: unpaidInvoices.length ? `${unpaidInvoices.length} hóa đơn chưa trả` : "Đã thanh toán đủ",
      sideBadgeClass: unpaidInvoices.length ? "badge-warning" : "badge-success",
    })}

    <div class="stats-grid">
      <a class="stat-card purple" href="#invoices">
        <div class="stat-icon">🧾</div>
        <div class="stat-info">
          <div class="stat-label">Hóa đơn</div>
          <div class="stat-value">${invoices.length}</div>
          <div class="stat-sub">${unpaidInvoices.length} chưa thanh toán</div>
        </div>
      </a>
      <a class="stat-card red" href="#payments">
        <div class="stat-icon">💳</div>
        <div class="stat-info">
          <div class="stat-label">Còn phải trả</div>
          <div class="stat-value sm">${fmtMoney(outstanding)}</div>
          <div class="stat-sub">${nextDue ? `Hạn gần nhất ${formatDateVN(nextDue)}` : "Không có hóa đơn đến hạn"}</div>
        </div>
      </a>
      <a class="stat-card yellow" href="#readings">
        <div class="stat-icon">⚡</div>
        <div class="stat-info">
          <div class="stat-label">Điện kỳ này</div>
          <div class="stat-value sm">${latestPeriod ? `${fmtNumber(electricity, 1)} kWh` : "—"}</div>
          <div class="stat-sub">${latestPeriod ? `Kỳ ${latestPeriod}` : "Chưa có chỉ số"}</div>
        </div>
      </a>
      <a class="stat-card blue" href="#readings">
        <div class="stat-icon">💧</div>
        <div class="stat-info">
          <div class="stat-label">Nước kỳ này</div>
          <div class="stat-value sm">${latestPeriod ? `${fmtNumber(water, 1)} m³` : "—"}</div>
          <div class="stat-sub">${latestPeriod ? `Kỳ ${latestPeriod}` : "Chưa có chỉ số"}</div>
        </div>
      </a>
    </div>

    <div class="dashboard-grid">
      <div class="table-wrapper">
        <div class="table-header">
          <div>
            <div class="table-title">🧾 Hóa đơn gần đây</div>
            <div class="panel-sub">Hóa đơn mới nhất của hộ</div>
          </div>
          <a class="panel-link" href="#invoices">Xem tất cả →</a>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Kỳ</th>
                <th class="num">Tổng tiền</th>
                <th>Trạng thái</th>
                <th>Hạn thanh toán</th>
                <th></th>
              </tr>
            </thead>
            <tbody>${recentRows}</tbody>
          </table>
        </div>
      </div>

      <div class="panel">
        <div class="panel-head">
          <div>
            <div class="panel-title">⚠️ Cảnh báo tiêu thụ</div>
            <div class="panel-sub">${alerts.length ? `${alerts.length} cảnh báo chưa xử lý` : "Không có bất thường"}</div>
          </div>
          <a class="panel-link" href="#ai">Phân tích →</a>
        </div>
        ${alertsHtml}
      </div>
    </div>

    <div class="section-title">Truy cập nhanh</div>
    <div class="quick-grid cols-4">${quickActions}</div>

    <div class="panel" style="margin-top:18px">
      <div class="panel-head" style="margin-bottom:12px">
        <div>
          <div class="panel-title">🏠 Thông tin hộ</div>
          <div class="panel-sub">Dùng khi cần đối chiếu hợp đồng hoặc liên hệ quản lý</div>
        </div>
      </div>
      <div class="info-list">
        <div class="info-row"><span class="info-label">Hộ / Phòng</span><span class="info-value">${escapeHtml(household.name)}</span></div>
        <div class="info-row"><span class="info-label">Chủ hộ</span><span class="info-value">${escapeHtml(household.owner_name || "—")}</span></div>
        <div class="info-row"><span class="info-label">Số điện thoại</span><span class="info-value">${escapeHtml(household.phone || "—")}</span></div>
        <div class="info-row"><span class="info-label">Địa chỉ</span><span class="info-value">${escapeHtml(household.address || "—")}</span></div>
        <div class="info-row"><span class="info-label">Đồng hồ đang dùng</span><span class="info-value">${meters.length ? meters.map(m => escapeHtml(m.meter_number)).join(" · ") : "—"}</span></div>
        <div class="info-row"><span class="info-label">Đã thanh toán</span><span class="info-value">${fmtMoney(payments.reduce((s, p) => s + (p.amount_paid || 0), 0))}</span></div>
      </div>
    </div>`;
}

// ── Init ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  // Ngày hiện tại trên topbar
  const dateEl = document.getElementById("topbar-date");
  if (dateEl) {
    dateEl.textContent = new Date().toLocaleDateString("vi-VN", {
      weekday: "long", day: "2-digit", month: "2-digit", year: "numeric",
    });
  }

  applyRoleUI();

  // Khi phiên đăng nhập hết hiệu lực → quay về trang đăng nhập
  Api.onUnauthorized(() => {
    if (!Auth.isLoggedIn()) return;
    Auth.clear();
    Api.setCredentials("", "");
    applyRoleUI();
    showToast("Phiên đăng nhập đã hết hiệu lực, vui lòng đăng nhập lại", "warning");
    if (location.hash !== "#login") location.hash = "#login";
    else handleRoute();
  });

  // Kiểm tra health + cập nhật trạng thái topbar
  const statusEl = document.getElementById("system-status");
  try {
    await Api.get("/api/health");
    if (statusEl) statusEl.classList.remove("offline");
  } catch {
    if (statusEl) {
      statusEl.classList.add("offline");
      statusEl.innerHTML = `<span class="status-dot" aria-hidden="true"></span><span>Mất kết nối</span>`;
    }
    showToast("Không kết nối được server!", "error");
  }

  // Bổ sung tên hộ cho chip phạm vi nếu phiên trước chưa lưu
  if (Auth.isLoggedIn() && !Auth.isAdmin() && !Auth.householdName) {
    Api.get("/api/households")
      .then(list => { if (Array.isArray(list) && list[0]) Auth.setHouseholdName(list[0].name); })
      .catch(() => {});
  }

  handleRoute();
});
