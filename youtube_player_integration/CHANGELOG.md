# Changelog

## 0.26.37 - 2026-09-21

### "Bị giật, tiếng thì mất 10s mới có" — thẻ kết luận vội rồi tự dỡ bỏ khung đang chạy tới

> *"Tôi đang phát ra loa mà bật nghe trên máy này là bị giật, tiếng thì mất 10s mới có"*

Bản 0.26.36 hỏi khung **đúng một lần ở giây 2,5** rồi kết luận. Mà phép thử "có bị chặn
tiếng không" lại coi **trạng thái −1 (chưa chạy)** là bị chặn — trên điện thoại khung
YouTube thường mất vài giây mới nạp xong và báo về. Kết quả: thẻ dỡ bỏ một khung **sắp
kêu**, rồi quay về đường cũ qua máy chủ. Cộng lại đúng bằng mười giây, và cú chuyển giữa
chừng chính là cái giật.

Hai chỗ sửa, cùng một nguyên tắc: **chỉ kết luận khi có bằng chứng**.

1. **Canh thay vì hỏi một lần.** Nay chỉ hai câu trả lời được tính là dứt khoát: khung báo
   *đang phát* mà *câm* → bị chặn thật, lùi ngay; hoặc quá 8 giây vẫn chưa hề kêu. Còn
   "chưa báo gì" thì đợi tiếp và thúc tiếng. Khung báo đang phát mà không câm thì thôi
   canh, để yên cho nó chạy.
2. **Không tua khung trong 6 giây đầu.** Trình phát mới mở còn đang ổn định; tua vào quãng
   ấy là cú giật đầu tiên người nghe gặp, mà lệch lúc đó chỉ vì nó chưa kịp chạy.

### Đường lùi cũng hết giật, và nhanh hơn một nhịp

Khi phải lùi về thẻ âm thanh, trước đây nó **phát từ giây 0** rồi vòng canh mới kéo về chỗ
loa — nghe một quãng sai chỗ rồi giật sang chỗ đúng, và cú kéo ấy tốn thêm một lượt xin dữ
liệu (đo 20/09/2026: YouTube mất **1,64 giây** để trả byte đầu khi nhảy vào giữa bài). Nay
nó vào thẳng giây của loa ngay khi nạp.

### Và nếu vẫn không có tiếng, thẻ sẽ NÓI RA VÌ SAO

Dòng trạng thái lúc lùi nay kèm số đo: `câm=… trạng thái=… giây=…`. Lần sau chỉ cần đọc
dòng ấy là biết khung bị trình duyệt chặn thật hay chỉ chưa kịp nạp — khỏi đoán thêm vòng
nào nữa.

## 0.26.36 - 2026-09-21

### Tích loa lúc đang nghe trên máy: hết quãng im lặng ở giữa

Soát lại cả bốn nước đi của tiếng thì lộ ra một quãng chết không ai để ý: bấm tích loa
trong lúc đang nghe (hoặc đang xem) trên máy thì thẻ **tắt tiếng máy ngay lập tức**, trong
khi loa còn phải chờ máy chủ giải bài rồi mới nạp đệm.

Đo trên máy chủ 20/09/2026: riêng việc giải một bài YouTube mất **1,59 giây**, và loa Cast
còn vài giây nữa mới thật sự kêu — chính vì thế thẻ đã có sẵn thang tua 1,2 / 2,4 / 3,8 /
6 giây để chờ loa. Cộng lại là vài giây **không có tiếng ở đâu cả**.

Nay tiếng trên máy chạy tiếp cho tới **nhịp đầu tiên loa thật sự báo "playing"** rồi mới
tắt. Nếu quá 15 giây loa vẫn im thì thẻ không nhường nữa — loa hỏng thì ít nhất người dùng
còn nghe được trên máy, thay vì mất cả hai.

| Nước đi | Trước | Nay |
|---|---|---|
| Đang nghe (chỉ tiếng) trên máy → tích loa | im lặng vài giây rồi loa kêu | nghe liên tục, máy tắt đúng lúc loa kêu |
| Đang xem video trên máy → tích loa | khung câm ngay, chờ loa | khung giữ tiếng tới khi loa kêu |
| Đang nghe loa → bật "nghe trên máy này" | 4–10 giây (bản trước) | khung YouTube vào thẳng giây của loa (0.26.34) |
| Chọn một bài KHÁC để phát ra loa | dừng ngay | vẫn dừng ngay — vừa chọn bài mới mà còn nghe bài cũ mới là lạ |

## 0.26.35 - 2026-09-21

### Lớp tiếp sức luồng nay trả lời cả HEAD

Soát lại cả đường đi của tiếng thì thấy một khả năng bị đánh rơi giữa đường. Đo trên máy
nhà 20/09/2026, cùng một địa chỉ luồng:

| Hỏi kiểu gì | Máy phát (c2a / add-on) | Qua lớp tiếp sức của tích hợp |
|---|---|---|
| GET kèm `Range: bytes=0-1` | 206, `audio/mp4`, `accept-ranges: bytes` | 206 — đúng |
| HEAD | 200 kèm kiểu và cỡ tệp | **405 Method Not Allowed** |

Cả hai máy phát đều cố ý trả lời HEAD (c2a có tuyến riêng, add-on có hẳn hàm
`head_stream`), nhưng lớp tiếp sức chỉ khai `get`, nên aiohttp từ chối. Trình phát nào
hỏi HEAD trước khi tải — AVFoundation của máy nhà Táo, vài loa DLNA — sẽ coi như luồng
hỏng mà không có lý do nào hiện ra.

Nay lớp tiếp sức hỏi máy phát **một byte** rồi suy ra cỡ tệp từ `Content-Range`, đúng cách
`head_stream` của add-on làm — nên chạy được với cả bản add-on đời cũ chưa có hàm ấy.

**Add-on không phải sửa gì.** Nó đã đúng từ trước; chỗ hụt nằm ở lớp tiếp sức.

## 0.26.34 - 2026-09-20

### Nghe trên máy này: lấy tiếng thẳng từ YouTube, không đi vòng qua máy chủ nữa

> *"mở nhạc trên loa, sau đó tích vào nghe trên thiết bị này cũng mãi mới có tiếng, đồng bộ
> quá lâu, trong khi card này thì quá nhanh"* — chủ máy 20/09/2026, kèm mã nguồn thẻ
> `phicomm-r1-card`.

Đọc thẻ ấy thì ra điều quyết định: **nó không bao giờ phát nhạc bằng thẻ `<audio>`**. Nhạc
luôn nằm trong khung nhúng YouTube; phần tử âm thanh duy nhất của nó là một dòng im lặng,
chỉ để iOS coi trang là đang có tiếng.

Thẻ này thì đi đường dài, và đây là toàn bộ chỗ mất thời gian:

| Chặng | Đường cũ (thẻ `<audio>`) | Đường mới (khung YouTube) |
|---|---|---|
| Lấy địa chỉ luồng | hỏi máy chủ giải bài — đo 1,5–2,6 giây | không có chặng này |
| Tải tiếng | qua máy chủ nhà mình | thẳng từ Google |
| Vào đúng giây của loa | tua sau khi đã tải, tức xin lại dữ liệu và nạp đệm lại | `start=` ngay trong địa chỉ nhúng |
| Giữ cho khớp loa | vòng tua mỗi giây | không cần |

Từ bản này, bấm **"Nghe trên máy này"** trong lúc loa đang phát một bài YouTube sẽ mở một
khung YouTube **thu bé còn một điểm ảnh**, vào thẳng giây loa đang ở. Thẻ trông y như cũ —
không hiện video, không thêm nút nào — chỉ là có tiếng gần như ngay.

Zing MP3 và link audio thì khung YouTube không phát được, nên vẫn đi đường cũ.

### Tắt màn hình vẫn nghe — ai giữ tiếng thì theo NỀN TẢNG, không theo "có loa hay không"

| Máy | Khi màn hình tắt | Nên ai mang tiếng |
|---|---|---|
| iPhone / iPad / Safari | khung nhúng sống tiếp **nếu** trang còn một dòng im lặng đang chạy | khung YouTube + `_giuTiengNen()` |
| Android và máy khác | Chrome treo khung nhúng lúc trang ẩn | phần tử `<audio>` |

Nên đường nhanh **tự nhường**: máy không phải nhà Táo mà đang bật "nghe khi tắt màn hình"
thì vẫn đi phần tử âm thanh như trước — chậm hơn, nhưng là thứ duy nhất còn chạy khi màn
hình đã tắt. Bật công tắc ấy giữa chừng cũng vậy: thẻ giao tiếng lại cho phần tử âm thanh
rồi đóng hẳn khung.

Đồng thời sửa một lỗ hổng có sẵn: nhánh giữ-tiếng-trong-khung của máy nhà Táo trước đây còn
đòi **không có loa nào đang phát**, nên vừa ra loa vừa nghe trên iPhone mà bật nghe-khi-tắt-
màn là rơi xuống nhánh phần tử âm thanh — đúng thứ WebKit không tải nổi, tức mất tiếng. Có
loa hay không thì WebKit vẫn thế, nên điều kiện ấy bỏ đi.

### Safari im tiếng

Trên Safari (iPhone, iPad, cả Mac) phần tử âm thanh đo được là **không bao giờ tải**
(`mang=3`, tức không tìm được nguồn). Đó chính là chuyện "dùng Safari không có tiếng mà
phicomm có tiếng": thẻ phicomm không hề dùng phần tử ấy. Nay mọi đường YouTube của thẻ này
cũng vậy, nên Safari đi chung một đường đã chạy được với mọi máy khác.

### Khung nhúng chuyển sang `www.youtube.com`

Chrome quyết định cho một khung tự phát **kèm tiếng** hay không theo mức gắn bó của người
dùng với chính tên miền ấy. `youtube-nocookie.com` thì gần như không máy nào từng mở nên
điểm bằng không — khớp với thứ đo được 20/09: dựng khung có tiếng trên Android thì rơi về
nút play của YouTube. `phicomm-r1-card` dùng `www.youtube.com` và nghe được ngay.

Giả thuyết này **chưa đo trực tiếp được**, nên có lối lùi: khung bị chặn tiếng thì 1,5 giây
sau thẻ tự trả việc về đường cũ — chậm như trước, chứ không mất tiếng.

### Hai nền tảng nhập lại làm một

Chỗ tách Android với máy nhà Táo trong "Nghe trên máy này" (mới thêm hôm qua) nay bỏ đi: cả
hai đi chung đường khung.

### Đo trên máy, không chỉ chạy test

Dựng thẻ trong Chrome không cần Home Assistant, bật chế độ chỉ-mang-tiếng rồi đọc kích
thước thật:

| Trạng thái | Khung hình | Lớp `video-on` | Nút phóng to / đóng |
|---|---|---|---|
| Chỉ mang tiếng | **1 × 1** điểm ảnh, vẫn nằm trong trang | không | ẩn |
| Xem video như cũ | 477 × 268 | có | hiện |

Một bẫy CSS đã dính và đã chữa: đặt `width: 1px` thì khung **vẫn rộng 497px**, vì bề rộng
do một luật sáu lớp của bố cục hai cột đặt. Phải chặn bằng `max-width` — thuộc tính khác
nên không phải tranh độ ưu tiên.

## 0.26.33 - 2026-09-20

### Bấm "Nghe (chỉ tiếng)" mà vẫn ra video

> *"À giờ chọn chỉ nghe, hình tai nghe, nó lại ra mặc định video."*

Đúng, và đây là lỗi có sẵn chứ không phải mới. Khi có loa được tích, dòng quyết định mở
hình hay không gộp hai ý làm một:

```js
if ((watch && isVideo) || this._video.open) { … }
```

Vế thứ hai nghĩa là: **hễ đang mở hình thì bài mới cũng mở hình** — bất kể người dùng vừa
bấm nút nào. Nên đang xem một bài, bấm nút tai nghe cho bài khác, thì hình lại hiện lên.

Ý định đã nêu rõ ở nút bấm thì không được đoán lại. Nay bấm nút tai nghe là **đóng hình**.

Đo lại trên trình duyệt, cùng một cảnh (đang mở hình, loa "Phòng khách" đã tích):

| Bấm | Thẻ làm gì |
|---|---|
| Xem video | mở hình |
| Nghe (chỉ tiếng) | **đóng hình** |

## 0.26.32 - 2026-09-20

### Safari trên máy Mac bị xếp nhầm vào nhóm Android

Chủ máy mở thẻ bằng Safari trên iMac, không nghe được gì, và gửi kèm dòng số của thẻ:

```
nap=0  mang=3  loi=0  nguon=1  dom=0
```

`mang=3` là **NETWORK_NO_SOURCE**: phần tử âm thanh đã **bỏ cuộc**, không tìm được nguồn
phát — dù địa chỉ đã có (`nguon=1`) và không có lỗi nào (`loi=0`). Đây cùng một họ hỏng
với iPhone, vì Safari trên máy Mac cũng chạy WebKit.

Vì sao nó lọt ra ngoài suốt: hàm nhận dạng máy nhà Táo phải hỏi thêm **màn cảm ứng** để
phân biệt iPad đời mới với máy Mac — hai máy khai chuỗi nhận dạng giống hệt nhau. Máy Mac
để bàn không có màn cảm ứng, nên bị xếp vào nhóm Android và đi đúng con đường đã hỏng.

Nay có thêm `laSafari`, và cổng chung `laTao` gồm iPhone, iPad **và** Safari trên macOS.
Chrome trên Android cũng khai chuỗi "Safari" nên phải loại ra, nếu không Android lại bị
kéo sang nhầm đường.

### Hai nền tảng ngược nhau — và đây là chỗ chúng tách

Bản 0.26.31 cho mọi máy dựng lại khung để bật tiếng. Chủ máy thử trên Android và gửi ảnh:
khung dựng lại **không tự phát được**, Chrome đưa về nút play của YouTube kèm dòng "Chạm
vào video để phát có tiếng". Nên bản sửa ấy đúng cho máy nhà Táo nhưng sai cho Android.

Gộp hai phép đo lại thì ra bảng này, và từ đây thẻ đi theo đúng nó:

| Máy | Phần tử `<audio>` | Khung YouTube dựng lại có tiếng |
|---|---|---|
| Android (Chrome) | **chạy** — chủ máy xác nhận | không tự phát được, rơi về nút play |
| iPhone / iPad | không tải (`mang=2`) | **chạy** |
| Safari trên máy Mac | bỏ cuộc (`mang=3`) | **chạy** |

Nên nút "nghe trên máy này" lúc đang xem video kèm loa: máy nhà Táo giữ tiếng **trong
khung**, Android dùng **phần tử âm thanh**.

Đo lại trên ba chuỗi nhận dạng thật: Safari-Mac → đường khung; iPhone → đường khung;
Android → đường phần tử âm thanh, ở **cả hai** vị trí của công tắc tắt-màn-hình.

### Bỏ ràng buộc "phải bật nghe khi tắt màn hình mới nghe được trên máy"

> *"Phải bật nghe khi tắt màn hình kèm theo thì mới bật được nghe trên máy này."*

Đúng như vậy, và đó là lỗi của tôi: nhánh phần tử âm thanh trước đây chỉ mở khi công tắc
tắt-màn-hình đang bật. Hai thứ ấy không liên quan gì đến nhau. Nay nhánh nào chạy là do
**máy** quyết, không do công tắc.

### Bấm xem trong lúc công tắc tắt-màn-hình đang bật

Đây chính là đường đã đưa chủ máy vào cảnh trong ảnh chụp Safari: thẻ giao tiếng cho phần
tử âm thanh, phần tử ấy đứng ở `mang=3`, nên hình chạy mà không có tiếng và thẻ phải xin
một cú chạm. Nay trên máy nhà Táo, đường này **giữ tiếng trong khung** và bật dòng im lặng
giữ trang — tắt màn hình vẫn nghe tiếp.

Ở đây cố ý **không** gọi bước mở khoá phần tử âm thanh, dù nhánh xem thường có gọi: nó
phát một dòng im lặng qua phần tử ấy, mà Apple ghi rõ iOS chỉ cho **một** luồng chạy một
lúc — đúng thứ sẽ tranh chỗ với tiếng trong khung.

### "mất 4s đến 10s mới có tiếng"

Phần lớn quãng ấy là **một lượt hỏi máy chủ** xin địa chỉ luồng — đo trước đây là 1,5–2,6
giây — rồi mới tới lúc tải dữ liệu. Nay thẻ lấy sẵn địa chỉ luồng của **bài loa đang
phát**, nên lúc bấm không còn lượt hỏi nào. Mỗi bài chỉ hỏi máy chủ đúng một lần.

Và nhánh "nghe khi tắt màn hình" nạp **ngay** thay vì chờ nhịp đồng bộ kế tiếp — mỗi nhịp
là 2 giây chờ thêm vô ích.

## 0.26.31 - 2026-09-20

### Lỗi dừng video: thủ phạm là lệnh bật tiếng, không phải phần tử âm thanh

Chủ máy đưa một phép so sánh có đối chứng, và nó lật ngược giả thuyết tôi đang theo:

> *"tôi thấy khi nghe trên máy này mà đang phát ra loa bị dừng video, nhưng chọn cả nghe
> khi tắt màn hình thì không sao, tôi đang dùng android"*

Cùng một máy, cùng cảnh "loa + máy", chỉ khác một công tắc — và công tắc đó làm lỗi biến
mất. Hai nhánh ấy chỉ khác đúng một điều:

| Công tắc "nghe khi tắt màn hình" | Tiếng đi đường nào | Kết quả |
|---|---|---|
| Tắt | thẻ gửi lệnh `unMute` cho khung YouTube | **video dừng** |
| Bật | khung giữ nguyên câm, phần tử `<audio>` mang tiếng | bình thường |

Nên thủ phạm là **lệnh bật tiếng gửi qua `postMessage`**, chứ không phải phần tử âm
thanh như tôi đã ngờ suốt mấy bản trước.

Lý do: cú bấm của người dùng nằm ở trang **thẻ**, còn trình phát nằm trong khung
`youtube.com` — khác miền. Lệnh `unMute` đi qua `postMessage` nên **cử chỉ người dùng
không đi theo**. Với trình duyệt, đó là cảnh một video đang tự phát ở chế độ câm bỗng bật
tiếng mà không ai chạm vào nó, và cách nó xử là **tạm dừng video**. Luật này có ở cả
Chrome trên Android lẫn WebKit trên iPhone và macOS.

Thẻ `phicomm-r1-card` chủ máy đưa chạy được trên mọi máy vì nó **không bao giờ** làm động
tác câm-rồi-bật. Địa chỉ nhúng của nó (dòng 1896) không hề có tham số `mute`:

