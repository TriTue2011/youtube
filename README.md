# TriTue Music Player cho Home Assistant

Repository độc lập gồm cả hai phần cần thiết:

| Thành phần | Thư mục | Công dụng |
|---|---|---|
| Home Assistant add-on / Docker image | [`youtube_player`](youtube_player/) | Tìm kiếm, Web UI, API và relay bài Zing công khai |
| Custom integration + Lovelace card | [`custom_components/tritue_youtube_player`](custom_components/tritue_youtube_player/) | Chọn nhiều `media_player`, phát nhạc và điều khiển trên Home Assistant |

Không cần license key. Token trong log add-on chỉ là khóa kết nối nội bộ giữa
integration và add-on, không phải khóa kích hoạt.

## Cài add-on

Trong **Settings → Add-ons → Add-on Store → Repositories**, thêm:

```text
https://github.com/TriTue2011/youtube
```

Cài **TriTue YouTube Player**. Muốn phát Zing tới loa, công bố cổng `8099` trong
tab Network và đặt:

```yaml
public_base_url: http://IP_HOME_ASSISTANT:8099
```

Chỉ mở cổng này trong LAN; không NAT/forward ra Internet.

## Cài custom integration bằng HACS

Trong **HACS → Custom repositories**, thêm cùng URL trên với loại
**Integration**, tải **TriTue YouTube Player**, rồi khởi động lại Home Assistant.
Thêm integration và dùng URL add-on mặc định:

```text
http://b5248dd0-youtube-player:8099
```

Token được in trong log add-on khi khởi động. Nếu chạy Docker độc lập, dùng
`http://IP_MAY_DOCKER:8099`.

## Thêm card

Integration tự đăng ký JavaScript resource. Thêm Manual card:

```yaml
type: custom:tritue-youtube-player-card
entity: media_player.tritue_youtube_player_player
title: Nhạc trong nhà
entities:
  - media_player.phong_khach
  - media_player.phong_bep
```

Card có tìm kiếm YouTube/Zing, nhập HTTP audio, chọn nhiều thiết bị, ảnh bìa,
trạng thái đang phát, play/pause/stop/next/previous và âm lượng theo capability
thật của từng entity.

Add-on giữ phiên phát dùng chung gồm metadata, hàng đợi và danh sách đầu ra, nên
card trên trình duyệt khác vẫn thấy bài đã phát. Xem kết quả phân tích clean-room
[APK YouTube Music](docs/YOUTUBE_MUSIC_APK_ANALYSIS.md) làm cơ sở cho hợp đồng
này.

## Tuyến phát hiện có

- **YouTube:** dùng receiver YouTube chính thức trên Cast TV hoặc deep link
  Android TV/box; quảng cáo của YouTube vẫn hoạt động.
- **Zing công khai:** add-on tạo URL relay có chữ ký rồi HA gửi URL này tới
  Cast audio, DLNA, ESPHome hoặc media player hỗ trợ HTTP audio.
- **HTTP Audio:** card gửi URL MP3/AAC/M4A/FLAC/OGG/OPUS/WAV/HLS trực tiếp tới
  driver `media_player` của Home Assistant.

Phiên bản hiện tại **chưa relay/transcode âm thanh YouTube/YouTube Music thành
MP3 cho Google Mini, DLNA hoặc ESP**. Vì vậy card chủ động khóa các kết hợp
không hợp lệ thay vì gửi một trang YouTube như URL audio. Mục tiêu relay đa
codec vẫn là phần phát triển tiếp theo.

Xem cấu hình chi tiết tại [tài liệu add-on](youtube_player/DOCS.md) và
[tài liệu integration/card](youtube_player_integration/README.md).
