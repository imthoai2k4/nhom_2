/* =============================================================
   chat.js — Floating chat panel với trợ lý AI
   ============================================================= */

const Chat = (() => {
  let isOpen = false;
  let currentSessionId = null;
  let sessions = [];
  let sessionsDrawerOpen = false;

  // ── Mount UI ──────────────────────────────────────────────
  function mount() {
    // tránh mount 2 lần
    if (document.getElementById("chat-fab")) return;

    // FAB
    const fab = document.createElement("button");
    fab.id = "chat-fab";
    fab.className = "chat-fab";
    fab.title = "Mở chat AI";
    fab.innerHTML = "💬";
    fab.onclick = togglePanel;
    document.body.appendChild(fab);

    // Panel
    const panel = document.createElement("aside");
    panel.id = "chat-panel";
    panel.className = "chat-panel";
    panel.innerHTML = `
      <div class="chat-header">
        <div class="chat-header-left">
          <div class="chat-header-icon">🤖</div>
          <div>
            <div class="chat-header-title">Trợ lý AI</div>
            <div class="chat-header-sub">Hỏi về hóa đơn, tiêu thụ, cảnh báo…</div>
          </div>
        </div>
        <div class="chat-header-actions">
          <button class="chat-header-btn" id="chat-history-btn" title="Lịch sử hội thoại">🗂️</button>
          <button class="chat-header-btn" id="chat-new-btn" title="Hội thoại mới">➕</button>
          <button class="chat-header-btn" id="chat-close-btn" title="Đóng">✕</button>
        </div>
      </div>

      <!-- Drawer lịch sử sessions -->
      <div class="chat-sessions-drawer" id="chat-sessions-drawer">
        <div class="chat-sessions-drawer-header">
          <h4>📚 Lịch sử hội thoại</h4>
          <button class="chat-header-btn" id="chat-sessions-close" title="Đóng">✕</button>
        </div>
        <div id="chat-sessions-list" style="overflow-y:auto; flex:1"></div>
      </div>

      <div class="chat-messages" id="chat-messages">
        <div class="chat-welcome" id="chat-welcome">
          <div class="chat-welcome-icon">🤖</div>
          <div class="chat-welcome-title">Xin chào!</div>
          <div class="chat-welcome-sub">Tôi là trợ lý AI của hệ thống quản lý điện nước. Bạn có thể hỏi tôi về số điện thoại hộ gia đình, số đồng hồ, hóa đơn, cảnh báo bất thường…</div>
          <div class="chat-welcome-suggest">
            <button data-q="SĐT hộ 101?">🔍 SĐT hộ 101?</button>
            <button data-q="Số đồng hồ điện phòng 102?">⚡ Số đồng hồ phòng 102?</button>
            <button data-q="Hóa đơn tháng 7 phòng 101?">🧾 Hóa đơn phòng 101?</button>
            <button data-q="Có cảnh báo bất thường nào không?">⚠️ Cảnh báo bất thường?</button>
          </div>
        </div>
      </div>

      <div class="chat-quick" id="chat-quick">
        <button class="chat-quick-btn" data-q="SĐT hộ 101?">🔍 SĐT hộ 101</button>
        <button class="chat-quick-btn" data-q="Công nợ phòng 102?">💳 Công nợ</button>
        <button class="chat-quick-btn" data-q="Có cảnh báo nào?">⚠️ Cảnh báo</button>
      </div>

      <div class="chat-input-area">
        <textarea
          id="chat-input"
          class="chat-input"
          placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter xuống dòng)"
          rows="1"
        ></textarea>
        <button class="chat-send" id="chat-send" title="Gửi">➤</button>
      </div>
    `;
    document.body.appendChild(panel);

    // Wire events
    document.getElementById("chat-close-btn").onclick = togglePanel;
    document.getElementById("chat-new-btn").onclick = newSession;
    document.getElementById("chat-history-btn").onclick = toggleSessionsDrawer;
    document.getElementById("chat-sessions-close").onclick = toggleSessionsDrawer;
    document.getElementById("chat-send").onclick = sendCurrentMessage;

    const input = document.getElementById("chat-input");
    input.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendCurrentMessage();
      }
    });
    input.addEventListener("input", autoResize);

    // Gợi ý nhanh
    panel.querySelectorAll("[data-q]").forEach(btn => {
      btn.addEventListener("click", () => {
        const q = btn.dataset.q;
        input.value = q;
        autoResize();
        sendCurrentMessage();
      });
    });
  }

  function autoResize(e) {
    const el = e?.target || document.getElementById("chat-input");
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(120, el.scrollHeight) + "px";
  }

  // ── Toggle panel ──────────────────────────────────────────
  function togglePanel() {
    isOpen = !isOpen;
    const panel = document.getElementById("chat-panel");
    if (isOpen) {
      panel.classList.add("open");
      // focus input
      setTimeout(() => document.getElementById("chat-input")?.focus(), 250);
      // load sessions lần đầu
      if (sessions.length === 0) loadSessions();
    } else {
      panel.classList.remove("open");
    }
  }

  function newSession() {
    currentSessionId = null;
    renderMessages([]);
    closeSessionsDrawer();
  }

  // ── Sessions drawer ───────────────────────────────────────
  async function loadSessions() {
    try {
      const data = await Api.get("/api/chat/sessions");
      sessions = Array.isArray(data) ? data : [];
      renderSessionsList();
    } catch (e) {
      console.error("load sessions:", e);
    }
  }

  function renderSessionsList() {
    const list = document.getElementById("chat-sessions-list");
    if (!list) return;
    if (sessions.length === 0) {
      list.innerHTML = `<div class="chat-sessions-empty">Chưa có hội thoại nào</div>`;
      return;
    }
    list.innerHTML = sessions.map(s => `
      <div class="chat-session-item ${s.id === currentSessionId ? "active" : ""}" data-id="${s.id}">
        <span class="chat-session-item-title">${escapeHtml(s.title)}</span>
        <span class="chat-session-item-date">${formatDate(s.updated_at)}</span>
        <button class="chat-session-delete" data-del="${s.id}" title="Xóa">🗑️</button>
      </div>
    `).join("");
    list.querySelectorAll("[data-id]").forEach(el => {
      el.addEventListener("click", e => {
        if (e.target.dataset.del) return;
        openSession(parseInt(el.dataset.id));
      });
    });
    list.querySelectorAll("[data-del]").forEach(btn => {
      btn.addEventListener("click", async e => {
        e.stopPropagation();
        const id = parseInt(btn.dataset.del);
        if (!confirm("Xóa hội thoại này?")) return;
        try {
          await Api.delete(`/api/chat/sessions/${id}`);
          if (currentSessionId === id) {
            currentSessionId = null;
            renderMessages([]);
          }
          loadSessions();
          showToast("Đã xóa hội thoại", "success");
        } catch (err) {
          showToast("Lỗi xóa: " + (err.detail || err.message), "error");
        }
      });
    });
  }

  function toggleSessionsDrawer() {
    sessionsDrawerOpen = !sessionsDrawerOpen;
    document.getElementById("chat-sessions-drawer")
      .classList.toggle("open", sessionsDrawerOpen);
    if (sessionsDrawerOpen) loadSessions();
  }
  function closeSessionsDrawer() {
    sessionsDrawerOpen = false;
    document.getElementById("chat-sessions-drawer")?.classList.remove("open");
  }

  async function openSession(id) {
    try {
      const data = await Api.get(`/api/chat/sessions/${id}`);
      currentSessionId = data.session.id;
      renderMessages(data.messages);
      renderSessionsList();
      closeSessionsDrawer();
    } catch (e) {
      showToast("Không mở được hội thoại", "error");
    }
  }

  // ── Messages render ───────────────────────────────────────
  function renderMessages(messages) {
    const box = document.getElementById("chat-messages");
    const welcome = document.getElementById("chat-welcome");
    if (welcome) welcome.remove();

    if (!messages || messages.length === 0) {
      box.innerHTML = `<div class="chat-empty">Bắt đầu hội thoại mới…</div>`;
      return;
    }
    box.innerHTML = messages.map(m => renderMsgHtml(m)).join("");
    box.scrollTop = box.scrollHeight;
  }

  function renderMsgHtml(m) {
    const content = m.role === "assistant" ? renderMd(m.content) : escapeHtml(m.content);
    return `
      <div class="chat-msg ${m.role}">
        <div>${content}</div>
        <div class="chat-msg-meta">${formatTime(m.created_at)}</div>
      </div>
    `;
  }

  function appendMsg(m) {
    const box = document.getElementById("chat-messages");
    const empty = box.querySelector(".chat-empty");
    if (empty) empty.remove();
    const welcome = document.getElementById("chat-welcome");
    if (welcome) welcome.remove();
    box.insertAdjacentHTML("beforeend", renderMsgHtml(m));
    box.scrollTop = box.scrollHeight;
  }

  function appendLoading() {
    const box = document.getElementById("chat-messages");
    box.insertAdjacentHTML("beforeend", `
      <div class="chat-msg assistant loading" id="chat-loading">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    `);
    box.scrollTop = box.scrollHeight;
  }
  function removeLoading() {
    document.getElementById("chat-loading")?.remove();
  }

  // ── Send message ──────────────────────────────────────────
  async function sendCurrentMessage() {
    const input = document.getElementById("chat-input");
    const send = document.getElementById("chat-send");
    const text = input.value.trim();
    if (!text) return;
    if (!Auth.isLoggedIn()) {
      showToast("Vui lòng đăng nhập để dùng chat", "warning");
      return;
    }

    // user bubble (optimistic)
    appendMsg({
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    });

    input.value = "";
    input.style.height = "auto";
    send.disabled = true;
    appendLoading();

    try {
      const res = await Api.post("/api/chat/message", {
        session_id: currentSessionId,
        message: text,
      });
      removeLoading();
      currentSessionId = res.session_id;
      appendMsg(res.user_message);
      appendMsg(res.assistant_message);
      // cập nhật sessions list
      if (sessions.length === 0 || !sessions.find(s => s.id === res.session_id)) {
        loadSessions();
      }
    } catch (e) {
      removeLoading();
      appendMsg({
        role: "system",
        content: "❌ Lỗi: " + (e.detail || e.message || "Không thể gửi tin nhắn"),
        created_at: new Date().toISOString(),
      });
    } finally {
      send.disabled = false;
      input.focus();
    }
  }

  // ── Markdown đơn giản ─────────────────────────────────────
  function renderMd(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // code
    html = html.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');
    // bold
    html = html.replace(/\*\*([^*]+)\*\*/g, '<span class="md-strong">$1</span>');
    // italic
    html = html.replace(/(^|\W)\*([^*]+)\*(?=\W|$)/g, '$1<span class="md-em">$2</span>');
    // quote
    html = html.replace(/^&gt; (.+)$/gm, '<div class="md-quote">$1</div>');
    // bảng markdown đơn giản (header | col1 | col2)
    html = html.replace(
      /((?:^\|.+\|.+\n)+)/gm,
      (block) => {
        const lines = block.trim().split("\n");
        if (lines.length < 2) return block;
        const head = lines[0].split("|").slice(1, -1).map(s => s.trim());
        // bỏ line separator (---|---|---)
        const body = lines.slice(2).map(l => l.split("|").slice(1, -1).map(s => s.trim()));
        return `<table><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead>
                <tbody>${body.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
      }
    );
    // newline
    html = html.replace(/\n/g, "<br>");
    return html;
  }

  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
    } catch { return ""; }
  }
  function formatDate(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
    } catch { return ""; }
  }

  return { mount, togglePanel, newSession };
})();

// Auto-mount khi DOM sẵn sàng
document.addEventListener("DOMContentLoaded", () => {
  Chat.mount();
});