```js
const targetSrc = `https://www.youtube.com/embed/${videoId}?autoplay=1&enablejsapi=1&playsinline=1&rel=0`;
```

Khung sinh ra đã có tiếng sẵn, ngay trong cú bấm.

**Bản sửa, theo nguyên tắc chứ không theo danh sách:** mọi đường cần bật tiếng cho khung
giờ đi qua một cửa duy nhất, `_batTiengKhung`, và cửa ấy **dựng lại khung** bằng địa chỉ
không có `mute`, kèm `start` ở đúng giây đang xem — thay vì gửi lệnh. Bốn nơi cùng lớp
lỗi đã đổi: bật tiếng trên máy khi đang ra loa, bỏ tích loa cuối cùng, đổi bài trong cùng
trình phát, và bộ dò tiếng-bị-chặn.

Khung vốn đã có tiếng thì **không nạp lại** — nạp lại chỉ tổ mất toàn màn hình và mất mấy
giây. Đây là lý do đường đổi bài thường ngày vẫn nhanh như cũ.

Đo trên trình duyệt thật, đúng cảnh chủ máy báo:

| Cảnh | Lệnh gửi tới khung | `mute=1` còn không | `start` |
|---|---|---|---|
| Đang ra loa, bấm nghe trên máy (khung đang câm) | không còn `unMute` đơn độc | **mất** | **137** (đúng giây đang xem) |
| Khung vốn đã có tiếng | chỉ `playVideo` | giữ nguyên, không nạp lại | — |

Và phép đo đồng bộ hình cũ vẫn giữ nguyên kết quả đã kiểm ở 0.26.25: chỉ ra loa 0 cú tua,
loa + máy 0 cú tua, loa lành mạnh 2 cú tua.

### iPhone phải tự bấm biểu tượng loa mới nghe được

Cùng một gốc, một biểu hiện khác. Thẻ `phicomm-r1-card` gửi `unMute` + `setVolume` **bốn
lần**, ở mốc 0 / 300 / 800 / 2000 mili giây sau khi dựng khung (dòng 1904-1908). Thẻ của
tôi chỉ gửi **một lần**, sau 2,5 giây.

Lý do phải gửi nhiều lần: giao diện lập trình của trình phát YouTube chưa nhận lệnh ngay
lúc khung vừa nạp, nên gửi đúng một lần là rơi vào khoảng chưa ai nghe. Nay thẻ dùng
nguyên bậc thang ấy.

Chỗ này khác `_batTiengKhung` ở một điểm cần nói rõ: ở đây khung sinh ra vốn **không** có
tham số `mute`, nên đây không phải động tác câm-rồi-bật — ta chỉ đang gỡ cái câm mà chính
YouTube tự đặt để được phép tự phát trên điện thoại.

### Đang nghe trên máy mà tích loa thì loa nhận bài ngay

> *"tối ưu cả đang phát mà chọn loa thì phát được luôn âm thanh, không cần phải chuyển bài"*

Trước đây đường xử lý lúc tích loa chỉ lo ca **đang xem video**; ca **chỉ nghe** rơi ra
ngoài, nên tích loa xong không có gì xảy ra và chủ máy phải bấm lại bài mới ra tiếng.

Nay tích loa lúc đang nghe thì loa nhận bài **tiếp từ đúng giây đang nghe**, không phát
lại từ đầu. Loa Cast mất vài giây mới thật sự bắt đầu, nên cú tua **chờ** loa báo đang
phát rồi mới gửi, và chỉ gửi **một** lần — tua liên tiếp là sinh ra giật.

Nghe **ghép** theo loa (loa đã có bài rồi) thì không đụng vào.

### Chọn xong bài thì thu gọn danh sách tìm kiếm

> *"sau khi tìm kiếm mà chọn phát 1 bài xong thì ẩn phần danh sách tìm kiếm đi, sau đó
> muốn thay đổi bài thì kích vào"*

Danh sách thu về một thanh tóm tắt ghi tên bài vừa chọn và số kết quả; bấm vào là mở lại.
Tìm lượt mới thì danh sách tự mở ra, vì người vừa tìm là đang muốn nhìn nó.

Danh sách **không bị xoá** — nó vẫn là hàng chờ phát tiếp, chỉ thôi chiếm màn hình.

## 0.26.30 - 2026-09-20

### iOS "nghe khi tắt màn hình" — chép từ một bản cài ĐÃ CHẠY ĐƯỢC

Chủ máy đưa thẻ `phicomm-r1-card` kèm đúng một câu: *"dùng trên iPhone nghe nhạc, xem
video trên iPhone bình thường"*. Đọc mã của nó thì ra điều tôi tìm cả ngày, và nó đơn
giản đến mức khó chịu:

**Thẻ ấy không phát nhạc bằng thẻ `<audio>` bao giờ.**

Nhạc luôn nằm trong khung YouTube. Phần tử âm thanh chỉ để phát một dòng **im lặng lặp
vô hạn**, giữ cho iOS coi trang là đang có tiếng nên không cắt khi tắt màn hình. Thẻ của
tôi thì làm ngược: cố đẩy luồng nhạc thật qua `<audio>` — đúng thứ iOS từ chối, và là
gốc của mọi lần hỏng suốt hôm nay.

Nay đường "nghe khi tắt màn hình" trên iOS **giữ tiếng trong khung**, kèm hai thứ chép
nguyên từ bản chạy được:

- **Dòng im lặng**: dao động 20 Hz, âm lượng 0,0001 — vô thanh trên thực tế nhưng là
  tiếng **thật**, nên iOS không coi là im lặng giả. Lùi về tệp WAV im lặng nếu máy không
  có Web Audio. `loop` để dòng không bao giờ kết thúc; `playsinline` **và**
  `webkit-playsinline` vì Safari đời cũ chỉ hiểu tên thứ hai; nằm trong trang ở kích
  thước 1×1 điểm ảnh, mờ 0,01 — **không** dùng `display:none`, vì WebKit bỏ qua phần tử
  media bị ẩn hẳn.
- **Wake Lock**, nếu máy có.

### Lần đầu đo được trên WebKit thật

Cũng hôm nay dựng được chỗ đo: chạy **engine WebKit thật** (cùng lõi Safari) trong một
container dùng một lần, không đụng gì tới máy chủ. Hai kết quả đáng giá:

Một, mô hình cũ của thẻ — phần tử sống lâu, mở khoá bằng im lặng, đổi `src` — **chạy tốt
trên WebKit máy bàn**: `nap=4`, không lỗi, đồng hồ tiến 1 → 4 → 9 giây đúng nhịp. Tức nó
không hỏng vì WebKit nói chung, mà vì luật riêng của iOS.

Hai, dòng im lặng mới **chạy liên tục**: đồng hồ tiến 2,51 giây trong 2,5 giây thực.

Nói rõ giới hạn: đây là WebKit trên Linux, không phải Safari trên máy Mac hay iPhone.
Nó loại bỏ được một lớp giả thuyết, không thay được phép thử trên máy thật của chủ máy.

## 0.26.29 - 2026-09-20

### Changed — bấm nghe bài PHÁT TRỰC TIẾP thì mở hình, không bỏ qua nữa

Chủ máy: *"thì sẽ không phải bỏ qua"*. Đúng. Bản 0.26.28 nhận ra bài trực tiếp rồi báo
một câu và đứng im — biết lỗi thì tốt hơn mã lỗi thô, nhưng nhạc vẫn không chạy.

Đo thêm trên bản kê luồng của bài trực tiếp thật:

```
Content-Type thật : application/vnd.apple.mpegurl
bản kê chứa       : địa chỉ TUYỆT ĐỐI tới googlevideo.com
```

Hai điều rút ra. Một: **loa không vướng gì** — bản kê dùng địa chỉ tuyệt đối nên loa
Cast tự đi lấy từng đoạn, đường ra loa vẫn đi như cũ. Hai: chỉ thẻ `<audio>` của Chrome
là không phát được HLS, còn **khung YouTube thì phát tốt**.

Nên nay bấm nghe một bài trực tiếp sẽ **mở hình lên** kèm lời giải thích, thay vì đứng
im. Có tiếng ngay, chỉ là kèm hình.

Đo lại sau khi sửa, cả bốn thao tác:

```
nghe bài thường      → phát luồng bình thường
nghe bài trực tiếp   → mở hình, không đặt nguồn, không lỗi
next sang trực tiếp  → không đặt nguồn, không lỗi
xem bài trực tiếp    → mở hình bình thường
```

### Fixed — máy chủ khai sai kiểu nội dung cho bài trực tiếp

Bảng tra kiểu không có đuôi `m3u8` nên nó rơi về mặc định `audio/mp4` — một lời khai
sai khiến bên nhận tưởng phát được rồi mới hỏng. Nay khai đúng
`application/vnd.apple.mpegurl`.

Sửa ở **cả hai bản song song** (add-on và c2a) và đã đối chiếu khớp từng dòng.

## 0.26.28 - 2026-09-20

### Fixed — bấm sang bài PHÁT TRỰC TIẾP thì báo "NotSupportedError"

Chủ máy: *"khi next bị lỗi này"*, kèm ảnh dòng đỏ **"Máy này không phát được tiếng bài
này (NotSupportedError)"**, rồi chỉ đúng chỗ: *"hình như YouTube trực tiếp bị lỗi, next
qua bài đó không sao"*.

Đo trên c2a, đúng bài trong ảnh — "Bolero Trữ Tình Hay Nhất Không Quảng Cáo" của Ngọc
Diệu Bolero:

```
thời lượng        = None                       ← dấu hiệu bài trực tiếp
luồng giải ra     = …/playlist/index.m3u8      ← bản kê HLS, không phải file nhạc
máy chủ khai báo  = audio/mp4                  ← KHAI SAI kiểu
```

Bài phát trực tiếp không có file nhạc cố định, chỉ có một bản kê luồng HLS. Thẻ
`<audio>` của Chrome **không phát được** định dạng đó (chỉ Safari làm được), nên nó trả
đúng `NotSupportedError` — nhưng người dùng chỉ thấy một mã lỗi kỹ thuật vô nghĩa.

Nay thẻ nhận ra bài trực tiếp và nói thẳng: *"đang phát trực tiếp nên không nghe riêng
tiếng được — bấm nút xem để nghe"*. Xem video thì vẫn chạy bình thường, vì khung YouTube
tự lo được HLS.

Nhận dạng bằng **thời lượng**, không phải đuôi địa chỉ: lúc bấm nghe thì chưa có địa chỉ
nào cả, mà bài trực tiếp thì không có thời lượng — đó là thứ biết được ngay. Và bài trực
tiếp cũng không còn bị lấy sẵn địa chỉ, đỡ một lượt hỏi máy chủ không bao giờ dùng tới.

Đo lại sau khi sửa, bấm next sang bài trực tiếp: **không đặt nguồn, không gọi phát** —
nên không còn dòng lỗi nào.

### Còn một chỗ máy chủ khai sai, chưa sửa

Máy chủ trả `media_content_type: audio/mp4` cho một địa chỉ `.m3u8`. Hiện không ai dùng
trường đó nên chưa gây hại, và thẻ nhận dạng bằng thời lượng chứ không dựa vào nó. Nhưng
đó là một lời khai sai nằm sẵn chờ người sau tin nhầm — ghi lại để sửa khi đụng tới
đường giải luồng.

## 0.26.27 - 2026-09-20

### Fixed — máy Android mà hiện lời nhắn nói về iPhone

Chủ máy gửi ảnh điện thoại Android đang hiện dòng đỏ:

> *"iPhone không cho vừa xem video vừa nghe khi tắt màn hình. Đang ưu tiên xem — chạm
> vào video để nghe…"*

Đây là chỗ tách nền tảng còn sót sau 0.26.22. Giới hạn "một luồng một lúc" là của iOS;
trên Android mà nhánh này nổ thì **nguyên nhân khác hẳn**, nên nói câu của iOS vừa sai
vừa đẩy người đọc đi tìm nhầm chỗ.

Nay lời nhắn chia theo máy đang cầm. Và bản Android **mang theo số đo** —
`nap`, `mang`, `loi`, `nguon`, `dom` — để nếu nó còn hiện thì lần sau biết ngay vì sao,
thay vì lại đoán.

Đã soát toàn bộ file: đây là chuỗi người dùng thấy **duy nhất** còn nhắc tên iPhone;
mọi chỗ khác chỉ là chú thích trong mã.

## 0.26.26 - 2026-09-20

### Fixed — iPhone: video mặc định câm, phải tự bấm nút loa mới nghe

Chủ máy gửi ảnh trình phát YouTube trên iPhone: bài đang chạy nhưng **câm**, phải chạm
nút tắt/bật tiếng của chính trình phát mới có tiếng.

Đây không phải YouTube làm, mà là thẻ tự tắt. Khi xem một mình (không chọn loa), thẻ
thấy khung nhúng chưa phát được tiếng thì **tắt tiếng khung** và giao việc phát cho
phần tử âm thanh của chính nó. Cách ấy đúng trên máy bàn và Android. Trên iOS thì
không: phần tử âm thanh ở đó **đo được là không bao giờ tải** — `nap=0 mang=2 loi=0`,
thu được hai lần độc lập. Thế là khung bị câm, phần tử im, và người dùng không nghe gì
cho tới khi tự mò ra nút loa.

Nay trên iOS tiếng **nằm nguyên trong khung**: thẻ xin phát lại rồi hiện lời nhắc chạm
vào video — đúng thao tác mà chủ máy đang phải tự nghĩ ra. Đó cũng là đường duy nhất đo
được là chạy trên iOS, vì WebKit chỉ chịu phát tiếng sau một cú chạm thật.

Giả lập trên chính mã của thẻ, chạy hai lần với hai user-agent khác nhau:

```
iPhone  : cướp tiếng = false | lệnh gửi: unMute, playVideo | soundHere = true
máy bàn : cướp tiếng = true  | lệnh gửi: (không có)        | soundHere = false
```

Tức iOS đổi, còn mọi nền tảng khác giữ nguyên hành vi cũ.

### Chưa đụng tới

Đường **"nghe khi tắt màn hình"** vẫn giao tiếng cho phần tử âm thanh, kể cả trên iOS.
Đó là lựa chọn có chủ ý của người dùng và là thứ duy nhất về lý thuyết sống sót qua lúc
tắt màn — nhưng trên iOS nó vẫn chưa chạy. Việc đó tách riêng, chưa gộp vào bản này.

## 0.26.25 - 2026-09-20

### Fixed — "ra loa thì bình thường, nghe cả hai nơi thì lỗi video"

Chủ máy tả đúng cấu hình: điện thoại Android, mở nhạc trên Home Assistant ra loa, thẻ
nối vào c2a. Và thêm một câu quyết định: *"trước kia bản .19 không sao"*.

Đo trên loa thật trong nhà, lấy mẫu cách nhau 25 giây:

```
googlehome5802:  playing | media_position = 0 → 0 | mốc thời gian KHÔNG đổi
                 bài dài 10684 giây
```

Loa không báo lại vị trí bao giờ. Mà thẻ tính giây của loa bằng `media_position` **cộng
thời gian trôi kể từ mốc**, nên khi mốc đã cũ 90 giây thì con số suy ra là 90 — trong
khi sự thật không ai biết.

Giả lập trên chính mã của thẻ, nạp đúng số đo ấy:

```
A) Chỉ ra loa (hình câm)   : seekTo 91.2 , seekTo 97.2   → 2 cú tua / 8,4 giây
B) Ra loa + nghe trên máy  : unMute, seekTo 99.6 , seekTo 105.6
```

Hình đang ở giây 1–8 thì bị **quăng tới giây 91**, rồi lặp mỗi ~5 giây.

Điều này giải thích luôn vì sao chủ máy thấy "ra loa thì bình thường": **cú tua xảy ra ở
cả hai trường hợp**, nhưng khi hình còn câm và tai đang nghe loa thì không ai để ý. Bật
tiếng trên máy lên là nghe rõ từng cú nhảy.

Nay chốt lại: số **ngoại suy** thì không được tua hình. Đo lại sau khi sửa:

```
A) 0 cú tua     B) 0 cú tua, vẫn unMute cho máy     C) loa khoẻ: 2 cú tua
```

Ca C là hàng rào ngược: loa nào Home Assistant làm mới vị trí đàng hoàng thì vẫn đồng bộ
được như cũ.

### Tôi đã gỡ đúng cái chốt này ở bản trước, và đó là quyết định sai

Chốt này có ở 0.26.22, và tôi gỡ hẳn ở 0.26.24 vì lúc ấy **không chứng minh được** nó
cần thiết — phép giả lập khi đó chỉ đếm số lần *cửa mở*, không phải số lần thật sự tua.
Nay đo đúng thứ cần đo thì thấy nó cần thật.

Khác biệt so với 0.26.22: chốt **chỉ** áp cho vòng kéo hình. Vòng kéo tiếng vẫn để
nguyên, vì đó là thứ duy nhất giữ tiếng trên máy đi cùng loa — chốt cả hai thì mất đồng
bộ (lỗi của .22), gỡ cả hai thì hình bị quăng (lỗi của .24).

## 0.26.24 - 2026-09-20

### Gỡ HẲN cái chốt của bản 0.26.22 — nó dựng trên một chẩn đoán đã bị rút lại

Chủ máy: *"vẫn lỗi khi nghe cả 2 nơi, tôi yêu cầu kiểm tra thật kỹ"*. Kiểm kỹ thì ra
chuỗi nhân quả, và nó dẫn ngược về chính tay tôi.

Khi đang mở video **và** có loa, bấm "Nghe trên máy này" **không** vào chế độ nghe-kèm.
Nó **bỏ tắt tiếng khung YouTube** — nghĩa là máy phát luồng của YouTube còn loa phát
luồng qua máy chủ, **hai nguồn khác nhau**. Thứ duy nhất giữ chúng cùng nhịp là vòng
kéo hình theo loa. Bản 0.26.22 chặn đúng vòng ấy, và 0.26.23 vẫn còn chặn — nên chế độ
nghe-cả-hai-nơi mất luôn cơ chế giữ nhịp duy nhất của nó.

Cái chốt ấy đáng ra không nên tồn tại. Nó dựng trên kết luận rằng vòng đồng bộ gây ra
cái giật — mà chính tôi đã rút lại ở 0.26.23, vì phép giả lập chỉ đếm số lần **cửa mở**
chứ không phải số lần thật sự tua. Một thay đổi dựa trên chẩn đoán đã rút lại, lại gây
hỏng hai lần, thì gỡ hẳn chứ không giữ một nửa.

### Nói thẳng giới hạn: nghe cùng lúc trên loa và trên máy thì KHÔNG khớp tuyệt đối

Đây không phải lỗi sửa được bằng một bản vá, nên nói rõ để khỏi chờ.

Loa và điện thoại là hai bộ giải mã độc lập, nhận hai luồng khác nhau, khởi động lệch
nhau, và đường mạng tới mỗi bên cũng khác. Thẻ chỉ có thể **kéo chúng lại gần** khi
lệch quá ngưỡng, chứ không thể khoá chúng vào cùng một nhịp. Tai người nghe ra tiếng
vọng khi lệch chỉ vài phần trăm giây — dưới ngưỡng mà bất kỳ cơ chế nào ở đây với tới
được.

Muốn nghe hai nơi mà không vọng thì cách thật sự là **cho cả hai cùng phát từ một
nguồn có đồng hồ chung**, việc của hệ thống multiroom chứ không phải của thẻ này.

### Còn mở: cái giật của hình

Vẫn chưa tìm ra. Điều đã biết chắc là loa Google Home trong nhà báo vị trí đúng một lần
rồi đứng im, nên giây mà thẻ đọc được là phép cộng thời gian trôi. Điều **chưa** biết là
nó có thật sự làm hình giật hay không — tôi chưa đo được số lần tua thật, và lần trước
đã trình bày một phép đo như thể nó chứng minh nhiều hơn thực tế.

## 0.26.23 - 2026-09-20

### Fixed — lỗi do CHÍNH bản 0.26.22 gây ra: loa và máy không còn đồng bộ

Chủ máy: *"tiếng loa và thiết bị không đồng bộ nhỉ, cái trước cái sau"*.

Bản 0.26.22 chặn **cả hai** vòng đồng bộ khi giây của loa không phải số đo tươi. Vòng
kéo tiếng chính là thứ **duy nhất** giữ tiếng trên máy đi cùng loa — chặn nó đi thì hai
bên trôi khỏi nhau, và chế độ vừa-loa-vừa-máy mất luôn lý do tồn tại.

Nay chốt ấy chỉ còn áp cho vòng kéo **hình**. Hai bên trả giá khác hẳn nhau: tua khung
YouTube là một cú nạp lại thấy được bằng mắt, nên thà để hình trôi còn hơn giật; còn
đặt lại giây của phần tử âm thanh thì rẻ, và đó là cái người dùng thật sự cần.

### Đính chính một kết luận tôi đã nói quá chắc

Ở 0.26.22 tôi trình bày phép giả lập như bằng chứng rằng vòng đồng bộ gây ra cái giật.
**Nó không chứng minh được điều đó.** Phép ấy đếm số lần *cửa mở*, không phải số lần
thật sự tua — mà cửa mở 11/12 nhịp là chuyện bình thường của một vòng đồng bộ lành
mạnh. Cú tua chỉ xảy ra khi lệch quá ngưỡng, và tôi chưa đo cái đó.

Phần vẫn đúng và vẫn giữ: loa Google Home trong nhà báo `media_position = 3.300666` rồi
đứng im vĩnh viễn, nên con số thẻ bám vào là phép cộng thời gian trôi. Nhưng con số ấy
neo vào đúng lúc Home Assistant báo lần cuối, nên với một loa phát liên tục thì nó vẫn
bám sát sự thật — đủ tốt để canh tiếng, chỉ không đủ chắc để giật hình.

## 0.26.22 - 2026-09-20

### Fixed — vừa loa vừa máy: hình giật và mất tiếng. MỘT gốc, hai triệu chứng

Chủ máy: *"video vẫn bị giật giật và không nghe thấy tiếng trên thiết bị khi vừa loa
vừa thiết bị"*. Lần này có số đo từ chính loa trong nhà, chứ không phải suy luận.

Đo trên loa **đang phát thật**, lấy mẫu mỗi 1,2 giây:

```
googlehome5802:  media_position = 3.300666  (KHÔNG bao giờ đổi)
                 giây thẻ suy ra = 127 → 128 → 129 → … → 138
```

Loa báo vị trí đúng **một lần** rồi thôi. Thứ duy nhất chuyển động là phép ngoại suy
của thẻ: nó lấy con số cũ rồi cộng thêm thời gian đã trôi. Nghĩa là "đồng hồ loa" mà
thẻ đang bám vào là **suy đoán từ một mẫu cũ, không phải số đo** — và vì nó tiến đều
1:1 nên hàng rào thêm ở 0.26.16 không hề bắt được.

Hậu quả đúng hai điều chủ máy thấy, từ cùng một gốc:

- **Hình giật**: vòng đồng bộ kéo video về con số bịa ra mỗi khi lệch quá ngưỡng. Nó
  không bao giờ tự hiệu chỉnh nên cứ lệch lại — mỗi lần là một cú tua thật, thấy giật.
- **Mất tiếng trên máy**: vòng kia đặt thẳng `currentTime` của phần tử âm thanh về
  chính con số ấy, cứ 4 giây một lần. Tiếng bị quăng đi quăng lại nên nghe như không có.

**Nguyên tắc sửa**: số *suy ra* thì được phép vẽ thanh tiến trình, nhưng **không được
phép dịch chuyển một bộ phát khác**. Muốn kéo ai thì phải có số đo còn tươi (trong
vòng 10 giây). Loa nào Home Assistant không làm mới thì hình cứ chạy êm theo nhịp của
chính nó — lệch một chút còn hơn giật liên tục.

### Tự dựng lại để kiểm, không bắt chủ máy thử

Chủ máy: *"bạn tự giả lập xem nào"*. Đúng. Giả lập chạy trên **chính mã của thẻ**, nạp
đúng số đo ở trên:

```
1) Loa kẹt, CHƯA có chốt (trước bản sửa):  12 nhịp → cho kéo 11
2) Loa kẹt, CÓ chốt      (sau bản sửa)  :  12 nhịp → cho kéo  0
3) Loa khoẻ, CÓ chốt                     :  12 nhịp → cho kéo 11
```

Phép 1 dựng lại được đúng lỗi, phép 2 cho thấy chốt chặn được, phép 3 cho thấy ca lành
mạnh không bị chặn nhầm. Giây suy ra của loa kẹt là **135,7** trong khi loa khoẻ là
**11,7** — chênh lệch ấy chính là quãng mà hình và tiếng bị kéo về sai.

### Tách iOS khỏi Android

Chủ máy: *"xem tách riêng iP và Android ra"*. Đúng, vì hai nền tảng hỏng khác nhau, và
đã có lần một bản vá cho iOS làm hỏng luôn Android.

Nay có một cổng nhận dạng nền tảng, và chỗ đầu tiên đi qua nó là bộ canh tiếng: hai hẹn
giờ trong đó (nhắc lại lệnh phát sau 3 giây, báo chẩn đoán sau 12 giây) đều dựng lên từ
hành vi của WebKit. Trên Android chúng chỉ có thể gây hại — cú nhắc lại có thể chen vào
một luồng đang tải bình thường, còn lời nhắn 12 giây thì báo hỏng oan. Từ nay Android
chạy đúng đường 0.26.2, không dính một dòng vá iOS nào.

(iPad đời mới khai user-agent giống máy Mac, nên cổng này hỏi thêm màn cảm ứng — Mac
thật không có.)

## 0.26.21 - 2026-09-20

### Trả đường tiếng về đúng bản 0.26.2 — bản mà chủ máy đo là chạy được

Chủ máy: *"YouTube vẫn chưa nghe được, xem lại code của mấy bản trước khi sửa cho iOS
ấy, vẫn bình thường"*. Đúng, và đây là việc nên làm từ mấy bản trước.

Loạt bản 0.26.13–0.26.20 xây một mô hình phát mới để chữa iOS. Kết quả đo trên máy
thật: **iOS vẫn không nghe được, và Android — vốn đang tốt — cũng hỏng theo.** Đã thử
chữa mô hình ấy ba lần (0.26.18, .19, .20) mà vẫn hỏng. Theo đúng quy ước của chính dự
án này — *sai một chỗ hai lần thì đừng sửa lần thứ ba* — bản này không chữa tiếp mà
**trả nguyên trạng** phần phát tiếng về bản 0.26.2.

Cụ thể, quay lại đúng mô hình cũ: **một** phần tử âm thanh sống lâu, mở khoá bằng đoạn
im lặng **ngay trong cú chạm**, rồi đổi `src` khi có địa chỉ. Gỡ sạch mô hình mới —
phần tử-mới-mỗi-bài, `<source type>`, `autoplay`, bộ nút gốc, cờ "đã chạy", và việc gỡ
phần tử khỏi trang khi dừng. Có `assertNotIn` ghim để không ai dựng lại nửa vời.

### Vì sao giả thuyết của tôi sai, và đo thế nào mới biết

Tôi từng nghi thẻ `<source type="audio/mp4">` làm trình duyệt bỏ qua nguồn. **Đo thì
sai**: máy chủ trả đúng `audio/mp4`, một kiểu MIME hợp lệ.

Rồi dựng cả ba kiểu phần tử chạy **song song** trên đúng luồng thật qua Home Assistant:

```
1) MOI: <source src type=audio/mp4>   nap=4  loi=0  dai=213
2) MOI, khong dat type                nap=4  loi=0  dai=213
3) CU: audio.src = url  (0.26.2)      nap=4  loi=0  dai=213
```

Cả ba nạp luồng **y hệt nhau**: dữ liệu đủ, không lỗi, biết đúng thời lượng. Tức hình
dạng phần tử không phải thủ phạm — và cũng không có phép đo nào của tôi chứng minh được
mô hình mới tốt hơn. Nó chỉ dựa trên tài liệu, còn máy thật thì nói ngược lại. Máy thật
thắng.

### Giữ lại đúng một thứ: lấy sẵn địa chỉ luồng

Thứ duy nhất của đợt làm lại còn giữ, vì nó **không đụng một dòng nào** vào đường phát:
lớp nhớ địa chỉ luồng nằm bên trong hàm hỏi máy chủ. Ba bài đầu của danh sách và bài kế
tiếp được lấy sẵn, nên bấm bài là vào ngay thay vì chờ 1,5–2,6 giây. Lợi cho cả Android
lẫn iOS, và nếu có hỏng thì hỏng về đúng hành vi cũ chứ không thành thứ khác.

### Còn lại gì chưa xong

**iOS vẫn chưa nghe được.** Bản này không hứa chữa được — nó chỉ đưa mọi thứ về đúng
chỗ đã biết là chạy được trên Android, để không mất thêm nền tảng nào nữa. Việc iOS
quay lại từ đầu, và lần sau sẽ chỉ đổi khi có phép đo trên máy thật chứng minh, chứ
không đổi vì tài liệu nói vậy.

**Lỗi 153 của add-on trên iPhone** là chuyện khác: giao diện add-on đã có sẵn
`referrerpolicy` (có test ghim), nên đó là YouTube từ chối nhúng khi trang mở bằng địa
chỉ IP. Thẻ đã có đường lui cho ca này (lấy hình từ máy chủ), giao diện add-on thì chưa.

## 0.26.20 - 2026-09-20

### Fixed — lỗi do CHÍNH bản 0.26.19 gây ra: bấm "Nghe trên máy này" thì dừng video

Chủ máy: *"kích nghe trên máy này bị lỗi, không nghe thấy và dừng video"*. Đây là lỗi
tôi làm ra ở bản trước, không phải lỗi cũ.

Vòng đồng bộ có một dòng gương trạng thái tạm dừng của tiếng sang khung YouTube:

```js
if (audio.paused && [1, 3].includes(video.state)) this._videoCommand("pauseVideo");
```

Trước 0.26.19, lúc bấm nút thì đoạn im lặng mở khoá **đã chạy sẵn từ trước**, nên
`paused` là `false` và dòng này không đụng tới video. Bản 0.26.19 bỏ đoạn im lặng và
dựng phần tử mới — mà phần tử vừa dựng thì **luôn đang tạm dừng** trong khoảnh khắc chờ
khởi động. Thế là vừa bấm "Nghe trên máy này" là thẻ lập tức ra lệnh **dừng đúng cái
video đang xem**, trong khi tiếng cũng chưa kịp vào. Đúng hai triệu chứng.

Nay chỉ gương trạng thái dừng **sau khi tiếng đã từng chạy ít nhất một lần**. Phần tử
chưa chạy lần nào thì "đang tạm dừng" không có nghĩa là người dùng muốn dừng.

### Fixed — và một lỗ im lặng nữa lộ ra khi đo

Đo trong Chrome để kiểm tiền đề của chẩn đoán trên, và số đo lòi thêm chuyện khác:

```
ngay sau khi dựng  : paused = true
ngay sau khi vào trang : paused = true
sau 400ms          : paused = true, readyState = 4
```

`readyState = 4` nghĩa là dữ liệu đã đủ, vậy mà vẫn chưa chạy — tức **chỉ mỗi thuộc
tính `autoplay` không đủ để khởi động**. Mà bản 0.26.19 lại nuốt im lặng mọi lỗi của
`play()` (điều kiện `if (!audio.autoplay)` không bao giờ đúng). Hậu quả ở đường nhanh,
vốn cố ý không hiện bộ nút gốc: **không tiếng, không lỗi, không có gì để bấm**.

Nay bị từ chối thì bật luôn bộ nút gốc của chính phần tử và nói rõ phải làm gì. Một cú
chạm vào nút phát của phần tử là cử chỉ không trình duyệt nào từ chối — đúng lối thoát
mà trình duyệt Media của Home Assistant dùng.

### Đổi thêm — lấy sẵn địa chỉ cho CẢ bài video

Bản trước lọc bài video ra khỏi danh sách lấy sẵn, nghĩ rằng chúng sẽ được xem chứ
không nghe. Sai: bài video vẫn có nút "Nghe trên máy này", và đó đúng là đường hay phải
chờ nhất, vì người ta đang xem rồi mới chuyển sang nghe. Nay lấy sẵn cả ba bài đầu,
không lọc.

## 0.26.19 - 2026-09-20

### Fixed — gỡ HẲN mô hình cũ, và sao đúng hình dạng của Home Assistant

Bản 0.26.18 dựng mô hình mới nhưng **để sót mô hình cũ nằm lại**. Đọc kỹ mã thật của
Home Assistant (`hui-dialog-web-browser-play-media.ts`) thì thấy hai chỗ chưa khớp, và
một chỗ còn **có hại**.

**Sao đúng hình dạng.** HA viết:

```html
<audio controls autoplay>
  <source src=${sourceUrl} type=${sourceType} />
