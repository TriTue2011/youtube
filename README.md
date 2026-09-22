# TriTue YouTube Player cho Home Assistant

Tìm và phát **nhạc YouTube, Zing MP3, video Facebook và link audio trực tiếp** ra bất
kỳ loa nào trong Home Assistant — loa Google Cast, Android TV, tivi LG webOS, DLNA,
ESPHome, hay mọi `media_player` hỗ trợ `play_media` — hoặc nghe và xem ngay trên
điện thoại, máy tính đang mở dashboard. Tất cả điều khiển từ **một thẻ Lovelace**.

Không cần license key. Token in trong log chỉ là khoá kết nối nội bộ giữa tích hợp
và máy phát, **không phải khoá kích hoạt** — đừng đăng công khai.

## Mục lục

1. [Ba phần và cách chúng nối với nhau](#1-ba-phần-và-cách-chúng-nối-với-nhau)
2. [Cài đặt](#2-cài-đặt)
3. [Các cách nghe nhạc](#3-các-cách-nghe-nhạc)
4. [Mỗi thiết bị nghe thế nào](#4-mỗi-thiết-bị-nghe-thế-nào)
5. [Tuỳ biến thẻ](#5-tuỳ-biến-thẻ)
6. [Giới hạn đã biết](#6-giới-hạn-đã-biết)
7. [Nhật ký](#7-nhật-ký)
8. [Phát triển và kiểm thử](#8-phát-triển-và-kiểm-thử)

---

## 1. Ba phần và cách chúng nối với nhau

| Phần | Ở đâu | Làm gì |
|---|---|---|
| **Máy phát** | Add-on [`youtube_player`](youtube_player/), hoặc Docker, hoặc trình phát có sẵn trong **c2a** | Tìm kiếm, lấy luồng audio (YouTube qua `yt-dlp`, Zing công khai, Facebook), **tiếp sóng luồng có chữ ký** cho loa, giữ phiên phát và playlist |
| **Tích hợp** | [`custom_components/tritue_youtube_player`](custom_components/tritue_youtube_player/) | Tạo `media_player` ảo, các action tự động hoá, đo khả năng của từng loa, và **tự đăng ký thẻ** |
| **Thẻ** | Đi kèm tích hợp, tệp `www/tritue-youtube-player-card.js` | Giao diện: tìm bài, chọn loa, hàng đợi, âm lượng từng loa, xem video, nghe trên máy |

Luồng đi của một bài hát:

```text
Thẻ (trình duyệt) ──► Tích hợp (Home Assistant) ──► Máy phát (add-on hoặc c2a)
                                                        │
                        ┌───────────────────────────────┴──────────┐
                        ▼                                          ▼
          Loa không có app YouTube                    Cast / Android TV / webOS
          (DLNA, ESPHome, amply…)                     mở app YouTube gốc, có hình
          tải luồng audio từ máy phát
```

**Hai điều hay bị nhầm:**

- **HACS chỉ cập nhật tích hợp và thẻ**, không cập nhật máy phát. Tính năng nào của
  thẻ cần máy phát đỡ (ví dụ một nguồn nhạc mới) thì phải cập nhật **cả máy phát**,
  nếu không thẻ có nút mà bấm vào không ai trả lời.
- **Loa tải nhạc trực tiếp từ máy phát**, không qua trình duyệt. Nên loa vẫn phát và
  tự chuyển bài kể cả khi bạn đã đóng dashboard hay tắt điện thoại.

Hỗ trợ **`amd64` và `aarch64`** — đã chạy thật trên cả hai.

---

## 2. Cài đặt

Làm theo đúng thứ tự: máy phát → tích hợp → thẻ.

### 2.1. Máy phát

#### Cách A — Add-on của Home Assistant (khuyến nghị)

**Settings → Add-ons → Add-on Store → ⋮ → Repositories**, thêm:

```text
https://github.com/TriTue2011/youtube
```

Cài **TriTue YouTube Player**. Supervisor tự tải image dựng sẵn đúng kiến trúc máy.

**Để phát ra loa không có app YouTube** (DLNA, ESPHome, amply…): loa cần tải luồng từ
cổng `8099` của add-on.

- Add-on **cài mới** từ 0.8.2 trở lên: cổng được công bố sẵn, không phải làm gì.
- Add-on **đã cài từ trước**: vào tab **Network** của add-on và bật cổng `8099`. Khai
  cổng trong cấu hình không tự mở cổng cho bản đã cài — Supervisor để nó ở trạng thái
  tắt. nếu trùng cổng sử dụng đổi cổng khác thì public_base_url cũng đổi theo
- Chỉ phải điền `public_base_url: http://IP_HOME_ASSISTANT:8099` khi bạn **đổi cổng**
  ở tab Network, hoặc loa vẫn không ra tiếng.

- Trong config addon có mục token, để trống xem log. Khuyên nên đặt token bất kỳ (không phải long token). Token dùng để add vào tích hợp.
  
Cổng này chỉ mở trong mạng nhà. **Không NAT/forward ra Internet.** Địa chỉ phát có
chữ ký và tự hết hạn.

Loa Cast, Android TV và tivi webOS luôn phát YouTube bằng app gốc của chúng, nên
không cần cổng này.

#### Cách B — Docker Compose độc lập

Từ thư mục `youtube_player`:

```bash
PUBLIC_BASE_URL='http://IP_MAY_DOCKER:8099' docker compose up -d --build
```

Token tự sinh xem bằng `docker logs`. Chi tiết tuỳ chọn: [youtube_player/DOCS.md](youtube_player/DOCS.md).

#### Cách C — Trình phát có sẵn trong c2a

Nếu nhà đã chạy **c2a (chatgpt2api)** thì không cần add-on: c2a có một máy phát cùng
giao thức. Địa chỉ và token chép ở tab **YouTube** của c2a. Dạng địa chỉ:
`http://IP_C2A:3030/yt` (cần tích hợp ≥ 0.9.4 để nhận địa chỉ có `/yt`).

Cài song song được: mỗi kết nối là một mục riêng trong tích hợp.

### 2.2. Tích hợp

#### Qua HACS

**HACS → Custom repositories** → thêm `https://github.com/TriTue2011/youtube` loại
**Integration** → tải **TriTue YouTube Player** → khởi động lại Home Assistant.

#### Thủ công

Chép `custom_components/tritue_youtube_player` vào `/config/custom_components/`, rồi
khởi động lại Home Assistant.

#### Nối tích hợp với máy phát

**Settings → Devices & services → Add integration → TriTue YouTube Player.** Nhập địa
chỉ máy phát và token (in trong log máy phát khi khởi động):

| Máy phát | Địa chỉ |
|---|---|
| Add-on cài từ repo này | `http://b5248dd0-youtube-player:8099` |
| Add-on local | `http://local-youtube-player:8099` |
| Docker độc lập | `http://IP_MAY_DOCKER:8099` |
| c2a | `http://IP_C2A:3030/yt` |

Có thể chọn **loa phát mặc định** trong phần cấu hình của tích hợp.

### 2.3. Thêm thẻ

Tích hợp **tự đăng ký thẻ** vào Lovelace Resources, kèm `?v=<phiên_bản>` để trình
duyệt tự lấy bản mới sau mỗi lần cập nhật. Việc đăng ký chạy khi Home Assistant khởi
động, nên sau lần cài đầu tiên hãy **khởi động lại HA một lần**.

Sau đó: sửa dashboard → **Thêm thẻ** → tìm **TriTue YouTube Player**. Hoặc thêm thẻ
thủ công:

```yaml
type: custom:tritue-youtube-player-card
entity: media_player.tritue_youtube_player_<host_may_phat>
```

`entity` là `media_player` ảo của tích hợp — tên có kèm host của máy phát. Chỉ cần
hai dòng trên; thẻ tự đọc các loa khác trong nhà.

### 2.4. Thẻ không hiện hoặc báo "Custom element doesn't exist"

Thẻ đã đăng ký đúng ở máy chủ nhưng trình duyệt còn giữ bản cũ. Làm theo thứ tự:

1. **Khởi động lại Home Assistant**, hoặc reload nhanh: Settings → Devices & services →
   TriTue YouTube Player → ⋮ → **Reload**.
2. **Xoá bộ nhớ đệm của trình duyệt.** HA có service worker nên `Ctrl/Cmd+Shift+R`
   thường không đủ: mở **DevTools → Application → Storage → Clear site data** (sẽ phải
   đăng nhập lại). Trên app HA của điện thoại: thoát hẳn app rồi mở lại, hoặc
   **Settings → Companion App → Debugging → Reset frontend cache**.
3. **Kiểm resource** ở Settings → Dashboards → ⋮ → **Resources**: phải có dòng
   `/tritue_youtube_player/tritue-youtube-player-card.js?v=<phiên_bản>`.
4. Chưa có thì **thêm tay**: Add resource → URL
   `/tritue_youtube_player/tritue-youtube-player-card.js`, loại **JavaScript Module**.
   Lần khởi động lại sau, tích hợp tự gắn `?v=`.

---

## 3. Các cách nghe nhạc

Mỗi bài trong kết quả tìm kiếm có hai nút: **xem** (video) và **nghe** (chỉ tiếng).
Chúng làm gì tuỳ vào việc bạn **có tích loa hay không**:

| Bạn muốn | Làm thế nào | Tiếng ra ở đâu | Tắt màn hình điện thoại |
|---|---|---|---|
| Nghe ra loa trong nhà | Tích một hoặc nhiều loa → bấm **nghe** | Loa | Loa vẫn phát, vẫn tự chuyển bài |
| Xem video ra tivi | Tích tivi → bấm **xem** | Tivi (app YouTube gốc) | Tivi vẫn phát |
| Nghe ngay trên điện thoại | Không tích loa nào → bấm **nghe** | Điện thoại | Xem [mục 4](#4-mỗi-thiết-bị-nghe-thế-nào) |
| Xem video ngay trên thẻ | Không tích loa nào → bấm **xem** | Điện thoại / máy tính | Tắt công tắc «Nghe khi tắt màn hình»: dừng. Bật: tiếng vẫn chạy |
| Loa phát, điện thoại nghe cùng | Loa đang phát → bấm **Nghe trên máy này** | Loa **và** điện thoại | Xem mục 4 |
| Loa phát, thẻ hiện hình | Tích loa → bấm **xem** | Loa (hình trên thẻ tắt tiếng, chạy theo loa) | Loa vẫn phát |

### 3.1. Phát ra loa

- **Nhiều loa cùng lúc**, khác loại cũng được — ví dụ tivi + loa Google + loa DLNA
  trong một lượt.
- **Âm lượng từng loa:** mỗi loa đã tích có thanh trượt riêng. Thẻ không ép một mức
  chung, nên Cast và DLNA giữ âm lượng độc lập.
- **Tích thêm loa khi đang phát** thì loa đó tự vào bài; **bỏ tích** thì chỉ loa đó
  dừng, các loa khác tiếp tục.
- **Mỗi lần phát là một nhóm.** Tích loa nào thì thẻ hiện bài, tiến độ và video của
  loa đó. Nút **«Cho … nghe cùng»** đưa loa khác vào đúng bài, đúng chỗ đang phát.
- **Tự chuyển bài không cần mở thẻ:** Home Assistant thấy loa hết bài thì tự phát bài
  kế của nhóm, kể cả khi bạn đã đóng trình duyệt.
- **Chuyển bài nhanh:** máy phát lấy sẵn bài kế của mỗi nhóm loa, và dùng lại link
  tới gần lúc hết hạn.

### 3.2. Nghe hoặc xem ngay trên máy đang mở thẻ

Không tích loa nào rồi bấm **nghe**: tiếng phát ngay trên máy đó, có hàng đợi, tự sang
bài, và nút điều khiển trên màn hình khoá.

Bấm **xem**: video mở ngay trên thẻ. Có nút phóng to và toàn màn hình; trên điện thoại
Android, toàn màn hình **tự xoay ngang**. Trình duyệt chặn tự phát có tiếng thì thẻ
hiện «Chạm vào video để phát có tiếng» — iPhone luôn đòi một cú chạm vào chính video.

### 3.3. Nghe cùng loa

Loa đang phát mà bạn muốn điện thoại cũng có tiếng: bấm **Nghe trên máy này**. Thẻ giữ
tiếng trên máy cho tới khi loa thật sự lên tiếng, nên không có quãng im lặng ở giữa.

### 3.4. Nghe khi tắt màn hình

Công tắc **«Nghe khi tắt màn hình»** (mặc định tắt).

- **Tắt:** tắt màn hình hoặc chuyển ứng dụng thì tiếng trên máy dừng; mở lại thì phát
  tiếp từ chỗ cũ.
- **Bật:** tắt màn hình vẫn nghe tiếp — trong giới hạn của từng nền tảng, xem
  [mục 4](#4-mỗi-thiết-bị-nghe-thế-nào).

Loa thì luôn phát tiếp kể cả khi đóng trình duyệt hay app, vì Home Assistant tự chuyển
bài.

### 3.5. Playlist chung cả nhà

- Dán link **playlist YouTube** hoặc **album Zing** vào ô tìm kiếm → **«Lưu cả playlist
  này»**.
- Nút **+** ở mỗi bài để thêm vào playlist có sẵn.
- Phát cả playlist ra loa (tự chuyển bài) hoặc nghe trên máy.
- **Chia sẻ:** chép **mã chia sẻ** gửi người khác; họ dán mã để lưu về.
- Thẻ trong HA và trang web c2a nối cùng máy phát **thấy chung một danh sách**.

### 3.6. Từ khoá nhanh và video ghim

Khi chưa tìm gì, thẻ hiện **Bài hát gợi ý**: một hàng **từ khoá nhanh** (bấm là tìm) và
các **mục** chứa **video ghim sẵn** (bấm là phát).

- Nút **ghim** ở mỗi kết quả tìm kiếm: chọn mục để gắn bài vào, hoặc tạo mục mới ngay
  tại chỗ. Ghim được bài YouTube và Facebook.
- Nút **✕** trên từ khoá, trên mục, hay trên video ghim là **xoá thật**, không phải ẩn.
- Có thể **dán link video** để ghim thẳng vào một mục.
- Dữ liệu lưu trong Home Assistant, **dùng chung cả nhà**. Ai đăng nhập cũng xem được;
  **chỉ quản trị viên** được thêm, sửa, xoá.

### 3.7. Nói với trợ lý Assist

Bật **TriTue Music** trong trợ lý (LLM) của Home Assistant rồi nói *"mở bài …"*. Trợ lý
đưa 10 bài, hỏi phát ra loa nào (một, nhiều, hay tất cả) rồi phát. Nói được cả *"bài
kế ở bếp"*, *"dừng loa phòng khách"*, *"đang phát gì"*.

### 3.8. Tự động hoá

Tích hợp có bốn action dùng được trong script và automation:

| Action | Làm gì |
|---|---|
| `tritue_youtube_player.play_on_players` | Phát một bài YouTube, Zing công khai hoặc link HTTP ra một hoặc nhiều loa; đặt được âm lượng, nhập vào nhóm đang phát, hoặc phát cả playlist |
| `tritue_youtube_player.skip` | Sang bài kế (hoặc lùi bài) của một nhóm loa |
| `tritue_youtube_player.stop_session` | Dừng hẳn một nhóm loa |
| `tritue_youtube_player.remove_players` | Rút một số loa khỏi nhóm, các loa còn lại tiếp tục |

Ví dụ — sáng 6 giờ bật nhạc ra loa phòng khách:

```yaml
action: tritue_youtube_player.play_on_players
data:
  entry_id: 01J00000000000000000000000   # mã mục cấu hình của tích hợp
  source: youtube                        # youtube | zing | http
  target: dQw4w9WgXcQ                    # mã video, link YouTube, hoặc link Zing
  entity_id:
    - media_player.phong_khach
  volume_level: 0.35
```

Tham số đầy đủ xem trong **Developer tools → Actions**, hoặc tệp
[`services.yaml`](custom_components/tritue_youtube_player/services.yaml).

---

## 4. Mỗi thiết bị nghe thế nào

Mỗi nền tảng có luật riêng về phát tiếng và tự phát, nên thẻ chọn đường khác nhau cho
từng máy. Bảng dưới là **số đo trên máy thật**, không phải lý thuyết:

| Thiết bị | Nghe trên máy | Xem video trên thẻ | Tắt màn hình khi đang nghe |
|---|---|---|---|
| **Android** (app HA hoặc Chrome) | Phần tử âm thanh | Khung YouTube | ✅ Nghe tiếp |
| **iPhone / iPad** (app HA) | Phần tử âm thanh (từ 0.26.74) | Khung YouTube | ✅ Nghe tiếp khi đang **nghe**, hoặc khi **xem** với công tắc «Nghe khi tắt màn hình» bật (từ 0.26.75) |
| **Chrome trên máy tính** | Phần tử âm thanh | Khung YouTube | — |
| **Safari trên máy Mac** | Phần tử âm thanh | ❌ Lỗi 153, thẻ tự chuyển sang chỉ nghe tiếng | — |

**Vì sao iPhone tắt màn thì video dừng mà nhạc vẫn chạy?** Khi khoá máy, iOS treo trang
để tiết kiệm pin. Tiếng chỉ sống sót nếu nó phát ra từ **phần tử âm thanh của chính
trang**; khung nhúng của bên thứ ba như YouTube thì bị treo ngay. Đo trong hộp đen: khoá
màn lúc video ở giây 308,3 thì 88 giây sau vẫn là 308,3.

Nên trên iPhone, tiếng khi tắt màn luôn phải đi qua phần tử âm thanh. App Home Assistant
cho iOS có khai quyền phát tiếng nền (`UIBackgroundModes: audio`), và đã thử thật với một
bài Zing: khoá màn vẫn nghe tiếp. Từ 0.26.74, bấm **nghe** một bài YouTube là đi đúng phần
tử ấy.

Muốn **xem** mà tắt màn vẫn nghe thì bật công tắc «Nghe khi tắt màn hình» trước. Từ
0.26.75, lúc ấy thẻ **cho tiếng lên trước rồi mới bật hình**: tiếng phát ra từ phần tử âm
thanh, hình tắt tiếng chạy theo. Khi khoá màn, hình đứng lại còn tiếng chạy tiếp; mở màn
lên thì hình tự đuổi kịp. Thứ tự này là thứ đã đo chạy được trên iPhone — ngược lại, để
khung video chạy trước thì phần tử âm thanh không chen vào được.

Trên iPhone, tiếng thường cần vài giây mới lên, chậm hơn Android — trình phát của iOS nạp
tệp dài lâu hơn.

**Lần đầu phải tự bấm phát trên iPhone** là đúng thiết kế của Apple: trang phải được một
cú chạm thật trước khi được phép phát tiếng. Chạm một lần, những lần sau trong cùng phiên
không cần nữa.

---

## 5. Tuỳ biến thẻ

### 5.1. Trình sửa bằng giao diện

Bấm **Sửa thẻ** trên dashboard là có trình sửa với ba tab:

- **Cấu hình** — entity của máy phát, tiêu đề, loa chọn sẵn.
- **Hiển thị** — nền, màu, độ đục, cỡ chữ, kiểu sóng nhạc, ẩn/hiện từng nguồn.
- **Bố trí** — xếp ngang hay dọc, bề rộng cột video.

Không cần nhớ khoá YAML nào; bảng dưới chỉ để tham khảo khi sửa bằng tay.

### 5.2. Toàn bộ khoá cấu hình

| Khoá | Mặc định | Ý nghĩa |
|---|---|---|
| `entity` | *(bắt buộc)* | `media_player` ảo của tích hợp |
| `entry_id` | — | Mã mục cấu hình của tích hợp. Thêm vào nếu entity đôi lúc chớp tắt, để thẻ khỏi phụ thuộc trạng thái entity |
| `entities` | loa mặc định của tích hợp | Danh sách loa được **tích sẵn** khi mở thẻ |
| `title` | `TriTue Music` | Tiêu đề thẻ |
| `layout` | `horizontal` | `horizontal`: hai cột; `vertical`: xếp dọc một cột. Chọn rõ `horizontal` thì thẻ giữ hai cột **kể cả khi hẹp** |
| `player_width` | — | 20–80: bề rộng cột video, tính theo % (chỉ áp cho bố cục hai cột) |
| `waveStyle` | `bars` | Kiểu sóng nhạc: `bars`, `simple`, `dots` |
| `bg_style` | `gradient` | `gradient`, `solid`, hoặc `none` (trong suốt, ăn theo dashboard) |
| `bg_color` | — | Màu nền, dạng `#rrggbb` |
| `accent_color` | — | Màu nhấn (nút, viền, sóng nhạc) |
| `accent2_color` | — | Màu nhấn phụ |
| `text_color` | — | Màu chữ chính |
| `text_dim_color` | — | Màu chữ phụ |
| `surface_color` | — | Màu mặt các ô nổi, bảng chọn |
| `line_color` | — | Màu viền, đường kẻ |
| `danger_color` | — | Màu cảnh báo, nút xoá |
| `opacity` | `100` | 0–100: độ đục của nền |
| `zoom` | `100` | 50–150: thu phóng chữ và nút |
| `show_youtube` | `true` | Hiện nguồn YouTube trong hàng chọn nguồn |
| `show_zing` | `true` | Hiện nguồn Zing MP3 |
| `show_facebook` | `true` | Hiện nguồn Facebook |
| `show_playlist` | `true` | Hiện tab Playlist |

Các khoá màu **để trống là giữ nguyên diện mạo gốc**. Ẩn một nguồn chỉ ẩn khỏi giao
diện, không khoá nó phía máy phát: bài của nguồn ấy vẫn phát lại được từ hàng đợi hay
playlist.

### 5.3. Ví dụ đầy đủ

```yaml
type: custom:tritue-youtube-player-card
entity: media_player.tritue_youtube_player_172_16_10_38
title: Nhạc cả nhà
entities:
  - media_player.phong_khach
layout: vertical
waveStyle: dots
bg_style: solid
bg_color: "#141210"
accent_color: "#ff8a3d"
opacity: 90
zoom: 110
show_facebook: false
```

### 5.4. Muốn thẻ rộng hơn

Bề rộng của thẻ **không** chỉnh bằng CSS, mà do kiểu dashboard quyết định:

- **Dashboard kiểu Sections:** thẻ đã tự lấy trọn bề ngang của section. Nếu vẫn chật
  thì section đang hẹp — vào cài đặt view, giảm **"Max number of sections wide"** xuống
  1 để section trải hết màn hình.
- **Dashboard kiểu Masonry:** thẻ rộng đúng bằng một cột; không có cách nào kéo rộng hơn.
- **View kiểu Panel:** một thẻ chiếm trọn màn hình — hợp nhất nếu muốn xem video to.

Thẻ rộng ra **không đè** lên thẻ khác: dashboard xếp theo lưới, các thẻ tự giãn chỗ.

### 5.5. Ẩn thiết bị

- Loa hay tivi đang **mất kết nối** (`unavailable`) tự ẩn khỏi thẻ và tự hiện lại khi có
  kết nối.
- Nút **ẩn thiết bị** trên thẻ để giấu hẳn những loa bạn không bao giờ dùng. Danh sách ẩn
  lưu trong Home Assistant, áp cho mọi máy.

---

## 6. Giới hạn đã biết

### 6.1. Safari trên máy Mac không xem được video — lỗi 153

**Triệu chứng:** bấm **xem** trên Safari của máy Mac, khung video hiện *"Lỗi cấu hình
trình phát video — Lỗi 153"*. Thẻ tự chuyển sang phát tiếng của bài đó, nên vẫn nghe
được, chỉ mất hình. **Chrome trên cùng máy Mac, Android và iPhone đều xem bình thường.**

**Đã biết chắc:**

- YouTube trả mã 153 khi nó **không nhận được referrer** — tức không biết trang nào đang
  nhúng. Kiểm được bằng cách dán thẳng `https://www.youtube.com/embed/<mã video>` vào
  thanh địa chỉ: lúc ấy không trình duyệt nào gửi referrer, và **cả Chrome lẫn Safari**
  đều ra 153.
- Home Assistant trả tiêu đề `Referrer-Policy: no-referrer` cho mọi trang của nó.
- Thẻ chống lại bằng thuộc tính `referrerpolicy="strict-origin-when-cross-origin"` đặt
  trên khung video — đúng như mã nhúng chính thức lấy từ nút *Chia sẻ → Nhúng* của
  YouTube. Chrome và iPhone tôn trọng thuộc tính ấy nên chạy tốt.

**Đã thử và loại trừ, mỗi thứ bằng một phép đo:**

| Nghi can | Cách thử | Kết quả |
|---|---|---|
| Mở HA bằng địa chỉ IP | Mở bằng tên miền | Vẫn 153 |
| Tên miền nhúng | Tự đổi sang `youtube-nocookie.com` (0.26.73) | Vẫn 153 |
| Video bị giới hạn | Hỏi YouTube: `age_limit=0`, `playable_in_embed=True`, công khai | Không phải |
| Bảo vệ chống theo dõi nâng cao | Tắt trong Safari → Nâng cao | Vẫn 153 |
| Ngăn theo dõi giữa các trang, cửa sổ riêng tư, tiện ích | Tắt / mở cửa sổ thường | Vẫn 153 |

**Chưa giải được.** Còn một hướng chưa thử: cho tích hợp tự phục vụ một trang trung gian
cùng tên miền với Home Assistant, mang chính sách referrer riêng, rồi đặt khung YouTube
bên trong. Đây là cách đã có người làm chạy được trong app iOS, nhưng hiện **tạm dừng**.

**Cách dùng trong lúc chờ:** trên máy Mac, **xem video bằng Chrome**. Bấm **nghe** trên
Safari thì vẫn chạy bình thường.

### 6.2. Video trên iPhone dừng khi khoá màn

Khung YouTube bị iOS treo ngay khi khoá máy — không vá được từ phía thẻ. Tiếng thì giữ
được: bấm **nghe**, hoặc bật công tắc «Nghe khi tắt màn hình» rồi mới bấm **xem**. Xem
[mục 4](#4-mỗi-thiết-bị-nghe-thế-nào).

### 6.3. Các loa không đồng bộ từng mẫu

Loa mới vào sẽ phát bài **từ đầu**, không khớp vị trí với loa đang phát — Cast và DLNA vốn
không đồng bộ mẫu với nhau. Cần khớp thời điểm giữa nhiều phòng thì dùng **Cast group**
(các loa Google) hoặc **Snapcast**.

### 6.4. Loa ESP32 / ESPHome

YouTube trả định dạng `m4a`/`opus`. Cast và DLNA phát tốt, nhưng firmware media_player của
ESPHome thường chỉ giải mã MP3/FLAC/WAV, nên **có thể không phát được bài YouTube**. Zing
(MP3) và link HTTP thì vẫn ổn.

### 6.5. Một số video không cho nhúng

Một số video của hãng đĩa (VEVO…) bị YouTube từ chối nhúng. Thẻ tự chuyển sang phát tiếng
của bài đó.

### 6.6. Bảo mật token

Token tích hợp là khoá xác thực giữa tích hợp và máy phát. Nó hiện trong log để bạn sao
chép; đừng chia sẻ ra ngoài.

---

## 7. Nhật ký

Thẻ **không** ghi nhật ký chẩn đoán vào Home Assistant. Bản cũ viết một dòng mỗi
vài giây mỗi lần bấm phát (`tritue_youtube_player.the`), nên file log và cơ sở dữ
liệu của người cài thẻ tăng liên tục.

---

## 8. Phát triển và kiểm thử

```bash
# Add-on: hành vi HTTP
python -m unittest discover -s youtube_player/tests -v

# Hợp đồng giữa add-on, tích hợp và thẻ
python -m pip install aiohttp
python -m unittest discover -s youtube_player_integration/tests -p 'test_*.py' -v

# Cú pháp
python -m compileall -q custom_components/tritue_youtube_player
node --check youtube_player/app/static/app.js
node --check custom_components/tritue_youtube_player/www/tritue-youtube-player-card.js
```

CI (`.github/workflows/build.yml`) chạy các bộ test trên, Hassfest, rồi dựng image đa kiến
trúc đẩy lên GHCR. Release của tích hợp tự tạo khi `manifest.json` đổi phiên bản trên
`main`; ghi chú phát hành lấy từ
[`youtube_player_integration/CHANGELOG.md`](youtube_player_integration/CHANGELOG.md).

Tài liệu thêm: [add-on](youtube_player/DOCS.md) · [API](youtube_player/API.md) ·
[tích hợp và thẻ](youtube_player_integration/README.md) ·
[phân tích clean-room APK YouTube Music](docs/YOUTUBE_MUSIC_APK_ANALYSIS.md).
