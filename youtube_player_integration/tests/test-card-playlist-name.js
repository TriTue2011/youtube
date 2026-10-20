"use strict";
/* Hàm thuần «tìm playlist theo tên» của thẻ (khối CARD-PLAYLIST-NAME-HELPERS): gõ lại tên đã có không được đẻ playlist trùng.
   Chạy: node youtube_player_integration/tests/test-card-playlist-name.js */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const CARD = path.join(__dirname, "..", "..", "custom_components", "tritue_youtube_player", "www", "tritue-youtube-player-card.js");
const src = fs.readFileSync(CARD, "utf8");
const begin = "/* === BEGIN CARD-PLAYLIST-NAME-HELPERS === */";
const end = "/* === END CARD-PLAYLIST-NAME-HELPERS === */";
const i0 = src.indexOf(begin);
const i1 = src.indexOf(end);
assert.ok(i0 !== -1 && i1 > i0, "thieu khoi CARD-PLAYLIST-NAME-HELPERS trong file card");
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(src.slice(i0 + begin.length, i1) + "\nthis.tim = cardTimPlaylistTheoTen;", sandbox);
const tim = sandbox.tim;

const ds = [{ id: "aaaaaaaaaaaa", name: "Account cafe" }, { id: "bbbbbbbbbbbb", name: "home" }];
assert.equal(tim(ds, "home").id, "bbbbbbbbbbbb");
assert.equal(tim(ds, "  HOME ").id, "bbbbbbbbbbbb", "không phân biệt hoa/thường, bỏ khoảng trắng đầu cuối");
assert.equal(tim(ds, "account   CAFE").id, "aaaaaaaaaaaa", "gộp khoảng trắng giữa");
assert.equal(tim(ds, "Home 2"), null);
assert.equal(tim(ds, ""), null);
assert.equal(tim(ds, "   "), null);
assert.equal(tim(null, "home"), null, "chưa tải danh sách thì coi như chưa có");
assert.equal(tim([null, { id: "c" }, { id: "d", name: "x" }], "x").id, "d", "bỏ qua phần tử hỏng");
console.log("test-card-playlist-name: OK");