</audio>
```

Địa chỉ nằm trong `<source>` **kèm `type`**, chứ không gắn thẳng lên phần tử. `type` là
gợi ý thật cho WebKit — có nó thì trình duyệt biết ngay có phát được không, khỏi tự đánh
hơi byte đầu. Máy phát vốn đã trả `media_content_type` nên không tốn thêm lượt hỏi nào;
số đo trên máy chủ cho thấy đó là `audio/mp4`.

**Chỗ có hại.** Lúc mở video YouTube, thẻ vẫn gọi cú "mở khoá" cũ — tức dựng một phần tử
tiếng **ngay trước khi khung video mở**. Apple giới hạn iOS ở đúng một luồng tại một
thời điểm, nên đó là tự tay giành chỗ của chính cái video vừa bấm. Đã bỏ.

**Dọn hết phần còn lại**: đoạn im lặng mở khoá, hàm `unlock()`, hàm dựng phần tử cũ, và
số đo `mo_khoa=…`. Số đo ấy đã làm xong việc của nó — chính `mo_khoa=ok` đi kèm `nap=0`
là bằng chứng bác bỏ mô hình cũ; mô hình chết thì số đo của nó cũng bỏ, chứ không giữ
lại một con số không còn đo điều gì. Có `assertNotIn` ghim để không ai vô tình dựng lại.

**Dừng là gỡ hẳn.** Trước đây dừng nhạc chỉ bỏ địa chỉ rồi để phần tử nằm lại trong
trang — mà còn nằm lại là còn giữ chỗ phát duy nhất của iOS, khiến bài sau phải xếp hàng
sau một thứ đã im từ lâu. Nay: dừng, bỏ nguồn, `load()` cho WebKit thật sự buông, rồi
gỡ khỏi trang.

### Android có đổi gì không

Không xấu đi, và có lợi một phần. Android/Chrome chưa bao giờ vướng luật một-luồng hay
luật cử chỉ, nên phần đó với nó là vô hại. Cái nó được hưởng là **lấy sẵn địa chỉ
luồng**: bấm một bài trong ba bài đầu, hoặc chuyển sang bài kế tiếp, thì không còn phải
chờ 1,5–2,6 giây hỏi máy chủ nữa — nhạc vào gần như tức thì.

### Kiểm chứng

Bộ test của thẻ 15/15 đạt, và thẻ được **nạp thật trong trình duyệt** để chắc bản dọn
không làm vỡ gì: đăng ký thành phần thành công, các hàm đều còn, **không một lỗi nào lúc
nạp**. Vẫn chưa thử trên iPhone thật — không có máy iOS ở đây.

## 0.26.18 - 2026-09-20

### Fixed — iOS: bỏ hẳn mô hình cũ, làm y như trình duyệt Media của Home Assistant

Chủ máy: *"không có tiếng gì luôn. Tìm kiếm thêm thông tin cộng đồng chia sẻ để làm cho
đúng đi, không đoán mò nữa"*. Đúng. Bốn giả thuyết trước đều là suy đoán, và đây là câu
trả lời có nguồn.

**Tài liệu của Apple nói thẳng:**

> *"On iOS, preload and autoplay are disabled. **No data is loaded until the user
> initiates it.** The JavaScript `play()` and `load()` methods are inactive until the
> user initiates playback, unless triggered by user action."*

> *"Currently, all devices running iOS are limited to playback of a **single** audio or
> video stream at any time."*

Câu đầu mô tả **chính xác** bộ số chụp được hai lần: `nap=0 mang=2 loi=0 nguon=1 dom=1`
— phần tử có nguồn, nằm trong trang, tự nhận đang tải, không lỗi, và không một byte nào
về. Không phải hỏng: là iOS đang làm đúng điều Apple viết.

Và `mo_khoa=ok` **không hề mâu thuẫn**. Cú mở khoá thành công trên một nguồn khác — đoạn
im lặng. Ngay sau đó thẻ đổi `src` sang địa chỉ thật, và **cú tải mới ấy không còn nằm
trong cú chạm nữa**. Toàn bộ mô hình "mở khoá một lần rồi đổi nguồn" mà các bản
0.26.13–0.26.15 xây lên chính là thứ Apple nói là không chạy.

**Trình duyệt Media của chính Home Assistant chạy được trên iPhone, và nó làm ngược
lại.** Đọc `hui-dialog-web-browser-play-media.ts`: địa chỉ được giải xong **trước**, rồi
mới dựng một phần tử **hoàn toàn mới mang sẵn địa chỉ**; nó **không gọi `play()` bằng
JavaScript** mà để thuộc tính `autoplay` lo; và nó luôn có `controls` làm lối thoát —
chạm vào nút phát của chính phần tử là cử chỉ không thể thật hơn.

Nay thẻ làm đúng ba điều đó:

- **Phần tử mới cho mỗi bài**, `src` gắn từ lúc sinh ra, không bao giờ đổi `src` của một
  phần tử đang sống.
- **`autoplay` + `playsinline`**, và khi phải hỏi máy chủ trước thì hiện luôn **bộ nút
  gốc** để người dùng có đường chạm thật.
- **Lấy sẵn địa chỉ luồng trước cú chạm** — ba bài đầu của danh sách, và bài kế tiếp mỗi
  khi một bài bắt đầu. Có sẵn thì `listen()` chạy thẳng, **không một `await` nào chen
  vào**, nên cả việc dựng lẫn việc tải đều nằm trong cử chỉ người dùng. Đây là điều kiện
  bắt buộc, không phải tối ưu tốc độ.
- **Một luồng một lúc**: phần tử cũ bị gỡ hẳn khỏi trang chứ không chỉ tạm dừng, vì còn
  trong trang là còn giữ chỗ.

Cách này giải thích luôn mọi báo cáo cũ mà không cần thêm giả thuyết nào: *"lượn qua app
khác rồi quay lại thì lại phát"* (đổi app buộc WebKit xét lại chỗ ngồi), *"khi phát rồi
thì khoá màn vẫn phát được"* (giữ được chỗ thì giữ luôn), *"chuyển bài khác là lại tịt"*
(đổi bài là một lượt tải mới, ngoài cử chỉ — nay đã lấy sẵn bài kế tiếp).

### Máy chủ đã được minh oan bằng số đo, không phải bằng lập luận

Đo trên Home Assistant thật (`172.16.10.200`), qua đúng đường ký mà thẻ dùng, **không
gửi header xác thực** — vì thẻ `<audio>` không bao giờ gửi — và giả làm iPhone Safari:

```
Range: bytes=0-1  →  206 | Content-Range: bytes 0-1/3449447 | Content-Length: 2
không Range       →  200 | Content-Length: 3449447
Accept-Ranges: bytes | Content-Type: audio/mp4
```

Safari đòi máy chủ phải trả 206 cho cú hỏi hai byte đầu; máy chủ trả đúng, ở cả nguồn
gốc lẫn lớp trung chuyển của tích hợp. Giả thuyết byte-range chết hẳn.

### Chưa kiểm được

Nói thẳng: **chưa thử trên iPhone thật** — không có máy iOS ở đây. Kiểm được là bộ test
của thẻ và các số đo máy chủ ở trên. Phần bản sửa dựa vào là tài liệu Apple và mã nguồn
của Home Assistant, không phải suy đoán; nhưng chỉ máy của chủ máy mới xác nhận được.

## 0.26.17 - 2026-09-20

### Fixed — ĐÂY mới là ca iOS: "có đổi" không phải là "có tiến"

Chủ máy: *"tôi đang nói iOS, chứ Android lại bình thường"*. Nói thẳng trước: bản
0.26.16 vừa rồi **không chạm tới ca này** — nó vá hai đường bám loa, mà ca của chủ máy
không có loa nào cả. Cùng một triệu chứng, khác đường đi.

Đường của chủ máy là: mở video YouTube trên iPhone, không chọn loa. iOS không cho khung
nhúng tự phát có tiếng, nên thẻ chuyển sang **tự phát tiếng bằng phần tử âm thanh của
chính nó**, còn hình chạy câm và bám theo tiếng ấy.

Hàng rào ở đường này có từ 19/09, nhưng nó hỏi sai câu. Nó hỏi *"giây có KHÁC nhịp
trước không"*. Trên iPhone, WebKit cắt luồng rồi cho chạy lại từ đầu, nên giây bò
`0 → 0,2 → 0 → 0,3 → 0…` — **đổi liên tục mà chẳng đi tới đâu**. Câu hỏi đúng phải là
*"có TIẾN không"*.

Đây cũng là lý do Android không sao: bộ phát của nó không cắt luồng kiểu ấy, nên giây
tiến đều và hàng rào cũ vô tình vẫn đúng. Một lỗi chỉ hiện ở một phía không có nghĩa là
lỗi nằm ở phía ấy — nó nằm ở phép thử quá lỏng, chỉ là phía kia không chạm tới.

### Và chỗ suýt sửa hụt: sai ở ĐỘ DÀI QUÃNG SO, không phải ở con số ngưỡng

Bản đầu của hàm mới vẫn để lọt. Số đo trên đúng chuỗi giây mà iPhone sinh ra:

```
hàng rào CŨ  -> cho kéo 6/6 lần      <- đúng lỗi chủ máy gặp
hàng rào MỚI -> cho kéo 1/6 lần      <- vẫn chưa đủ
```

Lọt vì mỗi nhịp lại vứt mốc so sánh cũ đi, nên lần nào cũng chỉ so trên một quãng rất
ngắn — mà trên quãng ngắn thì cú nhảy `0 → 0,3` trông y hệt chạy thật. Nới hay siết
ngưỡng đều không chữa được, vì cái sai nằm ở **độ dài quãng so**.

Nay chưa chứng minh được thì **giữ nguyên mốc cũ**, nên quãng so cứ dài thêm mãi: đồng
hồ nhảy loạn quanh 0 không bao giờ đuổi kịp, còn đồng hồ chạy thật đạt ngay ở lần so
đầu tiên. Đo lại: **0/6**.

Chín phép đo chạy trên chính mã đã sửa, trong trình duyệt thật:

```
1. loa khoẻ                -> cho kéo        2. loa kẹt (giây đứng yên)  -> chặn
3. loa tụt về 0            -> chặn           4. bốn đường riêng mốc      -> đều cho kéo
5. nhịp dày ~40ms          -> cho kéo (không chết vòng)
6. đổi loa giữa chừng      -> chặn ở nhịp đầu
7. nhiều loa, loa đầu im   -> chọn loa CÓ báo giây
8. iOS, luồng cứ chạy lại  -> CŨ 6/6 lọt, MỚI 0/6
9. tiếng trên máy chạy đều -> cho kéo
```

Nay cả **bốn** đường đồng bộ dùng chung một hàng rào, thay vì mỗi đường một phép thử tự
nghĩ ra. Phép thử "có nhúc nhích không" vẫn giữ cho bộ dò kẹt — ở đó câu hỏi đúng là
*"đã chết hẳn chưa"*, khác hẳn câu *"có được phép kéo ai không"*.

### Vẫn chưa phải bản sửa gốc rễ của iOS

Nói rõ để khỏi trông đợi nhầm: bản này chặn **hậu quả** (hình bị giật về 0), không chữa
**nguyên nhân** (iOS cắt luồng rồi chạy lại). Gốc rễ vẫn là khoảng chờ giữa cú chạm và
lúc có địa chỉ luồng, đã nói ở 0.26.15 — việc lớn hơn, để riêng một bản.

## 0.26.16 - 2026-09-20

### Fixed — video bị kéo về 0 liên tục: vá nốt HAI nhánh còn hở

Chủ máy: *"bị lại lỗi video reset về 0 liên tục"*, và ngay sau đó: *"xem xét hết các
trường hợp, không chỉ phát trên thiết bị — xem cả phát ra loa, vừa loa vừa thiết bị,
nhiều loa"*. Câu thứ hai đúng chỗ, và nó chỉ ra rằng bản sửa hôm 19/09 mới xong **một
phần ba**.

Thẻ có **ba đường đồng bộ đồng hồ**, và cả ba đều có thể kéo thứ khác về theo mình:

| Đường | Ai dẫn | Ai bị kéo | Hàng rào trước bản này |
|---|---|---|---|
| Nghe trên máy, xem hình trên thẻ | tiếng trên máy | hình | **có** (19/09) |
| Xem hình trong khi loa phát | loa | hình | **không có** |
| Nghe trên máy cùng lúc với loa | loa | tiếng trên máy | **không có** |

Hàng rào ấy trả lời đúng một câu: *đồng hồ dẫn có thật sự đang chạy không?* Thiếu nó
thì một đồng hồ **đứng im** vẫn được tin, và cứ vài giây nó lại lôi thứ đang chạy
bình thường về chỗ nó đứng. Đó chính là cảnh giật về 0 lặp mãi.

Vì sao đồng hồ loa đứng im mà nhìn vẫn như đang chạy: thẻ không đọc thẳng con số loa
báo, mà **cộng thêm khoảng thời gian trôi** kể từ mốc Home Assistant ghi nhận. Loa nào
cứ báo mãi một con số nhưng mốc thời gian thì làm mới liên tục — khá nhiều loa làm thế
— sẽ cho ra một giây **tụt về chỗ cũ sau mỗi lần Home Assistant đẩy trạng thái**, trong
khi công thức trông vẫn "đang tiến". Nên phép thử phải là so **với chính nó ở nhịp
trước**: tiến được ít nhất một nửa quãng thời gian thật đã trôi thì mới tin.

Bảy phép đo chạy trên chính mã đã sửa:

```
1. loa khoẻ                  -> cho kéo = true     2. loa kẹt (giây đứng yên)   -> false
3. loa tụt về 0              -> false              4. hai đường riêng mốc       -> cả hai true
5. nhịp dày ~40ms            -> true (không chết vòng)
6. đổi sang loa khác         -> false ở nhịp đầu
7. nhiều loa, loa đầu im     -> chọn loa_phong_khach (loa CÓ báo giây)
```

Phép đo 5 chắn một bẫy tự đặt ra: nếu mỗi nhịp đều ghi đè mốc so sánh thì mốc luôn mới
tinh, quãng trôi không bao giờ đủ lớn để kết luận, và vòng đồng bộ **chết hẳn** thay vì
được chắn. Nay hai nhịp quá gần nhau thì giữ nguyên mốc cũ.

### Fixed — NHIỀU LOA: ba đường đồng bộ từng đọc ba cái đồng hồ khác nhau

Tìm ra trong lúc rà theo yêu cầu *"nhiều loa"*. Mỗi đường tự chọn loa dẫn nhịp một kiểu:
thanh tiến trình lấy loa đầu tiên **có báo giây**; vòng kéo hình lấy loa đầu danh sách
đang chạy, báo giây hay không cũng lấy; vòng kéo tiếng lấy loa đầu danh sách rồi thấy
giây rỗng là lặng lẽ thoát.

Hai hệ quả trong một phiên nhiều loa: hình bám loa này trong khi thanh tiến trình chạy
theo loa kia; và chỉ cần loa đầu danh sách không bao giờ báo giây là **cả hai vòng kéo
đứng im hẳn**, dù loa thứ hai vẫn báo đàng hoàng. Nay cả ba đọc chung một loa dẫn nhịp.

### Đã kiểm gì, và CHƯA kiểm được gì

Kiểm được: bảy phép đo ở trên chạy trên mã thật trong trình duyệt thật, cộng bộ test
của thẻ. Nói thẳng phần chưa kiểm: **chưa dựng lại được đúng cảnh của chủ máy** — lúc đo
trong nhà không loa nào đang phát, nên tôi chưa bắt tận tay một loa cụ thể báo kẹt. Cái
chắc chắn là hai nhánh trên **thiếu hàng rào mà nhánh thứ ba đã phải có**, và thiếu nó
thì một đồng hồ đứng im sẽ kéo được thứ khác — đó là cơ chế, không phải suy đoán.

## 0.26.15 - 2026-09-20

### Fixed — toàn màn hình Facebook: hình lấp kín, điều khiển nổi lên trên

Chủ máy: *"thanh điều khiển không chiếm chỗ khi mở toàn màn, như bây giờ đang chiếm"*.

Đúng vậy, và đó là hệ quả của chính bản 0.26.11: tôi cho thanh tiến trình và hàng nút
hiện lại nhưng **để nguyên trong luồng bố cục**, nên chúng bóp hẹp khung hình. Nay đưa
**khung hình ra khỏi luồng** cho nó lấp kín, rồi để điều khiển nổi đè lên — chữa theo
chiều này thì mai thêm một nút nữa hình vẫn đầy màn.

Một chi tiết suýt làm bản sửa hụt: khung hình bị ràng buộc tỉ lệ 16:9, nên chỉ đặt
`inset: 0` thì chiều cao vẫn tính từ bề rộng. Đo được **485×273 trên khung phát
485×757** — vẫn hụt hai phần ba. Phải gỡ ràng buộc tỉ lệ; phần thừa do video không
đúng tỉ lệ màn đã có `object-fit: contain` lo nên không méo hình.

Đo lại sau khi sửa: khung hình **485×757 — lấp kín**, dải điều khiển đè lên hình, đĩa
quay của chế độ chỉ-nghe đã ẩn. Đường YouTube **không đổi gì**.

### Fixed — tự ẩn sau 3 giây, và nút X là THOÁT TOÀN MÀN

Hai báo cáo, cùng một gốc: thanh tiến trình và hàng nút mà 0.26.11 trả lại **chưa được
nối vào cơ chế tự mờ**. Nên hàng biểu tượng (chứa nút thoát) mờ đi đúng hẹn, còn thanh
điều khiển nằm lì — chủ máy thấy "không tự ẩn" và "không có nút X". Nút X vẫn ở đó, chỉ
là đã mờ. Nay cả ba mờ và hiện lại cùng nhịp.

Và nút X nay **thoát toàn màn hình**, đúng như chủ máy chốt: *"nút x phải là thoát toàn
màn hình chứ không phải chuyển chế độ gì cả"*. Trước đây nó gọi thẳng đóng video — hình
tắt nhưng tiếng vẫn chạy nên người dùng rơi vào chế độ chỉ-nghe mà họ không hề chọn. Ở
toàn màn hình đây lại là nút **duy nhất** còn hiện, nên nó càng phải đúng nghĩa. Ngoài
toàn màn hình thì X vẫn là đóng video như cũ.

### Fixed — nút ▶ lúc kẹt phải PHÁT LẠI, không phải tạm dừng

Số đo mới từ iPhone khép lại một nhánh lớn:

```
nap=0 mang=2 loi=0 nguon=1 dom=1 mo_khoa=ok
```

`mo_khoa=ok` nghĩa là **cú mở khoá đã thành công** — phần tử được phép phát, có nguồn,
nằm trong trang, vậy mà suốt 12 giây không một byte. Theo đúng bảng đã công bố ở
0.26.14, nhánh này bác bỏ mô hình *"mở khoá một lần là xong"*: iOS đòi lệnh phát nằm
**trong chính cú chạm**, không phải chỉ cần phần tử từng được phép.

Cú chạm vào nút ▶ là cơ hội cứu duy nhất còn lại — nhưng lúc ấy phần tử "không tạm
dừng" (nó tưởng đang phát), nên bản cũ đem đúng cú chạm ấy đi **tạm dừng** một thứ vốn
đã đứng im. Nay khi kẹt, ▶ là phát lại. Lời nhắn cũng đổi thành việc cần làm thay vì chỉ
kêu hỏng.

**Chưa phải bản sửa gốc rễ** — nói rõ để không trông đợi nhầm. Gốc rễ là khoảng chờ
1,5–2,6 giây giữa cú chạm và lúc có địa chỉ luồng. Đã thử một lối tắt và **đo thấy nó
chết**: chữ ký của Home Assistant không sống sót khi thêm tham số (trả 401), nên không
thể ký sẵn một địa chỉ rồi gắn mã bài vào lúc chạm. Lối còn lại là ký sẵn **từng địa
chỉ cho từng bài** ngay sau khi tìm — việc lớn hơn, để riêng một bản.

## 0.26.14 - 2026-09-20

### Changed — đo nốt chỗ duy nhất còn tối: cú mở khoá có thành công không

Dòng chẩn đoán của 0.26.13 đã hiện ra trên máy chủ máy, và nó **loại sạch hai nghi
can**:

```
nap=0  mang=2  loi=0  nguon=1  dom=1
```

`nguon=1` — phần tử **đã chọn được nguồn phát**. `dom=1` — nó **đã nằm trong trang**.
Vậy mà sau 12 giây vẫn không có byte nào và cũng không lỗi.

Đó là chữ ký của iOS **từ chối tải dữ liệu** vì việc phát chưa được một cú chạm cho
phép — WebKit cố tình không lấy dữ liệu cho tới khi được phép, đúng `readyState 0` +
`networkState LOADING` + không lỗi.

**Cú chạm thì không bị mất** — đã kiểm: nút tai nghe gọi thẳng `_playResult`, và không
có `await` nào chen vào trước lúc `unlock()` chạy. Nên chỉ còn một khả năng chưa ai
kiểm: **chính cú mở khoá thất bại**. Mã đang nuốt im lặng lỗi của nó
(`play().catch(() => {})`), mà mọi thứ sau đó đều dựa vào nó.

Nay kết quả cú mở khoá được ghi lại và in kèm (`mo_khoa=`). Chỉ cần một lần tái hiện
nữa là biết chắc:

- `mo_khoa=ok` → cú mở khoá thành công, nhưng iPhone vẫn không cho tải ⇒ mô hình "mở
  khoá một lần là xong" sai, phải bỏ hẳn khoảng chờ giữa cú chạm và lúc có địa chỉ
  luồng (đổi kiến trúc, không phải vá).
- `mo_khoa=NotAllowedError` (hoặc tên lỗi khác) → hỏng ngay từ cú mở khoá, và chỗ phải
  sửa là đoạn im lặng chứ không phải đường lấy luồng.

**Kèm một phép thử lại** sau 3 giây, dựng thẳng từ mẹo người dùng tự tìm ra ("lượn qua
app khác rồi quay lại thì lại phát" — tức lệnh phát chỉ cần được nhắc lại). Rẻ và vô
hại: đang chạy rồi thì nhánh ấy thoát ngay.

Nói thẳng: bản này **là bước đo, không hứa hết lỗi**. Nhưng nó là bước đo cuối cùng —
sau nó thì không còn chỗ nào tối để mà đoán nữa.

## 0.26.13 - 2026-09-20

### Fixed — chỗ chẩn đoán đặt sai chỗ, nên ca quan trọng nhất không có số đo

Chủ máy: *"Chỉ nghe không chạy thanh thời gian nên không có tiếng"* — và **không dòng
chẩn đoán nào hiện ra**.

Đó là lỗi trong chính phần chẩn đoán của tôi: bộ bắt lỗi nằm trong vòng đồng bộ video,
mà vòng ấy **thoát ngay khi không có video mở**. Nên đúng ca "chỉ nghe" — ca quan trọng
nhất, và là ca chủ máy đang kẹt — lại chẳng đo được gì.

Nay việc canh tiếng nằm ở **chính bộ phát tiếng**, độc lập với video: 12 giây sau khi
bảo nó phát, nếu đồng hồ không nhúc nhích thì nói thẳng kèm năm số đo.

### Fixed — GỐC RỄ: phần tử mất trạng thái "đang phát" trong lúc chờ địa chỉ luồng

Người dùng iPhone mô tả đúng cơ chế, và bốn câu của họ đáng giá hơn cả đêm đo đạc:

> *"Chỉ nghe mới bật thì ko phát, nhưng lượn qua app khác rồi quay lại thì lại phát."*
> *"Khi phát rồi thì khoá màn vẫn phát được."*
> *"Nhưng chuyển bài khác là lại tịt."*

Đó là dấu vân tay của **mất trạng thái đang phát**, không phải của lỗi mạng hay lỗi
giải mã:

1. Bấm nghe → `unlock()` cho phần tử phát **nửa giây im lặng** trong chính cú chạm.
2. Thẻ đi xin địa chỉ luồng — đo thật mất **1,5–2,6 giây**.
3. Tới lúc gán địa chỉ, đoạn im lặng **đã kết thúc từ lâu**; phần tử đang ở trạng thái
   "đã phát xong", và WebKit không cho nó tự chạy lại ngoài cú chạm. Chrome không đòi
   thế, nên chỗ này êm suốt từ đầu.
4. Quay lại trang từ app khác chính là lúc WebKit chịu thi hành lệnh phát đang treo —
   nên "lượn qua app khác rồi quay lại thì lại phát".
5. Đã chạy rồi thì khoá màn vẫn chạy (không có gì làm nó dừng), nhưng **chuyển bài là
   lặp lại toàn bộ vũ điệu trên** nên tịt tiếp.

**Sửa:** cho đoạn im lặng **lặp vòng**, để phần tử luôn đang phát suốt lúc chờ. Khi ấy
việc gán bài thật chỉ là phát tiếp một thứ người dùng **đã cho phép**, không phải xin
phép lại. Tắt lặp ngay trước khi gán bài thật, ở **cả hai** đường dùng chung khuôn này
(`listen` và `loadAlong`) — không chỉ đường đang có báo lỗi.

**Kèm một lưới an toàn** dựng thẳng từ mẹo mà chính người dùng tìm ra: quay lại trang
mà có bài nhưng đang dừng thì thử phát lại. Nếu bản sửa lặp-vòng đã đủ thì nhánh này
không bao giờ chạy tới.

### Đã loại trừ thêm hai nghi can, đo được hẳn hoi

- **Phần tử nằm ngoài DOM** (bản 0.26.12 gắn vào `body`): đã gắn rồi mà vẫn im.
- **Cloudflare chặn luồng**: tên miền ngoài trả `403 error code 1010` với lời gọi
  script trần, nhưng giả dạng Safari iPhone thì **chạy tốt** — `206`, `Content-Range`
  đầy đủ, `audio/mp4`, 0,23 giây. Đường giao luồng sạch từ mọi góc đo được: nội bộ,
  qua Home Assistant, và qua Cloudflare.

### Xác nhận — xem video trên iOS đã chạy

Ảnh chủ máy gửi cho thấy thanh tiến trình chạy tới **0:20**: bản 0.26.12 thôi tự đóng
hình, và xem video có tiếng bình thường. Phần còn kẹt chỉ là bộ phát tiếng riêng.

## 0.26.12 - 2026-09-20

### Fixed — iOS: một gốc duy nhất cho cả ba triệu chứng

Ba báo cáo trong một buổi, và chúng **không phải ba lỗi**:

1. *"Nghe khi tắt màn hình không hoạt động."*
2. *"Bật video để xem thì không được trên iOS."*
3. *"Đang xem video chuyển sang chỉ nghe nhạc thì mất tiếng."*

Tất cả quy về **một chỗ**: phần tử `<audio>` của thẻ **không bao giờ tải được** trên
iOS. Đo hai lần độc lập đều ra `nap=0 mang=2 loi=0` — đang tải, chưa có byte nào,
không lỗi.

**Giả thuyết "khung YouTube chiếm đường" đã bị bác bỏ.** Clip 45 giây chủ máy gửi cho
thấy bản 0.26.9 tự đóng hình đúng như thiết kế, rồi tiếng **vẫn đứng ở 0:00 suốt gần
30 giây sau đó**. Gỡ khung video không giúp gì. Đây là giả thuyết thứ tư bị chính số
đo bác bỏ.

**Ứng viên mới, và nó giải thích được vì sao chỉ iOS hỏng:** `new Audio()` sinh ra một
phần tử **đứng ngoài DOM**. Chrome vẫn tải bình thường nên chỗ này êm suốt từ đầu, còn
WebKit thì có thể không bao giờ bắt đầu tải cho phần tử chưa gắn vào trang — khớp
chính xác `nap=0 mang=2 loi=0`. Nay phần tử được gắn vào `body`; thao tác rẻ và vô
hại, vì phần tử audio không khai `controls` thì không vẽ ra gì cả.

### Changed — bấm "xem" thì GIỮ HÌNH, không tự ý đổi ý người dùng

Bản 0.26.4 giữ hình nên mất tiếng lúc tắt màn; bản 0.26.9 giữ tiếng nên **mất hình**.
Cả hai đều tự quyết thay người dùng, và mỗi lần lại hỏng nửa còn lại.

Nay chọn theo **ý định đã nêu** — thứ duy nhất không phải đoán. Bấm "xem" thì giữ
hình và trả tiếng về chính khung ấy, kèm câu nói thẳng giới hạn của máy và chỉ ra lối
đi thay thế (nút tai nghe, đường đó đóng hình trước rồi mới phát nên không tranh chỗ).

### Added — hai số đo nữa, để lần tới khỏi đoán

Dòng chẩn đoán nay có thêm `nguon` (phần tử đã chọn được nguồn phát chưa — rỗng nghĩa
là nó chưa hề bắt đầu lấy địa chỉ) và `dom` (có nằm trong trang không). Đúng hai thứ
nghi ngờ còn lại sau khi loại bỏ khung video.

Nếu bản này chạy được thì `dom` chính là nguyên nhân. Nếu vẫn hỏng, hai số ấy sẽ chỉ
thẳng chỗ tiếp theo thay vì để tôi đoán lần thứ năm.

## 0.26.11 - 2026-09-20

### Fixed — phóng to video Facebook thì mất nút thoát và nút tua

Chủ máy báo: Facebook phóng to toàn màn thì ổn, nhưng không có nút thoát màn và không
chỉnh được thời gian.

Thủ phạm là một luật CSS:

```css
.player:is(.expanded, :fullscreen) :is(.progress, .control-bar, .nghe-hang) { display: none; }
```

Luật ấy sinh ra vì **khung nhúng YouTube đã có bộ nút riêng** nên thẻ nhường chỗ (yêu
cầu 18/09: *"lúc này dùng bằng YouTube là được"*). Nhưng video Facebook chạy bằng phần
tử `<video>` do chính thẻ dựng, mà `_tryPicture` dựng nó **không có bộ nút gốc** — thẻ
nhường chỗ cho một bộ nút không tồn tại. Nay luật chỉ áp khi **không phải** hình của
thẻ (`:not(.picture-on)`).

Tua bằng thanh của thẻ còn **đúng hơn** bộ nút gốc của trình duyệt: `_seekFraction`
dời **cả tiếng lẫn hình**, trong khi bộ nút gốc chỉ dời mỗi hình rồi bị vòng đồng bộ
kéo ngược về.

Đo trong trình duyệt, ba trạng thái:

| Trạng thái | Thanh tiến trình | Hàng nút phát | Nút thoát |
|---|---|---|---|
| Bình thường | hiện | hiện | hiện |
| Phóng to + khung YouTube | ẩn *(như cũ)* | ẩn *(như cũ)* | hiện |
| Phóng to + hình của thẻ | **hiện** | **hiện** | hiện |

**Một bản sửa hụt đã tự thu hồi:** ban đầu tôi nhắm vào `.np-zone`, nhưng đo ra nó bị
một luật nền ẩn trong **mọi** trường hợp — nó không phải chỗ chứa thanh tiến trình.
Hai phép sửa đó vô hại nhưng chú thích của chúng nói sai, nên đã gỡ bỏ thay vì để lại.

### Added — ghim được bài Facebook để sau nghe lại

Chủ máy: *"Face cũng chưa có phần lưu link bài để sau nghe lại, và khi lưu thì lưu như
ghim Facebook"*. Đúng vậy — **cả hai đường ghim đều chặn Facebook**:

- Nút ghim trên dòng kết quả chỉ dựng khi nguồn là `youtube`.
- Ô "dán link để gắn thẳng" ghi cứng `source=youtube`, nên link Facebook luôn bị máy
  phát đọc bằng bộ giải YouTube rồi trả rỗng.
- Và `normalize_song` đòi mã khớp khuôn 11 ký tự của YouTube, lại **không lưu nguồn** —
  nên dù lọt qua thì phát lại cũng bị coi là YouTube.

Nay bản ghi **mang theo nguồn**, mỗi nguồn một khuôn mã riêng (YouTube 11 ký tự,
Facebook là chuỗi số). Ô dán link tự suy nguồn từ chính cái link. Bản ghi cũ không khai
nguồn thì rơi về YouTube — đúng thứ đã lưu trước đây, không phải đoán.

**`suggestions.py` tới nay chưa hề có test chức năng nào** — chỉ được soi gián tiếp
bằng khớp chuỗi, và đó đúng là lý do lỗ hổng này sống được. Nay có `test_suggestions.py`
với 5 ca, gồm tương thích ngược và chặn chéo nguồn (mã YouTube khai là Facebook thì từ
chối, và ngược lại).

### Changed — thẻ tự chấm bản sửa iOS của chính nó

Ảnh chủ máy gửi cho thấy bản 0.26.9 đã chạy: thẻ tự tắt hình để nhường tiếng. Nhưng
thanh tiến trình vẫn `0:00`, nên **chưa kết luận được** giả thuyết đúng hay sai.

Thay vì hỏi rồi chờ, nay máy tự đo: bốn giây sau khi tắt hình, nó xem đồng hồ tiếng có
nhúc nhích không rồi nói thẳng — *"nay nghe được trên máy này"* hoặc *"tắt hình rồi mà
vẫn chưa ra tiếng — vậy không phải do khung video"*. Lần tới là biết ngay, khỏi mất một
vòng hỏi đáp.

## 0.26.10 - 2026-09-20

### Fixed — khởi động lại Home Assistant: nhạc vẫn chạy mà thẻ mất dấu bài và loa

Chủ máy báo: phát ra loa, khởi động lại Home Assistant thì **nhạc không mất**, nhưng
vào lại thẻ thì **không thấy bài đang phát, không thấy loa đang chọn**. Và hỏi thêm:
dùng add-on có bị như c2a không.

**Lỗi nằm trong thẻ, nên add-on và c2a dính y như nhau.** Chuỗi gây lỗi:

1. Home Assistant khởi động lại → loa biến mất một lúc (Cast dò lại).
2. `_syncPlayers` thấy loa `unavailable` liền **xoá nó khỏi danh sách đang chọn** —
   đúng thiết kế, để thiết bị mất kết nối không nằm lại trong lựa chọn.
3. Loa trở lại. Nhưng phiên vẫn là phiên cũ nên **chữ ký y hệt**, và hàm khôi phục có
   cổng canh `marker === this._sharedSessionMarker` nên **thoát sớm** — loa không bao
   giờ được chọn lại. Mất loa thì cũng mất luôn phiên đang theo, nên tên bài biến mất
   theo.

Chữ ký sinh ra để **khỏi vẽ lại thừa**, không phải để chặn lần cần vẽ lại thật. Nay
chỉ bỏ qua khi **cả hai** cùng khớp: chữ ký chưa đổi **và** lựa chọn hiện tại vẫn đủ
loa của phiên. Đã kiểm thứ tự gọi: hàm khôi phục chạy **trước** bộ lọc loa trong cùng
một nhịp, nên loa vừa trở lại là được chọn lại ngay.

### Đã kiểm, KHÔNG phải nguyên nhân

- **Tích hợp không tự giữ phiên.** `sessions.py` chỉ là hàm thuần đọc trạng thái; bộ
  điều phối mỗi nhịp hỏi thẳng máy phát. Khởi động lại Home Assistant không xoá gì.
- **Máy phát giữ phiên tới khi bị dừng hẳn.** `state` đặt `"playing"` lúc bắt đầu và
  **không chỗ nào** cập nhật lại.
- **Cờ `_manualSelection`** đặt `false` lúc khởi tạo, chỉ bật khi người dùng tự tay
  tích loa, **không** khôi phục từ bộ nhớ — nên nó không chặn gì. (Đây là nghi can đầu
  của tôi, và nó sai.)

### Còn một lỗ hổng khác, CHƯA sửa — nói ra để chủ máy quyết

Cả c2a lẫn add-on giữ phiên **thuần trong bộ nhớ**, không ghi xuống đĩa. Nên khi **máy
phát** khởi động lại — c2a được Watchtower cập nhật, add-on được nâng cấp, hoặc máy chủ
nhà khởi động lại — thì loa **vẫn phát tiếp** mà phiên biến mất, và thẻ không còn đường
nào nhận lại.

Khác biệt giữa hai đường, đo theo kiến trúc:

| Tình huống | c2a | Add-on |
|---|---|---|
| Khởi động lại **Home Assistant Core** | phiên còn (máy khác) | phiên còn (Supervisor không khởi động lại add-on) |
| **Khởi động lại máy chủ nhà** | phiên còn | **phiên mất** |
| **Cập nhật máy phát** | phiên mất | phiên mất |

Chữa được bằng cách ghi phiên xuống đĩa rồi nạp lại lúc khởi động — nhưng phải kiểm
loa có thật sự còn phát không trước khi khôi phục, nếu không sẽ bày ra phiên ma.

## 0.26.9 - 2026-09-20

### Fixed — iOS: "nghe khi tắt màn hình" không chạy. Gỡ đối thủ, đừng đầu hàng

Chủ máy xác nhận thêm hai điều, và chúng khoá chặt vùng nghi ngờ: lỗi xảy ra **cả khi
nối add-on**, và **cả trên Safari** — không riêng app Home Assistant.

Cộng với phép đo ở 0.26.8 (máy chủ giao byte đầu tiên sau **0,16 giây** trên chính
đường trình duyệt đi, mã 206, `Content-Range` đầy đủ), kết luận không còn chỗ lùi:
**máy phát vô can**, byte có sẵn ở đầu kia mà WebKit không kéo về.

Thứ duy nhất còn tranh chỗ là **khung YouTube đang phát ngay trên trang**. iOS chỉ cho
một phần tử phát chạy thật; khung video chiếm đường nên phần tử âm thanh xếp hàng mãi —
không lỗi, không dữ liệu, đúng bộ số `nap=0 mang=2 loi=0` thu được hai lần độc lập.

**Bản 0.26.4 xử sai chiều:** nó trả tiếng về cho khung YouTube. Mà iOS treo khung nhúng
lúc tắt màn hình, nên nó vứt đúng thứ người dùng vừa chọn. Nay làm ngược lại — **đóng
hình, giữ tiếng trên máy**, vì phần tử âm thanh mới là thứ sống sót qua lúc tắt màn.
Dùng lại `_listenOnly` vốn đã làm đúng việc ấy, không viết đường thứ hai; đã kiểm
`_closeVideo` không hề đụng tới bộ phát âm thanh.

Ngưỡng hạ từ 20 xuống **12 giây** — gấp hơn bốn lần trường hợp chậm nhất đo được
(xin vé 2,6 giây + byte đầu 0,16 giây), đủ rộng để không nổ oan trên mạng yếu.

**Bản sửa này tự chứng minh.** Nghe được tiếng ⇒ giả thuyết đúng. Vẫn im ⇒ nó sai, và
dòng nhắn nói rõ để báo lại — không phải đoán thêm vòng nữa. Nói thẳng: đây là giả
thuyết thứ tư; ba cái trước đều bị chính số đo bác bỏ, nên nó được viết sao cho kết quả
thật phán xử thay vì tôi.

## 0.26.8 - 2026-09-20

### Fixed — thẻ cướp tiếng trong lúc luồng MỚI ĐANG TẢI (lỗi của bản 0.26.4)

Bốn con số từ máy người dùng, thu được hai lần độc lập (22:31 và 22:35):

```
nap=0  mang=2  loi=0  giay=0.0
```

Đọc theo bảng đã công bố ở 0.26.6: phần tử âm thanh **đang tải** (`mang=2`) và **chưa
nhận được byte nào** (`nap=0`), **không có lỗi** (`loi=0`). Đây **không phải** "kẹt
giữa chừng" — đó là **chưa mở xong**. Bản 0.26.4 gộp hai trạng thái ấy làm một, nên nó
tuyên bố hỏng rồi trả tiếng về khung YouTube trong lúc luồng có thể đang chạy bình
thường. Mà iOS treo khung nhúng khi tắt màn hình, nên **chính bản sửa lại làm mất đúng
tính năng người dùng cần**. Lỗi này là của tôi, không phải của máy phát.

Nay tách hai đường:

| Tình trạng | Thẻ làm gì |
|---|---|
| `nap≥2`, đồng hồ đứng > 8 giây | kẹt thật → trả tiếng về khung, mời chạm |
| `nap<2`, đang tải > 20 giây | **chờ tiếp**, chỉ nói thật là chưa lấy được tiếng |

### Đã loại trừ xong phía máy chủ — đo trên chính đường trình duyệt đi

Gọi đúng chuỗi mà `<audio>` của iPhone dùng: xin vé qua Home Assistant, rồi tải vé đó
**không kèm chứng chỉ nào**, chỉ dựa chữ ký trên đường dẫn:

```
mã trả về     : 206
Content-Type  = audio/mp4
Content-Range = bytes 0-65535/4557665
Accept-Ranges = bytes
byte đầu tiên : 0,16 giây   (xin vé: 1,51 giây)
```

Cả chuỗi khoẻ mạnh đầu-cuối. Cộng với việc lỗi xảy ra **giống hệt** ở add-on lẫn c2a,
ở Safari lẫn app Home Assistant: **máy phát vô can**, byte có sẵn ở đầu kia mà WebKit
không kéo về.

Nghi vấn còn lại — **chưa chứng minh, nói rõ để không ai trông đợi nhầm**: lúc đó khung
YouTube đang phát video, mà iOS chỉ cho một phần tử phát chạy thật; khung video chiếm
đường nên phần tử âm thanh xếp hàng mãi. Nó khớp trọn bộ triệu chứng (phải bật loa
trong khung mới nghe được, tắt màn là im), nhưng đây đã là giả thuyết thứ tư trong khi
ba cái trước đều bị số đo bác bỏ, nên cần một phép thử trước khi sửa.

## 0.26.7 - 2026-09-19

### Fixed — mở hết màn hình thì ô tìm kiếm và hàng nguồn đè lên video

Chủ máy gửi ảnh chụp iPhone: lúc phóng to, hàng nguồn và ô tìm kiếm **hiện đè** lên
video đang xoay, chữ chồng lên nhau.

**Nói thẳng phần tôi không chứng minh được.** Lỗi này **không dựng lại được trong
Chrome**. Đo ở khổ 390px với khung phát đã phóng to, hỏi trình duyệt "phần tử trên
cùng tại tâm ô tìm kiếm là ai" thì nó trả về `.video-frame` — tức lớp phủ che đúng.
Kiểm thêm: `.player` tính ra `position: fixed` thật, và **không tổ tiên nào** có
`transform`/`filter`/`contain`/`will-change` để phá vỡ nó. Hai giả thuyết của tôi
(khối chứa bị phá, tranh chấp lớp chồng) đều **không đứng vững**; đây là đặc thù
WebKit mà tôi chưa tìm ra cơ chế.

**Nên bản sửa không nhắm vào cơ chế, nó gỡ bỏ chế độ hỏng:** phóng to thì ẩn hẳn cả
cột phải. Lớp phủ chạy đúng thì mấy khối ấy vốn đã khuất, chẳng mất gì; lớp phủ hụt
thì chúng đã ẩn nên không còn gì để đè lên video.

Ẩn **tất**, không chừa dải "đang phát" — dải ấy đã có luật ẩn riêng khi phóng to từ
yêu cầu 18/09 ("phóng to toàn màn hình thì ẩn hết, lúc này dùng bằng YouTube là
được"). Chừa nó ra chỉ tạo một ngoại lệ không có thật rồi đánh lừa người đọc sau.
Đường thoát vẫn còn: hàng biểu tượng nằm **trong** khung phát, không thuộc cột này.

Viết theo nguyên tắc ("mọi con trực tiếp") thay vì liệt kê bảy lớp, nên khối mới thêm
vào cột sau này tự được che.

Đo lại sau khi sửa:

| Trạng thái | Hàng nguồn | Ô tìm kiếm | Gợi ý | Kết quả |
|---|---|---|---|---|
| Thường, 390px | hiện | hiện (366×33) | hiện | — |
| Phóng to, 390px | **ẩn** | **ẩn (0×0)** | **ẩn** | **ẩn** |
| Phóng to, 1400px | **ẩn** | **ẩn** | **ẩn** | **ẩn** |

## 0.26.6 - 2026-09-19

### Changed — bắt máy TỰ KHAI BỆNH thay vì đoán tiếp về WebKit

Chủ máy báo: bật "Nghe khi tắt màn hình" là **mất tiếng**; tắt viên đó thì nghe được.
Điều này khớp đúng chuỗi đã dựng: bật viên ấy là chuyển tiếng sang bộ phát riêng của
thẻ, mà trên iPhone bộ phát đó **không bao giờ chạy** — nên mọi triệu chứng còn lại
(phải bật loa trong khung video, tắt màn là im) đều là hệ quả.

Bản 0.26.4 đã phát hiện được tình trạng "mở được nhưng không chạy" và trả tiếng về
cho khung. Nhưng nó **không biết vì sao**, mà ba nguyên nhân khả dĩ lại cần ba cách
sửa khác hẳn nhau. Trong một ngày tôi đã đoán sai cơ chế ba lần và đều bị chính số đo
bác bỏ (vẽ lại giao diện, vòng đồng bộ tua về 0, nội dung hỗn hợp HTTP/HTTPS), nên
bản này **không đoán nữa**: chỗ phát hiện nay in kèm bốn con số mà chỉ trình duyệt
biết.

| Số đo | Nghĩa |
|---|---|
| `nap=0` + `mang=2` | đang chờ dữ liệu — nghẽn mạng hoặc luồng không tới |
| `nap≥2` + `giay` đứng yên | có dữ liệu mà bị chặn phát — chuỗi cử chỉ người dùng |
| `loi≠0` | lỗi tải hoặc giải mã thật |

Người dùng chỉ cần tái hiện **một lần** rồi chụp màn hình là biết chắc, thay vì thêm
vài vòng sửa mò. Đây là bước **đo**, không phải bản sửa gốc rễ — nói rõ để không ai
trông đợi nhầm.

## 0.26.5 - 2026-09-19

### Fixed — ẩn bớt còn ba mục thì phải nằm CÙNG MỘT HÀNG

Chủ máy chốt: *"nếu 3 cái thì phải đặt cùng hàng như trước chứ"*. Bản 0.26.2 để chỗ
hẹp mặc định hai cột, nên mục thứ ba rơi xuống một mình — nhìn như lỗi bố cục chứ
không như một lựa chọn.

Nay ba mục ra ba cột ở **mọi** bề rộng. Bốn mục vẫn giữ 2×2 khi hẹp, vì đó là lý do
mặc định hai cột tồn tại: bốn nhãn dàn ngang ở cột hẹp từng làm chữ "YouTube" bị
chính nút cắt cụt (đo 19/09).

Đo trong trình duyệt thật, cột chứa rộng 376px (đúng ca điện thoại của chủ máy) và
622px — không tin luật CSS vừa viết:

| Số mục | Cột 376px | Cột 622px | Chữ tràn khỏi nút |
|---|---|---|---|
| 4 | 2 | 4 | không |
| 3 | **3** | 3 | không |
| 2 | 2 | 2 | không |

Cột "chữ tràn" đo riêng bằng `scrollWidth` so với `clientWidth` của từng nhãn, vì đó
mới là thứ hỏng khi nhồi thêm cột — số cột đúng mà chữ cụt thì vẫn là hỏng.

## 0.26.4 - 2026-09-19

### Fixed — tiếng "đang phát" mà không ra tiếng, và không ai báo gì

Bản 0.26.3 chặn được thiệt hại (video hết bị giật về 0) nhưng **chưa trả lại tiếng**:
người dùng vẫn ngồi trước một video chạy mượt mà im lặng. Đây là phần còn lại.

Ba dữ kiện của chủ máy khoanh vùng gọn nguyên nhân:

- Lỗi xảy ra với **cả add-on lẫn c2a** — hai máy phát khác hẳn nhau.
- Lỗi xảy ra **cả trên Safari**, không riêng app Home Assistant.

Hai điều đó loại máy phát và loại khung web của app. Lỗi ở **thẻ**.

**Vì sao nó hỏng im lặng:** phần tử âm thanh của thẻ chỉ được gắn **bốn** sự kiện —
`play`, `pause`, `ended`, `error`. Luồng *lấy không được* thì bắn `error` và thẻ đã có
đường xử lý. Nhưng luồng **mở được rồi kẹt giữa chừng** không bắn gì cả: phần tử vẫn
báo "không tạm dừng", `currentTime` thì đứng nguyên ở 0. Thẻ tin là đang phát, người
dùng không nghe thấy gì, và không có chỗ nào phát hiện ra.

**Sửa:** vòng đồng bộ nay tự đo — "đang phát" mà đồng hồ không nhúc nhích quá 8 giây
thì trả tiếng về cho khung YouTube và mời chạm để nghe, **dùng lại đúng đường phục
hồi đã có** cho ca luồng lỗi (nay tách thành một hàm, gọi từ cả hai chỗ, không chép
đôi).

**Một cái bẫy đã né:** `_syncVideo` không chỉ chạy mỗi 2 giây — nó còn chạy **mỗi lần
Home Assistant đẩy trạng thái**, tức nhiều lần mỗi giây. Đếm số nhịp thì ba nhịp trôi
qua trong chưa đầy một giây và báo nhầm ngay; nên phép đo dùng **thời gian thực** kể
từ lần đồng hồ nhúc nhích gần nhất.

Chưa chạm tới nguyên nhân gốc khiến luồng kẹt trên WebKit — nghi vấn hiện nay là khung
YouTube (dù đã tắt tiếng) giành mất phiên âm thanh của phần tử `<audio>`, nhưng chưa
đo được nên **không khẳng định**. Dù gốc rễ là gì, thẻ nay không còn im lặng chịu trận.

## 0.26.3 - 2026-09-19

### Fixed — video YouTube cứ chạy vài giây rồi giật về 0, lặp mãi

Chủ máy gửi clip quay màn hình iPhone 60 giây. Trích từng giây thì quy luật hiện ra
rất rõ, trên **hai** video khác nhau:

```
 9s 0:00   13s 0:01   17s 0:00   21s 0:00   25s 0:00
