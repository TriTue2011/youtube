# TriTue YouTube Player cho Home Assistant

[![Mở kho này trong HACS của bạn.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=TriTue2011&repository=youtube&category=integration)

Tìm và phát **YouTube, Zing MP3, video Facebook và link audio trực tiếp** ra loa trong Home Assistant
(Google Cast, Android TV, tivi webOS, DLNA, ESPHome, mọi `media_player` có `play_media`), hoặc nghe/xem ngay trên điện
thoại, máy tính. Điều khiển từ **một thẻ Lovelace**. Không cần license key.

Bản hiện tại: tích hợp **0.28.6** · máy phát (add-on) **0.9.9** · chạy trên `amd64` và `aarch64`.

## Ưu điểm và nhược điểm

**Ưu điểm**

- Không cần license key hay YouTube API key (tìm kiếm bằng `yt-dlp`, chỉ lấy thông tin bài, không tải nhạc).
- Một thẻ cho nhiều nguồn (YouTube, Zing, Facebook, link audio) và **nhiều loa cùng lúc**, khác loại cũng được; âm lượng riêng từng loa.
- Loa tải nhạc thẳng từ máy phát: đóng dashboard hay tắt điện thoại vẫn phát, Home Assistant tự chuyển bài.
- Playlist và hàng đợi dùng chung cả nhà, chia sẻ bằng mã; có từ khoá nhanh và video ghim.
- Điều khiển bằng giọng nói (Assist) và bằng 6 action trong automation.
- Nhiều loa tự khớp vị trí phát: loa vào sau không phát từ đầu, kiểm trôi mỗi 90 giây.
- Thẻ tự đăng ký vào Lovelace, có trình sửa bằng giao diện.

**Nhược điểm**

- Cần **một máy phát chạy riêng** (add-on, Docker hoặc c2a). HACS chỉ cập nhật tích hợp và thẻ, **máy phát phải cập nhật riêng**.
- Giải luồng YouTube dựa trên `yt-dlp` (phần mềm bên thứ ba): khi YouTube đổi cách phục vụ có thể phải cập nhật máy phát.
- Cast và DLNA không có đồng hồ chung: nhiều loa trong một phòng còn lệch vài trăm mili giây (cần khớp chặt thì dùng Cast group hoặc Snapcast); loa không hỗ trợ tua bị bỏ qua.
- Safari trên máy Mac xem video bị lỗi 153 (vẫn nghe được); video trên iPhone dừng khi khoá màn (tiếng thì giữ được khi bấm **nghe**).
- Loa ESPHome có thể không phát được bài YouTube (định dạng `m4a`/`opus`); một số video (VEVO…) không cho nhúng; Zing chỉ phát bài công khai, không có bài VIP.
- Cổng `8099` của máy phát chỉ nên mở trong LAN, **không forward ra Internet**; token tích hợp phải giữ kín.

## Cách hoạt động

| Phần | Ở đâu | Làm gì |
|---|---|---|
| **Máy phát** | Add-on [`youtube_player`](youtube_player/), Docker, hoặc trình phát có sẵn trong **c2a** | Tìm kiếm, lấy luồng audio, đưa luồng cho loa |
| **Tích hợp** | [`custom_components/tritue_youtube_player`](custom_components/tritue_youtube_player/) | Tạo `media_player` ảo, action, tự chuyển bài, tự đăng ký thẻ |
| **Thẻ** | Đi kèm tích hợp | Giao diện: tìm bài, chọn loa, hàng đợi, âm lượng, xem video |

```text
Thẻ (trình duyệt) ──► Tích hợp (Home Assistant) ──► Máy phát ──► loa tải luồng trực tiếp
```

## Cài đặt

Làm đúng thứ tự: máy phát → tích hợp → nối hai bên → thẻ.

### Bước 1 — Cài máy phát (chọn MỘT cách)

| Cách | Hợp khi | Ưu điểm | Nhược điểm |
|---|---|---|---|
| **A. Add-on** (khuyến nghị) | Home Assistant OS / Supervised | Cài một chạm, tự tải đúng image theo kiến trúc, có giao diện web trong HA | Chỉ có trên bản HA có Supervisor |
| **B. Docker Compose** | Mọi máy có Docker | Không cần Supervisor, đặt ở máy nào cũng được | Tự quản cổng, địa chỉ phát và việc cập nhật image |
| **C. c2a** | Nhà đã chạy c2a | Không cài thêm gì, dùng chung playlist với trang web c2a | Phụ thuộc c2a (c2a hỏng thì YouTube hỏng theo) |

**A. Add-on**

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**, thêm `https://github.com/TriTue2011/youtube`.
2. Cài **TriTue YouTube Player**, bấm **Start**.
3. (Nên làm) Ở tab **Configuration**, đặt `integration_token` là một chuỗi bất kỳ (không phải long-lived token của HA). Để trống thì add-on tự sinh, xem ở tab **Log**.
4. Cổng `8099` (loa tải luồng qua đây): add-on cài mới đã mở sẵn; add-on cài từ trước thì vào tab **Network** bật cổng `8099`. Chỉ điền `public_base_url: http://IP_HOME_ASSISTANT:8099` khi bạn đổi cổng hoặc loa không ra tiếng.

**B. Docker Compose** (trong thư mục `youtube_player`)

```bash
PUBLIC_BASE_URL='http://IP_MAY_DOCKER:8099' docker compose up -d --build
docker compose logs youtube-player      # token tự sinh nằm ở đây
```

**C. c2a:** mở tab **YouTube** của c2a, chép địa chỉ và token (địa chỉ có `/yt`, cần tích hợp ≥ 0.9.4).

### Bước 2 — Cài tích hợp

**HACS → ⋮ → Custom repositories**, thêm `https://github.com/TriTue2011/youtube`, loại **Integration** → tải **TriTue YouTube Player** → **khởi động lại Home Assistant**. (Hoặc bấm nút HACS ở đầu trang. Không dùng HACS thì chép `custom_components/tritue_youtube_player` vào `/config/custom_components/`.)

### Bước 3 — Nối tích hợp với máy phát

**Settings → Devices & services → Add integration → TriTue YouTube Player**, nhập địa chỉ và token:

| Máy phát | Địa chỉ |
|---|---|
| Add-on cài từ repo này | `http://b5248dd0-youtube-player:8099` |
| Add-on local | `http://local-youtube-player:8099` |
| Docker độc lập | `http://IP_MAY_DOCKER:8099` |
| c2a | `http://IP_C2A:3030/yt` |

### Bước 4 — Thêm thẻ

Tích hợp tự đăng ký thẻ khi Home Assistant khởi động (nên đã khởi động lại ở bước 2). Sửa dashboard → **Thêm thẻ** → **TriTue YouTube Player**, hoặc dán:

```yaml
type: custom:tritue-youtube-player-card
entity: media_player.tritue_youtube_player_<host_may_phat>
```

### Bước 5 — Thử

Mở thẻ, tìm một bài, tích một loa, bấm **nghe**. Không ra tiếng với loa DLNA/ESPHome thì kiểm cổng `8099` (bước 1A.4). Thẻ không hiện hoặc báo *Custom element doesn't exist*: xem [Khắc phục](docs/CHI-TIET.md#2-cài-đặt-chi-tiết) (mục 2.4: khởi động lại HA, xoá bộ nhớ đệm trình duyệt, kiểm Resources).

## Dùng nhanh

| Bạn muốn | Làm |
|---|---|
| Nghe ra loa trong nhà | Tích một hoặc nhiều loa → bấm **nghe** |
| Xem video ra tivi | Tích tivi → bấm **xem** |
| Nghe ngay trên điện thoại | Không tích loa nào → bấm **nghe** |
| Lưu playlist | Dán link playlist YouTube hoặc album Zing → **Lưu cả playlist này** |
| Bằng giọng nói | Bật **TriTue Music** trong trợ lý (LLM) của HA: *"Tìm bài …"*, *"Phát số 1 ở phòng khách"*, *"Bài tiếp theo"* |

**Action cho automation** (`tritue_youtube_player.*`, tham số đầy đủ trong **Developer tools → Actions**):

| Action | Làm gì |
|---|---|
| `play_on_players` | Phát một bài (mã hoặc link) ra các loa |
| `play_playlist` | Phát playlist trong kho theo mã 12 ký tự |
| `play_queue` | Phát hàng đợi chung ra các loa |
| `skip` | Sang bài kế hoặc lùi bài |
| `stop_session` | Dừng hẳn phiên phát |
| `remove_players` | Rút một số loa khỏi phiên, loa còn lại tiếp tục |

## Tài liệu thêm

- [Tài liệu chi tiết](docs/CHI-TIET.md): cài từng cách, các cách nghe nhạc, từng thiết bị, tuỳ biến thẻ, giới hạn đã biết kèm số đo.
- [Add-on](youtube_player/DOCS.md) · [API](youtube_player/API.md) · [tích hợp và thẻ](youtube_player_integration/README.md) · [nhật ký thay đổi](youtube_player_integration/CHANGELOG.md).

## Phát triển và kiểm thử

```bash
python -m unittest discover -s youtube_player/tests -v                                                  # máy phát
python -m pip install aiohttp && python -m unittest discover -s youtube_player_integration/tests -p 'test_*.py' -v   # hợp đồng
python -m compileall -q custom_components/tritue_youtube_player                                         # cú pháp
```

CI (`.github/workflows/build.yml`) chạy các bộ test trên, Hassfest, rồi dựng image đa kiến trúc lên GHCR. Release của tích hợp tự tạo khi `manifest.json` đổi phiên bản trên `main`.
