# Changelog

## 0.10.3 - 2026-09-15

Cần add-on **0.8.1** (hoặc c2a từ a9fb9c2) cho luồng hình.

### Added

- **Xem được video YouTube không cho nhúng.** Card lấy hình riêng của video từ máy phát
  (tối đa 720p trên điện thoại, 1080p màn hình lớn), tiếng đi riêng (loa hoặc máy này),
  hình chạy theo. Máy trong nhà tải hình thẳng từ YouTube (không qua máy phát). Tải thẳng
  không được nghĩa là đang ở ngoài nhà: mặc định chỉ nghe, có nút **«Xem hình»** ghi ước
  lượng MB/phút; bấm thì hỏi lại, đồng ý mới mở (các video bị chặn tiếp theo trong lần xem
  đó tự mở hình), Huỷ thì thôi.
- **Nút «Chỉ nghe» khi đang xem video**: tắt hình, tiếng chạy tiếp từ giây đang xem (có loa
  thì loa vẫn phát).
- **Toàn màn hình tự ẩn nút** sau 3 giây không chạm khi video đang chạy; chạm là hiện lại
  (lần chạm đó chỉ để hiện nút). Đang tạm dừng thì nút không ẩn.
- **Phát hành trên GitHub theo phiên bản** (`vX.Y.Z`, ghi chú lấy từ changelog) để HACS
  hiện số phiên bản và báo cập nhật — trước đây repo không có release nên HACS không báo.
  Muốn thấy ngay: HACS → ⋮ → Cập nhật thông tin.

### Fixed

- **Bấm «Xem video» mà không phát, nút ▶ của card không tác dụng** (app Home Assistant và
  trình duyệt chặn tiếng tự phát: khung YouTube chỉ chịu phát khi chạm thẳng vào nó). Nay
  card phát tiếng bằng trình phát của nó (mở khoá ngay trong cú bấm), hình YouTube chạy
  tắt tiếng theo; bấm ▶ của card khi khung chưa chạy cũng phát ngay. Máy phát không trả
  được tiếng thì giữ video và nhắc chạm vào video.
- **Toàn màn hình không xoay ngang trong app Home Assistant.** App (WebView) từ chối lệnh
  khoá xoay, và xoay máy làm HA vẽ lại cả trang nên thoát toàn màn hình. Khi không khoá được,
  card tự xoay khung hình 90° — chỉ việc cầm ngang máy; máy nào tự xoay thì dùng bố cục ngang.
- **Bấm nút toàn màn hình của chính YouTube khi đang toàn màn hình** không còn kẹt ở màn dọc:
  nút đó nay thoát hẳn toàn màn hình (chưa toàn màn hình thì nó xoay ngang như nút của card).

## 0.10.2 - 2026-09-15

Cần add-on **0.8.1** cho phần luồng hình (máy phát cũ vẫn chạy, chỉ chưa có luồng hình).

### Fixed

- **Đang nghe mà mở video thì mở đúng giây đang nghe.** Từ 0.9.8 (nghe trên máy) nút xem
  video ở khung Đang phát bị ẩn khi nghe trên máy, và bấm nút xem video của chính bài đang
  nghe trong danh sách thì phát lại từ đầu. Nay: nút hiện lại, bấm là video mở tại giây
  đang nghe, tắt tiếng và chạy theo tiếng; bấm xem bài loa đang phát cũng không gửi lại
  bài cho loa mà mở hình theo vị trí loa.

### Added

- View `stream` nhận `youtube_video` (chỉ hình, tối đa `max_height`) và trả thêm
  `direct_url`, `height`, `bitrate_kbps` — nền cho xem video bị YouTube chặn nhúng.

## 0.10.1 - 2026-09-14

### Added