10s 0:01   14s 0:02   18s 0:01   22s 0:01   27s 0:01
11s 0:00 ← 15s 0:03   19s 0:02              28s 0:00 ←
12s 0:00   16s 0:00 ← 20s 0:00 ←            29s 0:01
```

Video **có** chạy rồi bị kéo về 0, chu kỳ 4–5 giây — không phải "không phát được".
Cùng lúc, thanh tiến trình của thẻ **đứng yên ở 0:00**; mà ở chế độ "nghe khi tắt màn
hình", thanh ấy lấy số **thẳng từ `currentTime` của phần tử âm thanh**. Nên con số đó
nói thẳng: **đồng hồ của tiếng chưa hề chạy**, dù phần tử báo là không tạm dừng —
luồng bị kẹt trong khung web của app Home Assistant trên iPhone.

Vòng đồng bộ 2 giây có luật: *tiếng không tạm dừng, đã qua 4 giây từ lần tua trước, và
lệch quá 2 giây thì tua video về vị trí của tiếng*. Đồng hồ tiếng đứng ở 0, video bò
tới 0:03 là lệch quá 2 giây → tua về 0. Chu kỳ 4 giây trong luật chính là chu kỳ giật
về 0 đo được trên clip.

**Sửa ở đúng chỗ sai: đồng hồ dẫn phải ĐANG CHẠY thì mới được kéo đồng hồ theo.** So
`currentTime` với nhịp trước — một phép thử "đồng hồ có chạy không" đúng nghĩa, không
phải thêm ngưỡng tự nghĩ ra. Tiếng kẹt thì video cứ chạy tiếp, không ai giật nó nữa.

Không đụng tới nguyên nhân gốc của việc luồng tiếng kẹt trên app iPhone — đó là việc
khác. Nhưng dù nguyên nhân ấy là gì, thẻ cũng không được phá hỏng video vì nó.

## 0.26.2 - 2026-09-19

### Added — tự chọn hiện hay ẩn YouTube, Zing MP3, Facebook và Playlist

Tab **Hiển thị** của trình sửa thẻ có thêm nhóm "Hiện / ẩn mục" với bốn ô tích. Bốn
khoá cấu hình mới — `show_youtube`, `show_zing`, `show_facebook`, `show_playlist` —
đều **mặc định bật**, nên thẻ đang chạy không đổi gì. Ẩn ở đây là ẩn khỏi giao diện
chứ không khoá nguồn phía máy phát: bài thuộc nguồn bị ẩn vẫn nghe lại được từ hàng
đợi hay playlist.

**Số cột bám theo số mục còn hiện**, vì ẩn bớt mà giữ nguyên số cột thì hàng thừa ô
trống lệch hẳn sang một bên. Đo thật trong trình duyệt, đọc số cột trình duyệt tính
ra chứ không tin luật CSS vừa viết:

| Số mục | Cột chứa hẹp (376px) | Cột chứa rộng (565px) |
|---|---|---|
| 4 | 2 | **4** |
| 3 | 2 | **3** |
| 2 | 2 | **2** |
| 1 | **1** | **1** |
| 0 | ẩn cả khung | ẩn cả khung |

Chỗ hẹp giữ hai cột là **cố ý**, giữ nguyên hành vi cũ: bốn cột ở cột chứa hẹp làm
nhãn "YouTube" bị chính nút cắt cụt (đo 19/09). Lưu ý khi đọc bảng: thứ quyết định
là bề rộng **cột chứa thẻ**, không phải bề rộng thẻ — thẻ 900px trong bố cục hai cột
chỉ cho cột chứa 357px.

**Ba tình huống hỏng do chính tính năng này sinh ra, mỗi cái một chốt chặn** (nếu
không thì cho ẩn xong là thẻ tự mâu thuẫn với chính nó):

1. **Ẩn đúng nguồn đang mở** → tự dời sang nguồn còn hiện và xoá kết quả cũ. Để
   nguyên thì ô tìm kiếm vẫn gửi đi cái nguồn người dùng vừa bảo là không muốn thấy.
2. **Ẩn Playlist khi đang đứng trong khung Playlist** → chặn tại `_showView`, **một**
   cửa vào duy nhất, vì còn một đường tự nhảy vào khung đó sau khi lưu playlist; vá
   từng chỗ gọi là kiểu sót đã cắn nhiều lần. Nút "lưu cả playlist" cũng ẩn theo.
3. **Nhớ lần tìm cũ thuộc nguồn vừa bị ẩn** → không khôi phục nữa, nếu không màn hình
   hiện một danh sách kết quả mà hàng nút không còn mục nào ứng với nó.

Ô tích là loại điều khiển **đầu tiên** trong trình sửa dùng `.checked` thay vì
`.value`, nên cả hai chiều đọc và ghi đều phải thêm riêng; bật là mặc định nên khi
bật thì xoá hẳn khoá khỏi YAML, chỉ ghi lại đúng những mục bị ẩn.

## 0.26.1 - 2026-09-19

### Fixed — xem video Facebook trên iPhone: câm tiếng và tự mở lại bài từ giây 0

Chủ máy báo hai triệu chứng trên iPhone: *"mặc định tắt tiếng và restart liên tục thời
gian về 0"*. Hoá ra **một nguyên nhân duy nhất**, do chính bản Facebook hôm nay sinh ra.

Facebook không cho nhúng trình phát, nên thẻ chiếu video bằng phần tử `<video>` của
riêng mình. Phần tử ấy **luôn** được dựng ở trạng thái câm — đúng thiết kế, vì mọi
đường hình của thẻ đều để cho loa hoặc cho máy này giữ tiếng. YouTube có sẵn cơ chế
giao tiếng cho máy này khi khung nhúng không phát được (`_embedRefused`), còn đường
Facebook tôi viết hôm nay **đi vòng qua cơ chế đó**: đặt hình lên rồi không ai bật
tiếng cả.

Vì sao iPhone lộ rõ hơn máy khác: tuỳ chọn "nghe khi tắt màn hình" **mặc định tắt**,
mà chỉ khi bật nó đường xem mới khởi động tiếng trên máy. Máy nào cũng câm như nhau;
iPhone chỉ là nơi chủ máy dùng nhiều nhất.

Và triệu chứng thứ hai là **hệ quả của cùng lỗ hổng đó**, không phải lỗi riêng: nhánh
tự chuyển bài trong `_setVideoState` chỉ chạy khi *không có loa* **và** *không bám theo
tiếng máy này*. Hình câm rơi đúng vào cả hai điều kiện, nên một lần hình kết thúc sớm
là thẻ nhảy bài kế, mở lại từ giây 0, rồi lặp.

**Sửa ở tầng kiến trúc, không vá triệu chứng:** khi không có loa, đường xem Facebook
khởi động tiếng trên máy này và bật cờ bám-tiếng — dùng lại đúng lối YouTube vẫn dùng,
không đẻ nhánh tiếng thứ hai. Một thay đổi xoá cả hai triệu chứng: có tiếng, và cờ
bám-tiếng tự tắt nhánh tự-chuyển-bài nên vòng lặp không còn chỗ phát sinh.

Thứ tự gọi quan trọng và đã ghi rõ trong mã: trạng thái video phải đặt **trước** khi
gọi phát tiếng, vì bên nghe thông báo so mã bài của tiếng với mã bài của hình — gọi
ngược lại thì hai mã lệch nhau và chính nó mở lại video.

Bốn giả thuyết khác đã bị **đo và loại**, ghi lại để khỏi ai đi lại: thẻ vẽ lại giao
diện mỗi lần Home Assistant đẩy trạng thái (không — `_render()` chỉ chạy một lần); vòng
đồng bộ 2 giây tua hình về 0 (không — nhánh ấy thoát ngay khi chưa có tiếng); máy chủ
không hỗ trợ đọc từng khúc (không — đo thật: `206 Partial Content`, `accept-ranges:
bytes`); video Facebook mã hoá AV1 mà iPhone không giải nổi (không — luồng ghép là
`avc1`, tức H.264).

### Fixed — đang xem video Facebook mà tích loa thì gửi sai nguồn

Tìm ra bằng một lượt quét cùng lớp lỗi, không phải do ai báo: hàm "loa tham gia video
đang xem" gắn cứng nguồn `"youtube"` ở **hai** chỗ — hỏi loa có nhận nguồn YouTube
không, rồi gửi lệnh phát với nhãn nguồn YouTube trong khi địa chỉ là link Facebook.
Đang xem Facebook mà tích loa là loa nhận một thứ nó không hiểu, và câu báo lỗi cũng
nói nhầm tên nguồn. Nay cả ba chỗ đọc nguồn của chính bài đang xem.

Đường phía sau vốn đã sẵn sàng, đã kiểm lại từng mắt: lược đồ dịch vụ `play_on_players`
nhận `facebook`, danh sách khả năng mỗi loa quảng bá cũng có `facebook` — chỉ mỗi thẻ
còn gắn cứng.

### Không đổi — và đây là chủ ý

Hai chỗ khác cũng chỉ có `youtube` với `zing` nhưng **cố tình giữ nguyên**: công cụ nhạc
của trợ lý (`llm_api.py` ở tích hợp, `nhac_chat.py` ở c2a). Hai công cụ ấy nhận **từ
khoá** để bot tự tìm bài, còn Facebook chỉ tra được khi có **link cụ thể**. Mở ra chỉ
sinh ra lỗi khó hiểu khi người dùng nhờ bot "mở bài gì đó trên Facebook".

## 0.26.0 - 2026-09-19

### Fixed — tích hợp còn NĂM chỗ chặn nguồn Facebook, nay đã mở hết

Bản 0.24.0–0.25.1 thêm nút Facebook vào thẻ nhưng **chính tích hợp vẫn chặn**. Tôi chỉ
sửa cửa chặn của đường luồng rồi tưởng xong; thực tế còn năm chỗ nữa, mỗi chỗ hỏng một
kiểu và **không chỗ nào báo đúng nguyên nhân**:

- `http.py` — cửa chặn của **đường tìm kiếm** (khác cửa của đường luồng). Đây là chỗ
  chặn thẳng thao tác dán link: yêu cầu không bao giờ tới được máy phát.
- `playback.py` — danh sách nguồn mỗi loa quảng bá. Thiếu Facebook thì khi phát ra loa,
  bộ lọc loại **sạch mọi loa** rồi báo "loa không hỗ trợ nguồn" — sai hẳn nguyên nhân.
- `services.py` — lược đồ của dịch vụ phát ra loa, thẻ gọi chính dịch vụ này.
- `actions.py` — cửa chặn nguồn, **và** một nhánh gửi tới loa. Nhánh cuối của hàm là
  đường YouTube gốc chạy theo danh sách lời gọi dựng sẵn cho từng thiết bị; Facebook
  rơi vào đó thì danh sách rỗng nên **không gửi gì và cũng không báo lỗi**. Nay Facebook
  đi chung nhánh với Zing — cùng hình dạng "luồng chuyển tiếp đã ký".

**Bài học ghi lại:** thêm một nguồn phát không phải sửa một chỗ. Lần sau phải `grep`
toàn bộ tích hợp tìm mọi danh sách nguồn **trước** khi tuyên bố xong, thay vì chỉ dò
trong những tệp mình đang mở.

Riêng công cụ tìm nhạc của trợ lý (`llm_api.py`) **cố ý chưa mở** cho Facebook: công cụ
đó nhận *từ khoá*, còn Facebook chỉ nhận link dán vào — mở ra chỉ sinh lỗi mơ hồ.

### Changed — add-on lên 0.9.0

Mã Facebook đã nằm trong add-on từ mấy bản trước, **nhưng tôi quên tăng số phiên bản**
trong `youtube_player/config.yaml`. Supervisor chỉ mời cập nhật khi số đó đổi, nên máy
nào dùng add-on vẫn chạy bản cũ dù kho đã có mã mới. Nay 0.9.0, và dòng mô tả add-on đã
kể cả Facebook.

## 0.25.1 - 2026-09-19

### Fixed — ô tìm kiếm nay nói rõ vì sao hỏng

Chủ máy dán link Facebook và chỉ thấy *"Không thể tìm kiếm lúc này"* — câu chung chung
ấy nuốt mất thông tin duy nhất giúp truy nguyên. Đo được nguyên nhân thật: máy phát trả
`invalid_search_source`, tức **máy phát chưa biết nguồn Facebook**, không phải link sai.

Nay thẻ dịch thẳng mã lỗi của máy phát thành câu tiếng Việt nói rõ phải làm gì — ví dụ
*"Máy phát chưa hỗ trợ nguồn này — hãy cập nhật add-on"*, hoặc *"Nguồn Facebook chỉ
nhận LINK dán vào"*, hoặc *"Không đọc được link chia sẻ này — Facebook có thể đã đổi
trang"*. Mã lạ thì hiện nguyên mã thay vì giấu đi.

**Lưu ý về thứ tự cập nhật:** nút Facebook nằm ở thẻ, còn phần biết đọc link Facebook
nằm ở **máy phát**. HACS chỉ cập nhật tích hợp và thẻ, nên máy phát phải cập nhật riêng
thì nguồn Facebook mới chạy. Đây là chỗ bản 0.24.0 phát hành sớm hơn phần phía sau.

## 0.25.0 - 2026-09-19

### Added — xem video Facebook trên thẻ (nốt nửa còn lại)

Bản 0.24.0 mới nghe được. Nay xem được hình, và **nghe với xem vẫn là hai đường
riêng** đúng như chủ máy chốt: tiếng ra loa (hoặc ra máy đang mở thẻ), hình chiếu trên
thẻ và luôn tắt tiếng — không đẻ thêm lối phát tiếng thứ hai để rồi chồng tiếng.

Cách làm khác hẳn YouTube, vì Facebook **không cho nhúng** trình phát: thẻ xin máy phát
một địa chỉ luồng rồi chiếu thẳng vào phần tử `<video>` sẵn có. Nhờ dùng lại đúng cơ
chế ấy, thanh tiến độ, nút phát/dừng và **tua** chạy được ngay mà không phải viết thêm
gì — phần đọc mốc thời gian và phần gửi lệnh tua vốn đã ưu tiên phần tử video thật.

**Một cửa vào, không vá theo danh sách.** Nhánh Facebook đặt ngay đầu hàm mở hình. Thẻ
có **12 chỗ** gọi hàm này (hàng kết quả, hàng đợi, nút xem, khôi phục phiên…); vá từng
chỗ thì sót một là bấm vào đó hỏng, mà lỗi lại hiện ra ở nơi khác hẳn.

### Đã kiểm được gì, và chưa kiểm được gì

Nói thẳng để khỏi hiểu nhầm:

- **Đã kiểm:** cú pháp, chú thích cân 206/206, đấu nối đếm bằng grep (cửa rẽ nhánh có
  đúng một, không chỗ gọi nào bị bỏ lại), thẻ dựng sạch không lỗi JavaScript, 90 + 4
  phép kiểm máy phát và 56 + 17 phép kiểm tích hợp đều đạt. Phía máy phát, luồng hình
  đã đo trên dữ liệu thật: mp4 gộp sẵn, hình h.264 kèm tiếng AAC, tới 1080p.
- **Chưa kiểm được từ đây:** một lượt xem thật đầu-cuối. Việc đó cần Home Assistant
  thật cùng add-on đang chạy, nên **máy của chủ máy mới xác nhận được**.

## 0.24.0 - 2026-09-19

### Fixed — bấm đĩa không còn dừng nhạc

Chủ máy báo ngay: *"dừng đĩa lại dừng cả nhạc là sao"*. **Tôi hiểu sai yêu cầu.** Câu
gốc là "đĩa quay hay dừng bằng cách kích vào" — chỉ nói về **cái đĩa**, mà tôi lại nối
nút đĩa vào lệnh phát/dừng nhạc.

Nay bấm đĩa chỉ ghìm hoặc thả cho đĩa quay lại, và **không đụng tới nhạc**. Nhạc vẫn
chạy tiếp; nút phát/dừng nhạc vẫn ở hàng dưới như cũ. Dừng thì đĩa đứng im đúng góc
đang quay, không bật về vị trí đầu.

### Added — nguồn Facebook: NGHE được (chưa xem được hình)

Thêm nút **Facebook** cạnh YouTube và Zing MP3. Dán link video Facebook vào ô tìm
kiếm: dạng `/reel/…`, `/watch/?v=…`, `/…/videos/…`, **và cả link chia sẻ**
`/share/v/…` — thẻ tự lần ra mã video rồi phát.

Nói rõ giới hạn để khỏi hiểu nhầm:

- **Chỉ nghe**, chưa xem được hình trên thẻ. Máy phát đã giải được cả luồng hình
  (đo được: mp4 gộp sẵn, hình h.264 kèm tiếng AAC, tới 1080p), nhưng phía thẻ chưa
  nối đường xem, nên thẻ không mời bạn bấm xem ở bất cứ đâu.
- **Chỉ nhận link dán vào**, không tìm theo từ khoá: Facebook không có đường tìm kiếm
  công khai để gọi, hứa suông chỉ sinh lỗi mơ hồ.
- Đường đọc **link chia sẻ** là đường dự phòng không bền: nó đọc một trường nội bộ
  không có tài liệu của trang Facebook, nên Facebook đổi trang là hỏng — và khi hỏng
  nó báo rõ chứ không lặng lẽ thành "không tìm thấy bài nào".

### Fixed — hàng chọn nguồn gác theo sai thứ, nên bị cắt chữ

Hàng chọn nguồn quyết định số cột theo **bề rộng của cả thẻ**. Nhưng ở bố cục hai cột,
hàng ấy nằm trong cột phải — đo 19/09/2026: thẻ rộng 860px thì cột phải chỉ **337px**,
tức **hẹp hơn cả thẻ trên điện thoại** (374px). Hậu quả: thẻ rộng thì nó bung ra bốn
cột dù chỗ thật sự chỉ đủ hai, và chữ "YouTube" bị chính nút của nó cắt cụt.

Nay chính cột chứa nó là khung đo: mặc định hai cột, chỉ bung bốn khi cột thật sự rộng
trên 460px.

## 0.23.0 - 2026-09-19

### Added — bấm vào đĩa để phát hoặc dừng

Chủ máy: *"Đang dừng kích vào quay tròn, đang quay thì kích vào dừng đúng vị trí đó"*.

- Bấm (hoặc chạm) vào đĩa gọi **đúng cùng một hàm** với nút phát/dừng — một việc thì
  một chỗ, tách ra hai nơi là mầm lệch về sau.
- **Dừng đúng vị trí**: hiệu ứng quay luôn gắn sẵn, chỉ bật/tắt bằng
  `animation-play-state`. Nếu gỡ hẳn hiệu ứng lúc dừng thì ảnh bật ngược về góc 0 —
  đó chính là chỗ dễ làm sai.
- Đĩa là một nút thật: đi tới được bằng phím Tab, bấm được bằng Enter hoặc dấu cách,
  và có nhãn cho trình đọc màn hình.

## 0.22.2 - 2026-09-19

### Sửa lại kết luận Facebook — LẦN THỨ HAI, và lần này có bằng chứng ngược hẳn

Bản 0.22.1 kết luận "bài viết này không lấy được ẩn danh từ máy chủ". **Sai.** Chủ máy
gửi cùng nội dung đó dưới dạng địa chỉ reel, và nó lấy được sạch sẽ:

- Bóc luồng thành công: thời lượng 148,8 giây, có bản hình tới 1920×1080.
- **Có luồng tiếng riêng**: `mp4a.40.5`, ~73 kbps, 48 kHz — tức đủ để phát ra loa, chứ
  không phải chỉ có hình.
- Máy chủ phục vụ luồng: `video-hkg1-2.xx.fbcdn.net`.
- Trang nhúng: 206.373 byte và có `hd_src` (mốc so sánh: trang có nguồn phát ~190 nghìn
  byte, trang bị từ chối ~50 nghìn byte).

Nguyên nhân thật của mọi lần hỏng trước: tôi lấy **mã bài viết** (`story_fbid`,
`1135095972510953`) đem đi hỏi như thể nó là **mã video**. Mã video thật là
`1807802260572674`. Không hề có chuyện đòi đăng nhập, cũng không có chuyện thiếu quyền
xem — chỉ là hỏi sai mã, rồi dựng một kết luận về quyền xem lên trên dấu hiệu đó.

**Lớp lỗi, ghi lại để khỏi lặp:** suy từ một thông báo lỗi ra nguyên nhân, mà không
kiểm chứng rằng mình đã đưa đúng dữ liệu đầu vào. Thông báo "chỉ dành cho người dùng đã
đăng ký" là câu Facebook trả lời cho **một mã không tồn tại dưới dạng video**, không
phải câu trả lời về bài viết của chủ máy.

### Changed — dòng báo lỗi khi dán link không đọc được

Bỏ câu "link Facebook đòi đăng nhập nên không phát được" — câu đó sai. Nay nói đúng
hiện trạng: ô này chỉ nhận link YouTube, còn Facebook và Zing thì **máy phát chưa có
nguồn tương ứng**, tức là thiếu tính năng chứ không phải bị chặn.

### Chưa làm — nguồn Facebook cho máy phát

Đã đo được là khả thi và biết rõ khuôn mẫu: máy phát phân nhánh theo nguồn trong
`validate_stream_target`, mỗi nguồn có một danh sách máy chủ hợp lệ riêng
(`YOUTUBE_STREAM_HOSTS`, `ZING_CDN_HOSTS`) và một hàm giải luồng riêng theo cùng một
hình dạng. Thêm Facebook nghĩa là: thêm `fbcdn.net` vào danh sách cho phép, thêm một
nhánh nguồn, thêm một hàm giải luồng theo khuôn `resolve_youtube_audio`, và dạy đường
tìm kiếm nhận link Facebook. Đụng cả máy phát, tích hợp lẫn thẻ — chờ chủ máy quyết.

## 0.22.1 - 2026-09-19

### Sửa lại một khẳng định SAI trong ghi chú 0.22.0 (link Facebook)

Bản 0.22.0 viết rằng video Facebook chủ máy gửi "đòi tài khoản đã đăng nhập, không
phải nội dung công khai". **Khẳng định đó mạnh hơn bằng chứng.** Chủ máy gửi ảnh chụp
điện thoại: trình duyệt **không đăng nhập** vẫn xem và nghe được bài viết đó bình
thường. Bằng chứng tôi có lúc ấy chỉ là *công cụ bóc luồng trên máy chủ bị từ chối* —
tôi đã suy từ đó ra kết luận về quyền xem của video, và đó là suy diễn sai.

Đã đo lại đầy đủ. Những gì kiểm chứng được:

- **Phép đối chứng chạy đúng**: một video Facebook công khai khác bóc luồng thành công
  từ chính máy chủ này (ra tên bài và thời lượng). Vậy **không** phải chặn theo vùng,
  **không** phải thiếu hỗ trợ Facebook, **không** phải máy chủ mất đường ra Internet.
- **Không phải do phần mềm cũ**: cài thẳng từ kho mã nguồn vẫn ra đúng bản mới nhất, và
  bản mới nhất cho cùng kết quả. Giả thuyết "bộ bóc lạc hậu" đã thử và bị bác.
- **Cookie khách có thật**: túi cookie chứa `fr` và `sb` do Facebook cấp; phép thử kèm
  cookie khách là hợp lệ và vẫn bị từ chối. (Lần đầu tôi đếm nhầm số dòng rồi tưởng túi
  rỗng.)
- **Trình phát nhúng của chính Facebook** in ra màn hình: *"Video unavailable — This
  video may no longer exist, or you don't have permission to view it."*

Kết luận đúng với bằng chứng: **bài viết này không lấy được ẩn danh từ máy chủ, trong
khi điện thoại chủ máy xem được.** Khác biệt nằm ở mạng và ở phiên khách mà Facebook
cấp cho một trình duyệt điện thoại thật — thứ không tái hiện được trên máy chủ. Chưa
xác định được cách lấy nội dung này về máy chủ mà không mượn phiên đăng nhập.

Không có thay đổi mã nguồn nào trong bản này; chỉ sửa lại hồ sơ cho đúng sự thật.

## 0.22.0 - 2026-09-19

### Changed — khung sóng nhạc trong suốt, bỏ viền

Khung nghe bên ngoài đã có viền và nền riêng; lồng thêm một khung nữa bên trong là
viền trong viền. Nay sóng nhạc và bốn nút nằm thẳng trên nền ảnh bài hát.

### Added — dán link video để gắn thẳng vào mục gợi ý

Nút thứ ba trong hàng công cụ của khối gợi ý (biểu tượng mắt xích). Dán link, thẻ đọc
link rồi gắn bài vào mục đang mở — hoặc mục đầu tiên nếu mục đang mở là mục dựng sẵn.

Thẻ **không tự bóc link**: nó gửi nguyên văn vào đúng đường tìm kiếm sẵn có, vì máy
chủ đã biết đọc link YouTube. Đo được các dạng nhận đúng: `watch`, `youtu.be`,
`shorts`, `embed`, và `watch` kèm tham số playlist (lấy đúng một bài, không kéo cả
playlist). Chép logic bóc link sang thẻ sẽ thành hai chỗ phải sửa mỗi lần YouTube đổi
dạng link.

### Không làm được — link Facebook

Đo trên link chủ máy gửi: mọi dạng địa chỉ đều bị từ chối. Xem mục 0.22.1 bên trên —
cách diễn giải ban đầu ở đây đã sai và được sửa lại ở đó.

Máy phát còn khoá cứng theo nguồn (mỗi nguồn một danh sách máy chủ hợp lệ riêng), nên
thêm Facebook kéo theo một nguồn mới và một danh sách CDN mới, chứ không phải một dòng.

Link Zing dán vào ô này cũng chưa nhận — đường tìm kiếm hiện chỉ đọc link YouTube.

## 0.21.0 - 2026-09-19

### Changed — khối "chỉ nghe nhạc" dựng lại theo thẻ phicomm-r1

Chủ máy gửi tệp `phicomm-r1-card.js` để tham khảo. Ba điểm học được, và cả ba đều là
thứ bản cũ làm sai:

- **Hàng nút nằm BÊN TRONG khung sóng nhạc**, khung cao cố định. Bản cũ để sóng và nút
  thành hai khối rời, mỗi khối một nền, nên nút hay bị đẩy lệch và sóng cao lấn.
- **Ảnh bìa là một CỘT THẬT của lưới**, không phải lớp phủ. Hai lần trước tôi đặt đĩa
  bằng `position: absolute` nên nó tràn ra đè lên chữ.
- **Nền gần như không làm mờ** (blur 0,4px) — thứ đẩy ảnh xuống làm nền là **giảm sáng
  còn 58%** cộng một lớp tối dần. Bản cũ làm mờ rất mạnh mà vẫn sáng, nên chữ đè lên
  không đọc nổi.

### Changed — tên bài, nguồn phát và ảnh nền nằm chung một khung với đĩa

- Tên bài, ca sĩ và **nhãn nguồn** (YouTube / Zing MP3 / Link) chuyển vào ngay đầu khối
  nghe. Ô "Đang phát" tách riêng ở cột phải đã ẩn đi.
- Ảnh bài hát làm nền cho chính khung đó.
- Nhãn nguồn đặt ở **một** chỗ trong mã, không rải ra ba nhánh (xem video / nghe trên
  máy / phát ra loa) — ba nhánh đều thoát sớm nên rải ra là kiểu chắc chắn sót.

### Added — danh sách gợi ý thu gọn được, mặc định đóng

Chủ máy: *"List gợi ý có thể xoá và kích mới ra, không đưa hết ra màn"*. Đóng lại chỉ
còn hàng tiêu đề kèm mũi tên; bấm mũi tên là mở. Nhớ theo từng máy và từng thẻ, cùng
cách đã dùng cho kiểu bố cục và "nghe khi tắt màn hình".

### Changed — toàn màn hình: thẻ không vẽ gì lên video nữa

- Bỏ nốt nút đóng khi **toàn màn hình thật**. Đường ra không cần nút của thẻ: phím Esc,
  và nút thu nhỏ của chính YouTube.
- Thoát bằng nút của YouTube nay về **thẳng thẻ**, không dừng ở trạng thái phủ kín
  trang như trước.
- Kiểu phủ trang (máy không có element fullscreen, ví dụ iPhone) **vẫn giữ nút đóng**:
  ở đó không có phím Esc, bỏ nốt là nhốt người dùng trong màn hình không lối ra.

### Fixed — thẻ tràn ngang ở màn hình hẹp

Bố cục một cột dùng `grid-template-columns: 1fr`, mà `1fr` là viết tắt của
`minmax(auto, 1fr)` — mức tối thiểu `auto` bằng chiều rộng nội dung tối thiểu, nên chỉ
cần một khối con không co được là cột phình to hơn khung chứa. Đo ở bề rộng thẻ 400px:
trước khi sửa có **43 phần tử vượt mép thẻ**, đứng đầu là khối phát rộng 497px so với
thẻ 461px; sau khi sửa còn **0**.

### Fixed — mảng trống lớn giữa khối phát và thanh loa (màn hình rộng)

Cột phải cao cố định 640px, hai hàng lưới tự chia nhau phần dư nên hàng trên bị kéo
giãn. Trước đây danh sách gợi ý lấp đầy cột phải nên không lộ; từ lúc gợi ý đóng sẵn
thì hở hẳn. Nay phần dư dồn hết xuống hàng dưới.

## 0.20.12 - 2026-09-18

### Fixed — nút của card không còn che nút cài đặt của YouTube

- Hàng nút của card đặt ở **cạnh phải**, mà YouTube cũng đặt cụm bánh răng, phụ đề và
  phóng to ở đúng cạnh đó. Khi xoay ngang thì cả khung phát quay 90° nên hàng nút của
  card quay theo và rơi thẳng vào cụm ấy.
- Nay hàng nút chuyển sang **cạnh trái**, không còn tranh chỗ.

### Chưa sửa được — video mở ra nhưng đứng im

Nói thẳng: tôi **chưa tìm ra**, và không vá mò vào một chuỗi đang đúng.

- Đã lần hết đường đi khi **không chọn loa**: bước mở khoá bộ phát **có** chạy ngay
  trong cú chạm (trước khi mở video), hẹn giờ dự phòng 2,5 giây **có** được đặt, hàm
  kiểm tra kết luận "bị chặn" đúng khi trình phát còn ở trạng thái chưa khởi động, và
  nhánh chuyển tiếng sang máy **không** có chỗ thoát sớm sai.
- Đọc trên giấy thì chuỗi này phải chạy. Nghĩa là lỗi nằm ở thứ không nhìn thấy được
  từ mã — cần bằng chứng lúc chạy thật.
- **Cách lấy bằng chứng:** mở card trên trình duyệt máy tính, bật bảng điều khiển dành
  cho nhà phát triển (phím F12), chuyển sang tab Console, rồi bấm xem một video. Chụp
  lại những dòng báo lỗi hiện ra — nhất là dòng nào có chữ `play()` hoặc `NotAllowed`.
  Một ảnh chụp đó sẽ chỉ đúng chỗ hỏng nhanh hơn tôi đọc mã cả buổi.

## 0.20.11 - 2026-09-18

### Fixed — nút xoay ngang chưa từng hiện

- Chỗ gỡ thuộc tính ẩn cho các nút video chỉ liệt kê **bốn** nút (tai nghe, phóng to,
  toàn màn, đóng) — **thiếu nút xoay ngang**, trong khi thẻ của nó khai sẵn `hidden`.
  Nghĩa là nút ấy **chưa bao giờ hiện**, không phải mới mất.
- Đây là thiếu sót có sẵn chứ không do lần sửa nào gây ra. Luật ẩn nút khi máy đã nằm
  ngang vẫn giữ: lúc đó xoay thêm là vô nghĩa.

### Fixed — phóng to (chưa toàn màn) vẫn thấy dòng tên bài

- Lớp chữ đè trên ảnh chỉ được ẩn khi **đang mở video**. Phóng to lúc **chỉ nghe nhạc**
  thì video không mở, nên điều kiện cũ không với tới và tên bài lọt vào giữa màn hình.
- Nay ẩn theo cả trạng thái phóng to lẫn toàn màn hình, chặn ở **cả hai phía** — điều
  kiện trong JavaScript và một luật CSS, phòng khi JavaScript chưa kịp cập nhật.

### Changed — toàn màn hình chỉ còn đúng nút đóng

- Ở bản 0.20.4 tôi cố ý giữ hàng biểu tượng làm đường thoát và có ghi "muốn ẩn nốt thì
  bảo". Nay bỏ hết, **chỉ chừa nút đóng**.
- Giữ lại đúng nút đó là có lý do: bỏ sạch thì lối ra chỉ còn nút của YouTube và phím
  Esc — mà trình phát đang là thứ trục trặc, không nên để đường thoát duy nhất phụ
  thuộc vào chính nó.

### Đang tìm — video mở ra nhưng đứng im

- Chưa sửa trong bản này. Trong mã đã có sẵn bộ máy cho đúng triệu chứng ấy, kèm ghi
  chú dẫn lời chủ máy ngày 15/09, nên nhiều khả năng là hạn chế của trình duyệt: nhiều
  máy chỉ cho phát sau khi người dùng chạm thẳng vào khung video. Tôi đang đo lại đường
  bắt tay và tham số nhúng trước khi kết luận.

## 0.20.10 - 2026-09-18

### Added — tự chỉnh độ mờ ảnh nền trong cấu hình card

- Trình sửa card → **Nền → Độ mờ ảnh nền (px)**, kéo từ 0 tới 30. Mức 0 là ảnh bìa sắc
  nét hoàn toàn. Mặc định vẫn 6px như bản trước, nên thẻ chưa chỉnh gì thì không đổi gì.
- Giá trị bị chặn trong khoảng 0–30 ngay khi áp: ngoài khoảng đó không làm hỏng card
  nhưng cho ra thứ vô dụng — 0 thì chữ khó đọc trên ảnh, quá 30 thì chỉ còn một mảng màu.

### Changed — vạch thời gian ra ngoài vùng mờ, sóng cao hơn, nút xuống thấp

- **Vạch khoảng thời gian nay nằm ngoài lớp nền mờ.** Lớp nền dừng lại phía trên nó thay
  vì phủ kín khu phát.
- **Sóng nhạc cao hơn hẳn**: 26px → 40px (màn hình hẹp 20px → 32px).
- **Hàng nút tụt xuống**, tách rõ khỏi sóng nhạc.

### Một con số tôi phải nói rõ là ƯỚC LƯỢNG

- Khoảng chừa để vạch thời gian thoát khỏi vùng mờ đang đặt **34px**. Tôi không đo được
  chiều cao thật của hàng đó — CSS không có cách hỏi "hàng này cao bao nhiêu" để tự trừ.
  Lệch thì sẽ thấy ngay: hoặc vạch còn dính rìa mờ, hoặc có một dải trống mỏng phía dưới.
  Chỉnh lại chỉ là đổi một con số.

## 0.20.9 - 2026-09-18

### Fixed — hết cái khung rỗng dưới khu phát

Đây là **lỗi tôi tự tạo ra ở bản 0.20.7**, không phải lỗi có sẵn.

- Khi bỏ tên bài trùng lặp ở 0.20.7, tôi chỉ ẩn **dòng chữ** bên trong mà để lại **cái
  khung bọc nó**. Khung ấy có viền và khoảng đệm riêng (`padding: 14px 16px`,
  `border: 1px solid`), nên còn trơ một hộp có viền không chứa gì — thấy rõ trong ảnh
  chủ máy gửi lúc 22:58.
- Nay ẩn **cả khối**. An toàn vì đã đo trước: bên trong nó chỉ có ảnh bìa nhỏ, tên bài
  và dòng thông tin — cả ba đều đã có mặt trên lớp chữ đè trên ảnh.
- Điều kiện ẩn giữ nguyên là **"lớp chữ đang hiện"**, nên lúc chưa phát gì thì khối vẫn
  hiện đủ câu "Chưa phát bài nào — chọn một bài trong kết quả".

### Bài học tôi ghi lại cho chính mình

- Ẩn phần ruột mà quên cái vỏ là kiểu sửa **đẻ ra lỗi mới**: người dùng báo "thừa tên
  bài", tôi bỏ chữ đi và tạo ra một hộp rỗng còn khó hiểu hơn. Lần sau ẩn thứ gì thì
  phải xem cái bọc nó có tự vẽ viền, đệm hay nền hay không.

## 0.20.8 - 2026-09-18

### Changed — vạch tiến độ xuống dưới cùng, không còn kẹp giữa

- Thanh tiến trình vốn nằm **giữa** sóng nhạc và hàng nút. Chủ máy chốt: *"vạch tiến độ
  bài hát đang ở giữa"*, và ảnh mẫu cũng để nó **dưới cùng**. Nay thứ tự là sóng nhạc →
  hàng nút → thanh tiến trình.
- Khung kính bọc sóng nhạc và hàng nút vẫn liền mạch, vì hai khối đó vẫn cạnh nhau —
  thanh tiến trình xuống dưới cả khung chứ không chen vào giữa.

### Vì sao đổi trong bản dựng thẻ chứ không dùng CSS

- Cách gọn nhất trông có vẻ là thuộc tính `order` của CSS. Nhưng `.stage` khai
  `display: contents` và `.player` là khối thường, **không phải khung linh hoạt** — nên
  `order` sẽ **không có tác dụng gì cả**, và đó là kiểu hỏng lặng lẽ: viết xong thấy
  không đổi gì mà chẳng có lỗi nào báo.
- Đây là lần thứ hai `display: contents` của `.stage` suýt làm tôi mất công: lần trước
  là khi định vẽ lớp nền mờ lên chính nó.

## 0.20.7 - 2026-09-18

### Changed — khung chỉ nghe gọn lại còn khoảng một nửa

Bốn điểm chủ máy nêu sau khi xem bản 0.20.6 chạy thật.

- **Bỏ hàng tên bài trùng lặp.** Cùng một bài mà tên hiện hai lần — một lần đè trên ảnh,
  một lần ở hàng dưới. Nay hàng dưới tự ẩn **khi và chỉ khi** lớp chữ trên ảnh đang
  hiện. Làm theo dấu hiệu đó chứ không theo "đang ở chế độ chỉ nghe", vì cách sau sẽ
  nuốt luôn dòng "Chưa phát bài nào — chọn một bài trong kết quả" lúc chưa phát gì, tức
  lấy mất câu chỉ đường đúng lúc cần nhất.
- **Tên bài còn 2 dòng** thay vì 3, chữ nhỏ hơn một bậc. Ba dòng chữ đậm cỡ lớn là phần
  chiếm chiều cao nhiều nhất; tên dài hơn thì cắt bằng dấu ba chấm.
- **Đĩa nhỏ lại** và các khoảng đệm quanh sóng nhạc với hàng nút rút bớt.
- **Nền bớt nhoè**: giảm độ mờ, nhấc sáng lên, và lớp phủ tối mỏng đi. Trước đây hai lớp
  làm mờ chồng nhau nên ảnh bìa thành một mảng xám.

### Fixed — đĩa che mất số phút giây

- Thanh tiến trình chưa được chừa chỗ cho đĩa như sóng nhạc và hàng nút, nên đĩa đè lên
  số thời gian bên trái. Nay cả ba dùng **chung một công thức** khoảng chừa, tính thẳng
  từ cỡ đĩa — hai bên không thể lệch nhau khi màn hình đổi kích thước.

## 0.20.6 - 2026-09-18

### Fixed — bấm phát bài đầu bị nhảy về 0 giây hai ba lần

Đây là **lỗi tôi tự gây ra ở bản 0.20.2**, không phải lỗi có sẵn.

- Ở 0.20.2 tôi thêm bộ nhận biết "chủ máy tự tua trong khung YouTube": thấy thời gian
  trình phát báo về lệch quá 2,5 giây so với nhịp chạy đều thì coi là anh vừa kéo thanh,
  rồi **kéo loa và tiếng trên máy chạy theo mốc đó**.
- Nhưng lúc mới bấm phát, mọi bước nhảy đều là bình thường chứ không phải anh tua:
  - **Mốc của bài trước không được xoá.** `_openVideo` đặt lại tên bài, loa, chế độ
    tiếng — nhưng không đụng tới đồng hồ. Bài mới thừa hưởng mốc bài cũ, nên card suy ra
    một con số lớn trong khi trình phát mới báo về gần 0.
  - **Mở video từ giây đang nghe** cũng làm trình phát nhảy một quãng lớn và hợp lệ.
- Hậu quả: card hiểu nhầm thành "vừa tua về 0" và **tự gửi lệnh nhảy về 0** cho loa lẫn
  tiếng trên máy, lặp lại theo mỗi bản tin trình phát gửi trong lúc khởi động — đúng
  "hai, ba lần" rồi mới yên.

### Sửa theo nguyên tắc, không vá triệu chứng

- **Xoá đồng hồ khi mở bài mới**, diệt tận gốc việc thừa hưởng mốc cũ.
- **Chỉ tin bước nhảy khi trình phát chạy ổn định**: trạng thái phải là "đang chạy", và
  phải qua 5 giây kể từ lúc mở. Lúc đang nạp hoặc chưa khởi động thì thời gian báo về
  không đáng tin, nên không được dùng nó để ra lệnh cho loa.
- Tính năng tua trong khung YouTube vẫn giữ nguyên: kéo thanh của YouTube khi bài đã
  chạy ổn định thì loa vẫn đi theo anh như ở 0.20.2.

## 0.20.5 - 2026-09-18

### Fixed — chế độ chỉ nghe ở 0.20.4 gần như không hiện gì trên điện thoại

Đây là lỗi của bản trước, và nguyên nhân nằm trong chính CSS tôi viết:

- **Tôi tự đặt luật ẩn đĩa tròn khi card hẹp dưới 520px.** Điện thoại rơi đúng vào
  khoảng đó, nên đĩa **không bao giờ hiện** trên thiết bị dùng thật. Nay đĩa hiện ở mọi
  bề rộng, cỡ **co theo bề ngang card** thay vì đặt cứng.
- **Ảnh nền mờ quá tay**: `blur(18px)` kèm giảm sáng còn một nửa làm ảnh thành vệt xám,
  nhìn không ra ảnh bìa. Nay mờ nhẹ hơn và sáng hơn, thêm một lớp tối mỏng để chữ vẫn
  đọc được mà ảnh vẫn ra hình.
- Khoảng chừa chỗ cho đĩa nay **tính theo đúng công thức cỡ đĩa**, nên hai bên không thể
  lệch nhau khi màn hình đổi kích thước.

### Added — đúng bố cục mẫu

- **Tên bài và tên kênh nằm đè trên ảnh nền**, kèm **nhãn nguồn** (YOUTUBE / ZING MP3)
  ở góc trên-phải.
- **Sóng nhạc và hàng nút gộp thành một khung kính liền**, đặt bên phải đĩa.
- Đĩa có lỗ giữa cho ra dáng đĩa than, và chỉ quay khi đang phát.

### Cách làm, để không phá thứ đang chạy

- Lớp chữ này là **thẻ mới thêm vào**, không phải chuyển khối tên bài cũ sang. Đo trước
  khi làm: có **sáu luật CSS** và **ba chỗ JavaScript** đang bám vào đường
  `.np-zone .now…`; chuyển là phá cả sáu.
- Nội dung lấy **thẳng từ dòng tên bài vừa được đặt**, không dựng lại từ dữ liệu — hai
  nơi hiển thị cùng một bài thì không được phép lệch chữ.
- Điểm nối đặt trong `_showCover`, vì cả hai nhánh (nghe trên máy này, phát ra loa) đều
  kết thúc bằng lời gọi đó.
- **Không vẽ nút trái tim** như trong ảnh mẫu: card chưa có tính năng yêu thích, thêm
  vào sẽ là một nút bấm không làm gì.

## 0.20.4 - 2026-09-18

### Added — chế độ chỉ nghe có diện mạo riêng

- **Ảnh bìa bài hát làm nền mờ** tràn kín khu phát, và một **đĩa tròn** mang chính ảnh
  ấy, quay đều khi đang phát và đứng im khi tạm dừng.
- **Sóng nhạc và hàng nút nổi lên trên nền mờ**, hàng nút nằm trong một khung kính mờ.
- **Thanh tiến trình chuyển sắc** từ màu nhấn phụ sang màu nhấn chính, có **núm tròn**
  ở đầu vệt màu — vừa cho biết đang ở đâu, vừa mời kéo để tua.
- Xem video thì tất cả biến mất, khung hình trở lại nguyên trạng.

### Changed — toàn màn hình nhường hẳn cho trình phát YouTube

- Ở toàn màn hình, card **ẩn thanh tiến trình, hàng nút phát và dải thông tin bài hát**.
  Trình phát YouTube đã có đủ thanh tua và nút của nó; bày thêm một bộ nữa chỉ che hình.
- **Giữ lại hàng biểu tượng nhỏ ở góc trên-phải** (tai nghe, thu nhỏ, toàn màn hình,
  đóng). Đó là đường thoát chắc chắn của card, và nó vốn tự mờ đi khi để yên vài giây,
  chạm một cái là hiện lại. Muốn ẩn nốt thì nói, tôi bỏ.

### Về việc "bấm nút thu nhỏ của YouTube để thoát về card"

- Phần này **đã có sẵn trong mã từ trước**, không phải thêm mới: khi lớp toàn màn hình
  của YouTube xuất hiện bên trong khu phát mà card đang giữ toàn màn hình, card thoát
  luôn khỏi toàn màn hình. Tôi cố ý **không viết lại** — lắp thêm một đường thứ hai làm
  cùng việc là cách chắc chắn để hai bên đá nhau.
- Nếu sau khi cài bản này mà vẫn không thoát được, xin báo lại để tôi dựng đúng tình
  huống mà bắt lỗi, thay vì sửa mò vào đoạn đang chạy đúng.

### Những thứ phải làm kèm, thiếu là hỏng âm thầm

- **`.player` phải làm mốc định vị.** Lớp nền mờ không thể tô lên `.stage` vì `.stage`
  là `display: contents` — nó không phải một hộp thật, các con của nó do `.player` xếp.
  Đã kiểm trước khi thêm mốc: thứ duy nhất neo tuyệt đối bên trong là chú thích trên
  khung hình, mà nó neo vào `.video-frame` vốn có mốc riêng, nên không gì lệch chỗ.
- **Rãnh thanh tiến trình phải mở `overflow`.** Nó vốn đặt `hidden`, giữ nguyên thì cái
  núm tròn bị cắt cụt đúng một nửa.
- **Không tái dùng được biến `--poster` sẵn có**, dù nghe như đúng việc: nó chỉ áp cho
  khung hình lúc YouTube từ chối nhúng, và dựng địa chỉ ảnh từ mã video YouTube — tức
  sai với Zing MP3.
- **Ảnh được đặt tại `_showCover`**, điểm nút duy nhất mà cả hai đường phát (nghe trên
  máy này, và phát ra loa) đều đi qua. Nhờ vậy ảnh nền, mặt đĩa và ảnh bìa nhỏ không bao
  giờ lệch nhau.
- **Card hẹp thì bỏ đĩa tròn**: 96px chiếm gần nửa bề ngang điện thoại, giữ lại thì sóng
  nhạc bị đẩy xuống dưới nó. Nền mờ vẫn còn nên vẫn đúng tinh thần.

## 0.20.3 - 2026-09-18

### Added — chỉnh được cả bảng màu, và có bộ màu dựng sẵn

- Thêm **bảy màu chỉnh riêng** bên cạnh hai màu cũ (nền, nhấn): màu nhấn phụ, màu mặt
  thẻ con, màu chữ chính, màu chữ phụ, màu cảnh báo, màu viền.
- Thêm ô **"Bộ màu dựng sẵn"** để chọn một phát ra cả bảng, kèm mục **"Trả về mặc định"**
  xoá sạch màu đã chọn. Mọi ô màu bên dưới **vẫn chỉnh riêng được** như cũ.
- Bộ dựng sẵn đầu tiên — *Than chì · Cam san hô + Xanh cyan*: nền `#202120`, mặt thẻ
  `#303130`, nhấn `#FF7045`, nhấn phụ `#12A8CC`, cảnh báo `#FF4F62`, chữ `#F2F2F2`,
  chữ phụ `#A5A5A5`, viền `#8A642F`.

