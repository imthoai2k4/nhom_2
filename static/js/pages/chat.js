/* =============================================================
   chat.js — Floating chat panel với trợ lý AI
   ============================================================= */

const Chat = (() => {
  let isOpen = false;
  let currentSessionId = null;
  let sessions = [];
  let sessionsDrawerOpen = false;
  let isSending = false;

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
          <div class="chat-welcome-suggest" id="chat-welcome-suggest"></div>
        </div>
      </div>

      <div class="chat-quick" id="chat-quick"></div>

      <div class="chat-input-area">
        <textarea
          id="chat-input"
          class="chat-input"
          placeholder="Nhập câu hỏi… (Enter gửi)"
          title="Enter để gửi, Shift+Enter để xuống dòng"
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

    // Gợi ý nhanh — dùng event delegation vì danh sách được dựng lại theo vai trò
    panel.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-q]");
      if (!btn) return;
      input.value = btn.dataset.q;
      autoResize();
      sendCurrentMessage();
    });

    applyRoleSuggestions();
  }

  /** Gợi ý câu hỏi phù hợp với vai trò hiện tại (admin xem mọi hộ, user xem hộ mình). */
  function applyRoleSuggestions() {
    const isAdmin = Auth.isAdmin();
    const welcome = document.getElementById("chat-welcome-suggest");
    const quick = document.getElementById("chat-quick");
    if (!welcome || !quick) return;

    const welcomeItems = isAdmin
      ? [
          ["SĐT hộ 101?", "🔍 SĐT hộ 101?"],
          ["Số đồng hồ điện phòng 102?", "⚡ Đồng hồ phòng 102?"],
          ["Hóa đơn gần nhất của hộ 101?", "🧾 Hóa đơn phòng 101?"],
          ["Có cảnh báo bất thường nào không?", "⚠️ Cảnh báo bất thường?"],
        ]
      : [
          ["Hóa đơn gần nhất của tôi?", "🧾 Hóa đơn của tôi"],
          ["Công nợ hiện tại của tôi?", "💳 Công nợ của tôi"],
          ["Mức tiêu thụ điện nước gần đây?", "📈 Tiêu thụ gần đây"],
          ["Có cảnh báo bất thường nào không?", "⚠️ Cảnh báo bất thường?"],
        ];

    const quickItems = isAdmin
      ? [
          ["SĐT hộ 101?", "🔍 SĐT hộ 101"],
          ["Công nợ phòng 102?", "💳 Công nợ"],
          ["Có cảnh báo nào?", "⚠️ Cảnh báo"],
        ]
      : [
          ["Hóa đơn của tôi?", "🧾 Hóa đơn của tôi"],
          ["Công nợ của tôi?", "💳 Công nợ"],
          ["Có cảnh báo nào?", "⚠️ Cảnh báo"],
        ];

    welcome.innerHTML = welcomeItems
      .map(([q, label]) => `<button data-q="${q}">${label}</button>`)
      .join("");
    quick.innerHTML = quickItems
      .map(([q, label]) => `<button class="chat-quick-btn" data-q="${q}">${label}</button>`)
      .join("");
  }

  function autoResize(e) {
    const el = e?.target || document.getElementById("chat-input");
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(140, el.scrollHeight) + "px";
  }

  // ── Toggle panel ──────────────────────────────────────────
  function togglePanel() {
    isOpen = !isOpen;
    const panel = document.getElementById("chat-panel");
    // Ẩn nút mở chat khi cửa sổ đang mở để không đè lên nút gửi tin nhắn
    document.body.classList.toggle("chat-open", isOpen);
    if (isOpen) {
      applyRoleSuggestions();
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

  /** Đóng cửa sổ chat và hiện lại nút mở chat. */
  function closePanel() {
    isOpen = false;
    document.body.classList.remove("chat-open");
    document.getElementById("chat-panel")?.classList.remove("open");
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
        <div class="chat-msg-content">${content}</div>
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
    return box.lastElementChild;
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
    if (isSending) return;

    const input = document.getElementById("chat-input");
    const send = document.getElementById("chat-send");
    const text = input.value.trim();
    if (!text) return;
    if (!Auth.isLoggedIn()) {
      showToast("Vui lòng đăng nhập để dùng chat", "warning");
      return;
    }

    isSending = true;
    send.disabled = true;

    // Chỉ hiển thị 1 bubble người dùng (optimistic), sau đó thay bằng bản
    // ghi từ server để lấy đúng id/thời gian — không append thêm lần nữa.
    const optimisticEl = appendMsg({
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    });

    input.value = "";
    input.style.height = "auto";
    appendLoading();

    try {
      const res = await Api.post("/api/chat/message", {
        session_id: currentSessionId,
        message: text,
      });
      removeLoading();
      currentSessionId = res.session_id;

      if (optimisticEl && res.user_message) {
        optimisticEl.outerHTML = renderMsgHtml(res.user_message);
      }
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
      isSending = false;
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
    // Hỗ trợ cả bảng nằm cuối tin nhắn (không có newline sau dòng cuối).
    html = html.replace(
      /((?:^\|.+\|.+(?:\r?\n|$))+)/gm,
      (block) => {
        const lines = block.trim().split(/\r?\n/);
        if (lines.length < 2) return block;
        const head = lines[0].split("|").slice(1, -1).map(s => s.trim());
        // bỏ line separator (---|---|---)
        const body = lines.slice(2).map(l => l.split("|").slice(1, -1).map(s => s.trim()));
        if (!body.length) return block;
        const headHtml = head.map(h => `<th>${h}</th>`).join("");
        const bodyHtml = body
          .map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`)
          .join("");
        // Wrapper giúp bảng rộng cuộn ngang thay vì bị cắt cột trên màn hình nhỏ.
        return `<div class="md-table-wrap"><table><thead><tr>${headHtml}</tr></thead>` +
               `<tbody>${bodyHtml}</tbody></table></div>`;
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

  /**
   * Backend lưu created_at/updated_at dạng UTC nhưng serialize không kèm 'Z'.
   * Thêm 'Z' để trình duyệt không hiểu nhầm là giờ địa phương (lệch 7 giờ).
   */
  function parseServerDate(iso) {
    if (!iso) return null;
    if (iso instanceof Date) return iso;
    const raw = String(iso).trim();
    if (!raw) return null;
    const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(raw);
    const normalized = hasZone ? raw : raw.replace(" ", "T") + "Z";
    const d = new Date(normalized);
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function formatTime(iso) {
    const d = parseServerDate(iso);
    if (!d) return "";
    return d.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
  }
  function formatDate(iso) {
    const d = parseServerDate(iso);
    if (!d) return "";
    return d.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" });
  }

  return { mount, togglePanel, newSession, close: closePanel };
})();

// Auto-mount khi DOM sẵn sàng
document.addEventListener("DOMContentLoaded", () => {
  Chat.mount();
});
