"use strict";
/* Test-first cho bug "nút copy trên dòng playlist chép ra blob TTPL1 khổng lồ".
   Logic dựng chuỗi copy của thẻ nằm trong file card, giữa hai mốc
   BEGIN/END CARD-COPY-HELPERS — test trích đoạn đó ra và chạy bằng node,
   không cần trình duyệt.

   Đỏ trước khi helper tồn tại trong file card; xanh sau khi sửa.
   Chạy: node youtube_player_integration/tests/test-card-copy.js */
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
vm.runInContext(helpers, sandbox, { filename: "card-copy-helpers" });
const {
  cardCopyPlaylistText,
  cardCopyItemText,
  cardCopyQueueText,
} = sandbox;
assert.equal(typeof cardCopyPlaylistText, "function", "co cardCopyPlaylistText");
assert.equal(typeof cardCopyItemText, "function", "co cardCopyItemText");
assert.equal(typeof cardCopyQueueText, "function", "co cardCopyQueueText");

// 1. Playlist có mã nội bộ 12 ký tự -> chép đúng mã, KHÔNG phải blob
assert.equal(
  cardCopyPlaylistText({ id: "abcdef012345", name: "Nhạc vàng" }),
  "playlist_code: abcdef012345",
  "playlist id 12 ky tu -> playlist_code dung",
);

// 2. BUG: playlist mà id là blob TTPL1 (toàn bộ nội dung nén) -> KHÔNG chép blob
const blob = "TTPL1." + "eNqrVkrLz1ey".repeat(400);
assert.ok(blob.length > 4000, "blob gia lap phai lon");
assert.equal(
  cardCopyPlaylistText({ id: blob, name: "Nhạc vàng" }),
  "",
  "id la blob TTPL1 -> tra rong, khong chep blob",
);

// 3. Playlist thiếu id / id lạ -> rỗng, không chép rác
assert.equal(cardCopyPlaylistText({ name: "X" }), "", "thieu id -> rong");
assert.equal(cardCopyPlaylistText(null), "", "null -> rong");
assert.equal(cardCopyPlaylistText({ id: "PLabcdefgh1234" }), "", "id dang youtube -> rong");

// 4. Bài hát YouTube: chép source + mã video 11 ký tự
assert.equal(
  cardCopyItemText({ id: "dQw4w9WgXcQ", source: "youtube", title: "X" }, "youtube"),
  "source: youtube\ntarget: dQw4w9WgXcQ",
  "bai youtube -> source/target dung",
);

// 5. Bài hát chỉ có url (zing/facebook/http) -> dùng url
assert.equal(
  cardCopyItemText(
    { source: "zing", url: "https://zingmp3.vn/bai-hat/Abc12345.html", title: "Y" },
    "youtube",
  ),
  "source: zing\ntarget: https://zingmp3.vn/bai-hat/Abc12345.html",
  "bai chi co url -> dung url",
);

// 6. BUG: bài hát mà id là blob TTPL1 -> KHÔNG chép blob
assert.equal(
  cardCopyItemText({ id: blob, source: "youtube", title: "Z" }, "youtube"),
  "",
  "id bai la blob TTPL1 -> tra rong",
);

// 7. Bài hát không có id lẫn url -> rỗng
assert.equal(cardCopyItemText({ source: "youtube", title: "W" }, "youtube"), "", "thieu ca id va url -> rong");
assert.equal(cardCopyItemText(null, "youtube"), "", "null -> rong");

// 8. Hàng đợi: chép đúng queue_code
assert.equal(
  cardCopyQueueText("media_player.loa_phong_khach"),
  "queue_code: media_player.loa_phong_khach",
  "queue key -> queue_code dung",
);
assert.equal(
  cardCopyQueueText("abcd1234efgh"),
  "queue_code: abcd1234efgh",
  "ma hang doi duy nhat 12 ky tu -> queue_code dung",
);
assert.equal(cardCopyQueueText(""), "", "queue key rong -> rong");

console.log("OK: test-card-copy.js — tat ca assert xanh");
