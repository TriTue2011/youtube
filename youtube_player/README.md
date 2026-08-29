# Home Assistant Add-on: TriTue YouTube Player

Nguồn nhạc YouTube, Zing MP3 và HTTP audio cho `media_player` của Home Assistant,
chạy dưới dạng add-on hoặc Docker độc lập. Add-on cung cấp tìm kiếm, Web UI và
một API có Bearer token cho custom integration.

Để phát ra loa audio (Cast, DLNA, ESPHome…), add-on **resolve và tiếp sóng** một
luồng audio có chữ ký, ngắn hạn qua `/api/stream/<token>`: YouTube được lấy
`bestaudio` bằng `yt-dlp`, Zing lấy từ trang công khai. Loa chỉ nói chuyện với
add-on nên không gọi thẳng `googlevideo`/CDN, tránh lỗi `403` do URL gắn theo IP.
Token API là thông tin xác thực nội bộ, **không phải license key**.

Hỗ trợ `amd64` và `aarch64`. Cần `public_base_url` (URL LAN của add-on) và công
bố cổng `8099` thì loa mới tải được luồng phát.

Xem [DOCS.md](DOCS.md) để cài đặt/cấu hình và [API.md](API.md) để phát triển
integration.