### Những thứ phải làm kèm, nếu thiếu thì ô chọn màu chỉ là nút bấm giả

- Màu chữ trắng trước đây **ghi cứng ở 16 chỗ** và màu cảnh báo ở 7 chỗ với ba sắc đỏ
  khác nhau. Nay tất cả đi qua biến, **giá trị dự phòng đúng bằng màu cũ** — nên chưa
  chọn màu nào thì card không đổi một chút nào.
- Card gọi các biến giao diện chuẩn của Home Assistant rất nhiều: `--secondary-text-color`
  24 lần, `--divider-color` 14 lần, `--primary-text-color` 9 lần. Nên màu chữ và màu viền
  được đặt đè lên **chính các biến đó**, một chỗ là hơn năm mươi nơi đổi theo.
- Việc đặt đè ấy **chỉ xảy ra khi có màu hợp lệ**. Khai sẵn trong CSS thì lúc chưa chọn,
  giá trị dự phòng sẽ thay giá trị của giao diện đang dùng và làm đổi diện mạo ngoài ý
  muốn — đúng kiểu hỏng âm thầm mà không ai truy ra.
- Bộ màu dựng sẵn ghi **chín khoá trong một lần phát**. Gọi lần lượt thì Home Assistant
  nhận chín sự kiện liên tiếp, mỗi sự kiện mang một bản cấu hình dở dang.

