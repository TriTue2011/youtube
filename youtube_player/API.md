# Integration API v1

API này là hợp đồng clean-room giữa TriTue YouTube Player và custom integration
Home Assistant. Base URL là `http://b5248dd0-youtube-player:8099` khi cài app
từ repository này, hoặc `http://<host>:8099` khi chạy Docker.

## Xác thực

Mọi endpoint `/api/integration/*` yêu cầu header:

```http
Authorization: Bearer <integration-token>
```

Nếu không cấu hình token, server tự sinh một token, lưu tại
`/data/integration_token` và in ra log khởi động. Token là thông tin xác thực
cục bộ, không phải API key của YouTube hoặc license key.

## Endpoints

### `GET /api/integration/health`

Kiểm tra xác thực, phiên bản API và capability. Response thành công:

```json
{
  "success": true,
  "status": "ok",
  "api_version": "1",
  "app_version": "0.5.0",
  "capabilities": ["history", "play", "search", "session", "status", "stop", "zing_stream"],
  "sources": ["youtube", "zing"],
  "playback_sources": ["youtube", "zing", "http"]
}
```

### `GET /api/integration/status`

Trả về `state`, item tương thích API cũ, `history_count` và `session` dùng chung:

```json
{
  "revision": 42,
  "state": "playing",
  "position": 0,
  "duration": 213,
  "updated_at": "2026-08-29T12:00:00+00:00",
  "volume_level": null,
  "item": {
    "source": "youtube",
    "id": "dQw4w9WgXcQ",
    "title": "Never Gonna Give You Up",
    "artist": "Rick Astley",
    "album": "",
    "thumbnail": "https://...",
    "duration": 213
  },
  "queue": {"index": 0, "items": []},
  "output_entity_ids": ["media_player.phong_khach"],
  "supported_actions": ["stop"]
}
```

### `POST /api/integration/session`

Integration gọi endpoint này sau khi Home Assistant gửi media thành công tới
thiết bị vật lý. `source` nhận `youtube`, `zing` hoặc `http`; target YouTube/Zing
được đối chiếu với kết quả tìm kiếm gần nhất để giữ metadata và queue.

```json
{
  "source": "zing",
  "target": "https://zingmp3.vn/bai-hat/Ten-Bai/SONGID.html",
  "output_entity_ids": ["media_player.phong_khach"],
  "media_content_type": "audio/mpeg",
  "volume_level": 0.35
}
```

### `GET /api/integration/history`

Trả về `{ "success": true, "items": [...], "total": 1 }`. Mỗi mục chứa
`kind`, `id` và URL nhúng privacy-enhanced đã chuẩn hóa.

### `GET /api/integration/search?source=SOURCE&q=QUERY&limit=20`

Tìm tối đa 30 kết quả bài hát và trả metadata gồm `id`, `url`, `title`,
`channel`, `duration` và `thumbnail`. Nguồn YouTube dùng `yt-dlp` ở chế độ
`--flat-playlist --skip-download`: không cần YouTube Data API key, không tải
hoặc relay nội dung media. `source` nhận `youtube` hoặc `zing`; mặc định là
`youtube`. Zing dùng endpoint gợi ý web công khai và chỉ trả metadata, không
khẳng định bài đó phát được cho tới bước tạo stream.

### `POST /api/integration/stream`

```json
{
  "source": "zing",
  "target": "https://zingmp3.vn/bai-hat/Ten-Bai-Hat/SONGID.html"
}
```

Chỉ nhận URL bài Zing công khai. Server kiểm tra trước khả năng resolve rồi trả
`stream_url` có chữ ký, hạn dùng một giờ và `media_content_type`. Loa có thể tải
URL này mà không cần biết bearer token. URL được relay qua add-on, hỗ trợ Range,
không lưu tệp và không chuyển mã. `public_base_url`/`PUBLIC_BASE_URL` phải là URL
LAN mà loa truy cập được. YouTube không được hỗ trợ ở endpoint này.
URL đích phải nằm trong kết quả Zing công khai mà chính server trả về trong vòng
60 phút gần nhất; URL nhập trực tiếp hoặc kết quả thiếu cờ quyền phát sẽ bị từ
chối.

### `POST /api/integration/play`

```json
{"target": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
```

`target` nhận URL video, Shorts, playlist hoặc video ID 11 ký tự. Trang web
player đang mở nhận lệnh trong tối đa khoảng hai giây.

### `POST /api/integration/stop`

Dừng và xóa nội dung khỏi trang web player đang mở. Request thông thường không
cần body. Khi rollback một lệnh phát lỗi, integration gửi revision mà chính
lệnh đó đã tạo để không dừng nhầm phiên mới hơn của trình duyệt khác:

```json
{"expected_revision": 42}
```

Nếu revision hiện tại đã khác, response có `"stopped": false` và giữ nguyên
session mới.

## Lỗi ổn định

- `400 {"error":"invalid_request"}`: JSON/body không hợp lệ.
- `400 {"error":"invalid_youtube_target"}`: URL hoặc ID không được hỗ trợ.
- `401 {"error":"invalid_auth"}`: thiếu hoặc sai Bearer token.
- `403 {"error":"unverified_zing_target"}`: URL Zing không thuộc kết quả tìm
  kiếm công khai gần nhất hoặc metadata không xác nhận quyền phát công khai.
- `502 {"error":"search_unavailable"}`: nguồn metadata tìm kiếm tạm lỗi.
- `502 {"error":"stream_unavailable"}`: bài Zing không công khai, là VIP hoặc
  provider hiện không resolve được.
- `503 {"error":"integration_not_configured"}`: server được tạo thủ công mà
  không có token; tiến trình Docker/add-on bình thường luôn tự sinh token.
