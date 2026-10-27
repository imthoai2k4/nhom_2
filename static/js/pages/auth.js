/** pages/auth.js — Đăng nhập / Đăng xuất */
function renderLogin() {
  const c = document.getElementById("page-container");
  c.innerHTML = `
    <div style="display:flex;justify-content:center;align-items:center;min-height:60vh">
      <div class="table-wrapper" style="max-width:400px;width:100%;padding:32px">
        <div style="text-align:center;margin-bottom:24px">
          <div style="font-size:2.5rem;margin-bottom:8px">⚡</div>
          <div style="font-size:1.3rem;font-weight:700;color:var(--text-primary)">UtilityAI</div>
          <div style="font-size:0.83rem;color:var(--text-secondary)">Đăng nhập để tiếp tục</div>
        </div>
        <div class="form-grid" style="gap:14px">
          <div class="form-group">
            <label class="form-label">Tên đăng nhập</label>
            <input id="login-user" class="form-control" placeholder="admin" autocomplete="username">
          </div>
          <div class="form-group">
            <label class="form-label">Mật khẩu</label>
            <input id="login-pass" class="form-control" type="password" placeholder="••••••••" autocomplete="current-password">
          </div>
        </div>
        <div id="login-error" style="color:var(--accent-red);font-size:0.82rem;margin-top:8px;display:none"></div>
        <button class="btn btn-primary" style="width:100%;margin-top:16px" onclick="doLogin()">🔑 Đăng nhập</button>
      </div>
    </div>`;

  // Enter key to submit
  document.getElementById("login-pass")?.addEventListener("keydown", e => {
    if (e.key === "Enter") doLogin();
  });
}

async function doLogin() {
  const username = document.getElementById("login-user").value.trim();
  const password = document.getElementById("login-pass").value;
  const errEl = document.getElementById("login-error");
  errEl.style.display = "none";

  if (!username) { errEl.textContent = "Nhập tên đăng nhập"; errEl.style.display = "block"; return; }

  try {
    const res = await Api.post("/api/auth/login", { username, password });
    // Save credentials
    localStorage.setItem("username", res.username);
    localStorage.setItem("role", res.role);
    localStorage.setItem("pwd", password);
    if (res.household_id) {
      localStorage.setItem("household_id", res.household_id);
    } else {
      localStorage.removeItem("household_id");
    }
    Api.setCredentials(res.username, password);

    // Update UI
    document.getElementById("display-username").textContent = res.username;
    document.getElementById("display-role").textContent = res.role === "admin" ? "Quản trị viên" : "Người dùng";

    showToast(`Xin chào ${res.username}! (${res.role})`, "success");
    location.hash = "#dashboard";
  } catch (e) {
    errEl.textContent = e.detail || "Tên đăng nhập hoặc mật khẩu không đúng";
    errEl.style.display = "block";
  }
}

function doLogout() {
  Auth.clear();
  Api.setCredentials("", "");
  document.getElementById("display-username").textContent = "—";
  document.getElementById("display-role").textContent = "Chưa đăng nhập";
  showToast("Đã đăng xuất", "info");
  location.hash = "#login";
}