## 0.20.2 - 2026-09-18

### Added — tua được bằng thanh tiến trình

- Bấm hoặc kéo trên thanh tiến trình là **tua tới đúng chỗ đó**. Trước đây thanh chỉ để
  nhìn: tính năng tua **chưa bao giờ được làm**, không phải hỏng.
- Card có ba nguồn thời gian khác nhau — tiếng phát trên máy này, video xem trên thẻ, và
  loa — nên lệnh tua được gửi đúng cho nguồn đang phát. Loa nào không hỗ trợ tua thì card
  **nói thẳng** thay vì gửi rồi im lặng.

### Fixed — tua trong khung YouTube không bị kéo ngược về nữa

- Card vốn lấy loa làm đồng hồ chuẩn và liên tục ép video khớp theo, nên anh vừa kéo
  xong là nhịp đồng bộ kế tiếp lôi về chỗ cũ.
- Nay card **nhận ra anh tự tua**: thời gian trình phát báo về nhảy một quãng lớn so với
  nhịp chạy đều. Gặp vậy thì card giữ nguyên chỗ anh chọn và **kéo loa chạy theo anh**,
  thay vì làm ngược lại.

### Fixed — âm lượng loa

- **Thanh âm lượng nay ghi rõ TÊN LOA nó đang chỉnh**, thay cho chữ "Âm lượng" chung
  chung. Loa đích chỉ đổi khi chạm vào **tên** loa, còn tích ô vuông thì không — hai thao
  tác vốn độc lập theo đúng yêu cầu — nhưng trước đây màn hình không nói loa nào đang
  được chỉnh, nên tích loa B mà thanh vẫn chỉnh loa A thì trông y như báo sai mức.
