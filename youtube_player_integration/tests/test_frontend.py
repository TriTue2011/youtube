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
        self.assertIn("event.origin !== EMBED_ORIGIN", script)
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
        self.assertIn("document.body.appendChild(audio);", script)
        # 0.26.18 — ĐỔI HẲN MÔ HÌNH, theo đúng tài liệu Apple và mã của chính Home
        # Assistant. Apple: trên iOS "no data is loaded until the user initiates it",
        # và play()/load() vô tác dụng nếu không do người dùng khởi động. Giữ MỘT phần
        # tử sống rồi ĐỔI «src» cho bài mới là mở một lượt tải NGOÀI cú chạm — iOS
        # không tải, không báo lỗi, nằm im ở «đang tải»: đúng «nap=0 mang=2 loi=0».
        # Trình duyệt Media của HA chạy được trên iPhone vì nó dựng phần tử MỚI mang
        # sẵn địa chỉ, để «autoplay» lo việc phát, và có «controls» làm lối thoát.
        self.assertIn('audio.setAttribute("src", url);', script)
        self.assertIn("audio.autoplay = true;", script)
        self.assertIn("audio.playsInline = true;", script)
        self.assertIn("audio.controls = hienNut;", script)
        # Địa chỉ phải lấy TRƯỚC cú chạm, nếu không thì dù dựng phần tử mới, lượt tải
        # vẫn rơi ra ngoài cử chỉ người dùng. Có sẵn thì «listen» chạy THẲNG, không
        # một «await» nào chen vào — đó là điều kiện bắt buộc, không phải tối ưu.
        self.assertIn("listen(item, queue, index, startAt = 0) {", script)
        self.assertIn("const san = this.luongSan(item);", script)
        self.assertIn("async chuanBi(item) {", script)
        # ĐẤU NỐI, không chỉ có hàm. Viết đúng hàm rồi không gọi nó ở đâu là kiểu hỏng
        # im lặng nhất: mã trông đầy đủ mà đường nhanh không bao giờ chạy. Hai nơi gọi:
        # lúc hiện kết quả (để cú chạm đầu tiên có sẵn), và lúc bắt đầu một bài (để
        # bài KẾ TIẾP có sẵn — "chuyển bài khác là lại tịt" chính là chỗ này).
        self.assertIn("deviceAudio.chuanBi({ ...item, source: item.source || this._source })", script)
        self.assertIn("if (ke) this.chuanBi(ke);", script)
        # MỘT LUỒNG MỘT LÚC: Apple giới hạn iOS ở đúng một luồng tiếng hoặc hình. Phần
        # tử cũ còn trong trang là còn giữ chỗ, nên phải gỡ hẳn chứ không chỉ tạm dừng.
        self.assertIn('cu.removeAttribute("src");', script)
        self.assertIn("cu.remove();", script)
        # Mô hình im-lặng-lặp-vòng đã bị THAY, không được để sót lại nửa vời.
        self.assertEqual(script.count("audio.loop = false;"), 0)
        # Lưới an toàn: quay lại trang thì thử phát lại — chính là cái mẹo thủ công
        # mà người dùng tự tìm ra, nay làm tự động.
        self.assertIn("} else if (this.item && this.real() && audio.paused) {", script)
        # 0.26.14: GHI LẠI kết quả cú mở khoá. Bản cũ nuốt im lặng mọi lỗi ở đó, nên
        # nếu chính cú mở khoá hỏng thì không ai biết — mà mọi thứ sau đều dựa vào nó.
        self.assertIn('this.moKhoa = "dang-thu";', script)
        self.assertIn("mo_khoa=${this.moKhoa", script)
        # Và thử phát lại một lần sau 3 giây, đúng cái mẹo người dùng tự tìm ra.
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
        # 0.26.18: nay chỉ còn MỘT nơi gọi. Hai đường nghe (nghe một mình và nghe kèm
        # loa) trước đây mỗi đường tự dựng phần tử rồi tự canh; nay cả hai đi qua
        # «batDau», nên chỗ dựng phần tử và chỗ canh tiếng chỉ có một bản.
        self.assertEqual(script.count("this.canhTieng(audio, generation);"), 1)
        self.assertIn("batDau(url, startAt, generation,", script)
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
        self.assertIn("https://www.youtube-nocookie.com/embed/${id}", script)
        # HA pages send "Referrer-Policy: no-referrer" -> YouTube Error 153
        # unless the iframe carries its own policy, set before src.
        self.assertLess(
            script.index('iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin")'),
            script.index('iframe.setAttribute("src", src)'),
        )
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
        self.assertEqual(script.count("this._loaDanNhip("), 2)
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
