"use strict";
/* NV208 — test-first cho bug "nút SAO CHÉP trên thẻ chép sai mã cho bài Zing
   (và mọi nguồn cần URL)".
   Quy tắc NV201 phía tích hợp (`sessions.item_target`): URL trước, id sau —
   máy phát chuẩn hoá được từ URL với youtube/facebook nhưng BẮT BUỘC URL đầy
   đủ với zing (`validate_zing_target`). Thẻ phải theo CÙNG quy tắc qua một hàm
   chọn target dùng chung `cardChonTarget`.
   Test trích khối BEGIN/END CARD-COPY-HELPERS trong file card và chạy bằng node.
   Chạy: node youtube_player_integration/tests/test-card-copy-target-nv208.js */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CARD = path.join(__dirname, "..", "..", "custom_components", "tritue_youtube_player", "www", "tritue-youtube-player-card.js");
const src = fs.readFileSync(CARD, "utf8");
const begin = "/* === BEGIN CARD-COPY-HELPERS === */";
const end = "/* === END CARD-COPY-HELPERS === */";
const i0 = src.indexOf(begin);
const i1 = src.indexOf(end);
assert.ok(i0 !== -1 && i1 !== -1 && i1 > i0, "thieu khoi CARD-COPY-HELPERS trong file card");

const helpers = src.slice(i0 + begin.length, i1);
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(helpers, sandbox, { filename: "card-copy-helpers-nv208" });
const { cardCopyItemText, cardChonTarget } = sandbox;
assert.equal(typeof cardCopyItemText, "function", "co cardCopyItemText");
assert.equal(typeof cardChonTarget, "function", "co cardChonTarget (ham chon target dung chung)");

// 1. Zing: có cả id (mã trần) và url -> chép URL, KHÔNG chép mã trần
const zingUrl = "https://zingmp3.vn/bai-hat/AbcDeFgH1234.html";
assert.equal(
  cardCopyItemText({ id: "AbcDeFgH1234", url: zingUrl, source: "zing", title: "Z" }, "youtube"),
  `source: zing\ntarget: ${zingUrl}`,
  "zing co ca id va url -> target la URL",
);
assert.equal(cardChonTarget({ id: "AbcDeFgH1234", url: zingUrl }), zingUrl, "cardChonTarget zing -> URL");

// 2. Facebook: có cả id và url -> chép URL
const fbUrl = "https://www.facebook.com/watch/?v=1234567890123456";
assert.equal(
  cardCopyItemText({ id: "1234567890123456", url: fbUrl, source: "facebook", title: "F" }, "youtube"),
  `source: facebook\ntarget: ${fbUrl}`,
  "facebook co ca id va url -> target la URL",
);

// 3. YouTube: có cả id và url -> chép URL (cùng thứ tự, không ngoại lệ theo nguồn)
const ytUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
assert.equal(
  cardCopyItemText({ id: "dQw4w9WgXcQ", url: ytUrl, source: "youtube", title: "Y" }, "youtube"),
  `source: youtube\ntarget: ${ytUrl}`,
  "youtube co ca id va url -> target la URL",
);

// 4. http: có cả id và url -> chép URL
const httpUrl = "https://example.com/audio/bai.mp3";
assert.equal(
  cardCopyItemText({ id: httpUrl, url: httpUrl, source: "http", title: "H" }, "youtube"),
  `source: http\ntarget: ${httpUrl}`,
  "http -> target la URL",
);

// 5. Bài chỉ có id (không url) -> vẫn chép id (tương thích ngược: YouTube chỉ có mã video)
assert.equal(
  cardCopyItemText({ id: "dQw4w9WgXcQ", source: "youtube", title: "X" }, "youtube"),
  "source: youtube\ntarget: dQw4w9WgXcQ",
  "chi co id -> target la id",
);
assert.equal(cardChonTarget({ id: "dQw4w9WgXcQ" }), "dQw4w9WgXcQ", "cardChonTarget chi id -> id");

// 6b. Blob cho test 7
const blob = "TTPL1." + "eNqrVkrLz1ey".repeat(400);
assert.ok(blob.length > 4000, "blob gia lap phai lon");

// 6. Mục thiếu cả id lẫn url -> rỗng
assert.equal(cardCopyItemText({ source: "zing", title: "W" }, "youtube"), "", "thieu ca id va url -> rong");
assert.equal(cardChonTarget({}), "", "cardChonTarget rong -> rong");

// 7. Blob TTPL1 ở id nhưng url hợp lệ -> chép URL (không còn bị chặn oan);
//    blob ở URL (hoặc cả hai) -> rỗng như cũ
assert.equal(
  cardCopyItemText({ id: blob, url: ytUrl, source: "youtube" }, "youtube"),
  `source: youtube\ntarget: ${ytUrl}`,
  "id blob + url hop le -> chep URL",
);
assert.equal(cardCopyItemText({ id: "dQw4w9WgXcQ", url: blob, source: "youtube" }, "youtube"), "", "url blob -> rong");

// 8. trim: url toàn khoảng trắng -> rơi về id
assert.equal(
  cardChonTarget({ id: "abc123", url: "   " }),
  "abc123",
  "url trang -> roi ve id",
);

console.log("OK: test-card-copy-target-nv208.js — tat ca assert xanh");
