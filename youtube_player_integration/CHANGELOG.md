# Changelog

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
