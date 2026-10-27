/** pages/auth.js — Đăng nhập / Đăng xuất */
function renderLogin() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div class="auth-shell">
      <div class="auth-card">
        <div class="auth-brand">
          <div class="auth-logo" aria-hidden="true">⚡</div>
          <div class="auth-title">UtilityAI</div>
          <div class="auth-sub">Hệ thống quản lý hóa đơn điện nước</div>
        </div>

        <form class="form-grid" style="gap:14px" onsubmit="event.preventDefault(); doLogin();">
          <div class="form-group">
            <label class="form-label" for="login-user">Tên đăng nhập</label>
            <input id="login-user" class="form-control" placeholder="admin" autocomplete="username" autofocus>
          </div>
          <div class="form-group">
            <label class="form-label" for="login-pass">Mật khẩu</label>
            <div style="position:relative">
              <input id="login-pass" class="form-control" type="password" placeholder="••••••••" autocomplete="current-password" style="padding-right:44px">
              <button class="icon-btn" type="button" onclick="togglePasswordVisibility()" aria-label="Hiện / ẩn mật khẩu"
                style="position:absolute;right:4px;top:50%;transform:translateY(-50%)">👁️</button>
            </div>
          </div>

          <div id="login-error" class="auth-error" style="display:none" role="alert"></div>

          <button class="btn btn-primary btn-block" type="submit" style="margin-top:2px">🔑 Đăng nhập</button>
        </form>

        <div class="auth-hint">
          <div class="auth-hint-title">Đăng nhập nhanh (tài khoản demo)</div>
          <div class="auth-demo">
            <button type="button" onclick="fillDemoAccount('admin','admin123')">👑 Quản trị viên · admin</button>
            <button type="button" onclick="fillDemoAccount('ho101','ho101')">🏠 Hộ gia đình · ho101</button>
          </div>
        </div>
      </div>
    </div>`;

  document.getElementById("login-pass")?.addEventListener("keydown", e => {
    if (e.key === "Enter") doLogin();
  });
  document.getElementById("login-user")?.addEventListener("keydown", e => {
    if (e.key === "Enter") document.getElementById("login-pass")?.focus();
  });
}

function fillDemoAccount(username, password) {
  const userEl = document.getElementById("login-user");
  const passEl = document.getElementById("login-pass");
  if (userEl) userEl.value = username;
  if (passEl) passEl.value = password;
  passEl?.focus();
}

function togglePasswordVisibility() {
  const input = document.getElementById("login-pass");
  if (!input) return;
  input.type = input.type === "password" ? "text" : "password";
}

async function doLogin() {
  const username = document.getElementById("login-user").value.trim();
  const password = document.getElementById("login-pass").value;
  const errEl = document.getElementById("login-error");
  errEl.style.display = "none";

  if (!username || !password) {
    errEl.textContent = "Vui lòng nhập tên đăng nhập và mật khẩu";
    errEl.style.display = "block";
    return;
  }

  const btn = document.querySelector(".auth-card .btn-primary");
  if (btn) { btn.disabled = true; btn.textContent = "Đang đăng nhập…"; }

  try {
    const res = await Api.post("/api/auth/login", { username, password });
    Auth.saveSession(res, password);
    applyRoleUI();

    // Ghi nhớ tên hộ để hiển thị chip phạm vi dữ liệu trên thanh trên
    if (res.role !== "admin") {
      Api.get("/api/households")
        .then(list => { if (Array.isArray(list) && list[0]) Auth.setHouseholdName(list[0].name); })
        .catch(() => {});
    }

    showToast(`Xin chào ${res.username}!`, "success");
    if (location.hash === "#dashboard") handleRoute();
    else location.hash = "#dashboard";
  } catch (e) {
    errEl.textContent = e.detail || "Tên đăng nhập hoặc mật khẩu không đúng";
    errEl.style.display = "block";
    if (btn) { btn.disabled = false; btn.innerHTML = "🔑 Đăng nhập"; }
  }
}

function doLogout() {
  Auth.clear();
  Api.setCredentials("", "");
  applyRoleUI();
  showToast("Đã đăng xuất", "info");
  document.querySelector(".modal-overlay")?.remove();
  if (typeof Chat !== "undefined" && Chat.close) Chat.close();
  else document.body.classList.remove("chat-open");
  if (location.hash === "#login") handleRoute();
  else location.hash = "#login";
}
