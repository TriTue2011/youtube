# TriTue YouTube Player cho Home Assistant

Phát **nhạc YouTube, Zing MP3 và HTTP audio ra bất kỳ loa nào** trong Home
Assistant — loa Google Cast, DLNA, ESPHome hay mọi `media_player` hỗ trợ
`play_media` — điều khiển từ một Lovelace card duy nhất. YouTube ra loa hoạt
động giống hệt TTS: add-on tự lấy luồng audio rồi tiếp sóng cho loa.

Không cần license key. Token in trong log add-on chỉ là khóa kết nối nội bộ giữa
integration và add-on, **không phải khóa kích hoạt** — đừng đăng công khai.

## Gồm ba phần

| Thành phần | Thư mục | Công dụng |
|---|---|---|
| Add-on / Docker image | [`youtube_player`](youtube_player/) | Tìm kiếm, Web UI, API, và **relay luồng audio có chữ ký** (YouTube qua yt-dlp, Zing công khai) |
| Custom integration | [`custom_components/tritue_youtube_player`](custom_components/tritue_youtube_player/) | Media player ảo, action `play_on_players`, ma trận capability của từng loa |
| Lovelace card | (đi kèm integration) | Tìm nhạc, chọn nhiều loa, hàng đợi, âm lượng từng loa |

Hỗ trợ **`amd64` và `aarch64`** (đã kiểm chứng chạy thật trên cả hai).

## Tính năng

- **YouTube ra loa (mới):** TV/Android box mở app YouTube gốc (có hình); loa
  (Cast audio, DLNA, ESPHome…) nhận YouTube dưới dạng **luồng audio** — add-on
  dùng `yt-dlp` lấy `bestaudio`, ký một URL ngắn hạn rồi tự tải và tiếp sóng qua
  `/api/stream/<token>`. Nhờ vậy loa không gọi thẳng `googlevideo.com` nên tránh
  lỗi `403` do URL gắn theo IP (đây là điểm khiến `media_extractor` hay hỏng).
- **Zing MP3 công khai** và **HTTP audio trực tiếp** (MP3/AAC/M4A/FLAC/OGG/OPUS/WAV/HLS).
- **Phát đồng thời nhiều loa** khác loại trong một lượt (ví dụ TV + loa Google + loa DLNA).
- **Âm lượng từng loa:** mỗi loa đã chọn có thanh trượt riêng; phát không ép một
  mức chung nên Cast và DLNA giữ âm lượng độc lập.
- **Hàng đợi:** Bài trước / Bài tiếp duyệt kết quả tìm kiếm, và **tự chuyển bài
  kế khi hết bài**.
- **Tick loa để vào bài đang phát:** đang phát mà tick thêm một loa thì loa đó tự
  vào; bỏ tick thì chỉ loa đó dừng, các loa còn lại tiếp tục.
- **Phiên phát dùng chung:** metadata, hàng đợi và danh sách đầu ra được add-on
  giữ, nên card ở trình duyệt khác vẫn thấy đúng bài đang phát.

## 1) Cài add-on

### Cách A — Home Assistant Supervisor (khuyến nghị)

Trong **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, thêm:

```text
https://github.com/TriTue2011/youtube
```

Cài **TriTue YouTube Player**. Supervisor tự tải image dựng sẵn từ GHCR đúng
kiến trúc máy.

**Để phát ra loa (YouTube/Zing):** trong tab **Network** của add-on, công bố cổng
`8099`, rồi trong **Configuration** đặt:

```yaml
public_base_url: http://IP_HOME_ASSISTANT:8099
```

Đây là URL LAN mà loa truy cập được để tải luồng audio. Chỉ mở trong LAN,
**không NAT/forward ra Internet**. URL phát có chữ ký và tự hết hạn.

### Cách B — Docker Compose độc lập

Từ thư mục `youtube_player`:

```bash
PUBLIC_BASE_URL='http://IP_MAY_DOCKER:8099' docker compose up -d --build
```

Xem chi tiết tùy chọn tại [youtube_player/DOCS.md](youtube_player/DOCS.md).

## 2) Cài custom integration

### Qua HACS

**HACS → Custom repositories** → thêm `https://github.com/TriTue2011/youtube`
loại **Integration** → tải **TriTue YouTube Player** → khởi động lại Home
Assistant.

### Thủ công

Chép `custom_components/tritue_youtube_player` vào
`/config/custom_components/` rồi khởi động lại Home Assistant.

### Cấu hình

**Settings → Devices & services → Add integration → TriTue YouTube Player**.
Nhập URL add-on và token (in trong log add-on khi khởi động):

- Cài từ add-on store repo này: `http://b5248dd0-youtube-player:8099`
- Add-on local: `http://local-youtube-player:8099`
- Docker độc lập: `http://IP_MAY_DOCKER:8099`

Chọn loa phát mặc định (tùy chọn) trong phần cấu hình của integration.

## 3) Thêm card

Integration tự đăng ký JavaScript resource. Thêm một **Manual card**:

```yaml
type: custom:tritue-youtube-player-card
entity: media_player.tritue_youtube_player_172_16_10_200
title: Nhạc YouTube & Zing
```

Thay `entity` bằng đúng media player ảo của bạn (tên có kèm host/URL add-on).
Chỉ cần ba dòng trên là đủ — card tự đọc các loa `media_player` khác trong nhà.

> Nếu sau khi cập nhật mà card không đổi, đổi URL resource của card thành
> `…/tritue-youtube-player-card.js?v=<phiên_bản>` rồi hard-refresh — trình duyệt
> hay giữ bản card cũ trong cache.

## Lưu ý quan trọng

- **Không đồng bộ mẫu giữa các loại loa:** loa mới vào sẽ phát bài **từ đầu**,
  không khớp vị trí với loa đang phát (Cast và DLNA vốn không đồng bộ mẫu). Nếu
  cần khớp thời điểm giữa nhiều phòng thì phải dùng **Cast group** (các loa
  Google) hoặc **Snapcast**.
- **Loa ESP32/ESPHome:** YouTube trả `m4a`/`opus`. Cast và DLNA phát tốt; nhưng
  firmware ESPHome media_player thường chỉ giải mã MP3/FLAC/WAV, nên **có thể
  không phát được m4a**. Zing (MP3) và HTTP thì ESP vẫn ổn.
- **Bảo mật token:** token tích hợp là khóa xác thực giữa integration và add-on.
  Nó xuất hiện trong log add-on để bạn sao chép; đừng chia sẻ ra ngoài.

## Phát triển & kiểm thử

```bash
# Add-on: test hành vi HTTP + hợp đồng integration
python -m unittest discover -s youtube_player/tests -v
python -m pip install aiohttp
python -m unittest discover -s youtube_player_integration/tests -p 'test_*.py' -v

# Kiểm cú pháp
python -m compileall -q custom_components/tritue_youtube_player
node --check youtube_player/app/static/app.js
node --check custom_components/tritue_youtube_player/www/tritue-youtube-player-card.js
```

CI (`.github/workflows/build.yml`) chạy các test trên, Hassfest, HACS validation,
rồi build image đa kiến trúc đẩy lên GHCR.

Tài liệu thêm: [add-on](youtube_player/DOCS.md) ·
[API](youtube_player/API.md) ·
[integration/card](youtube_player_integration/README.md) ·
[phân tích clean-room APK YouTube Music](docs/YOUTUBE_MUSIC_APK_ANALYSIS.md).
