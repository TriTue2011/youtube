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

## Web UI

Mở trang web của player (`http://IP:8099` hoặc qua Ingress của add-on):

1. **Phát nội dung:** dán URL video, Shorts, playlist của YouTube hoặc nhập
   trực tiếp video ID vào ô "Phát nội dung" rồi Enter. Video YouTube phát ngay
   trong khung nhúng của trang; bài Zing/HTTP sẽ mở nguồn công khai trên tab
   mới (trang web chỉ sở hữu iframe YouTube).
2. **Chép mã đang phát:** khi có mục đang phát, nút "⧉ Chép mã đang phát"
   xuất hiện trong tiêu đề khung phát. Video thì chép URL `watch`, playlist
   thì chép URL playlist (kèm mã) — dùng lại để phát hoặc import. Nút ẩn khi
   chưa phát gì.
3. **Lịch sử:** mục "Đã phát gần đây" liệt kê các mục đã phát; mỗi mục có nút
   ⧉ để chép mã/URL của mục đó mà không cần phát lại.
4. **Tìm kiếm:** ô tìm kiếm trả kết quả YouTube/Zing; chọn kết quả để phát
   hoặc chép URL.

Nếu trình duyệt/điện thoại chặn clipboard API, nút chép sẽ mở hộp thoại
`window.prompt` để copy tay — cùng cơ chế đường lùi với thẻ Home Assistant.

Xem [DOCS.md](DOCS.md) để cài đặt/cấu hình và [API.md](API.md) để phát triển
integration.
