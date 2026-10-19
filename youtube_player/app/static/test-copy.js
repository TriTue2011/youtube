"use strict";
/* Test-first cho nhiệm vụ "copy playlist và video trên web app".
   Đỏ trước khi copy.js tồn tại; xanh sau khi implement.
   Chạy: node youtube_player/app/static/test-copy.js
   (repo gốc ở cwd = /home/hatch/workspace/youtube-yt-muse) */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const STATIC = path.join(__dirname);
const copy = require(path.join(STATIC, "copy.js"));

// 1. Video YouTube thường -> URL watch chuẩn
assert.equal(
  copy.buildCopyText({ kind: "video", id: "dQw4w9WgXcQ", source: "youtube" }),
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "video youtube -> url watch",
);

// 2. Video có url sẵn (zing/facebook/http) -> dùng nguyên url
assert.equal(
  copy.buildCopyText({ kind: "video", id: "123456789", source: "facebook", url: "https://www.facebook.com/watch/?v=123456789" }),
  "https://www.facebook.com/watch/?v=123456789",
  "video co url san -> dung nguyen url",
);

// 3. Playlist -> URL playlist (kèm mã)
assert.equal(
  copy.buildCopyText({ kind: "playlist", id: "PLabcdefgh1234", source: "youtube" }),
  "https://www.youtube.com/playlist?list=PLabcdefgh1234",
  "playlist -> url playlist",
);

// 4. Không có id -> chuỗi rỗng (không copy rác)
assert.equal(copy.buildCopyText({ kind: "video" }), "", "thieu id -> rong");
assert.equal(copy.buildCopyText(null), "", "null -> rong");

// 5. copyText: dùng clipboard API khi có
async function main() {
  {
    let written = null;
    const fakeNavigator = { clipboard: { writeText: async (t) => { written = t; } } };
    let prompted = false;
    await copy.copyText("https://www.youtube.com/watch?v=abc", "Sao chép:", fakeNavigator, { prompt: () => { prompted = true; } });
    assert.equal(written, "https://www.youtube.com/watch?v=abc", "clipboard duoc goi dung chuoi");
    assert.equal(prompted, false, "khong can fallback khi clipboard ok");
  }

  // 6. copyText: fallback window.prompt khi clipboard lỗi
  {
    const fakeNavigator = { clipboard: { writeText: async () => { throw new Error("denied"); } } };
    let promptLabel = null, promptValue = null;
    const fakeWindow = { prompt: (label, value) => { promptLabel = label; promptValue = value; return value; } };
    await copy.copyText("abc123", "Sao chép mã:", fakeNavigator, fakeWindow);
    assert.equal(promptValue, "abc123", "fallback prompt dung chuoi");
    assert.equal(promptLabel, "Sao chép mã:", "fallback prompt dung nhan");
  }
}

main().then(() => {
  console.log("copy.js: tat ca test xanh");
}).catch((err) => {
  console.error(err);
  process.exit(1);
});

// 7. Nút copy xuất hiện đúng chỗ: app.js render nút cho từng mục lịch sử
const appSrc = fs.readFileSync(path.join(STATIC, "app.js"), "utf8");
assert.match(appSrc, /history-copy/, "app.js co nut copy trong danh sach lich su");
assert.match(appSrc, /copy-current-btn/, "app.js co nut copy muc dang phat");
assert.match(appSrc, /buildCopyText/, "app.js dung ham buildCopyText tu copy.js");
assert.match(appSrc, /copyText\(/, "app.js dung ham copyText tu copy.js");

// 8. index.html tải copy.js và có nút copy cho mục đang phát
const htmlSrc = fs.readFileSync(path.join(STATIC, "index.html"), "utf8");
assert.match(htmlSrc, /<script[^>]*src="copy\.js"[^>]*><\/script>/, "index.html tai copy.js");
assert.match(htmlSrc, /id="copy-current-btn"/, "index.html co nut copy muc dang phat");
