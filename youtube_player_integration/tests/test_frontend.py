import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
COMPONENT_DIR = ROOT / "custom_components" / "tritue_youtube_player"


class LovelaceCardContractTests(unittest.TestCase):
    def test_services_do_not_import_removed_home_assistant_volume_constant(self):
        source = (COMPONENT_DIR / "services.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_names = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module == "homeassistant.const"
            for alias in node.names
        }

        self.assertNotIn("ATTR_VOLUME_LEVEL", imported_names)

    def test_integration_ships_multi_speaker_search_card(self):
        script = (COMPONENT_DIR / "www" / "tritue-youtube-player-card.js").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'customElements.define("tritue-youtube-player-card"', script
        )
        self.assertIn('callApi("GET", `tritue_youtube_player/search?', script)
        self.assertIn('callApi("GET", `tritue_youtube_player/capabilities?', script)
        self.assertIn('this._capabilityEntryId = "";', script)
        self.assertIn("this._supportsSource(entityId, this._source)", script)
        self.assertIn('callService("tritue_youtube_player", "play_on_players"', script)
        # 0.13: nguồn "Link audio" đã gỡ theo yêu cầu chủ máy — hàng nút nay là
        # YouTube / Zing MP3 / Playlist, nên hai điều kiện ghim nút và hàm xử lý
        # link trực tiếp không còn đúng nữa. Đổi hợp đồng vì TÍNH NĂNG đổi, không
        # phải để lách test.
        self.assertNotIn('data-source="http"', script)
        self.assertNotIn("_prepareHttpResult", script)
        self.assertIn('data-view="playlists"', script)
        # 0.26.2: ẩn từng mục của hàng nguồn qua cấu hình, và SỐ CỘT bám theo số mục
        # còn hiện — ẩn bớt mà giữ nguyên số cột thì hàng thừa ô trống.
        self.assertIn("show_youtube: true,", script)
        self.assertIn("show_playlist: true,", script)
        self.assertIn("this._applySourceVisibility()", script)
        self.assertIn("hang.classList.add(`so-${dem}`)", script)
        self.assertIn(".source-switch.so-1 { grid-template-columns: minmax(0, 1fr); }", script)
        # 0.26.5: BA MỤC THÌ MỘT HÀNG ở MỌI bề rộng — chủ máy chốt "nếu 3 cái thì phải
        # đặt cùng hàng như trước chứ". Luật phải có mặt HAI lần: một bản trong khối đo
        # bề rộng (thắng luật bốn cột), một bản không điều kiện (thắng mặc định hai cột
        # ở chỗ hẹp). Thiếu bản không điều kiện là mục thứ ba lại rơi xuống một mình.
        self.assertEqual(
            script.count(".source-switch.so-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }"),
            2)
        # Ba tình huống hỏng mà chính tính năng này sinh ra, mỗi cái một chốt chặn:
        # ẩn nguồn đang mở, ẩn Playlist khi đang đứng trong khung Playlist (chặn tại
        # MỘT cửa vào vì còn đường tự nhảy vào đó sau khi lưu), và khôi phục lần tìm
        # cũ thuộc nguồn vừa bị ẩn.
        self.assertIn("if (conLai.length && !conLai.includes(this._source)) {", script)
        self.assertIn('const moPlaylist = view === "playlists" && this._config.show_playlist !== false;', script)
        self.assertIn("this._nguonHienThi().includes(nguonNho)", script)
        self.assertIn("this._config.show_playlist === false ||", script)
        # Trình sửa: bốn ô tích, và ô tích đọc/ghi bằng .checked chứ không phải .value.
        self.assertIn('id="ed-show-youtube"', script)
        self.assertIn('batTat("ed-show-facebook", "show_facebook");', script)
        self.assertIn('tich("ed-show-playlist", config.show_playlist);', script)
        self.assertIn('media_content_type: item.media_content_type', script)
        self.assertIn('callService("media_player", "volume_set"', script)
        self.assertIn('this._skip(-1)', script)
        self.assertIn('this._transport("media_play_pause")', script)
        self.assertIn('this._skip(1)', script)
        self.assertIn("this._renderSpeakerVolumes(", script)
        # 0.9: the integration advances the queue (no browser needed); the card
        # must not advance speakers itself or songs would be skipped twice.
        self.assertNotIn("_checkAutoAdvance", script)
        self.assertIn("this._onSpeakerAdded(entityId)", script)
        self.assertIn("this._onSpeakerRemoved(entityId)", script)
        self.assertIn("if (this._manualSelection) return;", script)
        self.assertIn('class="speaker-volumes"', script)
        self.assertIn('callService("media_player", "media_stop"', script)
        self.assertIn('callService("tritue_youtube_player", "stop_session"', script)
        self.assertIn('callService("tritue_youtube_player", "remove_players"', script)
        self.assertIn('callService("tritue_youtube_player", "skip"', script)
        self.assertIn('aria-label="Tìm tên bài hát hoặc ca sĩ"', script)
        self.assertIn('aria-label="Bài trước"', script)
        self.assertIn('class="ctl main play-pause"', script)
        self.assertIn('aria-label="Bài tiếp theo"', script)
        # One player block: now playing, the card's video, controls and volumes together.
        self.assertIn('<section class="player" aria-label="Đang phát">', script)
        self.assertNotIn('class="now-playing"', script)
        self.assertNotIn("Điều khiển các thiết bị đã chọn", script)
        # Sessions (one per group of speakers) come from the virtual player's attribute.
        self.assertIn("attributes?.sessions", script)
        self.assertIn("_focusedSession()", script)
        self.assertIn("this._lastTicked = entityId;", script)
        self.assertIn("join: true", script)
        self.assertIn('class="progress" hidden', script)
        self.assertIn("this._updateProgress()", script)
        self.assertIn('class="pill device-sound"', script)
        self.assertIn('class="pill screen-off"', script)
        self.assertIn("this._toggleSoundHere()", script)
        self.assertIn("session_revision", script)
        self.assertIn("output_entity_ids", script)
        self.assertIn("queuePosition", script)
        self.assertIn("this._applySharedOutputs()", script)
        self.assertIn("this._selectedPlayers = new Set(sharedOutputs)", script)
        # 0.26.10: chữ ký không đổi VẪN phải chọn lại nếu lựa chọn đã trôi mất. Khởi
        # động lại Home Assistant → loa «unavailable» một lúc → «_syncPlayers» xoá nó
        # khỏi danh sách đang chọn; loa trở lại nhưng phiên vẫn là phiên cũ nên chữ ký
        # y hệt và cổng canh thoát sớm → loa không bao giờ được chọn lại.
        self.assertIn(
            "const duLoa = sharedOutputs.every((entityId) => this._selectedPlayers.has(entityId));",
            script)
        self.assertIn(
            "if (!sharedOutputs.length || (marker === this._sharedSessionMarker && duLoa)) return;",
            script)
        self.assertIn("source,\n        target: item.url || item.id,", script)
        self.assertIn("this._syncNowPlaying()", script)
        # Hidden players: loaded from and saved to the integration's HA storage.
        self.assertIn('callApi("GET", "tritue_youtube_player/hidden_players")', script)
        # 0.15: từ khoá và video gắn sẵn lấy từ tích hợp, không nằm trong YAML của
        # từng thẻ — thêm hay bớt card đều không mất dữ liệu.
        self.assertIn('callApi("GET", "tritue_youtube_player/suggestions")', script)
        self.assertIn('callApi("POST", "tritue_youtube_player/suggestions"', script)
        self.assertIn('action: "add_tag"', script)
        self.assertIn('action: "add_group"', script)
        self.assertIn('action: "pin_song"', script)
        # Chữ ký vẽ lại PHẢI gồm dữ liệu của nhà, nếu không thì đúng lúc nhận được
        # từ khoá mới lại là lúc bỏ qua việc vẽ lại.
        self.assertIn("this._goiY ? JSON.stringify(this._goiY)", script)
        self.assertIn('callApi("POST", "tritue_youtube_player/hidden_players"', script)
        self.assertIn("this._loadHiddenPlayers()", script)
        self.assertIn("!this._hiddenPlayers.has(entityId)", script)
        self.assertIn("this._renderHiddenPlayers(", script)
        self.assertIn("this._setHidden([entityId], true)", script)
        self.assertIn("this._setHidden(entityIds, false)", script)
        self.assertIn("this._showHidden = false;", script)
        # Watch the YouTube video on the card itself.
        self.assertIn('class="video-frame" hidden', script)
        # One play button per result: speakers when chosen, otherwise the video on the card.
        self.assertIn("this._openVideo(item, { withSpeakers: false })", script)
        self.assertNotIn("watch-result", script)
        # The card drives the embed over postMessage, so its buttons work for the video.
        self.assertIn("enablejsapi", script)
        self.assertIn("event.origin !== embedGoc", script)
        self.assertIn('this._videoCommand([1, 3].includes(this._video.state) ? "pauseVideo" : "playVideo")', script)
        self.assertIn("this._togglePlay()", script)
        # Speakers + video: the picture is muted and follows the speaker's position;
        # a speaker joining a video being watched seeks to it when it can.
        self.assertIn("this._syncVideo()", script)
        self.assertIn("this._seekPicture(speakerTime)", script)
        # 0.26.3: đồng hồ dẫn phải ĐANG CHẠY mới được kéo đồng hồ theo. Đo trên clip
        # quay màn hình iPhone: phần tử âm thanh báo "không tạm dừng" nhưng currentTime
        # đứng ở 0, nên vòng đồng bộ tua video YouTube về 0 mỗi 4 giây — đúng lỗi
        # "phát cứ về 0 liên tục". Không có dòng này thì lỗi quay lại mà không ai biết.
        self.assertIn(
            "const tiengDangChay = this._tiengGiayTruoc !== undefined"
            " && giayTieng !== this._tiengGiayTruoc;", script)
        self.assertIn(
            "if (!audio.paused && tiengDangChay && Date.now() >= this._lastVideoSeekAt + 4000",
            script)
        # 0.26.4: luồng MỞ ĐƯỢC NHƯNG KHÔNG CHẢY không bắn sự kiện nào — phần tử âm
        # thanh chỉ có play/pause/ended/error — nên phải tự đo mới thấy. Chủ máy gặp
        # trên iPhone với CẢ add-on lẫn c2a, và cả trên Safari: lỗi ở thẻ.
        # 0.26.8: CHƯA TẢI XONG khác hẳn KẸT. Số liệu thật từ máy chủ máy: nap=0 mang=2
        # loi=0 — đang tải, chưa có byte nào, không lỗi. Đường phục hồi chỉ dành cho ca
        # "có dữ liệu mà đồng hồ đứng"; nổ lúc chưa có dữ liệu là cướp tiếng của một
        # luồng có thể đang chạy, đưa về khung YouTube — mà iOS treo khung ấy khi tắt
        # màn, nên chính bản sửa lại làm mất đúng tính năng người dùng cần.
        self.assertIn("const coDuLieu = audio.readyState >= 2;", script)
        self.assertIn("if (!audio.paused && coDuLieu && doiQua > 8000) {", script)
        self.assertIn("if (!audio.paused && !coDuLieu && doiQua > 12000) {", script)
        # 0.26.12: người dùng bấm "xem" thì GIỮ HÌNH. Bản 0.26.9 đóng hình để nhường
        # tiếng, và chủ máy báo ngay "bật video để xem thì không được trên iOS"; clip
        # gửi kèm cho thấy sau khi đóng hình thì tiếng VẪN đứng ở 0:00 suốt ~30 giây,
        # tức gỡ khung video không hề giúp gì. Chọn theo Ý ĐỊNH đã nêu, thay vì tự ý
        # quyết thay người dùng rồi vứt mất một nửa yêu cầu.
        self.assertIn("if (video.open && video.followsDevice) {", script)
        self.assertIn("iPhone không cho vừa xem video vừa nghe khi tắt màn hình.", script)
        # Phần tử âm thanh phải NẰM TRONG tài liệu: «new Audio()» sinh ra phần tử đứng
        # ngoài DOM, và WebKit có thể không bao giờ bắt đầu tải cho phần tử như vậy.
        # 0.26.21 — TRẢ ĐƯỜNG TIẾNG VỀ ĐÚNG BẢN 0.26.2.
        # Chủ máy đo trên máy thật: bản cũ nghe được, loạt bản "sửa cho iOS"
        # (0.26.13–0.26.20) thì không, và còn làm hỏng cả Android. Đã thử mô hình
        # mới ba lần vẫn hỏng, nên theo đúng quy ước "sai một chỗ hai lần thì dừng":
        # không chữa tiếp, trả về nguyên trạng cái đang chạy được.
        # Mô hình đúng: MỘT phần tử sống lâu, mở khoá bằng đoạn im lặng NGAY TRONG
        # cú chạm, rồi đổi «src» khi có địa chỉ.
        self.assertIn("const SILENCE = ", script)
        self.assertIn("audio.src = SILENCE;", script)
        self.assertIn("  unlock() {", script)
        self.assertIn("audio.src = url;", script)
        # «real()» phân biệt bài thật với đoạn im lặng bằng chính địa chỉ — đây là
        # thứ giữ cho vòng đồng bộ video KHÔNG đụng vào khung lúc còn đang chờ.
        self.assertIn('return src && !src.startsWith("data:") ? this.element : null;', script)
        # Mô hình mới phải bị gỡ HẲN, không để sót nửa vời.
        self.assertNotIn("goPhanTu", script)
        self.assertNotIn("daChay", script)
        self.assertNotIn('nguon.type = kieu', script)
        # Thứ DUY NHẤT giữ lại từ đợt làm lại: lớp nhớ địa chỉ luồng. Nó nằm BÊN
        # TRONG «streamUrl» nên không đụng một dòng nào của đường phát, mà vẫn bỏ
        # được quãng chờ 1,5–2,6 giây hỏi máy chủ sau mỗi cú chạm.
        self.assertIn("async chuanBi(item) {", script)
        # 0.26.28: bài PHÁT TRỰC TIẾP không nghe riêng được bằng thẻ <audio>. Đo trên
        # c2a, đúng bài chủ máy gặp lỗi: thời lượng = None, luồng giải ra là
        # …/playlist/index.m3u8 (bản kê HLS), mà máy chủ lại khai là audio/mp4.
        # Chrome không phát được HLS bằng thẻ audio nên trả NotSupportedError — đúng
        # nghĩa, nhưng người dùng chỉ thấy một mã lỗi kỹ thuật.
        # Nhận dạng bằng THỜI LƯỢNG, không phải đuôi địa chỉ: lúc bấm nghe thì chưa
        # có địa chỉ, mà bài trực tiếp thì không có thời lượng.
        self.assertIn("laTrucTiep(item) {", script)
        self.assertIn("return !Number(item?.duration);", script)
        self.assertIn("đang phát trực tiếp nên không nghe riêng", script)
        self.assertIn("|| this.laTrucTiep(item)) return;", script)
        # 0.26.29: bấm NGHE một bài trực tiếp thì CHUYỂN SANG XEM, đừng bỏ qua — chủ
        # máy chốt "thì sẽ không phải bỏ qua". Bài trực tiếp chỉ có bản kê HLS mà thẻ
        # <audio> không phát được, nhưng KHUNG YOUTUBE thì phát tốt, nên mở hình lên
        # là có tiếng ngay. Đường ra loa không vướng gì: đo được bản kê dùng địa chỉ
        # tuyệt đối nên loa Cast tự lấy từng đoạn.
        self.assertIn("if (!watch && isVideo && deviceAudio.laTrucTiep(item)) {", script)
        self.assertIn("đã mở hình để nghe", script)
        self.assertIn("async layLuong(item) {", script)
        self.assertIn("if (ban && Date.now() - ban.luc <= 240000) return ban.url;", script)
        self.assertIn("deviceAudio.chuanBi({ ...item, source: item.source || this._source })", script)
        self.assertIn("if (ke) this.chuanBi(ke);", script)
        # Thử phát lại một lần sau 3 giây — cái mẹo người dùng iPhone tự tìm ra
        # ("lượn qua app khác rồi quay lại thì lại phát"), nay làm tự động. Đây là
        # phần DUY NHẤT của đợt sửa iOS còn giữ lại, vì nó chỉ NHẮC LẠI lệnh phát
        # chứ không đổi cách dựng phần tử — thứ đã đo được là làm hỏng cả Android.
        self.assertIn("this.thuLaiTimer = setTimeout(() => {", script)
        # 0.26.15: số đo «mo_khoa=ok» chứng minh phần tử ĐÃ được phép phát mà vẫn
        # không tải — tức iOS đòi lệnh phát nằm TRONG cú chạm, không phải chỉ cần
        # từng được phép. Nút ▶ là cú chạm ấy, nên lúc kẹt nó phải PHÁT LẠI chứ
        # không được đi tạm dừng một thứ vốn đã đứng im.
        self.assertIn("if (!audio.paused && audio.readyState === 0) {", script)
        self.assertIn("chạm nút ▶ để bắt đầu", script)
        # Canh tiếng phải nằm trong «deviceAudio», KHÔNG phải trong vòng đồng bộ video:
        # vòng ấy thoát ngay khi không có video, nên đúng ca "chỉ nghe" lại mất sạch
        # số đo — chủ máy báo "chỉ nghe không chạy thanh thời gian" mà không dòng chẩn
        # đoán nào hiện ra.
        self.assertIn("canhTieng(audio, generation) {", script)
        # 0.26.22 — TÁCH iOS KHỎI ANDROID, đúng lời chủ máy: "xem tách riêng iP và
        # Android ra". Hai hẹn giờ của bộ canh tiếng dựng lên từ hành vi WebKit;
        # trên Android chúng chỉ có thể gây hại (chen vào luồng đang tải, và báo
        # hỏng oan sau 12 giây). Từ đây thứ gì riêng cho iOS phải đi qua cổng này.
        self.assertIn("const laIOS = () => {", script)
        # 0.26.32: cổng này nay là «laTao» — iPhone, iPad VÀ Safari trên máy Mac,
        # vì cả ba cùng chạy WebKit. Xem phần 0.26.32 bên dưới để biết số đo.
        self.assertIn("if (!laTao()) return;", script)
        # 0.26.26: trên iOS thì ĐỪNG cướp tiếng của khung YouTube. «_soundFromDevice»
        # tắt tiếng khung rồi giao việc phát cho phần tử âm thanh — mà trên iOS phần
        # tử ấy đo được là không bao giờ tải. Kết quả: khung câm, phần tử im, không
        # nghe gì. Chủ máy gửi ảnh đúng cảnh đó: "trên iP phải bật biểu tượng loa mới
        # nghe được, mặc định tắt tiếng".
        # Giả lập với user-agent iPhone: không cướp tiếng, gửi unMute + playVideo,
        # soundHere vẫn true. Với user-agent máy bàn: hành vi cũ, không đổi.
        self.assertIn("if (!video.withSpeakers && !laTao()) {", script)
        # 0.26.30 — CHÉP TỪ MỘT BẢN CÀI ĐÃ CHẠY ĐƯỢC. Chủ máy đưa thẻ phicomm-r1-card
        # kèm "dùng trên iPhone nghe nhạc, xem video trên iPhone bình thường". Đọc mã
        # nó thì ra điều tìm cả ngày: nó KHÔNG phát nhạc bằng thẻ <audio> bao giờ.
        # Nhạc luôn ở khung YouTube; phần tử âm thanh chỉ phát một dòng IM LẶNG lặp
        # vô hạn để iOS coi trang là đang có tiếng và không cắt khi tắt màn.
        # Từng chi tiết đều có lý do, đừng "dọn" cho gọn:
        #   dao động 20 Hz + âm lượng 0,0001 → vô thanh nhưng là tiếng THẬT;
        #   loop → dòng không bao giờ kết thúc nên trạng thái phát không rụng;
        #   webkit-playsinline → Safari đời cũ chỉ hiểu tên này;
        #   1×1 điểm ảnh, mờ 0,01, KHÔNG display:none — WebKit bỏ qua media ẩn hẳn.
        # Đo trong WebKit thật: chạy liên tục, đồng hồ tiến 2,51s trong 2,5s thực.
        self.assertIn("async _giuTiengNen() {", script)
        self.assertIn("osc.frequency.setValueAtTime(20, this._nenCtx.currentTime);", script)
        self.assertIn("gain.gain.setValueAtTime(0.0001, this._nenCtx.currentTime);", script)
        self.assertIn('nen.setAttribute("webkit-playsinline", "");', script)
        self.assertIn("nen.loop = true;", script)
        self.assertIn('opacity: "0.01",', script)
        self.assertNotIn('nen.style.display = "none"', script)
        self.assertIn('navigator.wakeLock.request("screen")', script)
        # Và đường iOS phải GIỮ TIẾNG TRONG KHUNG, không chuyển sang phần tử âm thanh
        # — đó là chỗ mọi bản trước hỏng.
        # 0.26.34: điều kiện là NỀN TẢNG, không phải "có loa hay không". Có loa hay
        # không thì WebKit vẫn không tải nổi phần tử âm thanh, nên vừa ra loa vừa nghe
        # trên máy nhà Táo cũng phải giữ tiếng trong khung.
        # 0.26.57 thêm «&& video.state === 1»: dòng im lặng giữ nền chỉ được bật khi
        # khung ĐANG chạy, nếu không nó giành mất chỗ phát của khung trên iOS.
        self.assertIn(
            "if (on && laTao() && video.open && video.soundHere && video.item"
            " && video.state === 1) {",
            script,
        )
        # Và đường nhanh phải NHƯỜNG khi máy không phải nhà Táo mà đang bật nghe-khi-
        # tắt-màn: khung nhúng bị treo lúc trang ẩn, chỉ phần tử âm thanh còn chạy.
        self.assertIn("if (listenScreenOff() && !laTao()) return false;", script)
        # 0.26.27: lời nhắn phải ĐÚNG MÁY ĐANG CẦM. Chủ máy gửi ảnh điện thoại
        # Android mà hiện câu nói về iPhone — vừa sai vừa khiến người đọc đi tìm
        # nhầm chỗ. Giới hạn "một luồng một lúc" là của iOS; trên Android mà nhánh
        # này nổ thì nguyên nhân khác, nên phải nói khác VÀ kèm số đo để lần sau
        # biết ngay vì sao, thay vì lại đoán.
        self.assertIn("this._setStatus(laIOS()", script)
        self.assertIn("Chưa lấy được tiếng để nghe khi tắt màn hình", script)
        # iPad đời mới khai user-agent giống Mac — phải hỏi thêm màn cảm ứng.
        self.assertIn('return /Mac/.test(ua) && typeof document !== "undefined" && "ontouchend" in document;', script)
        # 0.26.25: chốt «_nhipDoDuoc» trở lại, nhưng CHỈ ở vòng kéo HÌNH, và lần này
        # có bằng chứng. Giả lập dựng đúng số đo của loa trong nhà (media_position = 0,
        # mốc thời gian không đổi): hình đang ở giây 1–8 bị quăng tới giây 91 rồi 97,
        # cứ ~5 giây một lần. Cú tua xảy ra cả khi chỉ ra loa, nhưng lúc hình còn câm
        # thì không ai để ý — nên chủ máy thấy "ra loa bình thường, nghe cả hai nơi
        # thì lỗi video".
        #   có chốt: A=0 tua, B=0 tua (vẫn unMute cho máy), loa khoẻ=2 tua.
        # Vòng kéo TIẾNG cố ý KHÔNG chốt: nó là thứ duy nhất giữ tiếng trên máy đi
        # cùng loa — chốt cả hai (bản 0.26.22) thì mất đồng bộ, gỡ cả hai (bản
        # 0.26.24) thì hình lại bị quăng. Đúng MỘT nơi gọi.
        self.assertIn("_nhipDoDuoc(entityId) {", script)
        self.assertIn("Date.now() - luc <= 10000", script)
        self.assertEqual(script.count("this._nhipDoDuoc("), 1)
        # BA đường nghe, mỗi đường tự canh: nghe một mình, nghe kèm loa, và (0.26.39)
        # đường phát NGAY TRONG CÚ BẤM khi địa chỉ luồng đã xin sẵn. (Đợt 0.26.18 từng
        # gộp về một qua «batDau»; bản ấy đã được trả về nguyên trạng 0.26.2 vì đo trên
        # máy thật thấy nó không nghe được.)
        self.assertEqual(script.count("this.canhTieng(audio, generation);"), 3)
        # 0.26.44 — ĐỪNG NHẢY VÀO GIỮA BÀI NGAY TỪ ĐỊA CHỈ. Số đo từ máy chủ máy
        # 21/09/2026 (hộp đen ghi vào nhật ký HA): đặt «#t=» rồi phát thì phần tử đứng ở
        # «nap=1» suốt tám giây — chỉ có phần mô tả tệp, không một mẫu âm thanh nào ở chỗ
        # đang phát, nên máy im dù đồng hồ vẫn nhích. Cùng lúc ấy đường phát TỪ ĐẦU đạt
        # «nap=4» và chạy ngon. Nay nạp từ đầu rồi chỉ nhảy khi ĐÃ CÓ dữ liệu thật.
        self.assertNotIn("#t=${Math.floor(batDau)}", script)
        self.assertIn("  nhayKhiSanSang(audio, batDau) {", script)
        self.assertIn('audio.addEventListener("canplay", nhay, { once: true });', script)
        self.assertIn("if (audio.readyState < 3 || audio.currentTime >= batDau - 0.5) return;", script)
        # Hai số đo thêm để phân định phần còn lại: đã chọn được nguồn phát chưa, và
        # phần tử có nằm trong trang không.
        self.assertIn("nguon=${audio.currentSrc ? 1 : 0} dom=${audio.isConnected ? 1 : 0}", script)
        # 0.26.6: khi bắt được tình trạng "mở được nhưng không chạy" thì phải in kèm SỐ
        # LIỆU của chính phần tử âm thanh. Không có bốn số này thì chỉ còn đường đoán,
        # mà ba nguyên nhân khả dĩ (chờ dữ liệu / bị chặn phát / lỗi giải mã) cần ba
        # cách sửa khác hẳn nhau.
        self.assertIn("nap=${audio.readyState} mang=${audio.networkState}", script)
        self.assertIn("loi=${audio.error ? audio.error.code : 0} giay=", script)
        # ĐO BẰNG THỜI GIAN, KHÔNG ĐẾM NHỊP: _syncVideo còn chạy mỗi lần hass đổi
        # trạng thái (nhiều lần mỗi giây), đếm nhịp là báo nhầm ngay.
        self.assertIn(
            "if (tiengDangChay || audio.paused || this._tiengChayLuc === undefined)"
            " this._tiengChayLuc = Date.now();", script)
        # Đường phục hồi dùng CHUNG cho hai ca (lấy luồng hỏng, và luồng kẹt), không chép đôi.
        self.assertIn("_traTiengVeKhung() {", script)
        # BA nơi gọi, không phải hai: luồng lấy hỏng, luồng có dữ liệu mà đứng im, và
        # (từ 0.26.12) luồng chưa tải được trong lúc người dùng đang XEM — cả ba đều
        # trả tiếng về khung thay vì chép lại đoạn xử lý.
        self.assertEqual(script.count("this._traTiengVeKhung();"), 3)
        self.assertIn("this._speakerJoinsVideo(entityId)", script)
        # Loa tích vào khi đang xem: nguồn lấy từ CHÍNH bài đang xem. Gắn cứng "youtube"
        # thì xem Facebook rồi tích loa sẽ hỏi sai khả năng của loa và gửi địa chỉ
        # Facebook kèm nhãn nguồn YouTube.
        self.assertIn('const nguon = item.source || "youtube";', script)
        self.assertIn("this._supportsSource(entityId, nguon)", script)
        self.assertIn("source: nguon,", script)
        self.assertIn('"media_player", "media_seek"', script)
        self.assertIn("${embedGoc}/embed/${id}", script)
        # 0.26.34 — khung nhúng lấy từ www.youtube.com. Chrome xét quyền tự phát
        # KÈM TIẾNG theo mức gắn bó với chính tên miền ấy, mà nocookie thì không
        # máy nào có. Thẻ phicomm-r1-card dùng youtube.com và nghe được ngay.
        self.assertIn('const EMBED_ORIGIN = "https://www.youtube.com";', script)
        # 0.26.73 — HAI ĐỊA CHỈ NHÚNG. «www.youtube.com» vẫn là mặc định để không
        # đụng vào iPhone đang phát được; nocookie là ĐƯỜNG LUI, chỉ bật khi chính
        # YouTube trả 150/153/101, và bật đúng MỘT LẦN mỗi lần mở trang.
        # Không dò theo tên trình duyệt: máy nào không gặp lỗi thì không đổi gì.
        self.assertIn('const EMBED_GOC_LUI = "https://www.youtube-nocookie.com";', script)
        self.assertIn("let embedGoc = EMBED_ORIGIN;", script)
        self.assertIn("let daDoiGocNhung = false;", script)
        self.assertIn("&& !daDoiGocNhung && this._video.item && this._video.item.id) {", script)
        self.assertIn("daDoiGocNhung = true;", script)
        self.assertIn("embedGoc = EMBED_GOC_LUI;", script)
        # Cờ latch KHÔNG BAO GIỜ được xoá — đó là chỗ 0.26.65 đẻ ra vòng lặp vô tận.
        self.assertNotIn("daDoiGocNhung = false;\n", script.split("let daDoiGocNhung = false;", 1)[1])
        # Đổi địa chỉ phải đứng TRƯỚC nhánh lùi về phần tử âm thanh.
        self.assertLess(
            script.index("embedGoc = EMBED_GOC_LUI;"),
            script.index("deviceAudio.khungHong = true;"))
        # Chỉ cấm ĐỊA CHỈ nhúng cũ; phần chú thích vẫn kể lại vì sao đã đổi.
        self.assertNotIn("youtube-nocookie.com/embed", script)
        # HA pages send "Referrer-Policy: no-referrer" -> YouTube Error 153
        # unless the iframe carries its own policy, set before src.
        self.assertLess(
            script.index('iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin")'),
            script.index('iframe.setAttribute("src", this._ytEmbedSrc(id,'),
        )
        # 0.26.31 — ĐỪNG BẬT TIẾNG CHO MỘT KHUNG ĐANG CÂM BẰNG postMessage.
        # Chủ máy đo trên Android 20/09/2026: "nghe trên máy này mà đang phát ra loa
        # thì bị dừng video, nhưng chọn cả nghe khi tắt màn hình thì không sao".
        # Hai nhánh ấy chỉ khác một điều — nhánh tắt-màn-hình để khung câm nguyên và
        # cho phần tử âm thanh mang tiếng, nhánh kia gửi «unMute». Lý do: cú bấm nằm
        # ở trang THẺ, còn trình phát nằm trong khung youtube.com khác miền, nên cử
        # chỉ người dùng không đi theo lệnh postMessage; trình duyệt thấy một video
        # tự phát đang câm bỗng bật tiếng mà không ai chạm vào, và nó TẠM DỪNG video.
        # Thẻ phicomm-r1-card chạy được trên cả hai máy vì địa chỉ nhúng của nó không
        # hề có tham số «mute» (dòng 1896) — khung sinh ra đã có tiếng sẵn.
        # Nên đường bật tiếng phải DỰNG LẠI khung tại đúng giây đang xem.
        self.assertIn("_batTiengKhung() {", script)
        self.assertIn(
            'iframe.setAttribute("src", this._ytEmbedSrc(id, { muted: false, start: giay }));',
            script)
        # Đường nhanh đổi bài (giữ toàn màn hình) chỉ được đi khi KHÔNG phải bật tiếng
        # cho khung đang câm — nếu không thì mỗi lần chuyển bài lại dính đúng bẫy trên.
        self.assertIn(
            "const phaiBatTieng = this._video.soundHere && this._video.muted !== false;",
            script)
        # Và mọi nơi cần tiếng đều đi qua một cửa: không còn «unMute» đơn độc nào
        # trong các nhánh đổi chế độ (chỉ còn trong «_traTiengVeKhung», nơi đã tạm
        # dừng video trước nên không dính luật tự-phát).
        self.assertNotIn('video.soundHere = true;\n      this._videoCommand("unMute");', script)
        # Bậc thang thúc tiếng 0 / 300 / 800 / 2000 mili giây — chép nguyên của
        # phicomm-r1-card (dòng 1904-1908). Giao diện lập trình của trình phát chưa
        # nhận lệnh ngay lúc khung vừa nạp, nên gửi đúng một lần là rơi vào khoảng
        # chưa ai nghe. Đây là chỗ chữa "trên iPhone phải tự bật biểu tượng loa".
        self.assertIn("this._thucTiengTimers = [300, 800, 2000].map((cho) => setTimeout(thuc, cho));", script)
        # 0.26.31 — ĐANG NGHE TRÊN MÁY MÀ TÍCH LOA thì loa nhận bài ngay. Trước đây
        # «_onSpeakerAdded» chỉ lo ca đang XEM VIDEO; ca chỉ-nghe rơi ra ngoài nên
        # tích loa xong không có gì xảy ra. Chủ máy 20/09/2026: "đang phát mà chọn
        # loa thì phát được luôn âm thanh, không cần phải chuyển bài".
        # «along» là nghe GHÉP theo loa (loa đã có bài rồi) nên phải loại ra.
        self.assertIn("if (deviceAudio.item && !deviceAudio.along) {", script)
        self.assertIn("async _loaNhanBaiDangNghe(entityId) {", script)
        # 0.26.49 — GIAO BÀI CHO LOA XONG PHẢI ĐỔI VAI sang "nghe cùng loa". Từ khi
        # tích loa mà vẫn giữ tiếng trên máy, thẻ còn tự coi là "nghe một mình" trong
        # khi thực tế đã là loa + máy, nên nút "Nghe trên máy này" không hiện lại được
        # — chủ máy 21/09/2026 kèm ảnh chụp 17:24: "đang chỉ nghe, tích vào loa sao
        # không ra chế độ nghe trên máy này". Đổi vai mà KHÔNG đụng vào tiếng đang
        # chạy: không đặt lại «src», không gọi phát lại, nên không có quãng hụt.
        self.assertIn("deviceAudio.along = true;", script)
        self.assertIn("deviceAudio.alongKey = deviceAudio.khoaLuong(item);", script)
        # Nút chỉ ẩn khi KHÔNG có loa nào để chạy theo. Điều kiện cũ ẩn luôn theo
        # «deviceAudio.item», tức ẩn đúng lúc cần nó nhất.
        self.assertIn("sound.hidden = video.open ? !video.withSpeakers : !session?.title;", script)
        self.assertNotIn("sound.hidden = !!deviceAudio.item", script)
        # Đừng cứu lượt nạp của phần tử mà CHÍNH THẺ vừa tắt: «networkState === 0» là
        # không còn nguồn nào. Log HA 21/09/2026 17:25:08 bắt đúng một lần như vậy.
        self.assertIn("&& audio.networkState !== 0;", script)
        # 0.26.75 — ĐO Ở GIÂY 3, CỨU Ở GIÂY 12. «cuuLuotNap» gọi lại load(), mà load()
        # xoá lượt nạp đang chạy: hộp đen iPhone 22/09/2026 cứu đúng giây 3, ngay sau
        # đó «phat=AbortError», giây 8 vẫn «nap=0» — trong khi máy chủ giao byte đầu
        # sau 0,04–0,3 giây. Phép đo bằng fetch không đụng phần tử nên giữ ở giây 3.
        self.assertIn("this.hopDenTimers = [1000, 3000, 8000, 12000].map((cho) =>", script)
        self.assertIn("if (cho === 3000 && chuaCoGi) this.doThuLuong(audio);", script)
        self.assertIn("if (cho === 12000 && chuaCoGi) this.cuuLuotNap(audio);", script)
        self.assertNotIn("this.doThuLuong(audio);\n          this.cuuLuotNap(audio);", script)
        # 0.26.75 — MÁY NHÀ TÁO XEM KHI BẬT CÔNG TẮC: TIẾNG TRƯỚC, HÌNH SAU. Nhánh cũ
        # giữ tiếng trong khung và báo sai "tắt màn vẫn nghe tiếp" (hộp đen 06:21:18:
        # tắt màn ở giây 13,2, bật lại vẫn 13,2). Tổ hợp chạy được đo lúc 06:24:12 là
        # đang nghe rồi mới bật hình — nên đợi tiếng thật sự chạy rồi mới _watchCurrent.
        self.assertNotIn("tiếng giữ trong video nên tắt màn hình vẫn nghe tiếp", script)
        self.assertIn("_moHinhKhiTiengLen(id) {", script)
        self.assertIn("if (a && !a.paused && a.readyState >= 2) {", script)
        self.assertIn("this._syncNowPlaying();\n        this._watchCurrent();", script)
        self.assertIn("if (Date.now() - batDau > 30000) {", script)
        self.assertEqual(script.count("this._moHinhKhiTiengLen(item.id);"), 2)
        # Bật công tắc lúc đang xem MỘT MÌNH thì chuyển tiếng; đang có loa thì giữ
        # đường cũ để không đụng phần đồng bộ với loa.
        self.assertIn("if (on && laTao() && video.open && video.soundHere && !video.withSpeakers", script)
        # 0.26.50 — MÁY NHÀ TÁO "CHỈ NGHE" ĐI BẰNG KHUNG, không bằng phần tử âm thanh.
        # Đo trên iPhone của chủ máy 21/09/2026, TÁM lượt liên tiếp, sau khi đã sửa
        # xong tốc độ luồng: phần tử âm thanh đứng ở «nap=0 mang=2 loi=0 phat=cho» —
        # lệnh phát không bị từ chối mà cũng không được chấp nhận, dữ liệu không bao
        # giờ tới, và KHÔNG lần nào báo lỗi. Cùng lúc «fetch» của chính trang lấy được
        # địa chỉ ấy (206, 107-194ms) lần nào cũng được, và «dem=1m/0k» nên không có
        # gì tranh chấp. Khung thì chạy — chủ máy: "nghe bài ghim bằng video được
        # luôn". Chỉ YouTube mới có khung để mượn, nên Zing/Facebook giữ nguyên đường
        # cũ.
        # 0.26.74 — ĐẢO LẠI: máy nhà Táo NGHE bằng phần tử âm thanh, y như Zing.
        # Đường khung dừng ngay khi khoá màn (hộp đen: «trangthai=2 giay=308.3», 88
        # giây sau vẫn 308.3). Căn cứ để đổi: lệnh load() của 0.26.64 làm phần tử âm
        # thanh chạy trên iPhone (22:00:13, nap=4 phat=ok); app HA cho iOS khai
        # «UIBackgroundModes: audio»; và chủ máy thử bài Zing — chính phần tử này —
        # khoá màn vẫn nghe được.
        self.assertIn("MÁY NHÀ TÁO NGHE NHẠC BẰNG PHẦN TỬ ÂM THANH — Y NHƯ ZING.", script)
        self.assertNotIn('if (laTao() && isVideo && source === "youtube"', script)
        # CHỈ đổi đường NGHE: cửa của «listen» vẫn nhường cho khung khi đang XEM video
        # có tiếng trên máy này, để đường xem không đổi — 0.26.71 đổi cả hai và khung
        # nhấp nháy liên tục.
        self.assertIn("dangXemCoTieng: null,", script)
        self.assertIn('&& typeof this.dangXemCoTieng === "function" && this.dangXemCoTieng()', script)
        self.assertIn("return Boolean(v.open && v.soundHere && !v.soundOnly && !v.withSpeakers);", script)
        # Không được có hẹn giờ tự mượn khung khi tiếng chưa tải — nghi can số một
        # của vòng nhấp nháy ở 0.26.71.
        self.assertNotIn("mượn khung YouTube`", script)
        # Loa Cast mất vài giây mới bắt đầu phát, nên tua phải CHỜ loa báo "playing"
        # rồi mới tua, và chỉ MỘT lần — tua liên tiếp là sinh ra giật.
        self.assertIn("_dongBoLoaVeGiay(entityId, giay, moc) {", script)
        # 0.26.31 — chọn xong bài thì THU GỌN danh sách kết quả, bấm thanh tóm tắt để
        # mở lại. Chủ máy 20/09/2026: "sau khi tìm kiếm mà chọn phát 1 bài xong thì ẩn
        # phần danh sách tìm kiếm đi, sau đó muốn thay đổi bài thì kích vào".
        # Danh sách KHÔNG bị xoá — nó vẫn là hàng chờ phát tiếp.
        self.assertIn('<button class="results-toggle"', script)
        self.assertIn("_thuGonKetQua(item) {", script)
        self.assertIn("this._thuGonKetQua(item);", script)
        # 0.26.32 — SAFARI TRÊN MÁY MAC đi cùng luật với iPhone. Chủ máy đo trên
        # Safari của iMac 20/09/2026 và gửi kèm số: nap=0 mang=3 loi=0 nguon=1 dom=0.
        # «mang=3» là NETWORK_NO_SOURCE — phần tử âm thanh đã BỎ CUỘC không tìm được
        # nguồn phát, dù địa chỉ đã có và không báo lỗi nào. Cùng họ hỏng với iPhone
        # vì cùng là WebKit. Trước đây máy Mac để bàn lọt ra ngoài vì «laIOS» phải
        # hỏi thêm màn cảm ứng để phân biệt iPad với Mac, mà Mac để bàn thì không có
        # — nên nó bị xếp vào nhóm Android và đi đúng con đường đã hỏng.
        self.assertIn("const laSafari = () => {", script)
        self.assertIn("const laTao = () => laIOS() || laSafari();", script)
        # Chrome trên Android cũng khai chuỗi "Safari" trong user-agent, nên phải loại
        # ra — nếu không thì Android bị kéo sang đường của máy nhà Táo.
        self.assertIn('!/Chrome|Chromium|Android|Edg\\//.test(ua)', script)
        # HAI NỀN TẢNG NGƯỢC NHAU, và đây là chỗ chúng tách. Đo 20/09/2026:
        #   - Android: dựng lại khung có tiếng thì Chrome KHÔNG cho tự phát, nó rơi
        #     về nút play của YouTube. Phần tử âm thanh thì chạy.
        #   - Safari/iOS: phần tử âm thanh không tải (mang=3 / mang=2). Khung thì chạy.
        # Nên nhánh khung phải gác bằng laTao(), KHÔNG phải bằng công tắc tắt màn hình.
        # 0.26.34 — HAI NỀN TẢNG NHẬP LẠI LÀM MỘT. Chỗ tách ở trên có từ 20/09/2026,
        # khi khung còn lấy từ youtube-nocookie.com và Chrome không cho nó tự phát
        # kèm tiếng. Nay khung lấy từ www.youtube.com nên cả hai nền tảng đi chung
        # đường khung; giả thuyết ấy sai thì _checkVideoSound tự trả việc về phần
        # tử âm thanh, nên không ai mất tiếng.
        # 0.26.38 — ĐƯỜNG KHUNG CHỈ DÀNH CHO MÁY NHÀ TÁO, và đây là luật đo được chứ
        # không phải đoán. Ảnh chụp Android của chủ máy 21/09/2026: khung dựng lại có
        # tiếng vẫn hiện nút play đỏ kèm "Chạm vào video để phát có tiếng" — Chrome
        # chặn tự phát kèm tiếng, đổi khung sang www.youtube.com KHÔNG thay đổi điều
        # đó (giả thuyết của bản 0.26.34, nay đã bị bác).
        self.assertIn(
            "} else if (video.open && video.withSpeakers && !video.picture && laTao()) {",
            script)
        self.assertIn("} else if (laTao() && this._ngheBangKhung()) {", script)
        # Và Android phải mở khoá phần tử âm thanh NGAY TRONG CÚ BẤM: thử khung trước
        # rồi mới lùi sau vài giây là mở khoá ngoài cử chỉ người dùng, Chrome từ chối
        # thẳng ("Trình duyệt chặn tự phát có tiếng"), tức mất tiếng hoàn toàn.
        self.assertIn("      deviceAudio.entryId = this._entryId();", script)
        self.assertIn("      deviceAudio.startAlong(phien && {", script)
        # 0.26.39 — và lệnh phát phải nằm NGAY TRONG cú bấm ấy khi đã có sẵn địa chỉ
        # luồng: đi qua một «await» là ra ngoài cử chỉ người dùng, Chrome đòi chạm lại.
        self.assertIn("""    const san = item ? this.nhoLuong.get(this.khoaLuong(item)) : null;
    const coSan = !!san?.url && Date.now() - san.luc <= 240000;""", script)
        # 0.26.42 — MỘT CÚ CHẠM CHỈ CHỨNG NHẬN MỘT LẦN PHÁT. Mở khoá bằng đoạn im lặng
        # rồi mới đổi src sang bài thật nghĩa là cú chạm chứng nhận cho đoạn im lặng;
        # bài thật bị coi là tự phát và nằm im (nap=0 mang=2) tới khi app được đánh thức
        # lại — chủ máy 21/09/2026: "vẫn phải ẩn app xuống, bật app khác rồi chọn lại
        # app HA mới hát". Có sẵn địa chỉ thì KHÔNG được phát đoạn im lặng trước.
        self.assertIn("    const audio = coSan ? this.audio() : this.unlock();", script)
        self.assertEqual(script.count("const audio = coSan ? this.audio() : this.unlock();"), 2)
        self.assertIn("if (video.soundOnly) {", script)
        # Ràng buộc cũ đã bỏ: chủ máy báo "Phải bật nghe khi tắt màn hình kèm theo
        # thì mới bật được nghe trên máy này".
        self.assertNotIn("!video.picture && !listenScreenOff()", script)
        # Bấm XEM trong lúc công tắc tắt-màn-hình đang bật: máy nhà Táo giữ tiếng
        # trong khung thay vì giao cho phần tử âm thanh — đúng đường đã đưa chủ máy
        # vào cảnh trong ảnh chụp Safari trên iMac.
        self.assertIn("if (listenScreenOff() && !laTao()) {", script)
        self.assertIn("if (listenScreenOff() && laTao()) {", script)
        # "mất 4s đến 10s mới có tiếng" trên Android: phần lớn quãng ấy là một lượt
        # hỏi máy chủ xin địa chỉ luồng (đo trước: 1,5-2,6 giây). Lấy sẵn cho bài LOA
        # ĐANG PHÁT thì lúc bấm không còn lượt hỏi nào.
        self.assertIn("if (session?.title && !deviceAudio.item) {", script)
        self.assertIn("deviceAudio.chuanBi({", script)
        # 0.26.33 — bấm "Nghe (chỉ tiếng)" là nói rõ KHÔNG muốn hình. Điều kiện cũ
        # gộp hai ý làm một («(watch && isVideo) || this._video.open»): hễ đang mở
        # hình thì bài mới cũng mở hình, bất kể người dùng bấm nút nào. Chủ máy báo
        # 20/09/2026: "giờ chọn chỉ nghe, hình tai nghe, nó lại ra mặc định video".
        # Ý định đã nêu rõ ở nút bấm thì không được đoán lại.
        self.assertNotIn("if ((watch && isVideo) || this._video.open) {", script)
        self.assertIn('BẤM "NGHE (CHỈ TIẾNG)" LÀ NÓI RÕ KHÔNG MUỐN HÌNH', script)
        self.assertIn("this._toggleVideoExpanded()", script)
        # 0.26.11: hình của CHÍNH THẺ (Facebook) thì phóng to vẫn giữ thanh tiến trình
        # và hàng nút. Luật ẩn sinh ra vì khung nhúng YouTube có bộ nút riêng; phần tử
        # «<video>» của thẻ thì «_tryPicture» dựng KHÔNG có bộ nút gốc, nên nhường chỗ
        # cho một bộ nút không tồn tại = mất sạch đường tua.
        self.assertIn(
            ".player:is(.expanded, :fullscreen):not(.picture-on)"
            " :is(.progress, .control-bar, .nghe-hang) { display: none; }",
            script)
        # 0.26.15: ở toàn màn hình, HÌNH lấp kín và điều khiển NỔI LÊN TRÊN. Bản
        # trước cho điều khiển hiện lại nhưng vẫn nằm trong luồng nên nó bóp hẹp
        # khung hình. «aspect-ratio: auto» là bắt buộc: khung hình vốn bị ràng buộc
        # 16:9 nên chỉ «inset: 0» thì vẫn chỉ cao 273/757.
        self.assertIn(
            ".player:is(.expanded, :fullscreen).picture-on > .stage > .video-frame {", script)
        self.assertIn("aspect-ratio: auto;", script)
        # Điều khiển phải mờ theo CÙNG NHỊP với hàng biểu tượng, nếu không thì nút
        # thoát mờ đi mà thanh điều khiển nằm lì.
        self.assertIn(
            ".player.idle:is(.expanded, :fullscreen) :is(.progress, .control-bar)"
            " { opacity: 0; pointer-events: none; }", script)
        # Nút X ở toàn màn hình là THOÁT TOÀN MÀN, không đóng video (đóng xong tiếng
        # vẫn chạy nên người dùng rơi vào chế độ chỉ-nghe mà họ không hề chọn).
        self.assertIn('} else if (player.classList.contains("expanded")) {', script)
        # 0.26.16: ĐỒNG HỒ DẪN PHẢI THẬT SỰ CHẠY thì mới được kéo ai. Hàng rào này có
        # ở nhánh nghe-trên-máy từ 19/09 («tiengDangChay») nhưng HAI nhánh bám loa thì
        # chưa, nên lỗi "kéo về 0 liên tục" còn nguyên một nửa: loa báo kẹt thì cứ 5
        # giây hình bị lôi về chỗ kẹt, và cứ 4 giây tiếng trên máy bị lôi theo.
        # Không thể so con số trần: «_speakerPosition» cộng thêm thời gian trôi nên
        # loa kẹt vẫn trông như đang tiến — phải so với chính nó ở nhịp trước.
        self.assertIn("_dongHoChay(khoa, ai, giay) {", script)
        self.assertIn("const chay = giay - truoc.giay >= troi * 0.5;", script)
        # Giữ mốc cũ khi hai nhịp quá gần nhau. Ghi đè thì mốc luôn mới tinh, quãng
        # trôi không bao giờ đủ lớn để kết luận, và vòng đồng bộ chết hẳn.
        self.assertIn("if (troi < 0.5) return false;", script)
        # 0.26.17 — CHỖ QUYẾT ĐỊNH CA iOS: chỉ làm mới mốc KHI ĐÃ CHỨNG MINH ĐƯỢC.
        # Làm mới mỗi nhịp thì quãng so luôn ngắn, mà trên quãng ngắn một cú nhảy
        # 0 → 0,3 trông y hệt chạy thật — đo được: luồng cứ chạy lại từ đầu vẫn lọt
        # 1/6 lần. Giữ mốc thì quãng so dài thêm mãi và nó không bao giờ đuổi kịp.
        self.assertIn("if (chay) so[khoa] = { ai, giay, luc };", script)
        # Mốc quá cũ (vừa tạm dừng lâu) thì lấy mốc mới, mất đúng một nhịp — nếu
        # không thì sau một lần dừng dài, đồng hồ chạy lại đàng hoàng vẫn bị cấm.
        self.assertIn("luc - truoc.luc > 5000", script)
        # BỐN đường đồng bộ, MỘT hàng rào. Mỗi đường giữ mốc riêng theo khoá: nhiều
        # đường cùng chạy trong một nhịp đẩy trạng thái, xài chung một mốc thì đường
        # sau luôn thấy quãng trôi bằng 0.
        self.assertEqual(script.count("this._dongHoChay("), 3)
        self.assertIn('this._dongHoChay("hinh", nhip, speakerTime)', script)
        self.assertIn('this._dongHoChay("tieng", nhip, speakerTime)', script)
        # Đường iOS: nghe trên máy, xem hình trên thẻ, KHÔNG loa nào cả. Hàng rào cũ
        # chỉ hỏi giây có KHÁC nhịp trước không, mà luồng bị WebKit cắt rồi chạy lại
        # thì giây đổi liên tục — đổi mà chẳng đi tới đâu, nên nó lọt sạch.
        self.assertIn('this._dongHoChay("tieng-may", "may", giayTieng)', script)
        # Vẫn giữ phép thử "có nhúc nhích không" cho bộ dò kẹt: ở đó câu hỏi đúng là
        # "đã chết hẳn chưa", khác hẳn câu "có được phép kéo ai không".
        self.assertIn(
            "const tiengDangChay = this._tiengGiayTruoc !== undefined"
            " && giayTieng !== this._tiengGiayTruoc;", script)
        # NHIỀU LOA: cả ba đường đồng bộ phải đọc CÙNG MỘT loa dẫn nhịp. Trước đây mỗi
        # đường chọn một kiểu, nên hình bám loa này còn thanh tiến trình chạy theo loa
        # kia; và loa đầu danh sách không báo giây là hai vòng kéo đứng im hẳn.
        self.assertIn("_loaDanNhip(session = this._focusedSession()) {", script)
        # Thêm hai nơi gọi so với bản đầu, vẫn là CÙNG một hàm chọn loa dẫn nhịp nên
        # đúng ý luật này: «_ngheBangKhung» (0.26.34) mở khung vào đúng giây của loa,
        # và «_toggleSoundHere» (0.26.39) lấy giây ấy để phát ngay trong cú bấm.
        self.assertEqual(script.count("this._loaDanNhip("), 4)
        # 0.26.11: ghim được bài Facebook, và bản ghi MANG THEO NGUỒN — thiếu nguồn thì
        # phát lại sẽ đi vào đường YouTube rồi chết ở cửa chặn mã 11 ký tự.
        self.assertIn('if (["youtube", "facebook"].includes(item.source || this._source)) {', script)
        self.assertIn('const nguon = song.source === "facebook" ? "facebook" : "youtube";', script)
        self.assertIn("source: dich.item.source || this._source,", script)
        # Ô "dán link để ghim": nguồn suy từ CHÍNH cái link, không còn ghi cứng youtube.
        self.assertIn(
            r'const nguonLink = /facebook\.com|fb\.watch/i.test(link) ? "facebook" : "youtube";',
            script)
        self.assertIn("source: nguonLink,", script)
        # 0.26.7: phóng to thì ẩn HẲN cả cột phải. Chủ máy gửi ảnh iPhone: hàng nguồn và
        # ô tìm kiếm đè lên video đang xoay. Lỗi KHÔNG dựng lại được trong Chrome (lớp
        # phủ che đúng khi đo), nên luật này gỡ bỏ chế độ hỏng chứ không nhắm vào cơ chế.
        # Dùng "> *" theo nguyên tắc: khối mới thêm vào cột sau này tự được che.
        self.assertIn(
            ".player:is(.expanded, :fullscreen) ~ .yt-zone-playlist .yt-playlist-inner > * {",
            script)
        self.assertIn("this._videoFullscreen()", script)
        self.assertIn("[hidden] { display: none !important; }", script)
        # Pasted YouTube links are longer than the 120-character text limit.
        self.assertIn('placeholder="Tìm tên bài hát, ca sĩ hoặc dán link YouTube…"', script)
        self.assertIn('input.maxLength = this._source === "zing" ? 120 : 2048;', script)
        http = (COMPONENT_DIR / "http.py").read_text(encoding="utf-8")
        self.assertIn("if not 1 <= len(query) <= 2048", http)
        self.assertNotIn("eval(", script)

    def test_card_listens_on_the_device_like_c2a(self):
        script = (COMPONENT_DIR / "www" / "tritue-youtube-player-card.js").read_text(encoding="utf-8")
        frontend = (COMPONENT_DIR / "frontend.py").read_text(encoding="utf-8")
        http = (COMPONENT_DIR / "http.py").read_text(encoding="utf-8")

        # Two buttons per song: watch the video, listen (sound only).
        self.assertIn('action("mdi:television-play", "Xem video", true);', script)
        self.assertIn('action("mdi:headphones", "Nghe (chỉ tiếng)", false);', script)
        # The device's sound comes from the player server through HA.
        self.assertIn('callApi("POST", "tritue_youtube_player/stream"', script)
        self.assertIn("hass.http.register_view(TriTueStreamView)", frontend)
        self.assertIn('url = "/api/tritue_youtube_player/stream"', http)
        # A video YouTube refuses to embed plays as sound instead of a dead frame.
        self.assertIn('this._videoCommand("addEventListener", ["onError"]);', script)
        self.assertIn("this._embedRefused();", script)
        # Each page the frame loads is handshaken again: words from the page it replaced
        # must not mark the new player ready (it then ignores every command).
        self.assertEqual(script.count('iframe.addEventListener("load", () => this._frameLoaded());'), 2)
        # A refused play() releases the video to its own sound; a superseded one is no error.
        self.assertIn('if (error?.name === "AbortError") return;', script)
        self.assertIn("if (video.open && video.followsDevice && isError && !video.picture) {", script)
        # Facebook không cho nhúng trình phát nên hình đi đường phần tử <video>, mà phần
        # tử ấy LUÔN câm. Không loa thì máy này phải phát tiếng và hình bám theo — thiếu
        # dòng này là xem Facebook không có tiếng, và vì cờ bám-tiếng cũng tắt nhánh tự
        # chuyển bài, thiếu nó còn sinh vòng mở lại bài từ giây 0 khi hình kết thúc sớm.
        self.assertIn("const theoTieng = followsDevice || !withSpeakers;", script)
        self.assertIn("followsDevice: theoTieng,", script)
        self.assertIn(
            "deviceAudio.listen(mucTieng, this._queue.length ? this._queue : [mucTieng],"
            " Math.max(0, this._queueIndex));",
            script,
        )
        # Screen-off listening, off by default: hiding the page pauses the sound.
        self.assertIn('document.addEventListener("visibilitychange"', script)
        self.assertIn('localStorage.getItem(LISTEN_SCREEN_OFF_KEY) === "1"', script)
        # Leaving the dashboard keeps the search and what plays.
        self.assertIn("this._remember();", script)
        self.assertIn("this._restore();", script)

    def test_card_manages_household_playlists(self):
        script = (COMPONENT_DIR / "www" / "tritue-youtube-player-card.js").read_text(encoding="utf-8")
        frontend = (COMPONENT_DIR / "frontend.py").read_text(encoding="utf-8")
        http = (COMPONENT_DIR / "http.py").read_text(encoding="utf-8")
        services = (COMPONENT_DIR / "services.py").read_text(encoding="utf-8")

        self.assertIn("hass.http.register_view(TriTuePlaylistsView)", frontend)
        self.assertIn('url = "/api/tritue_youtube_player/playlists"', http)
        self.assertIn('callApi("POST", "tritue_youtube_player/playlists"', script)
        # A pasted playlist link saves the whole playlist; + adds one song.
        self.assertIn('class="save-playlist"', script)
        self.assertIn('{ action: "import", text: value }', script)
        self.assertIn('{ action: "add", id: playlist.id, items: [target.item] }', script)
        # Speakers play the whole playlist as their queue.
        self.assertIn("...(playlist ? { playlist_id: playlist.id } : {}),", script)
        self.assertIn("vol.Optional(CONF_PLAYLIST_ID): cv.string,", services)

    def test_hidden_players_view_is_registered_and_persisted(self):
        frontend = (COMPONENT_DIR / "frontend.py").read_text(encoding="utf-8")
        http = (COMPONENT_DIR / "http.py").read_text(encoding="utf-8")

        self.assertIn("hass.http.register_view(TriTueHiddenPlayersView())", frontend)
        self.assertIn('url = "/api/tritue_youtube_player/hidden_players"', http)
        # 0.15: từ khoá và video gắn sẵn của cả nhà — lưu ở tích hợp nên mọi bảng
        # điều khiển và mọi máy dùng chung, thêm hay bớt card không mất dữ liệu.
        self.assertIn("hass.http.register_view(TriTueSuggestionsView())", frontend)
        self.assertIn('url = "/api/tritue_youtube_player/suggestions"', http)
        # Hai kho lưu trữ PHẢI khác khoá, nếu không tính năng này ghi đè danh sách
        # thiết bị đã ẩn.
        self.assertIn("STORAGE_KEY as SUGGESTIONS_STORAGE_KEY", http)
        self.assertIn("Store(hass, STORAGE_VERSION, STORAGE_KEY)", http)
        self.assertIn("await self._store.async_save(", http)
        self.assertIn("if user is None or not user.is_admin:", http)

    def test_card_is_auto_registered_and_version_busted(self):
        source = (COMPONENT_DIR / "frontend.py").read_text(encoding="utf-8")

        # Primary path: register a Lovelace resource after HA has started.
        self.assertIn("async_register_static_paths", source)
        self.assertIn("EVENT_HOMEASSISTANT_STARTED", source)
        self.assertIn("async_create_item", source)
        self.assertIn("integration.version", source)
        # Fallback for YAML-mode dashboards / unavailable collection.
        self.assertIn("add_extra_js_url", source)
        manifest = json.loads(
            (COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        self.assertIn("frontend", manifest["dependencies"])

    def test_hop_den_khai_may_nao_va_ban_nao(self):
        """Hộp đen phải nói rõ MÁY NÀO gửi và ĐANG CHẠY BẢN NÀO.

        Thiếu hai thứ này là tôi đứng hình 21/09/2026: nhật ký 18:12:57 ghi đường phần
        tử âm thanh, mà chủ máy có cả iPhone lẫn Android cùng mở thẻ — không biết dòng
        ấy của máy nào nên không kết luận được bản sửa cho iPhone đã chạy chưa.
        Số trong thẻ phải KHỚP manifest, nếu không hộp đen báo nhầm bản còn tai hại hơn
        là không báo.
        """
        script = (COMPONENT_DIR / "www" / "tritue-youtube-player-card.js").read_text(
            encoding="utf-8"
        )
        manifest = json.loads(
            (COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertIn("dauMay() {", script)
        self.assertIn('may=${may} goc=${goc} ban=${PHIEN_BAN_THE}', script)
        # 0.26.69 — ghi luôn ĐỊA CHỈ TRANG. Chủ máy 21/09/2026: "đang nói cùng bài hát
        # nhưng cái chạy được video, cái không". Cùng một video mà iPhone phát được còn
        # Safari trả 153 thì khác biệt nằm ở MÁY, và nghi can rõ nhất là địa chỉ mỗi
        # máy dùng để mở Home Assistant (tên miền hay địa chỉ IP).
        self.assertIn("GHI LUÔN ĐỊA CHỈ TRANG", script)
        # 0.26.70 — KHAI PHIÊN TRUYỀN THÔNG khi tiếng nằm trong khung.
        # Chủ máy gửi ảnh Trung tâm điều khiển iPhone 21/09/2026: "Không phát" — ngay
        # giữa lúc khung đang hát. iOS không biết thẻ đang phát nhạc thì tắt màn là nó
        # treo trang lại như một trang web im lặng. Đó là lý do THẬT của "tắt màn hình
        # vẫn chưa được", không phải dòng im lặng giữ nền.
        self.assertIn("_khaiPhienTruyenThong() {", script)
        self.assertIn('phien.playbackState = v.state === 1 ? "playing"', script)
        self.assertIn('dat("play", () => this._videoCommand("playVideo"));', script)
        self.assertIn("this._khaiPhienTruyenThong();", script)
        self.assertIn(f'const PHIEN_BAN_THE = "{manifest["version"]}";', script)
        # Đường KHUNG của máy nhà Táo cũng phải có hộp đen, nếu không nhánh ấy chạy
        # xong là im lặng tuyệt đối — không cách nào biết nó có phát được không.
        self.assertIn("_hopDenKhungTheoDoi(nhan) {", script)
        self.assertIn('this._hopDenKhungTheoDoi("nghe một mình bằng khung (nhà Táo)");', script)
        # 0.26.52 — KHUNG PHẢI HIỆN RA ĐÃ, thu lại sau khi đã chạy. Hộp đen trên iPhone
        # chủ máy 18:24 ngày 21/09/2026:
        #     chitieng=1 (thu bé)  → trangthai=-1 suốt 8 giây, chưa hề bắt đầu
        #     chitieng=0 (hiện ra) → trangthai=1, giay=2.4, đang chạy
        # iOS đòi một cú chạm vào CHÍNH video, mà khung một điểm ảnh thì không ai chạm
        # vào được — chủ máy: "không tự động phát video nhỉ, phải kích vào".
        # Khung mở ở dạng HIỆN (soundOnly false) để còn chạm được; 0.26.53 gom đoạn
        # này vào «_ngheBangKhungMotMinh» nên chuỗi nằm trên nhiều dòng.
        self.assertIn("      soundOnly: false,", script)
        self.assertIn("_thuKhungKhiDaChay() {", script)
        self.assertIn("this._thuKhungKhiDaChay();", script)
        # 0.26.53 — CHẶN Ở ĐÚNG MỘT CỬA, đừng vá từng nhánh. 0.26.50 chỉ chặn nhánh
        # "bấm chỉ nghe", còn sáu lối khác cùng gọi «deviceAudio.listen»: chuyển bài,
        # mở lại bài đang nghe, khôi phục sau khi tải lại trang… Chủ máy gửi ảnh 18:30
        # ngày 21/09/2026: khung video đang mở MÀ vẫn hiện dòng đỏ của phần tử âm thanh
        # ("nap=0 mang=2 loi=0 nguon=1 dom=1") — hai trình phát cùng chạy, và cái thứ
        # hai báo lỗi. Hậu quả đúng lời chủ máy: "cứ phải lỗi, dừng rồi play lại mới
        # được". Danh sách nhánh thì luôn thiếu; cửa chặn thì không.
        self.assertIn("nhuongChoKhung: null,", script)
        self.assertIn("&& this.nhuongChoKhung(item, queue, index, startAt)) {", script)
        self.assertIn("_ngheBangKhungMotMinh(item, queue, index, batDau = 0) {", script)
        self.assertIn("deviceAudio.nhuongChoKhung = (item, queue, index, batDau) =>", script)
        # 0.26.55 — ba lỗi người dùng báo 21/09/2026 trên iOS, cùng một gốc: từ khi
        # tiếng nằm HẲN trong khung, các đường điều khiển vẫn tác động lên phần tử âm
        # thanh nên không còn chạm tới thứ đang phát.
        # (a) "khi đang nghe youtube mà mở face thì tiếng vẫn còn" — «_xemFacebook»
        #     dùng lại chính ô «.video-frame» mà không gỡ thẻ khung YouTube bên trong.
        self.assertIn("if (this._video.open) this._closeVideo();\n      this._xemFacebook(", script)
        # (b) "stop bằng nút điều khiển không dừng video" — «deviceAudio.item» nay rỗng
        #     nên nhánh dừng cũ không khớp, và nhánh còn lại chỉ gửi «stopVideo».
        self.assertIn("if (!deviceAudio.item && this._video.open && this._video.soundHere", script)
        # (c) "kích vào nghe khi tắt màn hình không được" — nhánh ấy im lặng hoàn toàn,
        #     không cách nào biết nó rơi vào đâu. Nay có hộp đen.
        self.assertIn("bật/tắt nghe-khi-tắt-màn: bật=", script)
        # 0.26.56 — soát NỐT CÁC NÚT CÒN LẠI, cùng lớp lỗi.
        # Nút Phát khi khung chưa khởi động rơi vào «_soundFromDevice», hàm này CÂM
        # khung rồi giao tiếng cho phần tử âm thanh — thứ không bao giờ tải trên
        # WebKit. Đó đúng là "bấm play báo lỗi, rồi play lại thì nghe được".
        self.assertIn("MÁY NHÀ TÁO KHÔNG CÓ ĐƯỜNG TIẾNG NÀO NGOÀI KHUNG", script)
        self.assertIn('      this._videoCommand("playVideo");\n      this._setStatus("Chạm một lần', script)
        # Qua bài phải GIỮ vai "chỉ nghe": mở ra cho chạm được rồi tự thu, y như bài
        # đầu — mở thẳng ở dạng một điểm ảnh là đánh cược iOS không đòi chạm.
        self.assertIn("const dangChiNghe = this._video.soundOnly;", script)
        self.assertIn("if (dangChiNghe) this._thuKhungKhiDaChay();", script)
        # 0.26.57 — DÒNG IM LẶNG GIỮ NỀN chỉ được chạy SAU KHI khung đã phát.
        # iOS chỉ cho một luồng chạy một lúc; bật trước là nó giành mất chỗ của khung.
        # Hộp đen iPhone chủ máy 21/09/2026 bắt đúng tương quan:
        #   21:04:09 (chưa bật giữ nền)   → trangthai 1 sau một giây, nhạc chạy
        #   21:04:15 bật nghe-khi-tắt-màn
        #   21:05:02 và 21:05:22 (đã bật) → trangthai=-1 suốt 8 giây, không chạy
        self.assertIn("DÒNG IM LẶNG GIỮ NỀN CHỈ ĐƯỢC CHẠY SAU KHI KHUNG ĐÃ PHÁT", script)
        self.assertIn(
            "      if (listenScreenOff()) this._giuTiengNen();\n      deviceAudio.hass = this._hass;",
            script,
        )
        # Công tắc ấy cũng chỉ được bật dòng nền khi khung ĐANG chạy.
        self.assertIn("&& video.item && video.state === 1) {", script)
        # 0.26.58 — ĐANG MỞ ĐÚNG BÀI ẤY RỒI THÌ ĐỪNG MỞ LẠI. Dựng lại khung là xoá
        # luôn quyền phát mà cú chạm vừa cấp, nên trình phát tụt về "chưa bắt đầu".
        # Hộp đen iPhone chủ máy 21/09/2026 bắt nhiều cặp mở hai lần cách nhau chưa
        # tới một giây (21:06:30 hai lần, 21:08:15 rồi 21:08:16) và gần như lần nào
        # cũng kết thúc ở trangthai=-1 vĩnh viễn — đó là lý do lúc chạy lúc không.
        self.assertIn("ĐANG MỞ ĐÚNG BÀI ẤY RỒI THÌ ĐỪNG MỞ LẠI", script)
        self.assertIn(
            'String(dangMo.item?.id || "") === String(item.id || "")', script
        )
        # 0.26.59 — KÍCH LÀ CHẠY, KHÔNG BÁO GÌ, KHÔNG HỎI GÌ (chủ máy 21/09/2026).
        # Khung mở ẨN SẴN; chỉ hiện ra nếu quá 2,5 giây vẫn không chịu chạy.
        self.assertIn("MỞ ẨN SẴN", script)
        self.assertIn("      soundOnly: true,\n      startSeconds:", script)
        self.assertIn("QUÁ 2,5 GIÂY VẪN KHÔNG CHẠY", script)
        # 0.26.60 — vòng canh CHỈ được dừng khi khung ĐÓNG. Dòng chặn cũ còn xét
        # «v.soundOnly», viết từ hồi khung mở HIỆN rồi mới thu; nay khung mở ẨN SẴN
        # nên điều kiện ấy đúng ngay nhịp đầu, vòng canh tự tắt và cú "hiện khung ra
        # để chạm" không bao giờ nổ. Hộp đen iPhone 21:29–21:32 ngày 21/09/2026:
        # chitieng=1 suốt tới +8s trong khi trangthai đi 3 rồi tụt về -1.
        self.assertIn("CHỈ DỪNG KHI KHUNG ĐÓNG", script)
        self.assertNotIn("if (!v.open || v.soundOnly) {", script)
        # 0.26.61 — ba lỗi tiếp, đều do tiếng nay nằm TRONG khung.
        # (a) "đang xem video chuyển sang nghe audio không được, ngắt video luôn":
        #     «_listenOnly» gọi listen rồi ĐÓNG khung — mà tiếng nằm trong chính khung
        #     ấy. Máy nhà Táo chỉ được THU khung lại.
        self.assertIn("MÁY NHÀ TÁO: THU KHUNG LẠI, ĐỪNG ĐÓNG", script)
        # (b) "YouTube từ chối nhúng" là kết luận SAI: thẻ bắt mọi mã lỗi của trình
        #     phát. Đo 21/09/2026: ba video chủ máy mở đều playable_in_embed = true,
        #     kể cả bài 1 giờ 25 phút. Chỉ 101 và 150 mới là cấm nhúng.
        self.assertIn('CHỈ 101 VÀ 150 MỚI LÀ "KHÔNG CHO NHÚNG"', script)
        self.assertIn("if (maLoi === 101 || maLoi === 150) {", script)
        self.assertIn("khung báo lỗi: ma=", script)
        # (c) "bật khi nghe màn hình nhưng thoát ra màn hình chính không nghe được":
        #     iOS chỉ cho đánh thức AudioContext TRONG CÚ CHẠM, mà 0.26.57 dời việc
        #     giữ tiếng nền sang một vòng hẹn giờ. Tách đôi: mở khoá trong cú chạm,
        #     phát dòng nền sau khi khung đã chạy.
        self.assertIn("async _moKhoaTiengNen() {", script)
        self.assertIn("MỞ KHOÁ BỘ TRỘN TIẾNG — PHẢI gọi NGAY TRONG CÚ CHẠM", script)
        self.assertEqual(script.count("this._moKhoaTiengNen();"), 3)
        # 0.26.62 — KHÔNG gửi «origin» trong địa chỉ khung nhúng.
        # Hộp đen iPhone chủ máy 21:51–21:52 ngày 21/09/2026 ghi "khung báo lỗi:
        # ma=150" ba lần (150 = chủ video không cho nhúng). Nhưng hỏi thẳng YouTube
        # thì chính những video ấy đều playable_in_embed = true, kể cả bài 1:24:59.
        # Hai điều đó chỉ cùng đúng khi YouTube từ chối vì TRANG GỌI đứng ở địa chỉ IP
        # (app HA ở nhà mở bằng http://172.16.10.200:8123). Thẻ phicomm-r1-card —
        # thứ chạy được trên đúng máy ấy — dựng địa chỉ khung KHÔNG có «origin».
        # 0.26.65 — gửi «origin» hay không ĐỀU có thể bị từ chối, nên thẻ tự thử cả
        # hai. Đo trên iPhone chủ máy 21/09/2026, HA mở bằng địa chỉ IP:
        #   có gửi origin    → lỗi 150 (không cho nhúng từ đây)
        #   không gửi origin → lỗi 153 (không biết ai đang nhúng)
        # Gốc rễ là cái địa chỉ IP, không phải tham số — nhưng thẻ không bắt người
        # dùng đi sửa cấu hình mới nghe được nhạc.
        self.assertIn('if (!this._boOrigin) params.set("origin", location.origin);', script)
        self.assertIn("maLoi === 150 || maLoi === 153 || maLoi === 101", script)
        # 0.26.66 — KHÔNG DÒ QUA LẠI. Hộp đen 22:27:34–22:27:36 ngày 21/09/2026 cho
        # thấy vòng dò của 0.26.65 chạy mấy lần mỗi giây (153 → 150 → 153 …) vì CẢ HAI
        # cách đều tắc khi Home Assistant mở bằng địa chỉ IP. Chủ máy: "lỗi, nhảy loạn
        # xạ lên". Đường lui có thật là phần tử âm thanh kèm «load()» của 0.26.64 —
        # đo được trên chính iPhone ấy lúc 22:00:13: nap=4, phat=ok.
        self.assertIn("KHUNG KHÔNG DÙNG ĐƯỢC Ở NHÀ NÀY — LÙI VỀ PHẦN TỬ ÂM THANH", script)
        self.assertIn("deviceAudio.khungHong = true;", script)
        self.assertIn("if (laTao() && !this.khungHong && typeof this.nhuongChoKhung === \"function\"", script)
        self.assertNotIn("this._boOrigin = !this._boOrigin;", script)
        # 0.26.67 — chép Y NGUYÊN bộ tham số của «phicomm-r1-card», thứ chạy được trên
        # đúng iPhone này ở đúng địa chỉ IP này. Đo từ máy chủ 21/09/2026 không phân
        # giải được (trang nhúng trả về bình thường cho cả năm kiểu khai báo), nghĩa là
        # YouTube quyết định ngay trong trình duyệt — nên chép thứ đang chạy được.
        self.assertIn("CHÉP Y NGUYÊN BỘ THAM SỐ CỦA «phicomm-r1-card»", script)
        self.assertNotIn('cc_load_policy: "0"', script)
        self.assertIn("accelerometer; autoplay; clipboard-write;", script)
        # 0.26.68 — TẮT MÀN LÀ WEBKIT TẠM DỪNG KHUNG, phải bảo nó chạy tiếp.
        # Hộp đen iPhone chủ máy 22:42:37 và 22:42:47 ngày 21/09/2026 ghi đúng khoảnh
        # khắc tắt màn: trangthai=2 (đang tạm dừng), trong khi dòng giữ nền vẫn chạy
        # (nen=1) và công tắc vẫn bật (congtac=1). Dòng im lặng giữ được TRANG sống
        # nhưng không ngăn WebKit dừng KHUNG.
        # Thẻ phicomm-r1-card làm ba việc ở đúng lúc này; thẻ ta mới làm một.
        self.assertIn("_giuKhungChayKhiAn() {", script)
        self.assertIn('navigator.mediaSession.playbackState = "playing";', script)
        self.assertIn('if (this._video.state !== 1) this._videoCommand("playVideo");', script)
        # Và đừng kết tội cú thu khung khi thủ phạm là màn hình tắt.
        self.assertIn("MÀN HÌNH ĐANG TẮT THÌ ĐỪNG KẾT TỘI CÚ THU KHUNG", script)
        # 0.26.63 — đường giữ tiếng nền phải TỰ NÓI ĐƯỢC nó chạy hay hỏng, và phải
        # có đường lui khi bộ trộn tiếng chưa thức.
        self.assertIn("giữ tiếng nền: bắt đầu", script)
        self.assertIn("giữ tiếng nền HỎNG:", script)
        self.assertIn("BỘ TRỘN CHƯA THỨC THÌ ĐỪNG DÙNG DÒNG CỦA NÓ", script)
        self.assertIn('if (this._nenCtx.state === "running" && this._nenCtx.createMediaStreamDestination) {', script)
        # «resume()» treo vô thời hạn thì cả đường giữ nền chết lặng.
        self.assertIn("new Promise((xong) => setTimeout(xong, 2000)),", script)
        # Và phải ghi lại ĐÚNG LÚC màn hình tắt — lúc mọi thứ hỏng mà không ai thấy.
        self.assertIn("_theoDoiTatMan() {", script)
        # 0.26.64 — máy nhà Táo cần một lệnh nạp TƯỜNG MINH trước khi phát.
        # Đặt «src» rồi gọi thẳng «play()» thì WebKit nằm ở nap=0 mang=2; nhưng cú tự
        # cứu (load() rồi play()) thì chạy: hộp đen iPhone 22:00:11 ngày 21/09/2026
        # ghi "cứu lượt nạp" rồi hai giây sau "nap=4 … phat=ok", giây đi 0,3 → 3,3.
        # Nguồn không phải YouTube (Zing, Facebook) không có khung để mượn nên bắt
        # buộc đi đường này.
        self.assertIn("MÁY NHÀ TÁO CẦN MỘT LỆNH NẠP TƯỜNG MINH", script)
        self.assertIn("    if (laTao()) {\n      try {\n        audio.load();", script)
        self.assertIn("màn hình ${document.visibilityState === \"hidden\" ? \"TẮT\" : \"BẬT lại\"}", script)
        # Chỉ nghe phải TRÔNG NHƯ nghe nhạc: có tên bài, ảnh bìa, và còn nút Xem.
        self.assertIn("CHỈ NGHE BẰNG KHUNG THÌ TRÔNG NHƯ NGHE NHẠC", script)
        self.assertIn("if (video.open && video.soundOnly && video.item && !video.withSpeakers) {", script)
        # Bấm Xem chỉ BUNG khung ra, không dựng lại (dựng lại là mất quyền phát).
        self.assertIn("ĐANG CHỈ NGHE BẰNG KHUNG: bấm Xem chỉ là bung khung ấy ra", script)
        # Không còn hộp thoại chen ngang lúc đang phát.
        self.assertIn("BẤM CÁI NÀO LÀ CÁI ĐÓ CHẠY, KHÔNG HỎI LẠI", script)
        self.assertNotIn("Xem hình khi ở ngoài mạng nhà", script)

    def test_duong_cua_the_phai_gui_dia_chi_va_khong_nuot_ma_loi(self):
        """Đường lấy luồng của THẺ phải gửi gợi ý địa chỉ, y như đường ra loa.

        Add-on nằm sau NAT của Supervisor: mọi lời gọi của tích hợp tới nó đều từ
        172.30.32.1, dải mà chính add-on từ chối (loa không với tới được), nên nó
        KHÔNG BAO GIỜ tự học ra địa chỉ dùng được. Thiếu gợi ý thì nó trả 409
        «public_base_url_required».

        Đo trên máy .28 (add-on 0.9.7) ngày 21/09/2026: nhật ký add-on ghi
        «POST /api/integration/stream 409» cho MỌI nguồn — kể cả Zing vốn không dùng
        yt-dlp — trong khi tích hợp quy hết về 502 «stream_unavailable» nên thẻ chỉ
        hiện "Không lấy được tiếng bài này". Mã thật bị giấu, và người soát lỗi đi tìm
        yt-dlp suốt một tiếng.
        """
        source = (COMPONENT_DIR / "http.py").read_text(encoding="utf-8")

        self.assertIn("from .actions import speaker_base_url", source)
        self.assertIn(
            "public_base_url=speaker_base_url(hass, entry.runtime_data.client),", source
        )
        # Mã lỗi của máy phát phải ra tới ngoài, không bị thay bằng một mã chung.
        self.assertIn("except YouTubePlayerApiError as loi:", source)
        self.assertIn('ma = str(loi).strip() or "stream_unavailable"', source)
        self.assertIn("return self.json({\"error\": ma}, HTTPStatus.BAD_GATEWAY)", source)

    def test_http_dependency_and_service_description_are_packaged(self):
        manifest = json.loads(
            (COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        services = (COMPONENT_DIR / "services.yaml").read_text(encoding="utf-8")

        self.assertIn("http", manifest["dependencies"])
        self.assertIn("play_on_players:", services)
        self.assertIn("multiple: true", services)
        self.assertIn("- http", services)
        self.assertIn("media_content_type:", services)

    def test_native_play_media_records_its_physical_output(self):
        source = (COMPONENT_DIR / "media_player.py").read_text(encoding="utf-8")

        self.assertIn("client.async_update_session", source)
        self.assertIn("[self.target_entity_id]", source)

    def test_manifest_key_order_matches_hassfest(self):
        manifest = json.loads(
            (COMPONENT_DIR / "manifest.json").read_text(encoding="utf-8")
        )

        self.assertEqual(
            [
                "domain",
                "name",
                "codeowners",
                "config_flow",
                "dependencies",
                "documentation",
                "integration_type",
                "iot_class",
                "issue_tracker",
                "requirements",
                "version",
            ],
            list(manifest),
        )

    def test_init_declares_config_entry_only_schema(self):
        init_source = (COMPONENT_DIR / "__init__.py").read_text(encoding="utf-8")

        self.assertIn("CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)", init_source)


if __name__ == "__main__":
    unittest.main()
