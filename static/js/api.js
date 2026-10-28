/**
 * api.js — Fetch wrapper tự động đính kèm xác thực header
 * Khi server trả 401 (hết phiên / sai thông tin), gọi callback onUnauthorized.
 */
const Api = (() => {
  const _baseUrl = String(window.API_BASE_URL || "").replace(/\/$/, "");
  let _user = "", _pass = "";
  let _onUnauthorized = null;

  function setCredentials(u, p) { _user = u; _pass = p; }

  function onUnauthorized(fn) { _onUnauthorized = fn; }

  function _headers() {
    const h = { "Content-Type": "application/json" };
    if (_user) { h["X-Username"] = _user; h["X-Password"] = _pass; }
    return h;
  }

  async function _handle(res) {
    if (res.ok) return res.status === 204 ? null : res.json();

    let err;
    try { err = await res.json(); } catch { err = { detail: res.statusText }; }

    // 422 của FastAPI có detail là mảng lỗi → chuyển thành câu dễ đọc
    let detail = err.detail;
    if (Array.isArray(detail)) {
      detail = detail.map(d => d.msg).filter(Boolean).join("; ") || "Dữ liệu không hợp lệ";
    }

    if (res.status === 401 && _onUnauthorized) _onUnauthorized();

    const e = new Error(detail || "Lỗi không xác định");
    e.detail = detail || "Lỗi không xác định";
    e.status = res.status;
    throw e;
  }

  const _url = (url) => /^https?:\/\//i.test(url) ? url : `${_baseUrl}${url}`;
  const get    = (url)        => fetch(_url(url), { headers: _headers() }).then(_handle);
  const post   = (url, body)  => fetch(_url(url), { method: "POST",   headers: _headers(), body: JSON.stringify(body) }).then(_handle);
  const put    = (url, body)  => fetch(_url(url), { method: "PUT",    headers: _headers(), body: JSON.stringify(body) }).then(_handle);
  const del    = (url)        => fetch(_url(url), { method: "DELETE", headers: _headers() }).then(_handle);

  return { get, post, put, delete: del, setCredentials, onUnauthorized };
})();
