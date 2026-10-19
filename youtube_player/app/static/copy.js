/* Helper copy dùng chung cho web app TriTue YouTube Player.
   Tái dùng pattern của thẻ Home Assistant: clipboard API, hỏng thì
   window.prompt làm đường lùi (app HA trên điện thoại hay chặn clipboard).
   File plain script (không module): nạp trước app.js bằng <script src="copy.js">. */
(function (root) {
  "use strict";

  /* Dựng chuỗi copy cho một mục phát.
     - playlist: URL playlist YouTube (kèm mã, dùng mở lại hoặc import);
     - còn lại: url có sẵn, không có thì ghép URL watch từ video id.
     Trả chuỗi rỗng khi không có gì để copy (nút ẩn). */
  function buildCopyText(target) {
    if (!target || typeof target !== "object") return "";
    const id = String(target.id || "").trim();
    if (!id) return "";
    if (target.kind === "playlist") {
      return "https://www.youtube.com/playlist?list=" + encodeURIComponent(id);
    }
    const url = String(target.url || "").trim();
    if (/^https?:\/\//i.test(url)) return url;
    return "https://www.youtube.com/watch?v=" + encodeURIComponent(id);
  }

  /* Chép text vào clipboard; hỏng thì mở window.prompt để người dùng copy tay.
     navigatorRef/windowRef để test có thể tiêm bản giả. */
  async function copyText(text, label, navigatorRef, windowRef) {
    const str = String(text || "");
    if (!str) return;
    const nav = navigatorRef || (root.navigator || {});
    const win = windowRef || (root.window || root);
    try {
      if (!nav.clipboard || typeof nav.clipboard.writeText !== "function") {
        throw new Error("no_clipboard");
      }
      await nav.clipboard.writeText(str);
    } catch (_error) {
      if (win && typeof win.prompt === "function") {
        win.prompt(label || "Sao chép mã:", str);
      }
    }
  }

  const api = { buildCopyText: buildCopyText, copyText: copyText };
  root.TriTueCopy = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
