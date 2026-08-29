# Changelog

## 0.6.1 - 2026-08-29

### Fixed

- Proxy stream trả lời request `HEAD` (trước đây trả `501`): renderer DLNA
  thường HEAD để lấy Content-Type/Content-Length/Accept-Ranges trước khi GET.
  Nay trả đúng các header đó (kích thước lấy từ một probe range 0-0), giúp loa
  DLNA khó tính phát được thay vì bỏ cuộc.

## 0.6.0 - 2026-08-29

### Added

- Phát nhạc YouTube ra loa như Zing: `POST /api/integration/stream` nhận thêm
  `source: youtube`, dùng yt-dlp lấy luồng audio `bestaudio` rồi ký URL công khai
  ngắn hạn. Add-on tự tải và tiếp sóng qua `/api/stream/<token>` nên loa Google
  Cast, DLNA hay ESPHome không phải gọi thẳng `googlevideo.com` (tránh lỗi 403 do
  URL gắn theo IP).
- Token stream mang theo `source`, hỗ trợ cả Zing lẫn YouTube trên cùng một
  đường tiếp sóng.

### Fixed

- Lịch sử dùng chung nhiều nguồn: giao diện web dán nhãn đúng YouTube/Zing/HTTP,
  không còn báo lỗi khi bấm lại mục Zing/HTTP (mở trang nguồn thay vì nhồi vào
  iframe YouTube), và trang web không bị chiếm iframe khi loa đang phát Zing/HTTP.
- Bộ nhớ đệm stream tự dọn mục hết hạn thay vì phình mãi tới khi khởi động lại.
- Không giữ khóa `stream_lock` trong lúc gọi mạng, nên một lần resolve chậm không
  chặn các loa khác đang phát bài đã có trong cache.
- Giới hạn dung lượng phản hồi tìm kiếm Zing (2 MB) trước khi giải nén.

## 0.5.0 - 2026-08-29

### Added

- Hợp đồng phiên phát clean-room gồm state, metadata, position, queue, thiết bị
  đầu ra và supported actions, dựa trên mô hình MediaSession quan sát từ APK.
- Endpoint xác thực `POST /api/integration/session` cho YouTube, Zing và HTTP
  audio trực tiếp.

### Changed

- Giữ title, artist, album, thumbnail và duration của kết quả tìm kiếm khi phát,
  thay vì chỉ còn video ID.
- Lịch sử và trạng thái player dùng cùng một item đã chuẩn hóa.
- Rollback dùng revision có điều kiện để một lệnh Cast lỗi không dừng nhầm phiên
  mới hơn của người dùng khác.

## 0.4.1 - 2026-08-29

### Fixed

- Theo redirect ID mới của Zing trước khi lấy stream, thay vì gửi ID cũ từ kết
  quả tìm kiếm và nhận lỗi `403`.
- Dùng request web công khai hiện tại của Zing, ưu tiên MP3 320 kbps và tự hạ
  xuống 128 kbps khi bản 320 không được cung cấp công khai.

## 0.4.0 - 2026-08-28

### Added

- Nguồn tìm kiếm Zing công khai và stream URL ký hạn dùng cho loa trong LAN.
- Action Home Assistant phát tới một hoặc nhiều `media_player`, kèm âm lượng.
- Lovelace card riêng cho chọn nguồn, tìm kiếm, chọn loa, phát và dừng.

### Fixed

- Entity giữ config entry trong runtime, tránh lỗi polling trên trang thiết bị.
- Chỉ tạo luồng Zing cho kết quả có cờ phát công khai và được server tìm thấy
  trong 60 phút gần nhất; card dừng cả loa đã chọn lẫn player nguồn.

## 0.3.0 - 2026-08-28

### Added

- Tìm kiếm metadata bài hát không cần YouTube Data API key bằng `yt-dlp` ở chế
  độ không tải nội dung.
- Giữ video khởi đầu và playlist ID để Home Assistant có thể phát playlist qua
  ứng dụng YouTube Cast chính thức.

## 0.2.0 - 2026-08-28

### Added

- Bearer API dành cho custom integration: health, status, history, play và stop.
- Token bảo mật tự sinh, bền vững trong `/data` và có thể cấu hình thủ công.
- Đồng bộ lệnh phát/dừng từ integration tới giao diện web đang mở.

### Fixed

- Giao diện màn hình nhỏ không còn tràn ngang và có favicon riêng.

## 0.1.0 - 2026-08-28

### Added

- Giao diện phát video, Shorts và playlist qua YouTube privacy-enhanced embed.
- Lịch sử bền vững trong `/data`, có giới hạn và thao tác xóa.
- Health endpoint cho Docker và Home Assistant watchdog.
- Cấu hình chạy chung bằng Docker Compose hoặc Home Assistant Ingress.