- **Hết cảnh "kéo xong nhảy về mức cũ".** Bản cũ giữ mức vừa đặt đúng 5 giây rồi thả;
  loa nào báo lại chậm hơn là bị ghi đè bằng giá trị cũ — nên lỗi chỉ xuất hiện *thi
  thoảng*. Nay card chờ tới khi **chính loa đó lên tiếng** mới nhận giá trị mới.

### Changed — dòng chữ mô tả nguồn ở đầu card đã bỏ

- Bỏ theo yêu cầu: nó chiếm nguyên một dòng ngang đầu thẻ chỉ để nhắc lại thứ mà hàng nút
  nguồn ngay bên dưới đã nói.

### Changed — dòng đang phát ghi rõ nguồn

- Dòng thông tin bài hát nay có thêm **"YouTube"** hoặc **"Zing MP3"**.
- Lý do: hàng nút YouTube / Zing MP3 chỉ đổi **nơi tìm kiếm**, **không** đổi bài đang
  phát. Nên đổi tab xong vẫn thấy bài cũ chạy tiếp là đúng, nhưng trước đây card không hề
  nói bài ấy lấy từ đâu, không có cách nào biết.

## 0.20.1 - 2026-09-18

### Changed — ghim bài hát: chọn mục NGAY LÚC ghim, không phải chọn trước khi tìm

- Bấm nút ghim ở một bài trong kết quả tìm, nay **mở bảng chọn mục ngay tại dòng bài
  hát đó** — liệt kê các mục kèm số bài đang có, bấm một cái là xong. Bảng này giống hệt
  bảng "thêm vào playlist" mà anh đã quen, vì nó dùng chung một khuôn.
- **Tạo mục mới ngay trong bảng.** Gõ tên rồi bấm Tạo là mục được tạo và bài được gắn
  vào đó luôn, không phải quay ra khu gợi ý làm trước.
- **Vì sao cách cũ khó dùng.** Nút ghim lấy mục đã chọn sẵn bên khu gợi ý, mà khu đó
  biến mất ngay khi có kết quả tìm kiếm. Nên đúng lúc bấm ghim thì anh không nhìn thấy
  đích đến và cũng không đổi được; nếu chưa chọn gì thì bài **rơi âm thầm vào mục đầu
  tiên**. Tên mục chỉ nằm trong phần chú giải khi rê chuột — điện thoại không hiện ra.
- Nút ghim nay **luôn hiện** với bài YouTube. Trước đây nhà chưa tạo mục nào thì nút
  không hiện, thành ra không có đường bắt đầu.

### Fixed — "Nghe khi tắt màn hình" không còn bị đẩy xuống dòng riêng

- Hàng nút trước đây cho phép xuống dòng, nên trên điện thoại hễ chật là cái nút chữ dài
  bị đẩy hẳn xuống một dòng của riêng nó, trông như lỗi. Nay cụm biểu tượng giữ nguyên
  cỡ, cụm nút chữ được phép co lại và cắt bớt chữ khi chật, nên chúng **luôn nằm chung
  một hàng** ở mọi bề rộng — không phụ thuộc vào việc tôi đoán đúng cỡ màn hình.

### Hai điều cần nói thẳng

- **Logo YouTube trên video thì không bỏ được.** Tham số `modestbranding` từng làm mờ nó
  đã bị YouTube khai tử, chính họ ghi là "sẽ không có tác dụng"; logo và dòng tiêu đề lúc
  tạm dừng là do trình phát của YouTube vẽ, card không với tới được. Muốn không thấy nó
  thì dùng chế độ chỉ nghe.
- **Ảnh anh gửi là bản cũ.** Trong ảnh còn hai ô thả xuống kèm thùng rác, thứ đã bị gỡ
  sạch khỏi 0.20.0. Tôi đã tải file card thẳng từ máy chủ nhà anh và đếm: máy chủ đang
  phục vụ đúng bản mới. Nên phần "còn wave khi xem video" và "thùng rác xuống dòng" là
  do trình duyệt điện thoại còn giữ bản đã lưu đệm — xin anh tải lại trang một lần.

## 0.20.0 - 2026-09-18

### Changed — sóng nhạc và nút điều khiển chuyển lên ngay dưới video

- **Xem video:** nút điều khiển nằm **sát dưới khung hình**, và **sóng nhạc tự ẩn** — đã có
  hình chạy rồi thì sóng trang trí chỉ tốn chỗ.
- **Chỉ nghe nhạc:** khung video ẩn, nên **sóng nhạc chiếm đúng chỗ trống đó** — card gọn
  hơn, không còn một mảng trống. Sóng **giữ nguyên kích thước**, không phóng to theo khung
  video.
- Về kỹ thuật: ba khối (sóng nhạc, thanh tiến trình, nút điều khiển) chuyển từ cột phải
  sang trong khung phát ở cột trái. CSS thuần không làm được việc này vì hai khối nằm ở hai
  nhánh khác nhau của cây.

### Những thứ phải sửa kèm, nếu thiếu là hỏng âm thầm

- **Hiệu ứng sóng nhạc khi đang phát:** lớp `is-playing` vốn đặt trên khối cũ, mà ba luật
  CSS đòi sóng phải nằm **bên trong** khối đó. Chuyển đi là sóng hết sáng lúc đang phát —
  và `node --check` **không bắt được** loại lỗi này. Nay lớp đó đặt lên khối bao chung.
- **Định dạng lúc phóng to / toàn màn hình:** 5 bộ chọn vẫn trỏ vào vị trí cũ. Hai trong số
  đó hoá ra đã **thừa** sau khi chuyển (các nút nay là con của khung phát nên luật sẵn có
  đã bao trùm) nên xoá hẳn; số còn lại đổi sang đường mới.
- Đây là lần chuyển khối **thứ hai** trong ngày, và lần trước đã âm thầm làm hỏng một luật.
  Nên lần này tôi liệt kê trước **29 dòng** phụ thuộc rồi mới sửa, thay vì sửa xong mới dò.

### Fixed — nút xoá gợi ý: hết lỗi hiển thị, và giờ xoá được thật

- **Nút xoá nằm ngay cạnh từng mục.** Trước đây hai ô thả xuống dùng chung hai nút thùng
  rác đặt cuối hàng; hàng hẹp thì một nút bị đẩy xuống dòng riêng, trông đúng như lỗi anh
  chụp. Nay mỗi từ khoá và mỗi mục là một **thẻ nhỏ mang dấu × của riêng nó**, và các thẻ
  **tự xuống dòng** chứ không cuộn ngang — chuột lẫn cảm ứng đều với tới mọi mục.
- **Vì sao trước đây bấm mà không xoá được.** Ô thả xuống luôn mở ở dòng gợi ý "Tìm
  nhanh…", tức giá trị rỗng, nên nút xoá bị khoá. Muốn mở khoá phải chọn một mục, mà vừa
  chọn xong là cả khối gợi ý được vẽ lại và nút xoá biến mất theo. Tức là **không tồn tại
  khoảnh khắc nào** vừa có mục đang chọn vừa còn nút xoá trên màn hình — nên lệnh xoá không
  bao giờ gửi đi được. Dấu × gắn sẵn từng thẻ thì không cần chọn trước, vòng kín đó hết.
- Sửa kèm **hai lỗi CSS phát hiện lúc đo**, cả hai đều sẽ gây lỗi hiển thị y như anh thấy:
  hàng thẻ nhóm đã **mất luật `display: flex`** từ lần đổi giao diện trước (chỉ còn sót một
  luật cuộn mồ côi), và dấu × lẽ ra đỏ thì sẽ ra **màu cam**, vì một luật cũ tô màu cho mọi
  biểu tượng nằm trong thẻ — màu thừa kế luôn thua một khai báo đặt thẳng.

### Cần anh xác nhận

- Phần nhìn tôi **không kiểm được bằng máy**. Xin anh xem giúp ba cảnh: đang xem video
  (nút điều khiển sát dưới hình, không còn sóng), đang nghe nhạc (sóng nằm ở chỗ khung
  video, cỡ như cũ), và khu gợi ý (mỗi từ khoá, mỗi mục có dấu × riêng, bấm là mất hẳn).

## 0.19.1 - 2026-09-18

### Fixed — bản 0.19.0 làm MẤT từ khoá bạn đã tự thêm

- **Hãy bỏ qua 0.19.0, cài thẳng 0.19.1.** Hàm nạp lần đầu ở 0.19.0 **ghi đè** danh sách
  trong kho bằng danh sách mặc định. Nhà nào đã tự thêm từ khoá ở bản trước (lúc chưa có
  cờ `seeded`) thì lần đầu mở 0.19.0 là **mất sạch công đó**.
- Nay nạp lần đầu **GỘP** thay vì ghi đè: giữ nguyên mọi thứ đã có trong kho, chỉ thêm
  những mục mặc định còn thiếu. Nhóm trùng id thì giữ bản của nhà, không ghi đè tên.
- Tôi phát hiện ra khi soi lại kho thật trên máy chủ nhà: `tags` đã có một từ khoá tự thêm
  mà `seeded` thì chưa có — đúng kịch bản sẽ mất dữ liệu. Nay có phép thử dựng lại đúng
  tình huống đó, 8/8 đạt.

## 0.19.0 - 2026-09-18

### Changed — xoá là xoá DỮ LIỆU, không để dấu vết

- Bản 0.18.0 "xoá" mục dựng sẵn bằng cách **ghi tên vào danh sách ẩn** rồi lọc đi. Chủ
  máy nói thẳng là sai, và đúng: tên đã xoá vẫn nằm trong kho mãi mãi. Nguyên nhân gốc là
  danh sách mặc định **nằm cứng trong mã card**, nên không có "dữ liệu" nào để xoá.
- Nay **đảo nguồn sự thật**: lần đầu mở, card đẩy danh sách mặc định **vào kho** (một lần
  duy nhất, có cờ `seeded`). Từ đó **kho là nguồn duy nhất** — card không ghép hằng số
  dựng sẵn vào nữa, và **xoá là xoá thật khỏi dữ liệu**. Không còn khoá `hidden_tags` /
  `hidden_groups` nào.
- Nạp lại lần hai **không hồi sinh** thứ đã xoá; nếu không thì xoá xong tải lại trang là
  thấy mọi thứ quay về, tức xoá vô nghĩa.
- Chưa nạp được (tích hợp bản cũ, hoặc người xem không phải quản trị nên không có quyền
  ghi) thì card vẫn bày danh sách dựng sẵn để dùng được bình thường.

### Changed — "Nghe khi tắt màn hình" về cùng hàng với các biểu tượng

- Hai nút **"Nghe trên máy này"** và **"Nghe khi tắt màn hình"** nay nằm **chung một hàng**
  với sáu biểu tượng điều khiển video (chỉ nghe, xoay, phóng to, toàn màn hình, đóng) thay
  vì chiếm một dòng riêng bên dưới.
- Nhờ gộp hàng, **bỏ được luật vá ở 0.16.0** vốn phải ẩn cả khối để khỏi lộ dải trống khi
  chưa mở video: hàng bây giờ luôn có nội dung nên dải trống tự hết. Giữ luật vá đó lại thì
  nó sẽ ẩn luôn nút "Nghe khi tắt màn hình".
- Xử luôn một hệ quả dễ ship âm thầm: luật ẩn hai nút này lúc phóng to/toàn màn hình vốn
  nhắm "con trực tiếp của khung video", mà sau khi chuyển chỗ thì chúng không còn là con
  trực tiếp nữa — thiếu bước này là lúc xem toàn màn hình hai nút sẽ lọt vào giữa màn hình.

### Fixed — "chỉnh ngang mất tác dụng"

- **Lựa chọn của người dùng nay thắng luật tự động.** Card hẹp dưới 640px bị luật "xếp một
  cột" đè, kể cả khi đã chọn "Ngang" — nên chủ máy thấy chỉnh mà không có gì đổi. Đó là
  thiết kế sai của tôi: **luật tự động chỉ nên giúp khi chưa ai chọn, không được đè lên ý
  người dùng**. Nay chọn "Ngang" là ép hai cột, kể cả card hẹp (cột phải hạ tối thiểu
  xuống 200px để vừa). Chỉ tính là "đã chọn" khi bấm nút trên card hoặc khai `layout`
  thật trong cấu hình — không tính giá trị mặc định.

### Fixed

- **Nút xoá từ khoá không bao giờ bấm được — nay bấm được.** Bản 0.18.0 mở khoá nút xoá
  nhưng vẫn không xoá được, và lý do là một **vòng kín do tôi tự tạo**:
  1. Nút xoá bật theo ô đang chọn, mà ô mở ra ở dòng "🔍 Tìm nhanh…" có giá trị rỗng →
     lúc dựng lên nút **mờ**.
  2. Muốn bật thì phải chọn một từ khoá.
  3. Nhưng chọn xong là **tìm ngay**.
  4. Có kết quả tìm thì khối gợi ý **tự xoá sạch** — mang theo cả nút xoá vừa bật.

  Tức là không tồn tại trạng thái nào từ khoá đang chọn mà nút xoá còn trên màn hình.
  Đo trên máy chủ nhà xác nhận: `hidden_tags` **rỗng hoàn toàn**, lệnh xoá chưa bao giờ
  gửi được. Nay **chọn từ khoá chỉ điền vào ô tìm** và bật nút xoá; bấm **kính lúp** mới
  tìm.

### Đánh đổi, nói trước

- Trước đây chọn từ khoá là tìm luôn; nay phải bấm thêm kính lúp. Đây là cái giá để nút
  xoá còn trên màn hình mà bấm được — không phải sơ suất.

### Lớp lỗi để không lặp lại

- **Đừng đặt nút quản lý vào một khối tự xoá chính nó.** Khối gợi ý bị
  `replaceChildren()` rồi thoát sớm mỗi khi có kết quả tìm; mọi thứ bên trong đều biến
  mất. Chỗ đúng đắn về lâu dài là trình sửa cấu hình (không bao giờ tự xoá).

## 0.18.0 - 2026-09-18

### Fixed

- **Xoá được từ khoá và mục dựng sẵn.** Bản trước tôi chỉ cho xoá thứ nhà tự thêm, mà
  gần như mọi thứ trên màn hình đều là danh sách dựng sẵn — nên nút xoá lúc nào cũng mờ và
  đúng là **"không xoá được"**. Nay xoá được tất cả: thứ của nhà thì bỏ khỏi kho, thứ dựng
  sẵn nằm trong mã nên máy chủ ghi tên vào **danh sách ẩn** và card lọc đi — nhìn từ phía
  người dùng thì y như đã xoá.
- **Hai ô chọn về chung MỘT hàng** thay vì xếp thành hai hàng; card hẹp thì tự xuống dòng.
- **Nền ô chọn ăn theo màu nền card** thay vì màu cứng — đổi màu trong trình sửa xong hai
  ô này không còn lạc tông. Danh sách bung ra cũng được ép màu chữ/nền để khỏi trắng trên
  trắng.
- **Chế độ ngang dùng được ở card hẹp hơn:** ngưỡng hai cột hạ từ **901px xuống 640px**,
  cột phải tối thiểu từ 300px xuống 240px. Con số 901 trước đây là tôi tự đặt, quá cao nên
  card nửa màn hình không bao giờ xếp ngang được dù chọn "Ngang".
- **Gỡ logo YouTube trên đầu card** (biểu tượng của chính card).

### Không làm được — đã tra tài liệu Google

- **Watermark YouTube bên trong khung video không gỡ được.** Tài liệu chính thức:
  *"The `modestbranding` parameter is deprecated and will have no effect… the player now
  determines the appropriate branding treatment based on… player size, other API
  parameters, and additional signals."* CSS cũng không chạm được vào nội dung bên trong
  khung nhúng của bên khác. Phát ra loa hoặc tivi thì không có watermark này.

### Ghi chú về kiểm chứng

- Khi thêm hai danh sách ẩn, tôi **tự tạo ra một lỗi mất dữ liệu**: bốn nhánh ghi còn lại
  vẫn trả về tài liệu thiếu hai khoá mới, nghĩa là thêm một từ khoá sẽ **xoá sạch danh
  sách đã ẩn**. Phép thử chạy thẳng trên hàm thuần bắt được trước khi đẩy; nay cả 5 đường
  trả về đều giữ đủ, và có phép thử đầu-cuối chứng minh.

## 0.17.0 - 2026-09-18

### Đính chính một điều tôi đã nói sai ở 0.14.0

- Tôi từng ghi rằng "card nào **không khai** `getGridOptions` thì bị Home Assistant cấp
  mặc định hẹp — đó là lý do card chật". **Sai.** Tài liệu chính thức nói ngược lại: card
  không khai gì thì **mặc định đã lấy trọn 12 cột**. Nên hàm đó không phải thứ làm card
  hết chật, và tôi xin rút lại lời ấy.

### Changed

- **Khai `columns: "full"`** thay cho con số 12. Đây mới là cách tài liệu nêu để **ép**
  card rộng hết khổ, tương đương công tắc "Full width card" trong giao diện; con số 12
  chỉ là bề rộng mặc định của một section 12 cột.
- **Giới hạn cần biết:** cơ chế này **chỉ có ở dashboard kiểu Sections**. Ở **Masonry**
  (kiểu cũ) thì bề rộng card bằng bề rộng cột, `getCardSize()` chỉ ảnh hưởng chiều cao, và
  `layout-card` cũng không giúp được trừ khi dùng chế độ Panel. Muốn card thật sự rộng thì
  đổi view sang **Sections** hoặc **Panel**.

### Added

- **Phụ đề tắt mặc định** khi xem trên thẻ (`cc_load_policy=0`), và tắt chú thích nổi
  (`iv_load_policy=3`).
- Hai việc **không làm được**, nói rõ để khỏi chờ: YouTube đã bỏ tác dụng của tham số ẩn
  logo nên **logo vẫn còn**, và **không cho đặt độ phân giải** qua khung nhúng — người xem
  tự chọn trong nút bánh răng của trình phát.

## 0.16.0 - 2026-09-18

### Fixed

- **Card co giãn theo BỀ RỘNG CỦA CHÍNH NÓ, không theo cửa sổ.** Đây là lỗi thiết kế của
  tôi từ đầu: mọi điểm ngắt viết bằng `@media`, tức đo bề rộng **cửa sổ trình duyệt** —
  trong khi bề rộng card do **cột của dashboard** quyết định. Card đặt trong cột hẹp trên
  màn hình rộng vẫn nhận luật "máy tính" rồi **tràn ra ngoài**; thấy rõ nhất ở ô xem trước
  của trình sửa (~330px) nằm trong cửa sổ ~1040px. Nay card tự làm mốc đo
  (`container-type: inline-size`) và cả **5** điểm ngắt chuyển sang `@container`.
- **Đổi bố cục trong trình sửa nay có tác dụng.** Nút dọc/ngang trên card ghi vào bộ nhớ
  của máy và **đè vĩnh viễn** lên cấu hình, nên sửa trong trình sửa không thấy gì đổi —
  đúng chỗ "không đồng bộ giữa card và config". Nay đổi cấu hình thì xoá lựa chọn riêng
  của máy; bấm nút trên card vẫn thắng cho tới lần đổi cấu hình kế tiếp.
- **Card không rộng ra được**: `getGridOptions` của tôi trả thêm khoá `rows: "auto"` mà
  tôi chưa kiểm — một khoá sai là Home Assistant bỏ qua cả object. Nay chỉ khai `columns`
  và `min_columns`. Lưu ý: cơ chế này **chỉ áp dụng cho dashboard kiểu Sections**.
- **Dải trống phía trên nút "Nghe khi tắt màn hình"**: hàng sáu nút điều khiển video đều
  ẩn khi chưa mở video, nhưng khối cha vẫn chiếm trọn một dòng kèm lề. Nay ẩn cả khối khi
  bên trong không còn nút nào hiện.
- **Khoảng trống lớn trong khung Playlist**: luật gốc ép cột cao cứng 640px cho bố cục hai
  cột; khối điểm ngắt card hẹp gỡ `position` và `min-height` nhưng **quên gỡ `height`**.

### Changed

- **Hai hàng gợi ý đổi thành danh sách thả xuống.** Hàng cuộn ngang chỉ vuốt được bằng
  cảm ứng: chuột không kéo ngang được mà thanh cuộn lại bị ẩn, nên phần lớn từ khoá coi
  như không với tới. Thả xuống thì chuột, phím và cảm ứng đều dùng được, và không bao giờ
  tràn ở bất kỳ bề rộng nào.

### Added

- **Xoá được từ khoá, xoá mục, và gỡ video đã gắn.** Máy chủ đã hỗ trợ sẵn từ 0.15.0
  nhưng card chưa có nút nào — nay đủ cả ba. Nút xoá chỉ bật cho mục **của nhà**; mục dựng
  sẵn nằm trong mã nên không xoá được, và nút mờ đi kèm lời giải thích thay vì bấm không
  thấy gì xảy ra. Xoá mục có hỏi lại vì nó kéo theo mọi video đã gắn.

