"use strict";
/* Test các hàm thuần của thanh tua và khôi phục loa trong thẻ (khối CARD-PROGRESS-HELPERS giữa hai mốc BEGIN/END).

   Chủ máy 19/10/2026:
   - «Có chỗ tua nhạc ngay trong hộp dưới các nút điều khiển nhạc»: loa như d50s không báo media_position nên thẻ ẩn thanh tua;
     nay thẻ ƯỚC giây đang phát bằng đồng hồ (từ lúc bài bắt đầu) để thanh luôn hiện.
   - «Thoát vào lại HA thì phải giữ trình phát ở loa nào, đang phát bài nào đến đâu rồi; nhiều bài trên nhiều loa thì giữ ở loa cuối
     cùng thoát app»: nhớ loa cuối và lúc bài bắt đầu trong localStorage, vào lại thì khôi phục.
   Chạy: node youtube_player_integration/tests/test-card-progress.js */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CARD = path.join(__dirname, "..", "..", "custom_components", "tritue_youtube_player", "www", "tritue-youtube-player-card.js");
const src = fs.readFileSync(CARD, "utf8");
const begin = "/* === BEGIN CARD-PROGRESS-HELPERS === */";
const end = "/* === END CARD-PROGRESS-HELPERS === */";
const i0 = src.indexOf(begin);
const i1 = src.indexOf(end);
assert.ok(i0 !== -1 && i1 !== -1 && i1 > i0, "thieu khoi CARD-PROGRESS-HELPERS trong file card");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(src.slice(i0 + begin.length, i1), sandbox, { filename: "card-progress-helpers" });
const { cardUocBatDau, cardUocTienDo, cardLuuHopLe, cardChonKhoiPhuc, cardKhoaPhien } = sandbox;
for (const name of ["cardUocBatDau", "cardUocTienDo", "cardLuuHopLe", "cardChonKhoiPhuc", "cardKhoaPhien"]) {
  assert.equal(typeof sandbox[name], "function", `co ${name}`);
}

const NOW = Date.UTC(2026, 9, 19, 17, 0, 0);
// Giá trị sinh ra trong «vm» có prototype khác bên ngoài: so qua JSON thay vì deepStrictEqual.
const eq = (actual, expected, message) => assert.deepStrictEqual(JSON.parse(JSON.stringify(actual)), expected, message);

// --- khoá phiên + bài
assert.equal(cardKhoaPhien({ session_id: "s1", id: "abc", queue_index: 3 }), "s1|abc|3");
assert.equal(cardKhoaPhien(null), "");

// --- ước lúc bắt đầu: lấy mốc SỚM NHẤT đã thấy (cập nhật muộn của máy phát không làm lùi đồng hồ)
let uoc = cardUocBatDau(null, "k1", 0, NOW - 30_000, NOW);
assert.equal(uoc.key, "k1");
assert.equal(uoc.batDauMs, NOW - 30_000, "bài bắt đầu theo lời máy phát: vị trí 0 lúc cập nhật");
uoc = cardUocBatDau(uoc, "k1", 0, NOW - 5_000, NOW);                      // máy phát làm mới bản ghi ở giây 25
assert.equal(uoc.batDauMs, NOW - 30_000, "mốc sớm nhất được giữ, không nhảy về 5 s trước");
uoc = cardUocBatDau(uoc, "k2", 0, NOW - 2_000, NOW);                      // sang bài khác
assert.equal(uoc.key, "k2");
assert.equal(uoc.batDauMs, NOW - 2_000, "bài mới: đồng hồ tính lại");
assert.equal(cardUocBatDau(null, "k3", 40, NOW - 10_000, NOW).batDauMs, NOW - 50_000, "vị trí 40 s lúc cập nhật 10 s trước → bắt đầu 50 s trước");
assert.equal(cardUocBatDau(null, "k4", NaN, NaN, NOW).batDauMs, NOW, "thiếu mọi thông tin → coi như vừa bắt đầu");
assert.ok(cardUocBatDau(null, "k5", 0, NOW + 60_000, NOW).batDauMs <= NOW, "cập nhật 'trong tương lai' (lệch đồng hồ) không tạo giây âm");

// --- giây ước
eq(cardUocTienDo(NOW - 75_000, NOW, 217), { viTri: 75, tong: 217 });
eq(cardUocTienDo(NOW - 999_000, NOW, 217), { viTri: 217, tong: 217 }, "không vượt tổng");
eq(cardUocTienDo(NOW - 75_000, NOW, 0), { viTri: 75, tong: 0 }, "không rõ thời lượng: có giây, tong = 0");
eq(cardUocTienDo(NOW - 75_000, NOW, undefined), { viTri: 75, tong: 0 });
assert.equal(cardUocTienDo(NaN, NOW, 217), null);
assert.equal(cardUocTienDo(NOW + 5_000, NOW, 217).viTri, 0, "không có giây âm");

