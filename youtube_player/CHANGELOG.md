# Changelog

## 0.9.4 - 2026-09-20

### Fixed

- **Thêm bài Facebook vào playlist thì rơi im lặng.** `normalize_item` chỉ biết
  `youtube`, `zing`, `http` — gặp `facebook` là trả `None` và bài biến mất không một
  lời báo. Chủ máy báo: *"ghim video face được nhưng thêm playlist không được"* —
  ghim đi qua kho gợi ý của tích hợp nên chạy, còn playlist đi qua đúng hàm này.

  Nay có nhánh `facebook` với **khuôn mã riêng** (chuỗi số), không dùng chung khuôn
  lỏng với YouTube: mã của nguồn này khai sang nguồn kia thì bị từ chối, cả hai chiều.

  Sửa ở **cả hai bản song song** (add-on và c2a) và đã đối chiếu `diff` để chắc hai
  bản khớp từng byte — để chúng lệch nhau là lớp lỗi đã cắn dự án này nhiều lần.

## 0.9.3 - 2026-09-19

### Fixed

- **Trang của add-on gọi mục Facebook là "Video".** Danh sách đã nghe dán nhãn nguồn cho
  Zing MP3 và HTTP Audio nhưng không có Facebook, nên mọi mục Facebook hiện ra dưới cái
  tên chung chung "Video" — không phân biệt được với YouTube. Nay có nhãn riêng. Phần
  bấm vào để mở thì vốn đã đúng: mọi nguồn không phải YouTube đều mở trang gốc, vì
  trang này chỉ sở hữu khung nhúng YouTube.

## 0.9.2 - 2026-09-19

### Fixed

- **Link chia sẻ dạng `/share/r/` (chia sẻ reel) không đọc được.** Hai dạng chia sẻ của
  Facebook giấu mã video ở **hai nơi khác nhau**, đo trên trang thật:
  - `/share/r/` → thẻ `canonical` và `og:url` trỏ **thẳng** vào
    `facebook.com/reel/<mã video>`; trang **không có** trường nội bộ `impl_`.
  - `/share/v/` → thẻ `canonical` trỏ vào **bài viết**, vô dụng cho việc lấy mã video;
    mã nằm trong trường nội bộ `impl_`.

  Bản trước chỉ biết một nơi nên dạng reel báo `facebook_share_unreadable`. Nay đọc
  **thẻ chuẩn trước** — đó là thẻ HTML có tài liệu, bền hơn hẳn trường nội bộ — và chỉ
  lùi về `impl_` khi thẻ chuẩn không trỏ vào video. Địa chỉ lấy từ thẻ được đưa thẳng
  vào bộ đọc link sẵn có, không đẻ thêm bộ phân tích thứ hai.

  Kiểm trên **dữ liệu thật**: chạy bộ đọc mới trên chính hai trang đã tải về (298 KB và
  374 KB), cả hai ra đúng mã video.

## 0.9.1 - 2026-09-19

### Fixed

- **Add-on tự khai thiếu nguồn Facebook.** Điểm cuối "sức khoẻ" vẫn trả
  `"sources": ["youtube", "zing"]` và `"playback_sources": ["youtube", "zing", "http"]`
  dù add-on đã phát được Facebook từ 0.9.0. Không mã nào tiêu thụ hai trường này nên
  không có gì hỏng vì nó — nhưng một lời tự khai sai là thứ đánh lừa người đọc về sau.
  Tài liệu `API.md` đã sửa cho khớp.

## 0.9.0 - 2026-09-19

### Added

- **Nguồn Facebook — nghe và xem là hai đường riêng**, đối xứng với cặp `youtube` /
  `youtube_video` sẵn có: `facebook` trả luồng tiếng cho loa, `facebook_video` trả luồng
  hình cho thẻ `<video>` của trình duyệt. Đo được trên video thật: Facebook phục vụ tệp
  mp4 **gộp sẵn** (hình h.264 kèm tiếng AAC, tới 1920×1080), và có cả luồng chỉ-có-tiếng
  `m4a` ~73 kbps để phát ra loa.
- **Tra cứu bằng link dán vào**: `/reel/<mã>`, `/watch/?v=<mã>`, `/<trang>/videos/<tên
  bài>/<mã>/`, **và cả link chia sẻ** `/share/v/<mã>`. Cố ý **không** nhận tìm theo từ
  khoá: Facebook không có đường tìm kiếm công khai để gọi, hứa suông chỉ sinh lỗi mơ hồ.

### Ghi rõ giới hạn

