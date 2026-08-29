# Changelog

## 0.8.1 - 2026-08-29

### Added

- Card: chỉnh âm lượng **từng loa** riêng (mỗi loa đã chọn một thanh trượt),
  không còn ép một mức chung cho tất cả khi phát.
- Card: nút **Bài trước/Bài tiếp** phát mục liền kề trong hàng đợi kết quả tìm
  kiếm (trước đây gửi lệnh transport tới loa vốn chỉ phát một luồng nên không có
  bài kế) — bật/tắt theo vị trí trong hàng đợi.

## 0.8.0 - 2026-08-29

### Added

- YouTube phát được ra mọi loa hỗ trợ `play_media` (Google Cast audio, DLNA,
  ESPHome…): TV/Android box vẫn mở app YouTube gốc, còn loa nhận YouTube dưới
  dạng luồng audio ký sẵn từ add-on — cùng đường đi với Zing.
- `play_on_players` gửi một lệnh tới TV và loa trong cùng một lượt: TV phát
  video, loa phát nhạc.

### Changed

- Ma trận capability công bố `youtube` cho mọi `media_player` có `play_media`,
  kèm `youtube_transport` (native trên TV, audio trên loa). Card tự mở nguồn
  YouTube cho loa thay vì khóa lại.
- Thiết bị không hỗ trợ `play_media` là trường hợp duy nhất bị coi là không
  tương thích với mọi nguồn.

## 0.7.0 - 2026-08-29

### Added

- Entity công bố title, artist, album, ảnh bìa, duration, position, queue và danh
  sách thiết bị đầu ra từ phiên phát dùng chung của add-on.
- HTTP audio trực tiếp đi qua action của integration để mọi card/browser cùng
  thấy trạng thái đang phát.
- Hỗ trợ MIME HLS chuẩn bên cạnh MP3/AAC/M4A/FLAC/OGG/OPUS/WAV.
- Trình duyệt khác tự chọn lại `output_entity_ids` của phiên để các nút điều
  khiển tác động đúng loa đang phát.

### Changed

- Card ưu tiên metadata phiên từ entity Home Assistant; `localStorage` chỉ còn
  là fallback trong lúc coordinator chưa poll xong.
- Direct HTTP audio được chuẩn hóa MIME trước khi đặt âm lượng hoặc gửi tới loa;
  add-on và integration có contract test chung chống lệch codec.
- Giới hạn URL HTTP được kiểm tra trước khi phát; rollback YouTube chỉ dừng đúng
  revision do lệnh đang lỗi tạo ra.

## 0.6.0 - 2026-08-29

### Added

- API capability matrix cho Cast TV, Cast audio, Android TV, DLNA và các
  `media_player` HTTP audio khác.
- Card gắn nhãn transport, tự khóa nguồn không tương thích và tự thử lại khi HA
  chưa sẵn sàng lúc tải capability.

### Fixed

- Không còn gửi trang YouTube tới loa/DLNA như một luồng audio.
- Yêu cầu chỉ chứa thiết bị không tương thích bị từ chối trước khi thay đổi
  history/trạng thái add-on.
- Cast không khai báo `device_class` không còn bị đoán nhầm là TV.
- Now Playing không lấy tiêu đề cũ từ entity đang idle/off.

## 0.5.1 - 2026-08-29

### Added

- Nguồn HTTP Audio để gửi URL MP3/AAC/M4A/FLAC/OGG/OPUS/WAV/HLS trực tiếp
  tới một hoặc nhiều `media_player`, gồm cả loa Cast audio-only.
- Tự nhận diện MIME từ phần mở rộng và hỗ trợ cấu hình `http_content_type` cho
  URL ký số không có phần mở rộng.

## 0.5.0 - 2026-08-29

### Added

- Hiển thị bài đang phát, ảnh bìa, nguồn và các thiết bị nhận nhạc trên card.
- Nút bài trước, phát/tạm dừng, bài tiếp, dừng và âm lượng theo khả năng entity.
- Mở URL YouTube bằng deep link trên Android TV/FPT Box.

### Changed

- Phân biệt Cast có màn hình với loa audio-only; URL audio trực tiếp tiếp tục
  được Home Assistant chuyển tới Cast, DLNA, ESPHome và integration của loa.