- **Biểu tượng YouTube** cho tích hợp (`brand/icon.png`, `logo.png`, bản tối và @2x — cùng
  ảnh YouTube mà kho brands của Home Assistant dùng cho `custom-components/youtube`).
  Home Assistant 2026.3 trở lên tự hiện ở trang Tích hợp và thiết bị. Trang HACS hiện
  vẫn chỉ lấy icon từ máy chủ của HACS nên có thể chưa thấy (hacs/integration#5171).

## 0.10.0 - 2026-09-14

Cần add-on **0.8.0** (hoặc c2a từ commit d0715bd) — máy phát giữ playlist.

### Added

- **Playlist chung cả nhà trên card.** Thẻ "Tìm nhạc | Playlist". Dán link playlist
  YouTube hoặc album/playlist Zing MP3 vào ô tìm là có nút **«Lưu cả playlist này»**;
  mỗi kết quả có nút **+** thêm vào playlist có sẵn hoặc playlist mới. Mỗi playlist:
  phát cả playlist (tích loa thì loa phát và hàng đợi là cả playlist — Home Assistant
  tự chuyển bài; không tích thì nghe trên máy này), chép **mã chia sẻ**, đổi tên, xoá;
  từng bài xem video / nghe, lên, xuống, bỏ. Dán mã chia sẻ của người khác (từ card HA
  khác hoặc tab c2a) để lưu playlist của họ.
- View `GET/POST /api/tritue_youtube_player/playlists` (cần đăng nhập HA) chuyển lệnh
  tới máy phát; dịch vụ `play_on_players` nhận thêm `playlist_id`.

## 0.9.8 - 2026-09-14

### Added

- **Card giống tab c2a: mỗi bài hai nút xem video / nghe (chỉ tiếng).** Chưa tích loa
  thì nghe ngay trên máy đang mở card (hàng đợi là kết quả tìm, hết bài tự sang bài,
  nút trên màn hình khoá); tích loa thì loa phát, nút xem mở thêm video tắt tiếng.
  Tiếng trên máy lấy luồng của add-on/c2a qua view mới
  `POST /api/tritue_youtube_player/stream` (cần đăng nhập HA).
- **«Nghe trên máy này»** khi loa đang phát: máy đang mở card nghe cùng bài, dừng/phát
  và tua theo loa. **«Nghe khi tắt màn hình»** (mặc định tắt, nhớ theo máy): tắt thì
  trang bị ẩn là tiếng trên máy dừng, mở lại phát tiếp; bật thì nghe tiếp, video (nếu
  đang xem) tắt tiếng chạy theo tiếng.
- **Rời dashboard rồi quay lại vẫn thấy** danh sách tìm, bài đang phát, video; video
  đang xem có tiếng thì tiếng chạy tiếp trên máy trong lúc rời trang. Tải lại trang
  (mở lại app) vẫn còn danh sách tìm lần trước.

### Fixed

- **Video bị YouTube chặn nhúng không còn để khung chết.** Video của hãng đĩa (VEVO…)
  bị từ chối khi mở Home Assistant bằng địa chỉ IP — đo trên chính trang của hai máy
  HA: "M2M - The Day You Went Away" bị chặn, "Trót tin vào lời hứa" phát được; mở
  bằng tên (`homeassistant.local`) thì cả hai phát được. Card nhận lỗi của khung
  nhúng, chuyển sang phát tiếng bài đó và nói rõ lý do.

## 0.9.7 - 2026-09-14

### Fixed

- **Toàn màn hình trên điện thoại tự xoay ngang, video không bị cắt.** Bấm toàn màn
  hình trên thẻ, trình duyệt hỗ trợ khoá hướng (Chrome Android) sẽ xoay ngang; thoát
  thì trả hướng tự do. Khi nằm ngang, video 16:9 chiếm hết chiều cao, chỉ còn thanh
  nút điều khiển bên dưới (ẩn dòng tên bài, âm lượng từng loa, nhóm loa khác).

## 0.9.6 - 2026-09-14

### Changed

- **Thẻ gọn trên điện thoại.** Mở bằng điện thoại (nhất là app Home Assistant phóng
  chữ), ô tìm và nút tìm nằm cùng một hàng, nút tìm thành biểu tượng kính lúp, nút
  nguồn không xuống dòng ("HTTP Audio" đổi thành "Link audio"), chữ và ô chọn loa
  nhỏ lại.

### Fixed

- **Không liệt kê trình phát ảo của chính tích hợp như một loa.** Cài hai kết nối
  (add-on và c2a) thì thẻ của kết nối này từng hiện "TriTue YouTube Player (…)" của
  kết nối kia trong danh sách loa. Nay mọi media_player của tích hợp đều bị bỏ qua.

## 0.9.5 - 2026-09-14

### Changed

- **Thiết bị mất kết nối không hiện trên thẻ.** Loa/tivi đang `unavailable` không
  nằm trong danh sách chọn lẫn mục Đã ẩn, và bị bỏ khỏi lựa chọn; Home Assistant
  báo kết nối lại thì thiết bị tự hiện. Không còn thiết bị nào kết nối thì thẻ ghi
  rõ "Chưa có loa hay tivi nào đang kết nối".

## 0.9.4 - 2026-09-14

### Fixed

- **Kết nối được với trình phát của c2a.** Ô URL chỉ nhận địa chỉ gốc, trong khi c2a
  phục vụ player ở `/yt` và tab YouTube của c2a đưa ra `http://IP:3030/yt`: nhập
  `/yt` bị báo "không kèm đường dẫn", bỏ `/yt` thì gọi nhầm trang web c2a và báo
  "phản hồi không mong đợi". Nay URL được kèm đường dẫn (không kèm `?`/`#`).

## 0.9.3 - 2026-09-14

### Fixed

- **Không còn nhảy tới giây của bài trước.** Vừa gửi bài mới, loa còn báo vị trí
  của bài cũ vài giây; thẻ lấy vị trí đó cho thanh tiến độ và video nên hình nhảy
  tới giây cũ rồi mới chạy lại từ đầu. Nay thẻ đọc bài loa đang phát từ link luồng
  đã ký và chỉ dùng vị trí khi đúng bài của nhóm loa. Tự chuyển bài cũng bỏ qua
  báo cáo của bài cũ, nên bấm bài kế sát cuối bài không bị tính là bài mới đã hết.
- **Trình duyệt chặn tiếng tự phát.** Trên điện thoại và app Home Assistant, video
  xem trên thẻ có thể đứng yên hoặc chạy không tiếng cho tới khi chạm vào chính
  khung video. Thẻ thử bật tiếng một lần, rồi hiện "Chạm vào video để phát có tiếng".

## 0.9.2 - 2026-09-14

### Fixed

- **Assist nhận đúng loa có tên bắt đầu bằng "Tivi"/"Loa".** Nói "tivi LG" trước
  đây bị bỏ chữ "tivi" rồi mới so, còn "lg" quá ngắn để khớp một phần tên nên
  loa "Tivi LG" không được chọn. Nay thử cả cụm nguyên trước, rồi mới bỏ chữ loại
  thiết bị ở đầu.

## 0.9.1 - 2026-09-14

### Added

- **Mở nhạc bằng Assist.** Tích hợp đăng ký API trợ lý "TriTue Music" với 5
  công cụ: `tim_nhac` (tối đa 10 bài đánh số, dán link YouTube ra đúng video),
  `danh_sach_loa` (loa đánh số, bỏ loa đã ẩn trên card), `phat_nhac` (chọn bài
  theo số, loa theo tên — không dấu cũng được —, theo số, hoặc "tất cả"; mỗi
  loa một bài được), `dieu_khien_nhac` (tạm dừng, tiếp tục, bài kế, bài trước,
  dừng — cho vài loa hoặc nhóm mới nhất), `dang_phat` (bài nào ở loa nào, đang
  ở giây nào). Bật trong Cài đặt → Trợ lý giọng nói → trợ lý dùng LLM → tuỳ
  chọn → tích "TriTue Music" cạnh "Assist".

## 0.9.0 - 2026-09-14

Cần add-on 0.7.0 (hoặc c2a cùng đợt) để có nhiều phiên; với add-on cũ vẫn chạy
như một phiên.

### Added

- **Mỗi loa một bài hoặc nhiều loa chung bài.** `play_on_players` biến các loa
  đã chọn thành một phiên; loa rời phiên cũ.
- **Tự chuyển bài phía Home Assistant — tắt trình duyệt vẫn chạy.** Tích hợp
  theo dõi loa dẫn của mỗi phiên nó mở; loa hết bài (về idle/off gần cuối bài)
  thì phát bài kế trong hàng đợi của phiên ra đúng các loa đó. Tạm dừng không
  tính; dừng giữa bài không chuyển. Tivi mở ứng dụng YouTube gốc không báo hết
  bài nên không tự chuyển.
- Dịch vụ mới: `skip` (bài kế/trước của một phiên), `stop_session`,
  `remove_players` (bỏ loa khỏi phiên, loa khác phát tiếp); `play_on_players`
  thêm `session_id` và `join` (cho loa nghe cùng mà không phát lại loa khác).
- Thuộc tính `sessions` trên media player ảo: mỗi phiên một mục (bài, loa, vị
  trí hàng đợi).
- Card: **tích loa nào thì xem loa đó** — "Đang phát", thanh tiến độ và video
  trên card theo phiên của loa vừa tích (video đổi sang đúng bài và tua tới chỗ
  loa đang phát). Nhóm loa khác hiện thành nút bấm để chuyển sang xem. Nút
  "Cho … nghe cùng". ⏹ dừng các loa đang tích, loa khác phát tiếp. Nút "Nghe
  cả trên máy này" khi xem video kèm loa.

### Changed

- Card không còn tự chuyển bài cho loa (tích hợp làm, tránh chuyển hai lần);
  tích/bỏ tích loa không còn phát/tắt loa — trừ khi đang xem video một mình
  thì tích loa để loa phát tiếng video đó.
- Kiểm đầu-cuối trên Home Assistant thật (`tests_ha`, chạy trong CI): add-on
  thật + tích hợp, mỗi loa một bài, tự chuyển bài, dừng giữa bài, bài kế theo
  phiên, gộp/bỏ loa, dừng phiên.

## 0.8.8 - 2026-09-14

### Changed

- **Card gọn lại, một khối phát.** "Đang phát", nút điều khiển và âm lượng từng
  loa gộp thành một khối ở đầu card; video xem trên card thay chỗ ảnh bìa. Nút
  điều khiển là hàng nút tròn nhỏ ⏮ ⏯ ⏭ ⏹. Mỗi kết quả chỉ còn một nút ▶.
- **▶ tự chọn nơi phát.** Có chọn loa thì phát ra loa; chưa chọn loa thì bài
  YouTube phát video ngay trên card.
- **Nút điều khiển dùng được khi xem video.** Card điều khiển khung YouTube bằng
  postMessage (không nạp script ngoài): phát/tạm dừng, bài trước/tiếp (đổi bài
  không nạp lại khung), dừng, tự sang bài kế khi hết video. Phóng to và toàn
  màn hình mang theo cả hàng nút.

### Added

- **Loa kèm video.** Loa phát tiếng, video trên card tắt tiếng và bám theo vị
  trí loa báo về (`media_position`): loa tạm dừng thì hình dừng, lệch quá 2 giây
  thì tua lại. Đang xem trên card mà tích loa thì loa phát bài đó; loa tua được
  (bit SEEK) thì tua tới chỗ video đang chạy, loa không tua được thì hình tua
  theo loa. Bỏ loa cuối thì card lấy lại tiếng.

## 0.8.7 - 2026-09-14

### Added

- Ô tìm của card nhận **link YouTube** (cần add-on 0.6.4 hoặc c2a): dán link là
  ra đúng video đó. API tìm của integration nhận chuỗi tới 2048 ký tự để link
  chép từ app YouTube không bị cắt; máy chủ trình phát kiểm giới hạn chính xác.

## 0.8.6 - 2026-09-14

### Added

- **Ẩn loa/tivi không dùng khỏi card, khôi phục được.** Mỗi thiết bị trong
  "Chọn loa / màn hình" có nút × để ẩn; mục "Đã ẩn (n)" bên dưới khôi phục từng
  thiết bị hoặc tất cả. Danh sách lưu trong `.storage` của Home Assistant
  (`tritue_youtube_player.hidden_players`) nên còn nguyên sau khi khởi động lại
  HA, tải lại card hay cập nhật integration, và mọi card dùng chung một danh
  sách. Chỉ tài khoản quản trị ẩn/khôi phục được, giống sửa dashboard. Mục
  "Đã ẩn" luôn gập sẵn, chỉ bung ra khi bấm.
- **Xem video YouTube ngay trên card.** Nút xem trên từng kết quả YouTube và
  "Xem trên thẻ" ở mục Đang phát; khung có Phóng to (phủ kín màn hình), Toàn
  màn hình và Đóng; chất lượng chọn ở biểu tượng bánh răng trong khung.

### Fixed

- **Video YouTube báo "Error 153" trong Home Assistant.** HA gửi
  `Referrer-Policy: no-referrer` cho mọi trang, và YouTube từ chối khung nhúng
  không kèm Referer. Khung video của card tự đặt
  `referrerpolicy="strict-origin-when-cross-origin"` trước khi nạp, nên video
  chạy cả trên HAOS và app Companion.

## 0.8.5 - 2026-09-14

### Added

- **Tivi LG webOS mở app YouTube gốc (có hình).** Loa `webostv` trước đây rơi
  vào nhánh "phát audio" nên tivi LG chỉ nhận luồng tiếng. Nay integration gọi
  `webostv.command` với `system.launcher/launch` (`youtube.leanback.v4`,
  `contentId` = mã video) — cả ở action `play_on_players` lẫn media player ảo.
  Playlist trên LG báo lỗi rõ ràng thay vì im lặng phát sai.

## 0.8.4 - 2026-08-30

### Changed

- Card tự đăng ký thành **Lovelace resource** thật (hiện trong danh sách Tài
  nguyên, nạp giống mọi card HACS) thay vì chỉ chèn qua `add_extra_js_url` — nhờ
  vậy không bị service worker của HA giữ bản cũ, và không phải thêm resource thủ
  công. Đăng ký sau khi HA khởi động xong và chỉ khi collection đã nạp, để không
  xoá nhầm các resource sẵn có; dashboard YAML thì tự quay lại `add_extra_js_url`.

## 0.8.3 - 2026-08-29

### Added

- Card tự đăng ký (dùng `add_extra_js_url`) nên **không cần thêm resource thủ
  công** trong Lovelace nữa. URL card kèm `?v=<phiên_bản>` để trình duyệt tự nạp
  bản mới mỗi lần integration lên phiên bản, khỏi phải hard-refresh.

## 0.8.2 - 2026-08-29

### Added

- Card: tích một loa trong lúc đang phát thì loa đó **tự vào bài đang phát**; bỏ
  tích thì chỉ loa đó dừng, các loa còn lại tiếp tục. Sau khi tự chọn loa, card
  không ghi đè lựa chọn theo phiên dùng chung nữa.

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