// --- đọc kho lưu: chỉ nhận đúng khuôn, rác thì bỏ
eq(cardLuuHopLe(null), { chon: [], cuoi: "", uoc: null });
eq(cardLuuHopLe("không phải json"), { chon: [], cuoi: "", uoc: null });
const luu = cardLuuHopLe(JSON.stringify({
  chon: ["media_player.d50s", "media_player.cam", "script.evil", 5, "media_player.<img src=x onerror=1>"],
  cuoi: "media_player.cam",
  uoc: { key: "s1|a|0", batDauMs: NOW - 1000 },
}));
eq(luu.chon, ["media_player.d50s", "media_player.cam"], "chỉ giữ id media_player hợp lệ");
assert.equal(luu.cuoi, "media_player.cam");
eq(luu.uoc, { key: "s1|a|0", batDauMs: NOW - 1000 });
assert.equal(cardLuuHopLe(JSON.stringify({ cuoi: "script.x" })).cuoi, "", "cuối không phải media_player thì bỏ");
assert.equal(cardLuuHopLe(JSON.stringify({ uoc: { key: "k", batDauMs: "x" } })).uoc, null);
assert.ok(cardLuuHopLe(JSON.stringify({ chon: Array.from({ length: 50 }, (_, i) => `media_player.l${i}`) })).chon.length <= 8, "giới hạn số loa lưu");
assert.ok(cardLuuHopLe("x".repeat(100_000)).chon.length === 0, "chuỗi khổng lồ không làm gì");

// --- khôi phục loa
const CO_SAN = ["media_player.d50s", "media_player.cam", "media_player.tv"];
const P_D50S = { session_id: "s1", revision: 10, output_entity_ids: ["media_player.d50s"] };
const P_CAM = { session_id: "s2", revision: 7, output_entity_ids: ["media_player.cam"] };
// 1. nhiều phiên trên nhiều loa → giữ loa CUỐI CÙNG thoát app, dù phiên kia mới hơn
let kq = cardChonKhoiPhuc({ chon: ["media_player.cam"], cuoi: "media_player.cam", uoc: null }, [P_D50S, P_CAM], CO_SAN);
eq(kq, { chon: ["media_player.cam"], cuoi: "media_player.cam", phienId: "s2" });
// 2. không có loa cuối đã lưu → phiên mới nhất (revision cao nhất)
kq = cardChonKhoiPhuc(null, [P_CAM, P_D50S], CO_SAN);
assert.equal(kq.phienId, "s1");
eq(kq.chon, ["media_player.d50s"]);
// 3. loa cuối đã lưu không còn (biến mất / ẩn) → rơi về phiên mới nhất
kq = cardChonKhoiPhuc({ chon: ["media_player.da_xoa"], cuoi: "media_player.da_xoa", uoc: null }, [P_D50S, P_CAM], CO_SAN);
assert.equal(kq.phienId, "s1");
// 4. phiên nhiều loa: giữ cả nhóm, cuối = loa đã lưu nếu còn trong nhóm
const NHOM = { session_id: "s3", revision: 3, output_entity_ids: ["media_player.d50s", "media_player.tv"] };
kq = cardChonKhoiPhuc({ chon: ["media_player.tv"], cuoi: "media_player.tv", uoc: null }, [NHOM], CO_SAN);
eq(kq.chon, ["media_player.d50s", "media_player.tv"]);
assert.equal(kq.cuoi, "media_player.tv");
// 5. loa của phiên có loa không còn khả dụng → chỉ giữ loa còn dùng được
kq = cardChonKhoiPhuc(null, [{ ...NHOM, output_entity_ids: ["media_player.d50s", "media_player.mat"] }], CO_SAN);
eq(kq.chon, ["media_player.d50s"]);
// 6. không phiên nào đang chạy → vẫn giữ loa đã chọn lần trước (để vào lại thấy đúng loa)
kq = cardChonKhoiPhuc({ chon: ["media_player.cam", "media_player.mat"], cuoi: "media_player.cam", uoc: null }, [], CO_SAN);
eq(kq, { chon: ["media_player.cam"], cuoi: "media_player.cam", phienId: "" });
// 7. không phiên, không lưu → không làm gì
assert.equal(cardChonKhoiPhuc(null, [], CO_SAN), null);
assert.equal(cardChonKhoiPhuc({ chon: [], cuoi: "", uoc: null }, [], CO_SAN), null);
// 8. dữ liệu phiên hỏng không làm sập
assert.equal(cardChonKhoiPhuc(null, [null, {}, { output_entity_ids: "x" }], CO_SAN), null);

console.log("OK: test-card-progress.js — tat ca assert xanh");