- **Đường đọc link chia sẻ không bền.** Mã trong `/share/v/…` là mã **bài viết**
  (`1135095972510953`), không phải mã video (`1807802260572674`), và không suy ra được —
  phải tải trang rồi đọc một trường **nội bộ không có tài liệu** của Facebook. Facebook
  đổi trang là hỏng, và khi hỏng nó **báo rõ** (`facebook_share_unreadable`) chứ không
  lặng lẽ thành "không tìm thấy bài nào". Link `/reel/…` và `/watch/?v=…` thì đi thẳng,
  không phụ thuộc phép đọc này.
- Lấy trang chia sẻ **phải gửi kèm đầy đủ đầu đề giống trình duyệt**. Gọi trần bị
  Facebook đá sang trang đăng nhập và trả 400; gọi đủ đầu đề thì 200.
- Thông báo *"This video is only available for registered users"* của Facebook là lời từ
  chối cho **dạng địa chỉ không đọc được**, **không** phải lời nói về quyền xem — cùng
  một mã video, dạng `/watch/?v=` chạy còn dạng `/video.php?v=` thì báo câu đó.

## 0.8.3 - 2026-09-18

### Fixed

- **Phep tu do dia chi LAN o 0.8.2 khong dung duoc, da chan lai.** Log thuc te cho thay
  integration goi add-on tu `172.30.32.1` — mang noi bo cua Supervisor. Qua NAT thi
  `getsockname()` chi tra ve dia chi cua chinh container, nen 0.8.2 hoc duoc mot URL noi
  bo ma loa khong voi toi, va vi `create_stream_url` lui ve dia chi do nen loi
  `public_base_url_required` ro rang bi thay bang IM LANG. Nay tu choi cac dai
  172.17.0.0/16 .. 172.31.0.0/16; dai 172.16.0.0/16 van duoc nhan vi la LAN that.
- **Nhan goi y dia chi tu Home Assistant**: `/api/integration/stream` doc them khoa
  `public_base_url`; thu tu uu tien la tuy chon dat tay > goi y > dia chi hoc duoc.
  Goi y den tu loi goi da xac thuc bang token nen dang tin nhu phan con lai cua API.
- Ket qua: cau hinh nhu cu — neu chua dat `public_base_url` thi bao loi ro rang, khong
  im lang. Duong "khoi cau hinh" that su phai lay IP host qua Supervisor API, se lam rieng.

## 0.8.2 - 2026-09-17

### Fixed

- **Phát ra loa không còn phải cấu hình gì.** Loa tự tải luồng phát từ add-on, nên nó
  cần một địa chỉ LAN — trước đây phải tự vào tab **Network** công bố cổng `8099` rồi
  điền `public_base_url`, mà dòng trợ giúp lại chỉ ghi "bắt buộc khi phát Zing" nên ai
  nghe YouTube đều tưởng không cần. Không đặt thì loa **im tiếng**, và im lặng thật:
  integration chỉ ghi loa đó vào `skipped_targets` rồi bỏ qua nếu còn loa khác phát được.
  Nay cổng `8099` được công bố sẵn và add-on **tự lấy địa chỉ LAN** của máy chạy Home
  Assistant từ chính lời gọi đã xác thực bằng token của integration.
- Chỉ phải đặt `public_base_url` khi **đổi cổng** ở tab Network: bên trong container
  không thấy được cổng đã map ra host, nên phép tự dò sẽ quảng bá sai cổng.
- Phép dò học địa chỉ **chỉ từ lời gọi đã xác thực** `/api/integration/*`, nên request
  qua Ingress (không mang token) không bao giờ làm add-on quảng bá địa chỉ nội bộ của
  Supervisor — thứ mà loa không với tới được.

## 0.8.1 - 2026-09-15

### Added

- **Luồng hình riêng** `youtube_video` ("ID:chiều cao", 360–1080): chỉ hình, cao nhất không
  vượt màn hình, ưu tiên avc1/mp4 (trình duyệt nào cũng giải được), bỏ luồng m3u8.
  `/api/integration/stream` trả thêm `direct_url` (link gắn IP mạng nhà, máy trong nhà tải
  thẳng), `height`, `bitrate_kbps`. Đo 14/09/2026 trong Chrome: 1080p avc1/vp9/av1 phát
  thẳng bằng thẻ video 1920×1080.
- **deno cho yt-dlp** (`apk add deno`, `yt-dlp[default]`): không có trình chạy JS yt-dlp
  2026.8 báo "some formats may be missing". Deno 2.3.1 của Alpine được yt-dlp nhận.

## 0.8.0 - 2026-09-14

### Added

