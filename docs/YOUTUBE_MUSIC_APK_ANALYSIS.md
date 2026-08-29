# Phân tích clean-room APK YouTube Music

Tài liệu này ghi lại kiến trúc quan sát được để định hướng TriTue Music Player.
Không sao chép mã decompile, khóa, endpoint nội bộ hoặc cơ chế vượt entitlement.

## Mẫu đã kiểm tra

- Package: `com.google.android.apps.youtube.music`
- Version name: `9.34.52`
- Version code: `93452240`
- Min SDK: 26; target SDK: 36
- SHA-256:
  `31d4f4f97ace08a24dbab40635d494b0dcdb2159e491f31b924c0b17621c39ab`
- Công cụ đọc tĩnh: JADX 1.5.6 và Android manifest decoder. Bản APK bị làm
  rối tên; khoảng 155 class không decompile hoàn chỉnh, vì vậy kết luận chỉ dựa
  trên các component/callback còn đọc được và được đối chiếu chéo.

## Kiến trúc quan sát được

Manifest và các class liên quan cho thấy ứng dụng chia thành ba mặt phẳng:

1. **Nguồn và player**: `BackgroundPlayerService` chạy foreground với loại
   `mediaPlayback`.
2. **Điều khiển**: Android `MediaSession`/`MediaBrowserService` công bố trạng
   thái, metadata, hàng đợi và nhận media button/search intent.
3. **Đầu ra từ xa**: Google Cast/MDX dùng `MediaInfo`, `RemoteMediaClient` và
   notification riêng; đây không phải một URL MP3 công khai được đưa cho mọi
   thiết bị.

Các component đáng chú ý trong manifest:

- `com.google.android.apps.youtube.music.mediabrowser.MusicBrowserService`
- `androidx.media.session.MediaButtonReceiver`
- `com.google.android.libraries.youtube.player.background.service.BackgroundPlayerService`
- `com.google.android.libraries.youtube.mdx.castclient.CastOptionsProvider`
- `com.google.android.libraries.youtube.mdx.mediaroute.service.RemotePlaybackControlsService`
- Deep link `http/https://music.youtube.com/*` và scheme `vnd.youtube.music`
- Intent `android.media.action.MEDIA_PLAY_FROM_SEARCH`

## Hợp đồng phát nhạc có thể học

### Lệnh

MediaSession callback xử lý play, pause, stop, next, previous, seek,
skip-to-queue-item, repeat, shuffle, rating và play-from-search/media-id/URI.
Play-from-search ghép query với các extra chuẩn như artist, title, album, genre,
playlist và radio channel.

### Trạng thái và metadata

Ứng dụng công bố trạng thái playing/paused/idle/buffering/error, vị trí, tốc độ,
duration, title, artist, album artist, artwork, display title/subtitle và active
queue item ID. Hàng đợi chứa item có ID riêng, title, subtitle/artist/album và
artwork; cửa sổ queue quan sát được giới hạn xấp xỉ 25 item tùy feature flag.

### Cast và quảng cáo

Cast dùng receiver/metadata chính thức. `RemotePlaybackControlsService` còn theo
dõi cả trạng thái ad stage; APK không cho thấy thiết kế “lấy MP3 rồi bỏ quảng
cáo”. Việc một phiên hiện tại chưa gặp quảng cáo không có nghĩa add-on đang chặn
quảng cáo. Entitlement/background-play vẫn được kiểm tra trong luồng player.

### Giới hạn truy cập từ ứng dụng khác

`MusicBrowserService` có kiểm tra UID/package/signature allowlist. Vì vậy một
add-on độc lập không thể coi service này là API duyệt/tìm kiếm chung cho mọi máy.
ADB media key/deep link có thể là adapter riêng cho một Android box đã cấu hình,
nhưng không phù hợp làm lõi cho người dùng không có R1/Aibox.

## Áp dụng vào TriTue Music Player

| Khái niệm YouTube Music | Thiết kế clean-room của dự án |
|---|---|
| MediaSession | `session` dùng chung trong API add-on |
| MediaMetadata | `item` gồm source/id/url/title/artist/album/thumbnail/duration |
| Queue + active item | `queue.items` và `queue.index` |
| PlaybackState | state/position/duration/updated_at/supported_actions |
| Route/Cast session | `output_entity_ids` và capability từng `media_player` |
| MediaBrowser search | API search metadata YouTube/Zing đã chuẩn hóa |
| Cast/MDX | adapter HA Cast TV/box; không giả URL trang web là audio |
| Loa HTTP | relay Zing có chữ ký hoặc HTTP audio trực tiếp |

Phiên bản 0.5.0 triển khai phần hợp đồng phiên: giữ metadata từ kết quả tìm kiếm,
hàng đợi hiện tại, thiết bị đầu ra và now-playing dùng chung cho mọi trình duyệt.
Custom entity/card đọc trạng thái này thay vì chỉ dựa vào `localStorage`.

## Phần chưa thể tuyên bố hoàn thành

- Chưa có relay/transcode YouTube Music thành HTTP audio cho Google Mini/DLNA.
- Chưa có đồng bộ nhiều loa bằng clock/buffer; nên dùng group entity gốc của
  Cast/DLNA khi cần đồng bộ.
- Chưa có profile codec theo từng thiết bị và fallback MP3/AAC/FLAC.
- Không chặn, bỏ qua hoặc loại quảng cáo của YouTube/YouTube Music.
- Không dùng API nội bộ, chữ ký ứng dụng hoặc endpoint lấy từ APK.

Hướng phát triển hợp lệ tiếp theo là một browser-engine chính thức có giao diện
đăng nhập riêng, giữ nguyên quảng cáo/quyền tài khoản, xuất trạng thái qua hợp
đồng session và chỉ bật relay thử nghiệm khi điều khoản dịch vụ cho phép.