### Ghi chú

- **Nguồn nhạc "tự nhảy" sang Zing MP3 không phải lỗi**: card cố ý nhớ lần tìm gần nhất
  (nguồn, từ khoá, kết quả) để rời dashboard quay lại không mất — hành vi này đang được
  một điều kiện trong bộ test khoá lại. Muốn bỏ thì nói, tôi sẽ sửa cả test kèm lý do.

## 0.15.0 - 2026-09-18

### Added

- **Từ khoá tìm nhanh và video gắn sẵn do nhà tự tạo.** Đây là việc cuối trong danh sách,
  làm theo đúng phương án đã chốt: **lưu ở tích hợp, không nằm trong YAML của từng thẻ**,
  nên mọi bảng điều khiển và mọi máy đều thấy như nhau, và thêm hay bớt card không làm mất
  dữ liệu.
  - Nút **thêm từ khoá** và **thêm mục** ngay trên đầu dải gợi ý.
  - Nút **ghim** trên mỗi kết quả tìm, gắn bài đang xem vào mục của nhà. Nút chỉ hiện khi
    nhà đã tạo ít nhất một mục, vì gắn vào chỗ chưa có sẽ bị từ chối.
  - Mục dựng sẵn và mục của nhà hiện chung một dải; trùng tên thì mục của nhà thắng.
- **Đường API mới** `/api/tritue_youtube_player/suggestions`, kho lưu riêng
  (`tritue_youtube_player.suggestions`). Đọc thì ai đăng nhập cũng được, **ghi thì chỉ tài
  khoản quản trị** — cùng mức với việc sửa dashboard.

### Changed

- **`_syncPlayers` nay cũng canh bằng chữ ký trước khi dựng lại danh sách loa.** Đây là
  chỗ cuối cùng cùng lớp lỗi với hai chỗ đã sửa ở 0.12.2, lúc đó tôi ghi rõ là để làm
  riêng cho cẩn thận. Phần đuôi (âm lượng, nút điều khiển, đang phát) vẫn chạy mỗi lượt vì
  nó phản ánh trạng thái sống — cổng canh chỉ bọc đúng phần dựng lại chip loa.

### Ghi chú về kiểm chứng

- Phần lưu trữ viết dạng hàm thuần, không nhập gì của Home Assistant, nên chạy thẳng được
  để thử. Lần chạy thử đầu tiên bắt được **hai lỗi thật trong chính mã vừa viết**, sửa
  trước khi đẩy: chuỗi đặt nhầm chỗ danh sách bị tách thành từng ký tự
  (`{"tags": "abc"}` → `["a","b","c"]`), và tên tiếng Việt sinh mã mục hỏng
  ("Nhạc tối" → `nh-c-t-i`) khiến hai tên khác nhau có thể đụng nhau. Nay bỏ dấu đúng cách
  nên ra `nhac-toi`.

## 0.14.0 - 2026-09-18

### Added

- **Card tự xin bề rộng của dashboard.** Đây là lời giải cho câu "có cách nào tăng độ
  rộng của card không": ở dashboard kiểu **Sections**, Home Assistant chia lưới 12 cột và
  card nào **không khai gì** thì bị cấp mặc định hẹp — card này trước đây không khai gì
  cả. Nay nó xin trọn 12 cột (tối thiểu 6), và anh vẫn chỉnh lại được trong phần Bố cục
  của từng thẻ.

### Changed

- **Hai cột trông như hai thẻ liền nhau**, mỗi cột có nền, viền và bo góc riêng thay vì
  nằm chung một khối lớn. Chỉ áp dụng từ 901px trở lên; màn hình hẹp vẫn xếp dọc một cột
  vì viền lồng trong viền trông rối.
- **Ảnh bài hát gợi ý nhỏ lại** — ô tối thiểu từ 150px xuống 118px, nên máy tính xếp được
  nhiều bài hơn trên một hàng mà điện thoại vẫn đủ hai cột.

### Fixed

- **Thanh "Loa phát nhạc" bị vỡ ở khung hẹp.** Nhãn không có luật chống xuống dòng, trong
  khi nút "Đổi loa" đặt `flex: none` nên không co được — khung hẹp lại thì nhãn rơi xuống
  ba dòng, đội khung cao lên và **đè vào nút**. Thấy rõ trong ô xem trước của trình sửa.
  Nay nhãn cắt gọn bằng dấu ba chấm.

### Ghi chú về việc thêm card thứ hai

- Đo bằng `grep`: chỉ có **hai** chỗ dùng `position: fixed` (z-index 10 và 11), và cả hai
  đều thuộc lớp phủ video lúc phóng to / toàn màn hình. Ở trạng thái thường **không có gì
  tràn ra ngoài card**, nên thêm card thứ hai không bị đè. Riêng lúc phóng to, mã đã có
  sẵn phần nhận biết dashboard "nhốt" lớp phủ và tự chuyển sang chế độ toàn màn hình của
  trình duyệt.

## 0.13.1 - 2026-09-18

### Fixed

- **Kéo âm lượng về 0 rồi nó nhảy về chỗ cũ.** Card bỏ chốt giữ thanh trượt **ngay khi
  lệnh đặt âm lượng trả về**, nhưng Home Assistant còn đẩy tiếp vài bản trạng thái mang
  giá trị **cũ** trước khi loa kịp báo lại — thanh trượt bị ghi đè ngược. Kéo về 0 thấy rõ
  nhất vì quãng nhảy dài nhất. Nay card nhớ mức vừa đặt và bỏ qua mọi trạng thái còn mang
  giá trị cũ, cho tới khi loa xác nhận đúng mức đó hoặc quá 5 giây.
- **Loa đã tích giờ tô nền, không chỉ đổi viền.** Trước đây loa được chọn chỉ đổi màu viền
  nên nhìn lướt không thấy. Vẫn phân biệt được với loa **đang chỉnh âm lượng**: loa đã tích
  tô nền mờ, loa đang chỉnh tô đặc.
- **Nền tách bạch hẳn với các lựa chọn.** Khung chọn nguồn trước đây dùng nền cùng tông với
  nút đang chọn (đều là màu nhấn, chỉ khác độ mờ 0.08 với gradient) nên nhìn không ra đâu
  là nền, đâu là lựa chọn. Nay khung dùng nền tối trung tính, còn nút đang chọn **tô đặc**
  màu nhấn với chữ tương phản tính theo độ sáng của chính màu đó.

## 0.13.0 - 2026-09-18

### Changed

- **Gộp hai hàng nút thành một: YouTube · Zing MP3 · Playlist.** Hàng "Tìm nhạc /
  Playlist" riêng đã bỏ; nút Playlist chuyển vào chung hàng với nguồn nhạc. Nút nào sáng
  là do khung đang xem quyết định — đang mở Playlist thì nút Playlist sáng, ngược lại là
  nguồn đang chọn.

### Removed

- **Nguồn "Link audio" đã gỡ theo yêu cầu.** Gỡ trọn chứ không chỉ giấu nút: nút bấm,
  nhánh xử lý trong `_search`, cả hàm `_prepareHttpResult`, phần đổi gợi ý và nhãn nút
  tìm, và khoá cấu hình `http_content_type` của card. Từ nay **dán link MP3/FLAC/HLS
  thẳng vào ô tìm sẽ không phát được nữa**.
  Phần hỗ trợ `http` của *tích hợp* (dịch vụ `play_on_players`) **giữ nguyên** — đó là
  đường khác, không liên quan tới nút trên card.
- Hai điều kiện trong bộ test khoá hợp đồng (`data-source="http"` và
  `_prepareHttpResult`) được viết lại thành điều kiện **phải vắng mặt**, kèm một điều
  kiện mới cho nút Playlist. Hợp đồng đổi vì **tính năng bị gỡ theo yêu cầu**, không phải
  để lách test.

### Fixed

- **Mở Playlist xong không bị kẹt.** Khi gộp hàng, `_showView` vẫn đang ẩn cả
  `.source-switch` lúc mở Playlist — mà nút Playlist nay nằm trong chính hàng đó, nên ẩn
  đi là mất luôn đường quay lại YouTube/Zing. Nay hàng nút luôn hiện ở cả hai khung.

## 0.12.2 - 2026-09-18

### Fixed

- **Danh sách chọn thiết bị bị nháy khi mở.** Home Assistant gán lại `hass` cho trình sửa
  mỗi lần có bất kỳ thực thể nào trong nhà đổi trạng thái — nhiều lần mỗi giây — và trình
  sửa dựng lại toàn bộ danh sách mỗi lần như thế. Danh sách đang mở mà bị thay ruột thì
  nháy rồi đóng. Nay chỉ dựng lại khi **tập thiết bị hoặc tên của chúng thật sự đổi**, và
  chỉ gán lại lựa chọn khi nó lệch.
- **Dải gợi ý bị dựng lại liên tục.** Khối gợi ý không đọc gì từ trạng thái nhà — nội dung
  chỉ phụ thuộc nhóm đang chọn, nguồn nhạc, tab hiện tại và việc đã có kết quả tìm hay
  chưa — nhưng nó cũng được gọi mỗi lần đổi trạng thái, tức xoá và dựng lại hơn 60 nút
  (gồm cả thẻ ảnh) để cho ra kết quả y hệt. Ngoài việc phí, điều này **xoá mất cú vuốt
  ngang đang dở**, nên đây là nguyên nhân thứ hai khiến dải gợi ý khó cuộn, bên cạnh việc
  các nút bị co lại đã sửa ở 0.12.1. Nay canh bằng chữ ký, không đổi thì không đụng DOM.

### Ghi chú

- Đo bằng `grep`: còn **`_syncPlayers`** (hai chỗ dựng lại) cùng lớp lỗi này và cũng chạy
  mỗi lần đổi trạng thái. Chưa sửa trong bản này vì đó là hàm lớn nhất, có gắn sự kiện cho
  từng loa; sẽ làm riêng để không đụng vào phần chọn loa vừa mới chạy đúng.

## 0.12.1 - 2026-09-18

### Fixed

- **Kéo "độ đục" làm nền đổi sang màu khác thay vì mờ đi.** Nền thẻ có hai lớp: lớp màu
  phẳng ở dưới và lớp chuyển sắc vẽ đè lên. Độ đục trước đây chỉ áp cho lớp dưới, còn các
  mốc màu của lớp trên giữ nguyên độ đục cố định trong CSS, nên nền dashboard lẫn qua và
  cho ra một màu khác hẳn — hạ xuống 46% thì nền tím/đỏ. Nay ở kiểu chuyển sắc, ảnh nền
  được dựng lại với các mốc đã nhân theo mức người dùng chọn.
- **Dải gợi ý không vuốt ngang được.** Hai hàng nút (từ khoá và nhóm nhạc) đã có
  `overflow-x: auto`, nhưng các nút con của flex **mặc định co lại được**, nên chúng bị
  bóp cho vừa khung thay vì tràn ra — khung chẳng có gì để cuộn, chữ thì bị cắt cụt hai
  đầu. Nay hai hàng đó không cho nút co (`flex: 0 0 auto`), và hàng nhóm nhạc được bổ sung
  cuộn cảm ứng. Đo bằng `grep`: cả card đúng hai khung cuộn ngang, đã sửa cả hai.
- **Loa đang chỉnh âm lượng: tô nền thay cho viền, và chữ không còn trùng màu nền.**
  Trước đây loa được chọn chỉ có viền màu nhấn, mà chữ cũng đang là màu nhấn — với màu
  vàng thì gần như không đọc được. Nay tô hẳn nền, và màu chữ tính theo độ sáng cảm nhận
  của chính màu nhấn (nhấn sáng thì chữ tối, nhấn tối thì chữ trắng) nên luôn tương phản.
  Luật mới phải thêm một lớp phía trước mới thắng được `:has(input:checked)` — luật đó có
  độ ưu tiên cao hơn và nếu không xử lý thì chữ vẫn giữ nguyên màu nhấn.

## 0.12.0 - 2026-09-18

### Added

- **Sửa thẻ bằng giao diện, không phải gõ YAML nữa.** Bấm "Sửa thẻ" trên dashboard là
  mở trình sửa có ba tab:
  - **Cấu hình** — chọn thiết bị phát từ danh sách (entity của tích hợp được đánh dấu ★
    và xếp lên đầu), đặt tiêu đề, chọn kiểu sóng nhạc.
  - **Hiển thị** — loại nền (chuyển sắc / một màu / trong suốt ăn theo dashboard), màu
    nền, màu nhấn, thanh độ đục, thanh thu phóng cỡ chữ và nút.
  - **Bố trí** — kiểu xếp ngang hay dọc, bề rộng cột video.

  Card cũng hiện trong danh sách "Thêm thẻ" với cấu hình mẫu điền sẵn.
- **Khoá cấu hình mới**, đều tuỳ chọn: `bg_style`, `bg_color`, `accent_color`, `opacity`,
  `zoom`. Không đặt gì thì giao diện giữ nguyên như cũ.

### Changed

- Nền thẻ nay vẽ qua hai biến `--ad-bg-alpha` và `--ad-bg-image` nên đổi được bằng cấu
  hình; màu nhấn và màu nền đổ vào đúng ba biến mà toàn bộ giao diện đang dùng, nên chỉnh
  một chỗ là cả thẻ đổi theo.
- Phần hướng dẫn ở đầu tệp card liệt kê lại đủ các khoá (trước đây chỉ ghi ba khoá,
  thiếu cả `layout` lẫn `player_width`).

## 0.11.7 - 2026-09-18

### Fixed

- **Điện thoại không thấy thanh điều khiển.** Khối "Đang phát" — sóng nhạc, thanh tiến
  trình và bốn nút bài trước / phát tạm dừng / dừng / bài sau — nằm ở **cuối** cột danh
  sách, phía sau cả dải gợi ý lẫn lưới kết quả, nên phải cuộn rất lâu mới tới. Màn hình
  rộng không lộ ra vì cột phải cao cố định và khối này được ghim đáy bằng flex; nhưng ở
  màn hình hẹp `.yt-playlist-inner` bị đổi về `display: block`, mất luôn cách xếp flex,
  nên mọi khối rơi về đúng thứ tự trong tài liệu. Nay màn hình hẹp giữ nguyên flex column
  và khối điều khiển được đưa lên **đầu cột**, ngay dưới thanh chọn loa.

## 0.11.6 - 2026-09-18

### Changed

- **Một thanh âm lượng cho loa đang chọn, thay cho cả chồng thanh trượt.** Thanh gọn
  "Loa phát nhạc" cho biết đang chỉnh loa nào; nút "Đổi loa" bung danh sách để tích loa
  phát rồi thu lại.
- **Bấm tên loa và bấm ô tích là hai việc độc lập.** Trước đây mỗi loa là một `<label>`,
  mà trong HTML thì bấm bất cứ đâu bên trong `<label>` đều bật/tắt ô tích — nên không
  thể vừa chọn loa để chỉnh âm lượng vừa giữ nguyên việc loa nào phát. Nay tên loa là
  một nút riêng: bấm để đổi đích chỉnh âm lượng, kể cả với loa chưa tích; ô tích vẫn chỉ
  quyết định loa nào phát. Mỗi lần mở lại danh sách đều hiện đúng các loa đang được tích.

### Added

- **Nút chọn bố cục dọc/ngang ngay trên card**, cạnh biểu tượng YouTube. Lựa chọn được
  nhớ theo từng máy và từng thẻ, nên máy tính để ngang còn điện thoại để dọc mà không
  phải sửa YAML; nút này thắng khoá `layout` trong cấu hình. Màn hình hẹp vốn luôn xếp
  một cột nên nút tự ẩn ở đó.

## 0.11.5 - 2026-09-18

### Fixed

- **Thẻ không hiện, dashboard báo "Custom element doesn't exist".** Hai lệnh đăng ký
  thẻ nằm chung một cổng kiểm tra tên `youtube-player-card`, nên chỉ cần tên đó đã bị
  chiếm — tệp card nạp hai lần, hoặc một card khác đăng ký trùng tên — là
  `tritue-youtube-player-card`, đúng thẻ khai trong YAML, không bao giờ được định nghĩa.
  Nay mỗi thẻ tự canh tên của chính nó.
- **Card hiện trong danh sách "Thêm thẻ" của Home Assistant**, kèm ảnh xem trước:
  trước đây `window.customCards` chỉ khai tên phụ `youtube-player-card`, không khai tên
  thật đang dùng.
- **Bố cục vỡ trên điện thoại.** Luật đặt bề rộng cột video viết sau khối
  `@media (max-width: 900px)` và cùng độ ưu tiên, nên nó đè mất `grid-template-columns: 1fr`
  của màn hình hẹp: máy nhận lưới hai cột trong khi các vùng đã xếp dọc một cột. Nay luật
  đó nằm trong `@media (min-width: 901px)`.

## 0.11.4 - 2026-09-18

### Fixed

- **Phát ra loa không phải tự điền URL nữa.** Loa tải luồng phát thẳng từ add-on nên
  cần một địa chỉ LAN, mà add-on không tự suy ra được: mọi lời gọi của integration
  đến nó đều qua NAT của Supervisor (log thật: nguồn là `172.30.32.1`). Nay
  integration lấy **địa chỉ LAN mà chính Home Assistant công bố** (Cài đặt → Hệ thống
  → Mạng → URL Home Assistant) ghép với cổng của URL add-on đã cấu hình, rồi gửi kèm
  khi xin luồng. Đổi map cổng cũng ra đúng. Chưa cấu hình URL nội bộ thì không gửi gì
  và add-on vẫn báo lỗi rõ ràng, không im lặng.
- Cần add-on **0.8.3 trở lên** để nhận gợi ý này; bản add-on cũ bỏ qua khoá lạ nên
  vẫn chạy như trước.

## 0.11.3 - 2026-09-17

### Added

- **Gợi ý nhạc ngay khi mở card, kèm khung ảnh:** chưa tìm gì thì card bày sẵn bốn nhóm
  (Cafe Acoustic, Nhạc Trẻ Hot TikTok, Lofi Chill & Học Tập, Bolero & Trữ Tình) với 16 bài
  có ảnh thật và thời lượng, cùng dải chip từ khoá bấm là tìm ngay. Chạm một thẻ là phát
  trên loa đang tích, không phải gõ chữ nào. Có kết quả tìm kiếm thì khối gợi ý tự nhường chỗ.

### Changed

- **Bố cục ngang thành lưới 2x2:** video trên trái, loa/màn hình dưới trái tách hai cột
  (Loa và Màn hình), cột phải là tìm nhạc + kết quả + đang phát + sóng nhạc; tự xếp dọc lại
  khi thẻ hẹp dưới 900 px. `layout: horizontal` (mặc định) dùng lưới này, `layout: vertical`
  xếp một cột cho dashboard cột hẹp, `player_width` đặt bề rộng cột video.
- **Nút điều khiển video phủ trên khung hình** thay vì nằm dưới thanh điều khiển, và thêm
  sóng nhạc động khi chỉ phát tiếng (`waveStyle`: bars | simple | dots).
- Thẻ đăng ký thêm bí danh `youtube-player-card` để dashboard đang dùng tên đó vẫn chạy.

## 0.11.0 - 2026-09-15

### Fixed

- **Nghe/xem trên máy khi mở HA ngoài mạng nhà (4G/5G, tên miền HTTPS, Nabu Casa):** card từng đưa
  cho trình duyệt link luồng của máy phát trong mạng nhà (ví dụ `http://172.16.10.38:3030/…`) —
  ngoài nhà không tới được, còn trong trang HTTPS thì trình duyệt chặn link HTTP — nên báo
  "Máy này không phát được tiếng bài này (NotSupportedError)". Nay luồng đi qua chính Home
  Assistant bằng đường dẫn đã ký (hết hạn sau 1 giờ): mở HA bằng địa chỉ nào cũng nghe được, tua
  được. Áp dụng cho cả máy phát c2a lẫn add-on, cả tiếng lẫn hình riêng của video bị chặn nhúng.
  Loa vẫn lấy luồng thẳng từ máy phát như cũ. **Cần khởi động lại Home Assistant sau khi cập nhật.**

## 0.10.6 - 2026-09-15

### Fixed

Chủ máy báo trên app HA (.200, card 0.10.5): bấm xem video không tự phát, nút ▶ của card không
ăn, chạm play trong khung thì giật rồi dừng, vào toàn màn hình thì dừng, thu nhỏ lại không phát.
Tái hiện trên chính HA .200 (Chrome, chặn tự phát có tiếng) và sửa:

- **Khung YouTube bỏ qua mọi lệnh:** bấm xem khi trình phát nạp sẵn chưa xong thì card đổi trang
  của khung; tin nhắn của trang cũ lọt vào làm card tưởng trang mới đã sẵn sàng và thôi bắt tay,
  nên trang mới không nghe lệnh phát, dừng, tắt tiếng — video đứng yên trong khi tiếng máy chạy.
  Nay mỗi lần khung nạp trang mới (kể cả khi HA dựng lại card) card bắt tay lại từ đầu.
- **Tiếng máy không phát được mà video vẫn chạy theo nó:** trước chỉ nhả video khi máy chủ không
  trả luồng; trình duyệt từ chối phát thì card vẫn giữ video "theo tiếng máy" và dừng video mỗi
  lần chạm phát trong khung. Nay tiếng máy hỏng vì bất cứ lý do gì thì tắt hẳn tiếng máy, video tự
  giữ tiếng, hiện "Chạm vào video để phát có tiếng"; nút ▶ của card phát lại tiếng máy ngay trong
  cú bấm.
- **Báo đúng lý do:** trước mọi lỗi phát đều báo "chặn tự phát". Nay chặn tự phát, luồng không phát
  được (kèm tên lỗi / mã lỗi) báo khác nhau; bài bị bài mới chen ngang không báo lỗi.
- **Toàn màn hình:** app có thể báo trang "ẩn" trước khi vào toàn màn hình; card xét lại sau nửa
  giây, còn ẩn mà không toàn màn hình mới dừng tiếng (tắt màn hình thật).

## 0.10.5 - 2026-09-15

### Added

- **Danh sách loa / màn hình thu gọn sẵn**, bấm tiêu đề mới mở; khi thu gọn tiêu đề vẫn ghi loa
  đã tích (một hai loa thì ghi tên).
- **Video chạy nhanh hơn:** có kết quả tìm là card nạp sẵn trình phát YouTube (ẩn), bấm xem chỉ
  còn đổi bài trong khung đó; đóng video thì giữ khung cho lần sau. Link tiếng của bài được lấy
  sẵn ngay trong cú bấm, và card chờ 1,5 giây (thay vì 2,5) trước khi tự phát tiếng khi khung bị
  chặn tiếng tự phát.

### Fixed

- **Hình lệch tiếng:** trước đây chỉ chỉnh khi lệch quá 2 giây. Nay hình theo tiếng trên máy trong
  0,35 giây (đo trong Chrome: lệch 0,03 giây), theo loa trong 0,5 giây (vị trí loa do HA báo trễ vài
  trăm mili-giây nên siết hơn sẽ giật); mỗi lần tua nhắm vượt trước đúng thời gian các lần tua trước
  cần để hiện hình.
- **Phóng to/toàn màn hình trong app HA làm dừng video:** app báo trang "ẩn" thoáng qua khi vào toàn
  màn hình và card coi như tắt màn hình. Nay đang toàn màn hình thì không dừng.
- **Video cứ quay về 0 giây:** lúc tiếng đang tải (chưa có dữ liệu) card vẫn kéo hình về vị trí 0 của
  tiếng; khi HA vẽ lại trang (xoay máy) card mở lại video từ 0. Nay chờ tiếng có dữ liệu mới chỉnh, và
  mở lại đúng giây đang nghe; đang phóng to/toàn màn hình thì thẻ dựng lại vẫn ở chế độ phóng to.

## 0.10.4 - 2026-09-15

### Added

- **Nút xoay 90°** khi phóng to hoặc toàn màn hình lúc máy dựng đứng (máy khoá xoay): bấm là
  video nằm ngang vừa màn dọc, bấm lại trả dọc. Màn ngang thì không hiện nút. Toàn màn hình
  vẫn tự xoay như YouTube nơi trình duyệt cho khoá hướng; app không cho thì card tự xoay khung.

### Fixed

- **Toàn màn hình / phóng to không lấp đầy màn** (PC và điện thoại): card chừa một dải cho
  thanh điều khiển dưới hình nên hình nhỏ hơn màn, có viền đen. Nay hình lấp đầy như trình phát
  của YouTube (16:9, không cắt), thanh tiến độ và nút nổi đè lên mép dưới hình và tự ẩn khi
  không chạm. Dòng tên bài của card chỉ hiện khi xem bằng hình riêng (khung YouTube đã có tên).

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