- **Playlist chung cả nhà** (lưu trong thư mục dữ liệu của add-on, `playlists.json`):
  tạo nhiều playlist, thêm/bỏ/đổi chỗ bài; **lưu cả playlist từ link** playlist
  YouTube (yt-dlp) hoặc album/playlist Zing MP3 (bỏ bài VIP) — đo 14/09/2026: album
  Zing Sơn Tùng 28 bài trong 0,3 giây; **mã chia sẻ** `TTPL1.…` mở được ở add-on khác
  và ở c2a. API `GET/POST /api/integration/playlists`.
- Phát playlist ra loa: `/api/integration/session` nhận `playlist_id`, hàng đợi của
  phiên là cả playlist; bài Zing đã lưu phát được mà không cần vừa tìm lại.

## 0.7.1 - 2026-09-14

### Changed

- **Phát và chuyển bài nhanh hơn.** Luồng nhạc YouTube được lấy bằng yt-dlp chạy
  ngay trong tiến trình thay vì mở một tiến trình mới cho mỗi bài. Đo ngày
  14/09/2026: tiến trình mới mất 4,8–7,1 giây mỗi bài, riêng khâu nạp yt-dlp đã
  mất 2,2 giây; chạy trong tiến trình chỉ còn 1,6–2,5 giây.
- **Link luồng được dùng lại tới gần lúc hết hạn.** Link googlevideo tự mang hạn
  dùng (khoảng 6 giờ), nên phát lại, tua hay loa hỏi lại từng đoạn không phải lấy
  luồng lại sau 2 phút nữa. YouTube từ chối link cũ (403/404/410) thì lấy lại một lần.
- **Lấy sẵn luồng của bài kế.** Mỗi khi một nhóm loa bắt đầu một bài, bài kế trong
  hàng đợi được chuẩn bị ngầm, nên bấm bài kế và tự chuyển bài bắt đầu gần như ngay.

## 0.7.0 - 2026-09-14

### Added

- **Nhiều phiên phát — mỗi loa một bài, hoặc nhiều loa chung một bài.** Máy
  phát giữ một phiên cho mỗi nhóm loa; một loa chỉ thuộc một phiên (phát bài
  khác ra loa đó thì nó rời phiên cũ, phiên hết loa thì kết thúc). Mỗi phiên
  có hàng đợi riêng: bài kế/trước giữ đúng danh sách của phiên dù đã tìm bài
  khác. Giao diện web add-on vẫn dùng phiên riêng `web`.
- Integration API (tương thích v1): `/status` trả thêm `sessions`;
  `/session` nhận `session_id`, `controller`, `auto_advance`; `/stop` nhận
  `session_id`; mới `/session/outputs` đổi loa của một phiên mà không phát
  lại bài. Client cũ vẫn thấy `session` = phiên thay đổi gần nhất.

## 0.6.4 - 2026-09-14

### Added

- **Tìm theo link YouTube.** Dán link vào ô tìm là ra đúng video đó (tên, kênh,
  thời lượng, ảnh) thay vì tìm theo chữ của link. Nhận link chép từ app hay
  trình duyệt kể cả kèm tham số thừa (`app=desktop`, `list=RD…`, `pp=…`,
  `si=…`), `youtu.be`, Shorts, embed, live, có hoặc không `https://`; link
  trang playlist thì liệt kê các video trong playlist. Link từ app YouTube dài
  hơn 120 ký tự nên giới hạn cho link là 2048, từ khoá chữ vẫn 120.

## 0.6.3 - 2026-09-14

### Fixed

- Tìm YouTube ra cả **nhạc AI / cover đăng dạng video thường**. Trước đây chỉ
  tìm trong tab "Bài hát" của YouTube Music nên những video này không bao giờ
  hiện dù phát được; nay tìm trên YouTube thường (`ytsearch`), kết quả có thêm
  tên kênh và thời lượng.
- **Video không chạy khi mở giao diện add-on trong Home Assistant** ("Error 153 —
  Video player configuration error"). Trang của HA gửi `Referrer-Policy:
  no-referrer`, mà YouTube từ chối khung nhúng không kèm Referer. Khung phát nay
  tự đặt `referrerpolicy="strict-origin-when-cross-origin"`, đè chính sách của
  trang.

## 0.6.2 - 2026-08-29

### Fixed

- Đọc được body POST dạng **chunked** (Home Assistant Ingress gửi body kiểu này,
  không có Content-Length). Trước đây mọi POST từ panel add-on qua Ingress bị
  `400 invalid_request` — Web UI báo "Không thể mở nội dung". Nay Web UI của
  add-on chạy đúng khi mở qua Ingress.

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
