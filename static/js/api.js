/**
 * api.js — Fetch wrapper tự động đính kèm xác thực header
 */
const Api = (() => {
  let _user = "", _pass = "";

  function setCredentials(u, p) { _user = u; _pass = p; }

  function _headers() {
    const h = { "Content-Type": "application/json" };
    if (_user) { h["X-Username"] = _user; h["X-Password"] = _pass; }
    return h;
  }

  async function _handle(res) {
    if (res.ok) return res.status === 204 ? null : res.json();
    let err;
    try { err = await res.json(); } catch { err = { detail: res.statusText }; }
    const e = new Error(err.detail || "Lỗi không xác định");
    e.detail = err.detail || "Lỗi không xác định";
    e.status = res.status;
    throw e;
  }

  const get    = (url)        => fetch(url, { headers: _headers() }).then(_handle);
  const post   = (url, body)  => fetch(url, { method: "POST",   headers: _headers(), body: JSON.stringify(body) }).then(_handle);
  const put    = (url, body)  => fetch(url, { method: "PUT",    headers: _headers(), body: JSON.stringify(body) }).then(_handle);
  const del    = (url)        => fetch(url, { method: "DELETE", headers: _headers() }).then(_handle);

  return { get, post, put, delete: del, setCredentials };
})();
