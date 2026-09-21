/**
 * tritue-youtube-player-card.js   v1.0.0
 * ─────────────────────────────────────────────────────────────
 * Card "Xem/nghe YouTube" cho Home Assistant — tách riêng từ
 * announce-center.js để dùng độc lập, không cần cả bộ card thông báo.
 *
 * Tính năng:
 * ─ Tìm và phát nhạc/video từ YouTube, Zing MP3, hoặc dán link audio trực tiếp
 * ─ Phát ra loa/màn hình bất kỳ trong nhà (chọn nhiều loa cùng lúc)
 * ─ Lưu & quản lý Playlist riêng
 * ─ Bố cục ngang 2 cột (Video / Danh sách phát / Loa-màn hình / Đang phát)
 *   trên desktop, tự gập lại 1 cột trên màn hình hẹp
 * ─ Sóng nhạc nhấp nháy khi có bài đang chạy (3 kiểu: bars/simple/dots)
 *
 * YÊU CẦU BẮT BUỘC:
 *   Phải cài sẵn tích hợp Python "tritue_youtube_player" trong Home Assistant
 *   (custom_components/tritue_youtube_player) — tích hợp này cung cấp entity
 *   media_player ảo + API tìm kiếm/stream/playlist. File này CHỈ là giao diện
 *   phía trình duyệt, không tự phát được nhạc nếu chưa có tích hợp trên.
 *
 * Cách dùng (YAML):
 *   type: custom:youtube-player-card
 *   entity: media_player.ten_entity_tritue_youtube_player   # bắt buộc
 *   title: 🎵 Xem YouTube                                    # tuỳ chọn
 *   waveStyle: bars                                          # tuỳ chọn: bars | simple | dots
 *   layout: horizontal                                       # tuỳ chọn: horizontal | vertical
 *   player_width: 50                                         # tuỳ chọn: 20-80, bề rộng cột video (%)
 *   bg_style: gradient                                       # tuỳ chọn: gradient | solid | none
 *   bg_color: "#0d1525"                                      # tuỳ chọn: màu nền
 *   accent_color: "#00ffcc"                                  # tuỳ chọn: màu nhấn
 *   opacity: 100                                             # tuỳ chọn: 0-100, độ đục của nền
 *   zoom: 100                                                # tuỳ chọn: 50-150, thu phóng chữ và nút
 *
 * Không cần nhớ các khoá trên: bấm "Sửa thẻ" trên dashboard là có trình sửa
 * bằng giao diện với ba tab Cấu hình / Hiển thị / Bố trí.
 */
(() => {
  'use strict';

const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
/* Mã video Facebook là một CHUỖI SỐ dài, khác hẳn mã 11 ký tự của YouTube. Dùng
   «VIDEO_ID» cho mục Facebook sẽ loại sạch chúng mà không báo lỗi gì. */
const FB_VIDEO_ID = /^[0-9]{5,25}$/;
const SILENCE = "data:audio/wav;base64,UklGRrQBAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YZABAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA";

/** Máy này có phải iOS / iPadOS không.
 *
 * Chủ máy chốt 20/09/2026: "xem tách riêng iP và Android ra". Đúng, vì hai nền
 * tảng hỏng khác nhau và đã có lần một bản vá cho iOS làm hỏng luôn Android.
 * Từ đây, thứ gì dựng riêng cho iOS thì phải đi qua cổng này, để Android chạy
 * đúng đường vốn đã tốt.
 *
 * iPad đời mới khai user-agent giống máy Mac, nên phải hỏi thêm màn cảm ứng —
 * Mac thật không có «ontouchend».
 */
const laIOS = () => {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  if (/iPhone|iPad|iPod/.test(ua)) return true;
  return /Mac/.test(ua) && typeof document !== "undefined" && "ontouchend" in document;
};

/** Safari — KỂ CẢ trên máy Mac để bàn, không riêng iPhone.
 *
 * Chủ máy đo 20/09/2026 trên Safari của iMac và gửi kèm số:
 *     nap=0  mang=3  loi=0  nguon=1  dom=0
 * «mang=3» là NETWORK_NO_SOURCE — phần tử âm thanh đã BỎ CUỘC, không tìm được
 * nguồn phát, dù địa chỉ đã có («nguon=1») và không báo lỗi nào («loi=0»). Đây
 * cùng một họ hỏng với iPhone, vì Safari trên máy Mac cũng chạy WebKit.
 *
 * Vì sao trước đây nó rơi ra ngoài: «laIOS» phải hỏi thêm màn cảm ứng để phân
 * biệt iPad đời mới với máy Mac (hai máy khai user-agent giống nhau). Máy Mac để
 * bàn không có «ontouchend» nên bị xếp vào nhóm Android và đi đúng con đường đã
 * hỏng. Chủ máy chốt: "tối ưu hết cả cho android và ios, macos".
 */
const laSafari = () => {
  if (typeof navigator === "undefined") return false;
  const ua = navigator.userAgent || "";
  return /Safari/.test(ua) && !/Chrome|Chromium|Android|Edg\//.test(ua) && !/OPR\//.test(ua);
};

/** Máy nhà Táo chạy WebKit: iPhone, iPad, và Safari trên macOS. */
const laTao = () => laIOS() || laSafari();

/** Bản thẻ, để hộp đen nói rõ máy đang chạy bản nào — nâng cùng lúc với manifest. */
const PHIEN_BAN_THE = "0.26.59";

/* KHUNG NHÚNG LẤY TỪ «www.youtube.com», KHÔNG PHẢI «youtube-nocookie.com».
   Chrome cho một khung tự phát KÈM TIẾNG hay không là xét theo mức gắn bó của
   người dùng với CHÍNH tên miền ấy (Media Engagement Index). Máy nào cũng xem
   YouTube nên «youtube.com» có điểm cao, còn «youtube-nocookie.com» gần như không
   ai mở bao giờ nên điểm bằng không — cùng một đoạn mã, khung nocookie bị chặn
   tiếng còn khung youtube.com thì không. Đây đúng là điểm khác về địa chỉ giữa thẻ
   này và thẻ «phicomm-r1-card» chủ máy đưa 20/09/2026 (thẻ ấy dùng www.youtube.com
   và nghe được ngay trên cả Android lẫn iPhone), và nó khớp với thứ đo được cùng
   ngày: dựng khung có tiếng trên Android thì rơi về nút play của YouTube.
   ĐÂY LÀ GIẢ THUYẾT CHƯA ĐO TRỰC TIẾP, nên mọi đường bật tiếng đều phải có lối
   lùi tự động — xem «_checkVideoSound». */
const EMBED_ORIGIN = "https://www.youtube.com";
const STREAM_TOKEN = /\/api\/stream\/([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+/;

/* Tên nguồn để GHI RA dòng đang phát. Hàng nút YouTube / Zing MP3 chỉ đổi nơi TÌM
   KIẾM, không đổi bài đang phát — nên đổi tab xong nhìn vẫn thấy bài cũ là đúng, chỉ
   là card không hề nói bài ấy lấy từ đâu (chủ máy hỏi "có đang chạy đúng bài trên
   zing không"). Ghi hẳn tên nguồn ra thì không phải đoán nữa. */
const TEN_NGUON = { youtube: "YouTube", zing: "Zing MP3", facebook: "Facebook", http: "Link" };

/** Song in a speaker's signed stream URL (the payload is plain base64 JSON); null = not the player's stream. */
function streamTarget(mediaContentId) {
  const match = STREAM_TOKEN.exec(String(mediaContentId || ""));
  if (!match) return null;
  try {
    const base64 = match[1].replace(/-/g, "+").replace(/_/g, "/");
    const target = JSON.parse(atob(base64 + "===".slice((base64.length + 3) % 4))).target;
    return target ? String(target) : null;
  } catch (_error) {
    return null;
  }
}

const LISTEN_SCREEN_OFF_KEY = "tritue-youtube-player:listen-screen-off";
const SEARCH_KEY = "tritue-youtube-player:search:";
/* Bố cục dọc/ngang bấm ngay trên card. Nhớ theo TỪNG MÁY và từng thẻ, nên máy tính
   để ngang còn điện thoại để dọc mà không ai phải sửa YAML. Trình duyệt chặn lưu
   trữ thì vẫn đổi được, chỉ là không nhớ sang lần sau. */
const LAYOUT_KEY = "tritue-youtube-player:layout:";
function layoutChoice(entityId) {
  try {
    return localStorage.getItem(LAYOUT_KEY + entityId) || "";
  } catch (_error) {
    return "";
  }
}
function setLayoutChoice(entityId, layout) {
  try {
    localStorage.setItem(LAYOUT_KEY + entityId, layout);
  } catch (_error) {
    /* không lưu được thì thôi */
  }
}
/* Danh sách gợi ý đóng hay mở. Nhớ theo TỪNG MÁY và từng thẻ, giống hệt cách nhớ
   kiểu bố cục ngay trên. MẶC ĐỊNH LÀ ĐÓNG — chủ máy 19/09/2026: "List gợi ý có thể
   xoá và kích mới ra, không đưa hết ra màn". */
const SUGGEST_OPEN_KEY = "tritue-youtube-player:suggest-open:";
function suggestOpen(entityId) {
  try {
    return localStorage.getItem(SUGGEST_OPEN_KEY + entityId) === "1";
  } catch (_error) {
    return false;
  }
}
function setSuggestOpen(entityId, on) {
  try {
    localStorage.setItem(SUGGEST_OPEN_KEY + entityId, on ? "1" : "0");
  } catch (_error) {
    /* không lưu được thì thôi — lựa chọn chỉ còn tới lúc tải lại trang */
  }
}
// Links the player server can save as a whole playlist (it checks them properly).
const PLAYLIST_LINK = /^(TTPL1\.|https?:\/\/([a-z0-9-]+\.)*(youtube\.com|youtu\.be)\/\S*[?&]list=[A-Za-z0-9_-]+|https?:\/\/([a-z0-9-]+\.)*zingmp3\.vn\/(album|playlist)\/)/i;
const PLAYLIST_ERRORS = {
  invalid_playlist_link: "Dán link playlist YouTube, link album/playlist Zing MP3 hoặc mã chia sẻ (TTPL1.…).",
  invalid_share_code: "Mã chia sẻ không đúng hoặc bị cắt mất một đoạn.",
  playlist_unavailable: "Không đọc được playlist này — link sai, playlist riêng tư, hoặc YouTube/Zing đang lỗi.",
  playlist_empty: "Playlist này không có bài nào nghe được (riêng tư, VIP hoặc đã xoá).",
  playlist_full: "Playlist đã đủ 500 bài.",
  too_many_playlists: "Đã có 100 playlist — xoá bớt rồi thêm.",
  playlist_name_required: "Đặt tên cho playlist.",
  playlist_not_found: "Playlist này vừa bị xoá.",
  cannot_connect: "Không kết nối được máy phát nhạc.",
};
// Half a second of silence, played inside the tap so Safari/iOS unlocks the audio
// element before the player server answers with the song's stream.

let screenOffChoice = null;

/** "Nghe khi tắt màn hình" (remembered on this device, off by default). */
function listenScreenOff() {
  if (screenOffChoice === null) {
    try {
      screenOffChoice = localStorage.getItem(LISTEN_SCREEN_OFF_KEY) === "1";
    } catch (_error) {
      screenOffChoice = false;
    }
  }
  return screenOffChoice;
}

function setListenScreenOff(on) {
  screenOffChoice = on;
  try {
    localStorage.setItem(LISTEN_SCREEN_OFF_KEY, on ? "1" : "0");
  } catch (_error) {
    // Storage blocked: the choice lasts until the page reloads.
  }
}

// Phân loại Loa/Màn hình do người dùng tự sửa tay (khi device_class + tên thiết bị
// không đủ để đoán đúng, vd "living" không có từ khoá gì). Lưu trên trình duyệt
// (không cần đổi gì phía backend); áp dụng chung cho mọi dashboard trên máy này.
const DEVICE_KIND_KEY = "tritue-youtube-player:device-kind:";
function getDeviceKindOverride(entityId) {
  try {
    const v = localStorage.getItem(DEVICE_KIND_KEY + entityId);
    return v === "audio" || v === "video" ? v : null;
  } catch (_error) {
    return null;
  }
}
function setDeviceKindOverride(entityId, kind) {
  try {
    localStorage.setItem(DEVICE_KIND_KEY + entityId, kind);
  } catch (_error) {
    // Storage blocked: lựa chọn chỉ tồn tại đến khi tải lại trang.
  }
}

/** What a card showed when it left the page (search, queue, video), by entity. */
const cardMemory = new Map();

/**
 * Sound on the device showing the card: an <audio> element fed by the player
 * server's stream. It lives outside the card so leaving the dashboard neither stops
 * it nor loses the song and queue; coming back shows them again. Either listening
 * alone (no speaker ticked: its own queue, next song when one ends, lock-screen
 * buttons) or along with speakers (the card loads their song and keeps in step).
 * "Nghe khi tắt màn hình" off: hiding the page (screen off, another app) pauses it
 * and showing the page again resumes what was paused that way.
 */
const deviceAudio = {
  element: null,
  hass: null,
  entryId: "",
  item: null,
  queue: [],
  index: -1,
  along: false,
  alongKey: "",
  generation: 0,
  pausedByHide: false,
  //: Kết quả cú mở khoá gần nhất ("ok" / tên lỗi). Khai ở đây cho cùng nếp với mọi
  //: trạng thái khác của bộ phát — xem «unlock».
  listeners: new Set(),

  playRefused(error) {
    if (error?.name === "AbortError") return;
    this.notify(error?.name === "NotAllowedError"
      ? "Trình duyệt chặn tự phát có tiếng — bấm ▶ để nghe."
      : "Máy này không phát được tiếng bài này (" + (error?.name || "lỗi không rõ") + ").", true);
  },

  notify(message = "", isError = false) {
    this.listeners.forEach((listener) => listener(message, isError));
  },

  audio() {
    if (this.element) return this.element;
    const audio = new Audio();
    audio.preload = "auto";
    /* PHẦN TỬ PHẢI NẰM TRONG TRANG. «new Audio()» tạo ra một phần tử rời, không gắn vào
       đâu cả — và khung web của app Home Assistant chỉ chịu đi lấy dữ liệu cho phần tử
       rời ấy khi trang bị ẩn rồi hiện lại. Chủ máy đo 21/09/2026: "chọn nghe trên thiết
       bị này mà thoát app ra rồi vào lại là nghe được luôn, nhưng nếu không thoát thì
       tiếng mãi không nghe được. iPhone tương tự" — đúng dấu hiệu ấy.
       Thẻ «phicomm-r1-card» chủ máy đưa cũng gắn phần tử âm thanh của nó vào trang theo
       đúng kiểu này (ẩn một điểm ảnh, có «playsinline»), và nó chạy được trên cả hai
       nền tảng. */
    audio.setAttribute("playsinline", "");
    audio.setAttribute("webkit-playsinline", "");
    /* NẰM TRONG KHUNG NHÌN, đừng quăng ra «-9999px».
       Số đo trên iPhone của chủ máy 21/09/2026 loại hết mọi nghi can khác: cùng một địa
       chỉ, «fetch» của chính trang lấy được dữ liệu (mã 206, audio/mp4, 118ms) trong khi
       phần tử âm thanh đứng ở «nap=0» suốt tám giây và KHÔNG báo lỗi — tức nó không hề
       gửi yêu cầu nào. Đường truyền, địa chỉ và máy chủ đều đã bị loại.
       Nghi can còn lại: WebKit không cấp bộ giải mã cho phần tử nằm ngoài khung nhìn.
       Nên nay đặt ở góc trên bên trái, vẫn một điểm ảnh và gần như trong suốt, không
       nhận cú chạm — người dùng không thấy, mà trình duyệt thì thấy. */
    Object.assign(audio.style, {
      position: "fixed", top: "0", left: "0",
      width: "1px", height: "1px", opacity: "0.01",
      pointerEvents: "none", zIndex: "0",
    });
    document.body.append(audio);
    audio.addEventListener("play", () => this.notify());
    audio.addEventListener("pause", () => this.notify());
    audio.addEventListener("ended", () => {
      if (this.real() && this.item && !this.next(1)) this.notify("Đã nghe hết hàng đợi.");
    });
    audio.addEventListener("error", () => {
      if (this.real()) this.notify("Không phát được tiếng bài này trên máy này.", true);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        if (!listenScreenOff() && this.real() && !audio.paused) {
          audio.pause();
          this.pausedByHide = true;
        }
      } else if (this.pausedByHide) {
        this.pausedByHide = false;
        audio.play().catch(() => {});
      }
    });
    this.element = audio;
    return audio;
  },

  /** The <audio> element while it holds a song (not the unlocking silence). */
  real() {
    const src = this.element?.getAttribute("src") || "";
    return src && !src.startsWith("data:") ? this.element : null;
  },

  playing() {
    const audio = this.real();
    return !!audio && !audio.paused;
  },

  /** GỌI PHÁT VÀ NHỚ LẠI CÂU TRẢ LỜI CỦA TRÌNH DUYỆT.
   *
   *  Thiếu đúng dữ kiện này mà tôi đã đoán mò ba lần. `paused` không trả lời được:
   *  theo chuẩn, gọi `play()` là `paused` thành false NGAY, kể cả khi ngay sau đó
   *  trình duyệt chặn. Nên số đo «tamdung=0» của iPhone chủ máy (20 và 21/09/2026)
   *  KHÔNG chứng minh được lệnh phát đã được chấp nhận.
   *  Lời hứa của `play()` mới trả lời: xong êm là được phép, ném `NotAllowedError`
   *  là bị chặn. Hai đường chữa hoàn toàn khác nhau.
   */
  phatVaGhi(audio) {
    this.ketQuaPhat = "cho";
    this.cuChi = typeof navigator !== "undefined" && navigator.userActivation
      ? (navigator.userActivation.isActive ? 1 : 0)
      : -1;
    const hong = (error) => {
      this.ketQuaPhat = error?.name || "lỗi";
      this.playRefused(error);
    };
    try {
      const hua = audio.play();
      if (hua && hua.then) hua.then(() => { this.ketQuaPhat = "ok"; }, hong);
      else this.ketQuaPhat = "ok";
    } catch (error) {
      hong(error);
    }
  },

  /** Call inside the tap, before any await. */
  unlock() {
    const audio = this.audio();
    audio.src = SILENCE;
    audio.play().catch(() => {});
    return audio;
  },

  khoaLuong(item) {
    return `${item.source}:${item.url || item.id}`;
  },

  /* LẤY SẴN ĐỊA CHỈ LUỒNG — lớp nhớ nằm BÊN TRONG «streamUrl», cố ý không đụng
     vào mô hình phát. Đây là thứ duy nhất giữ lại từ đợt làm lại 0.26.13–0.26.20;
     toàn bộ phần đổi cách dựng phần tử đã được trả về đúng bản 0.26.2, vì chủ máy
     đo trên máy thật: bản cũ nghe được, bản mới thì không.
     Lợi ích vẫn còn nguyên (bấm bài là vào ngay, không chờ 1,5–2,6 giây hỏi máy
     chủ) mà không đổi một dòng nào trong đường phát. */
  nhoLuong: new Map(),

  async chuanBi(item) {
    // Bài trực tiếp thì không nghe riêng được (xem «laTrucTiep»), nên lấy sẵn địa
    // chỉ cho nó chỉ tốn một lượt hỏi máy chủ mà không bao giờ dùng tới.
    if (!item || !this.hass || !this.entryId || this.laTrucTiep(item)) return;
    const khoa = this.khoaLuong(item);
    if (this.nhoLuong.has(khoa)) return;
    this.nhoLuong.set(khoa, null);           // giữ chỗ, đừng hỏi hai lần
    const url = await this.layLuong(item);
    if (!url) { this.nhoLuong.delete(khoa); return; }
    this.nhoLuong.set(khoa, { url, luc: Date.now() });
    if (this.nhoLuong.size > 40) this.nhoLuong.delete(this.nhoLuong.keys().next().value);
  },

  /** Hỏi thẳng máy chủ, không qua lớp nhớ. */
  async layLuong(item) {
    if (item.source === "http") return String(item.url || item.id || "");
    try {
      const payload = await this.hass.callApi("POST", "tritue_youtube_player/stream", {
        entry_id: this.entryId,
        source: item.source,
        target: item.url || item.id,
      });
      return String(payload?.stream_url || "");
    } catch (_error) {
      return "";
    }
  },

  async streamUrl(item) {
    const ban = this.nhoLuong.get(this.khoaLuong(item));
    // Vé của máy phát ngắn hạn; quá 4 phút thì coi như không có, đi hỏi lại.
    if (ban && Date.now() - ban.luc <= 240000) return ban.url;
    return this.layLuong(item);
  },

  /** Bài PHÁT TRỰC TIẾP thì thẻ <audio> không nghe riêng được.
   *
   * Đo trên c2a 20/09/2026, đúng bài chủ máy gặp lỗi ("Bolero Trữ Tình Hay Nhất
   * Không Quảng Cáo" của Ngọc Diệu Bolero):
   *     thời lượng = None            ← dấu hiệu của bài trực tiếp
   *     luồng giải ra  = …/playlist/index.m3u8    ← bản kê HLS, không phải file
   *     máy chủ khai báo = audio/mp4              ← khai SAI kiểu
   * Chrome không phát được HLS bằng thẻ «audio» (chỉ Safari làm được), nên nó trả
   * «NotSupportedError» — đúng nghĩa, nhưng người dùng chỉ thấy một mã lỗi kỹ thuật.
   *
   * Nhận dạng bằng THỜI LƯỢNG chứ không bằng đuôi địa chỉ: lúc bấm nghe thì chưa
   * có địa chỉ, mà bài trực tiếp thì không có thời lượng — đó là thứ biết được ngay.
   */
  laTrucTiep(item) {
    return !Number(item?.duration);
  },

  /** Thẻ đặt hàm này để «listen» nhường việc cho khung YouTube trên máy nhà Táo. */
  nhuongChoKhung: null,

  /** Listen alone; `startAt` = second to start from (the sound of a video watched until now). */
  async listen(item, queue, index, startAt = 0) {
    /* MÁY NHÀ TÁO KHÔNG NGHE BẰNG PHẦN TỬ ÂM THANH — CHẶN Ở ĐÚNG MỘT CỬA.
       0.26.50 chặn ở nhánh «bấm chỉ nghe» trong «_playResult», nhưng còn sáu lối khác
       cùng gọi vào đây: chuyển bài, mở lại bài đang nghe, khôi phục sau khi tải lại
       trang, đổi bài theo loa… Chủ máy gửi ảnh 18:30 ngày 21/09/2026 với dòng đỏ
       "Máy này chưa chạy được tiếng — [nap=0 mang=2 loi=0 nguon=1 dom=1]" — đó là
       cảnh báo của phần tử âm thanh, tức một trong sáu lối ấy đã lọt, và kết quả là
       "cứ phải lỗi, dừng rồi play lại mới được".
       Vá từng nhánh là danh sách, và danh sách thì luôn thiếu. Chặn ở đây thì mọi lối
       đều đi qua đúng một cửa. */
    if (laTao() && typeof this.nhuongChoKhung === "function"
      && (item?.source || "youtube") === "youtube" && VIDEO_ID.test(String(item?.id || ""))
      && this.nhuongChoKhung(item, queue, index, startAt)) {
      this.stop();
      return;
    }
    if (this.laTrucTiep(item)) {
      this.notify(`“${item.title || item.id}” đang phát trực tiếp nên không nghe riêng`
        + " tiếng được — bấm nút xem để nghe.", true);
      return;
    }
    /* CÓ SẴN ĐỊA CHỈ THÌ ĐỪNG PHÁT ĐOẠN IM LẶNG TRƯỚC — xem «startAlong» để biết vì
       sao: một cú chạm chỉ chứng nhận cho một lần phát. */
    const san = this.nhoLuong.get(this.khoaLuong(item));
    const coSan = !!san?.url && Date.now() - san.luc <= 240000;
    const audio = coSan ? this.audio() : this.unlock();
    const generation = ++this.generation;
    Object.assign(this, { item, queue, index, along: false, alongKey: "", pausedByHide: false });
    this.mediaSession(item);
    this.notify();
    /* ĐỊA CHỈ ĐÃ XIN SẴN THÌ KHÔNG ĐƯỢC `await` GÌ TRƯỚC KHI PHÁT.
       Dựng lại trong Chrome 21/09/2026 với user-agent iPhone: bấm «Chỉ nghe» thì lệnh
       phát rơi ra SAU cú bấm (đi qua một `await` là đã ra ngoài phần chạy đồng bộ).
       Chrome vẫn cho vì cử chỉ còn hiệu lực năm giây, nhưng iOS thì không: đo
       20/09/2026 trên iPhone của chủ máy là «nap=0 mang=2 loi=0» — phần tử được phép
       phát, có nguồn, mà không tải một byte nào. Nên lấy thẳng từ lớp nhớ và phát ngay
       tại chỗ; chỉ khi chưa xin sẵn mới đi hỏi (và lúc ấy đành chịu một vòng chờ). */
    const url = coSan ? san.url : await this.streamUrl(item);
    if (generation !== this.generation) return;
    if (!url) {
      // One notification, carrying the error (the card keeps a video it was following).
      this.silence();
      Object.assign(this, { item: null, queue: [], index: -1, along: false });
      this.mediaSession(null);
      this.notify("Không lấy được tiếng bài này.", true);
      return;
    }
    audio.src = url;
    if (startAt >= 1) audio.addEventListener("loadedmetadata", () => { audio.currentTime = startAt; }, { once: true });
    this.phatVaGhi(audio);
    this.hopDenTheoDoi(coSan ? "nghe một mình, địa chỉ có sẵn" : "nghe một mình, phải hỏi máy chủ", audio);
    this.canhTieng(audio, generation);
    this.notify();
    // Lấy sẵn bài kế tiếp để cú chuyển bài không phải chờ.
    const ke = this.queue?.[this.index + 1];
    if (ke) this.chuanBi(ke);
  },

    /* ĐỪNG NHẢY VÀO GIỮA BÀI NGAY TỪ ĐỊA CHỈ. Số đo từ máy chủ máy 21/09/2026:
       đặt «#t=» rồi phát thì phần tử dừng ở «nap=1» suốt tám giây — chỉ đọc được phần
       mô tả tệp, không có một mẫu âm thanh nào ở chỗ đang phát, nên máy im dù đồng hồ
       vẫn nhích. Cùng lúc ấy đường phát TỪ ĐẦU đạt «nap=4» và chạy ngon.
       Nay nạp từ đầu (một lượt tải tuần tự, thứ khung web chịu làm), rồi chỉ nhảy tới
       chỗ của loa KHI ĐÃ CÓ DỮ LIỆU THẬT («canplay»). Không có dữ liệu thì thà nghe từ
       đầu còn hơn im lặng. */
  nhayKhiSanSang(audio, batDau) {
    if (!(batDau >= 1)) return;
    const nhay = () => {
      if (audio.readyState < 3 || audio.currentTime >= batDau - 0.5) return;
      audio.currentTime = batDau;
    };
    audio.addEventListener("canplay", nhay, { once: true });
    // Có máy không bắn «canplay» nữa nếu đã từng nạp bài khác: chốt thêm một mốc.
    setTimeout(nhay, 2500);
  },

  /** HỘP ĐEN — ghi trạng thái phần tử âm thanh vào NHẬT KÝ CỦA HOME ASSISTANT.
   *
   *  Vì sao cần: lỗi chỉ xảy ra trên máy thật của chủ máy, mà máy ấy thì không cắm dây
   *  vào đâu được — ADB đòi gọi ngược vào điện thoại, VPN nhà không cho, Simulator thì
   *  phải có Mac. Nhật ký HA là chỗ duy nhất cả hai phía cùng thấy: thẻ ghi vào, máy chủ
   *  đọc ra. Chủ máy chỉ việc bấm một lần rồi thôi.
   *
   *  Ý nghĩa từng số: «nap» = readyState (0 = chưa có dữ liệu nào), «mang» =
   *  networkState (2 = đang tải, 3 = không tìm được nguồn), «loi» = mã lỗi media,
   *  «giay» = đồng hồ của tiếng, «tamdung», «nguon» = đã chọn được nguồn phát chưa,
   *  «dom» = phần tử có nằm trong trang không.
   */
  /** Máy nào đang gửi, và đang chạy bản thẻ nào.
   *
   *  Thiếu hai thứ này mà tôi đứng hình 21/09/2026: log 18:12:57 ghi đường phần tử
   *  âm thanh, mà chủ máy có cả iPhone lẫn Android cùng mở thẻ — không cách nào biết
   *  dòng ấy của máy nào, nên không kết luận được bản sửa cho iPhone đã chạy chưa. */
  dauMay() {
    const ua = typeof navigator === "undefined" ? "" : navigator.userAgent || "";
    const may = laIOS() ? "ios" : /Android/.test(ua) ? "android" : laSafari() ? "safari" : "khac";
    return `may=${may} ban=${PHIEN_BAN_THE}`;
  },

  /** Ghi thẳng một dòng vào nhật ký Home Assistant (không kèm phần tử âm thanh). */
  ghiThang(dong) {
    if (!this.hass?.callService) return;
    this.hass.callService("system_log", "write", {
      message: `[the youtube] ${dong} ${this.dauMay()}`,
      level: "warning",
      logger: "tritue_youtube_player.the",
    }).catch(() => {});
  },

  hopDen(nhan, audio) {
    if (!this.hass?.callService) return;
    const a = audio || this.element;
    const so = a
      ? `nap=${a.readyState} mang=${a.networkState} loi=${a.error ? a.error.code : 0}`
        + ` giay=${Number(a.currentTime || 0).toFixed(1)} tamdung=${a.paused ? 1 : 0}`
        + ` nguon=${a.currentSrc ? 1 : 0} dom=${a.isConnected ? 1 : 0}`
        + ` ochoy=${(() => { const h = a.getBoundingClientRect(); return `${Math.round(h.left)},${Math.round(h.top)}`; })()}`
        + ` phat=${this.ketQuaPhat || "?"} cuchi=${this.cuChi ?? "?"}`
        + ` dem=${(() => {
          const goc = document.querySelector("tritue-youtube-player-card")?.shadowRoot;
          const dem = (chon) => document.querySelectorAll(chon).length
            + (goc ? goc.querySelectorAll(chon).length : 0);
          return `${dem("audio,video")}m/${dem("iframe")}k`;
        })()} ${this.dauMay()}`
      : "(chưa có phần tử)";
    this.hass.callService("system_log", "write", {
      message: `[the youtube] ${nhan} — ${so}`,
      level: "warning",
      logger: "tritue_youtube_player.the",
    }).catch(() => {});
  },

  /** Ghi hộp đen ngay lúc bấm rồi thêm ba mốc sau đó — đủ để thấy tiếng có chảy không. */
  hopDenTheoDoi(nhan, audio) {
    (this.hopDenTimers || []).forEach((id) => clearTimeout(id));
    this.hopDen(`${nhan} (ngay lúc bấm)`, audio);
    this.hopDenTimers = [1000, 3000, 8000].map((cho) =>
      setTimeout(() => {
        this.hopDen(`${nhan} (+${cho / 1000}s)`, audio);
        // Ba giây mà chưa có một byte nào: hỏi thẳng xem MẠNG của máy này có lấy được
        // dữ liệu từ đúng địa chỉ ấy không. Tách được hai chuyện hay bị lẫn — "máy không
        // với tới được luồng" với "với tới được mà trình phát không thèm tải".
        /* «networkState === 0» là phần tử KHÔNG còn nguồn nào — tức chính thẻ vừa
           tắt tiếng (đổi bài, giao cho loa, dừng hẳn). Cứu lúc ấy là dựng lại thứ
           vừa cố ý tắt. Log HA 21/09/2026 17:25:08 bắt đúng một lần như vậy. */
        if (cho === 3000 && audio && audio.readyState === 0 && !audio.error
            && audio.networkState !== 0) {
          this.doThuLuong(audio);
          this.cuuLuotNap(audio);
        }
      }, cho));
  },

  /** CỨU MỘT LẦN khi lượt tải chết lặng — và đồng thời là phép đo quyết định.
   *
   *  Ba giây trôi qua mà `readyState` vẫn bằng 0 và KHÔNG có lỗi nghĩa là lượt tải
   *  không hề khởi động: phần tử báo "đang tải" mà không một byte nào về. Chủ máy đã
   *  gặp đúng cảnh này trên iPhone và Android, và cách duy nhất thoát ra là ẩn app
   *  rồi mở lại — lúc ấy khung web tự dựng lại trình phát và bài hát mới chịu chạy.
   *  Đây là làm đúng việc ấy mà không bắt người dùng phải chuyển app: gọi lại lượt
   *  nạp một lần, rồi ghi hộp đen xem có ăn thua không.
   *
   *  Chỉ chạy khi phần tử đã chắc chắn chết, nên không thể làm hỏng ca đang chạy tốt.
   */
  cuuLuotNap(audio) {
    if (this.dangCuu) return;
    this.dangCuu = true;
    try {
      audio.load();
    } catch (_error) {
      // Máy nào không cho gọi lại thì thôi, vẫn còn cú phát bên dưới.
    }
    this.phatVaGhi(audio);
    this.hopDen("cứu lượt nạp: gọi lại load() rồi play()", audio);
    setTimeout(() => {
      this.hopDen("sau khi cứu (+2s)", audio);
      this.dangCuu = false;
    }, 2000);
  },

  /** Thử tải một byte từ chính địa chỉ mà phần tử âm thanh đang trỏ tới. */
  async doThuLuong(audio) {
    const src = audio?.currentSrc || audio?.getAttribute("src") || "";
    if (!src || this.dangThuLuong) return;
    this.dangThuLuong = true;
    const luc = Date.now();
    try {
      const tra = await fetch(src, { headers: { Range: "bytes=0-1" }, cache: "no-store" });
      const bo = await tra.arrayBuffer();
      this.hopDen(`thử tải bằng fetch: ma=${tra.status} byte=${bo.byteLength}`
        + ` kieu=${tra.headers.get("content-type") || "?"} ms=${Date.now() - luc}`, audio);
    } catch (loi) {
      this.hopDen(`thử tải bằng fetch: HỎNG ${loi?.name || loi} ms=${Date.now() - luc}`, audio);
    }
    this.dangThuLuong = false;
  },

  /** Canh xem tiếng có THẬT SỰ chạy không, sau 12 giây kể từ lúc bảo nó phát.
   *
   * Phải nằm Ở ĐÂY chứ không phải trong vòng đồng bộ video: vòng ấy thoát ngay khi
   * không có video mở, nên đúng ca "chỉ nghe" — ca quan trọng nhất — lại chẳng có
   * số đo nào. Chủ máy báo 20/09/2026: "chỉ nghe không chạy thanh thời gian nên
   * không có tiếng", mà dòng chẩn đoán thì không bao giờ hiện ra.
   *
   * Luồng MỞ ĐƯỢC NHƯNG KHÔNG CHẢY không bắn sự kiện nào — phần tử chỉ có
   * play/pause/ended/error — nên không tự canh thì hỏng hoàn toàn im lặng.
   */
  canhTieng(audio, generation) {
    clearTimeout(this.canhTimer);
    clearTimeout(this.thuLaiTimer);
    /* CHỈ CHẠY TRÊN MÁY NHÀ TÁO. Cả hai hẹn giờ dưới đây dựng lên từ hành vi của
       WebKit; Android vốn không vướng, nên ở đó chúng chỉ có thể gây hại: cú nhắc
       lại lệnh phát có thể chen vào một luồng đang tải bình thường, còn lời nhắn
       12 giây thì báo hỏng oan. Chủ máy chốt "xem tách riêng iP và Android ra" —
       đây là chỗ đầu tiên áp nguyên tắc ấy, để Android chạy đúng đường 0.26.2.
       0.26.32: mở rộng sang Safari trên máy Mac, cũng là WebKit — xem «laSafari». */
    /* CANH CHO MỌI NỀN TẢNG. Trước đây chỉ canh trên máy nhà Táo vì Android được cho
       là không vướng; chủ máy đo 21/09/2026 thì Android vướng y hệt ("không thoát app
       ra vào lại là tiếng mãi không nghe được"). Phép nhắc lại vẫn an toàn cho Android
       vì nó chỉ nổ khi đồng hồ ĐỨNG YÊN sau ba giây — luồng đang chạy bình thường thì
       nhánh này thoát ngay. */
    const moc = audio.currentTime;
    /* THỬ LẠI MỘT LẦN sau 3 giây. Người dùng iPhone thấy "lượn qua app khác rồi quay
       lại thì lại phát" — tức lệnh phát chỉ cần được nhắc lại một lần nữa là chạy.
       Rẻ và vô hại: đang chạy rồi thì nhánh này thoát ngay. */
    this.thuLaiTimer = setTimeout(() => {
      if (generation !== this.generation || !this.item) return;
      if (audio.currentTime > moc + 0.3) return;
      audio.play().catch(() => {});
    }, 3000);
    this.canhTimer = setTimeout(() => {
      if (generation !== this.generation || !this.item) return;
      if (audio.paused || audio.currentTime > moc + 0.3) return;   // đang chạy, yên tâm
      // Lời nhắn phải NÓI VIỆC CẦN LÀM, không chỉ kêu hỏng: chạm nút ▶ là một cú
      // chạm thật, và đó đúng là thứ iOS đang đòi để chịu tải dữ liệu.
      this.notify("Máy này chưa chạy được tiếng — chạm nút ▶ để bắt đầu."
        + ` [nap=${audio.readyState} mang=${audio.networkState}`
        + ` loi=${audio.error ? audio.error.code : 0}`
        + ` nguon=${audio.currentSrc ? 1 : 0} dom=${audio.isConnected ? 1 : 0}`
        + "]", true);
    }, 12000);
  },

  /** Next (+1) / previous (-1) song of the queue; false at either end. */
  next(step) {
    const target = this.index + step;
    const item = this.queue[target];
    if (!this.item || !item) return false;
    this.listen(item, this.queue, target);
    return true;
  },

  toggle() {
    const audio = this.real();
    if (!audio) return;
    /* ĐANG KẸT thì nút này là PHÁT LẠI, không phải tạm dừng. Số đo từ iPhone
       20/09/2026: «nap=0 mang=2 loi=0 nguon=1 dom=1 mo_khoa=ok» — phần tử đã được
       phép phát, đã có nguồn, đang "tải" mà suốt 12 giây không một byte. Tức iOS chỉ
       chịu lấy dữ liệu khi lệnh phát nằm TRONG CHÍNH CÚ CHẠM, chứ không phải chỉ cần
       phần tử từng được phép một lần.
       Cú chạm vào nút này là cơ hội cứu duy nhất còn lại — mà theo nghĩa đen thì lúc
       ấy phần tử "không tạm dừng", nên bản cũ đem đúng cú chạm ấy đi tạm dừng một thứ
       vốn đã đứng im. Đổi bài cũng vấp y hệt, đúng lời người dùng: "chuyển bài khác
       là lại tịt". */
    if (!audio.paused && audio.readyState === 0) {
      audio.play().catch(() => {});
      return;
    }
    if (audio.paused) audio.play().catch(() => {});
    else audio.pause();
  },

  silence() {
    this.generation++;
    this.alongKey = "";
    this.pausedByHide = false;
    if (!this.element) return;
    this.element.pause();
    this.element.removeAttribute("src");
    this.element.load();
  },

  stop() {
    this.silence();
    Object.assign(this, { item: null, queue: [], index: -1, along: false });
    this.mediaSession(null);
    this.notify();
  },

  /** Nghe cùng loa; PHẢI gọi ngay trong cú bấm.
   *
   *  `item` + `batDau` để phát NGAY TRONG CHÍNH CÚ BẤM khi địa chỉ luồng đã xin sẵn.
   *  Trình duyệt chỉ chắc chắn cho phát khi lệnh phát nằm trong cử chỉ người dùng; đi
   *  qua một `await` là đã ra ngoài cử chỉ. Chủ máy đo 21/09/2026: "tiếng rất lâu mới
   *  nghe thấy hoặc phải thao tác vào nghe khi tắt màn" — tức phải chạm thêm một lần
   *  nữa mới có tiếng, đúng dấu hiệu của lệnh phát nằm ngoài cử chỉ.
   *
   *  Vào đúng giây bằng mảnh địa chỉ `#t=`, không chờ `loadedmetadata` rồi mới tua:
   *  bớt một vòng chờ, và tránh luôn cảnh cú tua muộn đè lên vị trí mới hơn.
   */
  startAlong(item = null, batDau = 0) {
    if (this.item) this.stop();
    const san = item ? this.nhoLuong.get(this.khoaLuong(item)) : null;
    const coSan = !!san?.url && Date.now() - san.luc <= 240000;
    /* CÓ SẴN ĐỊA CHỈ THÌ ĐỪNG PHÁT ĐOẠN IM LẶNG TRƯỚC.
       Khung web của app chỉ chứng nhận MỘT lần phát cho MỘT cú chạm. Mở khoá bằng đoạn
       im lặng rồi mới đổi `src` sang bài thật nghĩa là cú chạm chứng nhận cho đoạn im
       lặng, còn bài thật bị coi là tự phát — nó nằm im ở «đang tải mà không có byte
       nào» (nap=0 mang=2) cho tới khi app được đánh thức lại. Chủ máy 21/09/2026: "vẫn
       phải ẩn app xuống, bật app khác rồi chọn lại app HA mới hát".
       Chưa có địa chỉ thì vẫn mở khoá như cũ — lúc ấy không còn cách nào khác. */
    const audio = coSan ? this.audio() : this.unlock();
    this.along = true;
    this.alongKey = "";
    if (coSan) {
      this.alongKey = this.khoaLuong(item);
      const generation = ++this.generation;
      this.mediaSession(item, false);
      audio.src = san.url;
      this.nhayKhiSanSang(audio, batDau);
      this.phatVaGhi(audio);
      this.hopDenTheoDoi("nghe cùng loa, phát ngay trong cú bấm", audio);
      this.canhTieng(audio, generation);
    }
    this.notify();
  },

  stopAlong() {
    this.silence();
    this.along = false;
    this.mediaSession(null);
    this.notify();
  },

  /** Load the speakers' song (nothing to do when it already is); `batDau` = giây loa
   *  đang ở. */
  async loadAlong(item, batDau = 0) {
    const key = `${item.source}:${item.url || item.id}`;
    if (!this.along || this.alongKey === key) return;
    this.alongKey = key;
    const generation = ++this.generation;
    this.mediaSession(item, false);
    const url = await this.streamUrl(item);
    if (generation !== this.generation || !this.along) return;
    if (!url) {
      this.notify("Không lấy được tiếng bài loa đang phát.", true);
      return;
    }
    const audio = this.audio();
    /* VÀO ĐÚNG CHỖ NGAY TRONG ĐỊA CHỈ («#t=»), đừng chờ «loadedmetadata» rồi mới tua.
       Dựng lại cảnh này trong Chrome 21/09/2026: cú tua muộn ấy còn ĐÈ LÊN vị trí mới
       hơn mà vòng canh vừa đặt — tiếng nhảy lùi hai giây ngay khi vừa bắt đầu. */
    audio.src = url;
    this.nhayKhiSanSang(audio, batDau);
    this.hopDenTheoDoi("nghe cùng loa, nạp sau cú bấm", audio);
    /* PHÂN LOẠI LỖI, ĐỪNG KÊU OAN. Đổi bài là lệnh phát cũ bị huỷ («AbortError») —
       chuyện bình thường, mà bản cũ đem hiện thành "trình duyệt chặn tự phát có
       tiếng", đúng dòng chữ đỏ chủ máy gặp trong ảnh 21/09/2026. */
    this.phatVaGhi(audio);
    this.canhTieng(audio, generation);
  },

  mediaSession(item, controls = true) {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
    const session = navigator.mediaSession;
    const handle = (action, handler) => {
      try {
        session.setActionHandler(action, handler);
      } catch (_error) {
        // This browser doesn't offer the action.
      }
    };
    session.metadata = item && typeof MediaMetadata !== "undefined"
      ? new MediaMetadata({
        title: item.title || item.id || "",
        artist: item.channel || item.artist || "",
        artwork: /^https?:\/\//.test(item.thumbnail || "") ? [{ src: item.thumbnail }] : [],
      })
      : null;
    const on = !!item && controls;
    handle("play", on ? () => this.real()?.play().catch(() => {}) : null);
    handle("pause", on ? () => this.real()?.pause() : null);
    handle("previoustrack", on ? () => this.next(-1) : null);
    handle("nexttrack", on ? () => this.next(1) : null);
    handle("stop", on ? () => this.stop() : null);
  },

  position() {
    const audio = this.real();
    if (!audio) return null;
    const duration = Number.isFinite(audio.duration) && audio.duration > 0 ? audio.duration : Number(this.item?.duration || 0);
    return { time: audio.currentTime, duration };
  },
};

const YOUTUBE_SUGGESTED_CATEGORIES = [
  {
    id: "acoustic",
    name: "Cafe Acoustic",
    icon: "mdi:coffee",
    songs: [
      {
        id: "v4tT04yJdWg",
        video_id: "v4tT04yJdWg",
        title: "Full Album Khói Thuốc Đợi Chờ ☘ Phương Phương Thảo || Jimmii Nguyễn Hits Cover Acoustic",
        artist: "Phương Phương Thảo Official",
        duration_seconds: 3983,
        thumbnail_url: "https://i.ytimg.com/vi/v4tT04yJdWg/hqdefault.jpg"
      },
      {
        id: "xFipDLcSR8I",
        video_id: "xFipDLcSR8I",
        title: "Tuyển Tập Những Bản Nhạc Hay Của Phương Phương Thảo | Playlist Acoustic Cover",
        artist: "Phương Phương Thảo Official",
        duration_seconds: 3840,
        thumbnail_url: "https://i.ytimg.com/vi/xFipDLcSR8I/hqdefault.jpg"
      },
      {
        id: "cWAUaH7TiUE",
        video_id: "cWAUaH7TiUE",
        title: "Nhạc Quán Cafe Hay Nhất 2021 - Nhạc Acoustic 8x 9x Nhẹ Nhàng | Nhạc Trẻ 8x 9x Đời Đầu Hay",
        artist: "NGUYỄN VĂN CHUNG MUSIC",
        duration_seconds: 2980,
        thumbnail_url: "https://i.ytimg.com/vi/cWAUaH7TiUE/hqdefault.jpg"
      },
      {
        id: "x6Tcs4_Btvo",
        video_id: "x6Tcs4_Btvo",
        title: "Guitar Buổi Sáng ☕ Bắt Đầu Ngày Mới Bình Yên | Nhạc Tập Trung Sâu Học Tập & Làm Việc",
        artist: "Guitar Coffee Music",
        duration_seconds: 3120,
        thumbnail_url: "https://i.ytimg.com/vi/x6Tcs4_Btvo/hqdefault.jpg"
      }
    ]
  },
  {
    id: "nhactre",
    name: "Nhạc Trẻ Hot TikTok",
    icon: "mdi:fire",
    songs: [
      {
        id: "LgRguLVuobM",
        video_id: "LgRguLVuobM",
        title: "BXH Nhạc Trẻ Remix Hay Nhất Hiện Nay ♫ Top 20 Bản EDM TikTok Hay Nhất - EDM Hot TikTok",
        artist: "Myn Xinh and Việt Mix DJ",
        duration_seconds: 3687,
        thumbnail_url: "https://i.ytimg.com/vi/LgRguLVuobM/hqdefault.jpg"
      },
      {
        id: "540JLNQBnYI",
        video_id: "540JLNQBnYI",
        title: "NHẠC REMIX TIKTOK TRIỆU VIEW - BXH Nhạc Trẻ Remix Hay Nhất Hiện Nay",
        artist: "Trang Xinh Music",
        duration_seconds: 5735,
        thumbnail_url: "https://i.ytimg.com/vi/540JLNQBnYI/hqdefault.jpg"
      },
      {
        id: "oOydk6FXGwU",
        video_id: "oOydk6FXGwU",
        title: "TOP 30 NHẠC REMIX TIKTOK TRIỆU VIEW: Vở Kịch Của Em, Thu Cuối, Lao Tâm Khổ Tứ",
        artist: "H2O Remix",
        duration_seconds: 6936,
        thumbnail_url: "https://i.ytimg.com/vi/oOydk6FXGwU/hqdefault.jpg"
      },
      {
        id: "4ZMk118CtSw",
        video_id: "4ZMk118CtSw",
        title: "NHẠC REMIX TIKTOK TRIỆU VIEW - BXH Nhạc Trẻ Remix Hay Nhất Hiện Nay",
        artist: "Ness Remix & H2O Remix",
        duration_seconds: 3952,
        thumbnail_url: "https://i.ytimg.com/vi/4ZMk118CtSw/hqdefault.jpg"
      }
    ]
  },
  {
    id: "lofi",
    name: "Lofi Chill & Học Tập",
    icon: "mdi:headphones",
    songs: [
      {
        id: "ZX2mjf9dFH8",
        video_id: "ZX2mjf9dFH8",
        title: "30 phút nhạc Lofi Chill không lời thư giãn nhẹ nhàng 🌿",
        artist: "Lucas Music",
        duration_seconds: 1819,
        thumbnail_url: "https://i.ytimg.com/vi/ZX2mjf9dFH8/hqdefault.jpg"
      },
      {
        id: "JBCFKYt14P4",
        video_id: "JBCFKYt14P4",
        title: "Nhạc Chill Nhẹ Nhàng - Nhạc Lofi Chill Gây Nghiện Hot TikTok",
        artist: "to thich cau",
        duration_seconds: 3237,
        thumbnail_url: "https://i.ytimg.com/vi/JBCFKYt14P4/hqdefault.jpg"
      },
      {
        id: "jfKfPfyJRdk",
        video_id: "jfKfPfyJRdk",
        title: "Lofi Hip Hop Radio - Beats to Relax/Study to",
        artist: "Lofi Girl",
        duration_seconds: 7200,
        thumbnail_url: "https://i.ytimg.com/vi/jfKfPfyJRdk/hqdefault.jpg"
      },
      {
        id: "F0XLVSbxhAo",
        video_id: "F0XLVSbxhAo",
        title: "Nhạc Chill Quán Cafe - Những Ca Khúc Lofi Nhẹ Nhàng Hay Nhất Dành Cho Quán Cafe",
        artist: "Phố Chill & Gió Xuân Chill",
        duration_seconds: 5448,
        thumbnail_url: "https://i.ytimg.com/vi/F0XLVSbxhAo/hqdefault.jpg"
      }
    ]
  },
  {
    id: "bolero",
    name: "Bolero & Trữ Tình Bất Hủ",
    icon: "mdi:music-clef-treble",
    songs: [
      {
        id: "jI5za9F3eQE",
        video_id: "jI5za9F3eQE",
        title: "Liên Khúc Bolero Tuyển Chọn | Em Xoá Tên Tôi Rồi - Hoàng Lâm Al",
        artist: "Ngọc Bích Al",
        duration_seconds: 3867,
        thumbnail_url: "https://i.ytimg.com/vi/jI5za9F3eQE/hqdefault.jpg"
      },
      {
        id: "4c6nzqeteYc",
        video_id: "4c6nzqeteYc",
        title: "Tuyển Chọn BOLERO Trữ Tình I Nhạc Vàng Xưa Ru Ngủ CỰC ÊM TAI - Ngọt Lịm SAY ĐẮM CON TIM",
        artist: "Bolero Phố Cũ",
        duration_seconds: 8357,
        thumbnail_url: "https://i.ytimg.com/vi/4c6nzqeteYc/hqdefault.jpg"
      },
      {
        id: "RXgbfTV1TQE",
        video_id: "RXgbfTV1TQE",
        title: "Tuyển Chọn Những Bài Nhạc Trữ Tình Hay Nhất Thế Kỷ - Sala Bolero",
        artist: "Sala Bolero",
        duration_seconds: 6673,
        thumbnail_url: "https://i.ytimg.com/vi/RXgbfTV1TQE/hqdefault.jpg"
      },
      {
        id: "HzVgG6qulSM",
        video_id: "HzVgG6qulSM",
        title: "50 Ca Khúc Bolero Tuyển Chọn KHÔNG QUẢNG CÁO Nghe 10000 Lần Không Thấy Chán",
        artist: "ĐẠI NHẠC HỘI",
        duration_seconds: 18813,
        thumbnail_url: "https://i.ytimg.com/vi/HzVgG6qulSM/hqdefault.jpg"
      }
    ]
  }
];
const QUICK_SEARCH_TAGS = [
  "Phương Phương Thảo",
  "Nhạc Trẻ Hot TikTok",
  "Lofi Chill",
  "Bằng Kiều",
  "Acoustic Buổi Sáng",
  "Lệ Quyên Bolero",
  "Nhạc Chill Thư Giãn"
];

class TriTueYouTubePlayerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._source = "youtube";
    this._selectedPlayers = new Set();
    // Loa đang được CHỈNH ÂM LƯỢNG. Độc lập với ô tích (loa nào PHÁT): bấm tên
    // một loa chỉ đổi đích của thanh âm lượng, không bật/tắt việc phát của nó.
    this._volumeTarget = "";
    this._speakerListOpen = false;
    this._results = [];
    this._rendered = false;
    this._defaultsApplied = false;
    this._capabilities = new Map();
    this._capabilityEntryId = "";
    this._capabilitiesLoading = false;
    // Từ khoá và video gắn sẵn của cả nhà, lấy từ tích hợp nên mọi bảng điều khiển
    // và mọi máy đều thấy như nhau. null = chưa tải xong.
    this._goiY = null;
    this._goiYLoading = false;
    this._sharedSessionMarker = "";
    // Queue of the video playing alone on the card. Speakers use the server
    // session's own queue, and the integration advances it (no browser needed).
    this._queue = [];
    this._queueIndex = -1;
    this._volumeRowsSig = "";
    this._activeVolumeEntity = null;
    this._manualSelection = false;
    // Ticking a speaker focuses it: "Đang phát", progress and the card's video
    // follow the session of the speaker ticked last.
    this._lastTicked = "";
    this._progressTimer = null;
    // Players hidden from this card. Stored by the integration in HA storage so
    // the list survives restarts and card reloads; restorable from the card.
    this._hiddenPlayers = new Set();
    this._hiddenLoading = false;
    this._hiddenLoaded = false;
    this._showHidden = false;
    this._nowWatchItem = null;
    // Video watched on the card itself: a YouTube embed driven over postMessage.
    this._video = this._idleVideo();
    this._onVideoMessage = (event) => this._handleVideoMessage(event);
    this._videoTimer = null;
    this._videoHandshakeTimer = null;
    this._lastVideoSeekAt = 0;
    this._pendingSpeakerSeek = null;
    this._mirrorHoldUntil = 0;
    this._alongSeekHold = 0;
    this._needsRestore = false;
    // Household playlists on the player server (null until loaded).
    this._view = "search";
    this._playlists = null;
    this._openPlaylist = "";
    this._playlistsRequested = false;
    this._addMenuFor = null;
    // Bảng chọn mục để ghim bài, khai cạnh «_addMenuFor» vì hai bảng cùng một lối.
    this._ghimMenuFor = null;
    this._onDeviceAudio = (message, isError) => this._deviceAudioChanged(message, isError);
  }

  _idleVideo() {
    return { open: false, ready: false, item: null, state: -1, time: 0, timeAt: 0, moUL: 0, withSpeakers: false, followsDevice: false, soundHere: true, soundOnly: false, muted: null, picture: null, pictureEl: null };
  }

  /* Hai hàm này là hợp đồng của Home Assistant: có chúng thì bấm "Sửa thẻ" trên
     dashboard sẽ mở trình sửa bằng giao diện thay vì bắt gõ YAML, và khi thêm thẻ
     mới HA lấy cấu hình mẫu từ getStubConfig. */
  static getConfigElement() {
    return document.createElement("tritue-youtube-player-card-editor");
  }

  static getStubConfig(hass) {
    const states = (hass && hass.states) || {};
    // Ưu tiên chính entity ảo của tích hợp này; không có thì để trống cho người
    // dùng tự chọn, KHÔNG đoán bừa một media_player bất kỳ.
    const mine = Object.keys(states).find(
      (id) => id.startsWith("media_player.") && id.includes("tritue_youtube_player"));
    return { entity: mine || "", title: "Nhạc YouTube & Zing", waveStyle: "bars" };
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string") {
      throw new Error("TriTue card requires a media_player entity");
    }
    this._config = {
      title: "TriTue Music",
      waveStyle: "bars",
      layout: "horizontal",
      // Diện mạo: để trống là giữ đúng giao diện cũ, không ép màu nào.
      bg_style: "gradient",   // gradient | solid | none (trong suốt, ăn theo dashboard)
      bg_color: "",           // màu nền, dạng #rrggbb
      accent_color: "",       // màu nhấn (nút, viền, sóng nhạc), dạng #rrggbb
      /* Bộ màu mở rộng. ĐỂ TRỐNG là giữ nguyên diện mạo cũ — _applyTheme chỉ đặt
         biến khi có màu hợp lệ, nên thẻ chưa cấu hình gì thì không đổi gì. */
      accent2_color: "",      // màu nhấn phụ, dạng #rrggbb
      text_color: "",         // màu chữ chính
      text_dim_color: "",     // màu chữ phụ
      surface_color: "",      // màu mặt thẻ con (bảng chọn, ô nổi)
      danger_color: "",       // màu cảnh báo / nút xoá
      line_color: "",         // màu viền, đường kẻ
      opacity: 100,           // độ đục của nền, 0-100
      zoom: 100,              // thu phóng chữ và nút, 50-150
      /* Hiện/ẩn từng mục của hàng nguồn. MẶC ĐỊNH BẬT HẾT, nên thẻ đang chạy không
         đổi gì. Ẩn ở đây là ẩn khỏi giao diện chứ không khoá nguồn phía máy phát:
         bài thuộc nguồn bị ẩn vẫn nghe lại được từ hàng đợi hay từ playlist. */
      show_youtube: true,
      show_zing: true,
      show_facebook: true,
      show_playlist: true,
      ...config,
    };
    /* Đổi «layout» trong trình sửa PHẢI thắng nút bấm trên card. Trước đây nút bấm
       ghi vào bộ nhớ của máy và đè VĨNH VIỄN, nên sửa trong trình sửa không thấy gì
       đổi — đúng chỗ «không đồng bộ giữa card và config». Nay: đổi trong cấu hình thì
       xoá lựa chọn riêng của máy này; bấm nút trên card vẫn thắng cho tới lần đổi
       cấu hình kế tiếp. */
    /* Ghi lại liệu người dùng có THẬT SỰ khai «layout» hay không. setConfig đặt sẵn
       mặc định "horizontal", nên nếu chỉ đọc this._config thì không phân biệt được
       "chưa ai chọn" với "đã chọn ngang" — mà hai trường hợp đó phải xử khác nhau. */
    this._layoutRo = typeof config.layout === "string" && config.layout !== "";
    const layoutMoi = this._config.layout || "";
    if (this._layoutTuConfig !== undefined && this._layoutTuConfig !== layoutMoi) {
      setLayoutChoice(this._config.entity, "");
    }
    this._layoutTuConfig = layoutMoi;
    // Sửa cấu hình ngay trên dashboard: áp lại ngay, khỏi chờ lần vẽ sau.
    if (this._rendered) {
      this._applyTheme();
      this._applyLayout();
      this._applySourceVisibility();
    }
  }

  set hass(hass) {
    this._hass = hass;
    deviceAudio.hass = hass;
    if (!this._rendered) {
      this._render();
      this._bindEvents();
      this._rendered = true;
      this._applyTheme();
      this._applyLayout();
      this._applySourceVisibility();
      this._renderSuggestions();
    }
    this._applySharedOutputs();
    this._syncPlayers();
    this._updateSourceButtons();
    this._loadCapabilities();
    this._loadHiddenPlayers();
    this._loadSuggestions();
    if (this._playlists === null && !this._playlistsRequested && this._entryId()) {
      this._playlistsRequested = true;
      this._loadPlaylists();
    }
    this._syncVideo();
    if (this._needsRestore) {
      this._needsRestore = false;
      this._restore();
    }
  }

  getCardSize() {
    return 8;
  }

  /** Bề rộng card. Ở dashboard kiểu "Sections", Home Assistant chia lưới 12 cột và
      card nào KHÔNG khai gì thì bị cấp mặc định hẹp — đó là lý do card này trông
      chật trên máy tính. Khai ở đây là xin trọn 12 cột; người dùng vẫn chỉnh lại
      được trong phần Bố cục của từng thẻ. min_columns giữ card còn dùng được khi
      bị kéo hẹp. */
  getGridOptions() {
    /* «columns: "full"» là cách tài liệu chính thức nêu để ép card rộng hết khổ,
       tương đương công tắc "Full width card" trong giao diện — khác với con số 12,
       vốn chỉ là chiều rộng mặc định của một section 12 cột.
       ĐÍNH CHÍNH điều tôi từng ghi ở 0.14.0: card KHÔNG khai gì thì vẫn được 12 cột
       sẵn, nên hàm này không phải thứ "làm card hết chật" như tôi đã nói.
       KHÔNG khai «rows»: tài liệu chỉ nhận số, và bỏ trống thì card không bị lưới
       ép chiều cao. Giới hạn thật: cơ chế này CHỈ áp dụng cho dashboard kiểu
       Sections; ở Masonry thì bề rộng card là bề rộng cột, mã card không đổi được. */
    return { columns: "full", min_columns: 6 };
  }

  connectedCallback() {
    if (!this._progressTimer) {
      this._progressTimer = setInterval(() => {
        this._updateProgress();
        this._syncAlong();
      }, 1000);
    }
    deviceAudio.listeners.add(this._onDeviceAudio);
    /* Máy nhà Táo: mọi lối gọi «listen» đều nhường việc cho khung — xem cửa chặn
       trong «deviceAudio.listen». */
    deviceAudio.nhuongChoKhung = (item, queue, index, batDau) =>
      this._ngheBangKhungMotMinh(item, queue, index, batDau);
    // Back on the dashboard (the same card, or a new one after leaving it): show the
    // search and what is playing again.
    this._needsRestore = true;
    if (this._rendered && this._hass) {
      this._needsRestore = false;
      this._restore();
    }
    if (!this._onFullscreenChange) {
      this._onFullscreenChange = () => {
        const player = this.shadowRoot?.querySelector(".player");
        if (!document.fullscreenElement) {
          this._ownFullscreen = false;
          this._leavingFullscreen = false;
          // Thoát bằng nút thu nhỏ của CHÍNH YouTube thì về hẳn thẻ, không dừng lại ở
          // trạng thái phủ kín trang. Chủ máy 19/09/2026: "điều khiển trực tiếp trên
          // video luôn, kể cả thu nhỏ màn hình về card". Trước đây chỉ gỡ "rotated",
          // nên thoát xong thẻ vẫn che cả trang và phải bấm thêm nút của card.
          player?.classList.remove("expanded", "rotated", "idle");
          clearTimeout(this._idleTimer);
          if (player) this._syncVideoExpandButton();
          try {
            screen.orientation?.unlock?.();
          } catch (_error) {
            // Nothing was locked.
          }
          return;
        }
        // Inside the shadow root the real fullscreen element (document's is the card).
        const inside = this.shadowRoot?.fullscreenElement;
        if (!player || !inside) return;
        if (inside !== player && player.contains(inside)) {
          // YouTube's own fullscreen button in the video. While the card is fullscreen it
          // reads as "make smaller" (owner 15/09/2026: it went back to portrait without
          // leaving fullscreen), so leave fullscreen altogether; otherwise turn sideways.
          if (this._ownFullscreen) {
            this._leavingFullscreen = true;
            document.exitFullscreen?.();
          } else {
            screen.orientation?.lock?.("landscape")?.catch?.(() => {});
          }
          return;
        }
        if (inside === player && this._leavingFullscreen) {
          // YouTube's layer is gone, the card's is still there: leave it too.
          this._leavingFullscreen = false;
          document.exitFullscreen?.();
          return;
        }
        this._ownFullscreen = inside === player;
        if (inside === player) this._syncVideoExpandButton();
      };
      document.addEventListener("fullscreenchange", this._onFullscreenChange);
    }
  }

  disconnectedCallback() {
    // Leaving the view unloads the iframe anyway; drop its listener and timers with it.
    clearInterval(this._progressTimer);
    this._progressTimer = null;
    clearInterval(this._waveTimer);
    this._waveTimer = null;
    clearInterval(this._henNhuongTieng);
    this._henNhuongTieng = null;
    clearInterval(this._henCanhChiTieng);
    this._henCanhChiTieng = null;
    if (this._onFullscreenChange) {
      document.removeEventListener("fullscreenchange", this._onFullscreenChange);
      this._onFullscreenChange = null;
    }
    deviceAudio.listeners.delete(this._onDeviceAudio);
    this._remember();
    this._closeVideo();
  }

  // Sinh markup sóng nhạc theo config wave_style — gọi 1 lần lúc _render() (không phải
  // mỗi lần cập nhật trạng thái), giống cách _veCotSong() của phicomm-r1-card.js sinh
  // sẵn các thanh rồi để CSS lo phần "đá đá".
  _renderWave() {
    const style = this._config.waveStyle || "bars";
    if (style === "simple") {
      const bars = Array.from({ length: 9 }, (_, i) => `<span style="--i:${i}"></span>`).join("");
      return `<div class="np-wave np-wave--simple" aria-hidden="true">${bars}</div>`;
    }
    if (style === "dots") {
      const cols = Array.from({ length: 14 }, (_, i) =>
        `<div class="wv-col" style="--i:${i}"><span class="wv-max"></span><span class="wv-dot"></span></div>`
      ).join("");
      return `<div class="np-wave np-wave--dots" aria-hidden="true">${cols}</div>`;
    }
    // "bars" (mặc định) — mật độ dày hơn bản cũ (12 → 22 thanh) để trông đầy hơn.
    const heights = [38, 62, 90, 45, 70, 33, 85, 55, 95, 40, 72, 58, 88, 42, 66, 30, 80, 50, 92, 36, 64, 78];
    const bars = heights.map((h, i) => `<span style="--i:${i};--h:${h}%"></span>`).join("");
    return `<div class="np-wave np-wave--bars" aria-hidden="true">${bars}</div>`;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        [hidden] { display: none !important; }
        /* Card tự làm MỐC ĐO cho chính nó. Trước đây mọi điểm ngắt viết bằng @media,
           tức đo bề rộng CỬA SỔ — sai về bản chất, vì bề rộng card do cột của
           dashboard quyết định chứ không phải cửa sổ. Card đặt trong cột hẹp trên
           màn hình rộng vẫn nhận luật "máy tính" rồi tràn ra ngoài; thấy rõ nhất ở
           ô xem trước của trình sửa (~330px) trong cửa sổ ~1040px. Đặt tên mốc để
           khỏi vô tình bám vào một khối bao khác của Home Assistant. */
        :host { container-type: inline-size; container-name: ytcard; }
        /* Nền do «bg_style» + «opacity» trong cấu hình điều khiển, qua hai biến
           --ad-bg-alpha (độ đục) và --ad-bg-image (kiểu nền). Mặc định giữ đúng
           diện mạo cũ, nên thẻ chưa cấu hình gì thì không đổi gì. */
        ha-card {
          overflow: hidden;
          color: var(--ad-text,#fff);
          background-color: rgba(var(--ad-c2,13,21,37), var(--ad-bg-alpha, 0.97));
          background-image: var(--ad-bg-image,
            radial-gradient(circle at 94% 2%, rgba(var(--ad-c1,0,204,204), .22), transparent 34%),
            linear-gradient(135deg, rgba(var(--ad-c1,0,204,204),0.22) 0%, rgba(var(--ad-c2,13,21,37),0.97) 55%));
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.3);
        }
        .wrap { padding: 16px; }
        header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
        /* Popup ngoài (announce-center-card) đã có tiêu đề + nút đóng riêng, nên h2 ở đây
           chỉ giữ lại cho JS gán textContent, không hiển thị để khỏi trùng chữ. */
        header .visually-hidden { display: none; }
        h2 { margin: 0; font-size: 1.2rem; line-height: 1.2; }
        .hint { color: rgba(255,255,255,.62); font-size: .86rem; }
        /* Khung chứa phải TỐI và trung tính hơn hẳn các nút bên trong. Trước đây
           khung dùng nền «màu nhấn 0.08» còn nút đang chọn dùng gradient cùng tông,
           chênh nhau quá ít nên nhìn không ra đâu là nền, đâu là lựa chọn. */
        .source-switch {
          display: grid;
          /* MẶC ĐỊNH HAI CỘT — bốn nút (YouTube, Zing MP3, Facebook, Playlist) dàn
             ngang chỉ vừa khi hàng thật sự rộng. Ba cột như bản cũ thì nút thứ tư rơi
             xuống một mình; bốn cột ở chỗ hẹp thì nhãn bị chính nút cắt cụt — đo
             19/09/2026, ảnh chụp cho thấy chữ "YouTube" đứt giữa chừng ở cột phải
             rộng 337px. Hai cột an toàn ở mọi chỗ hẹp, và luật ngay dưới mới bung ra
             bốn khi ĐO ĐƯỢC là đủ rộng. */
          grid-template-columns: repeat(2, minmax(0, 1fr));
          padding: 4px;
          margin: 12px 0 10px;
          border-radius: 12px;
          background: rgba(var(--ad-c2,13,21,37),0.55);
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.18);
        }
        /* Bung bốn cột khi CHÍNH CỘT CHỨA nó đủ rộng, không phải khi cả thẻ rộng. */
        @container ytcot (min-width: 460px) {
          .source-switch { grid-template-columns: repeat(4, minmax(0, 1fr)); }
          .source-switch.so-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          .source-switch.so-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        /* Ẩn bớt mục thì SỐ CỘT phải giảm theo, nếu không hàng thừa ô trống lệch hẳn
           sang một bên. Lớp «so-N» do «_applySourceVisibility» đặt theo số mục còn
           hiện. Chỉ viết những trường hợp KHÁC mặc định: chỗ hẹp vốn hai cột nên chỉ
           một mục mới phải sửa; chỗ rộng vốn bốn cột nên hai và ba mục phải sửa.
           Luật một-mục để ngoài khối đo vì nó đúng ở mọi bề rộng, và hai lớp (0,2,0)
           nên thắng luật một lớp bên trong khối đo bất kể thứ tự viết. */
        .source-switch.so-1 { grid-template-columns: minmax(0, 1fr); }
        /* BA MỤC THÌ MỘT HÀNG, ở mọi bề rộng — chủ máy chốt 19/09/2026: "nếu 3 cái
           thì phải đặt cùng hàng như trước chứ". Mặc định hai cột làm mục thứ ba
           rơi xuống một mình, nhìn như lỗi. Ba nhãn còn lại đều ngắn nên vẫn đủ
           chỗ; bốn mục thì vẫn giữ 2×2 khi hẹp vì nhãn "YouTube" từng bị cắt cụt. */
        .source-switch.so-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
        button, input { font: inherit; }
        button { cursor: pointer; }
        .source-button {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          border: 0;
          border-radius: 9px;
          padding: 7px 10px;
          color: rgba(255,255,255,.65);
          background: transparent;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .source-button ha-icon { --mdc-icon-size: 18px; flex: none; color: #ff0000; }
        /* Nút đang chọn: TÔ ĐẶC màu nhấn, chữ lấy màu tương phản đã tính theo độ
           sáng của chính màu nhấn — không còn gradient mờ lẫn vào nền. */
        .source-button[aria-pressed="true"] {
          color: var(--ad-on-accent, #0b0f17);
          background: var(--ad-accent, #00ffcc);
          box-shadow: 0 0 14px 1px rgba(var(--ad-c1,0,204,204),0.45);
        }
        .source-button[aria-pressed="true"] ha-icon { color: inherit; }
        form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 9px; }
        input[type="search"] {
          min-width: 0;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.25);
          border-radius: 11px;
          padding: 9px 12px;
          color: var(--ad-text,#fff);
          background: rgba(0,0,0,0.25);
          outline: none;
        }
        input[type="search"]:focus { border-color: var(--ad-accent,#00ffcc); box-shadow: 0 0 0 2px rgba(var(--ad-c1,0,204,204),0.25); }
        .primary {
          border: 0;
          border-radius: 11px;
          padding: 10px 15px;
          font-weight: 650;
        }
        .primary { color: var(--ad-text,#fff); background: linear-gradient(145deg, rgba(var(--ad-c1,0,204,204),0.65), rgba(var(--ad-c1,0,204,204),0.28)); box-shadow: 0 0 10px 1px rgba(var(--ad-c1,0,204,204),0.35); }
        .search-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; --mdc-icon-size: 19px; }
        button:disabled { cursor: not-allowed; opacity: .45; }
        .status { min-height: 18px; margin: 6px 1px 0; color: var(--secondary-text-color); font-size: .84rem; }
        .status.error { color: var(--ad-danger,#ff6b81); }
        .section { margin-top: 8px; }
        .section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; }
        .section-title h3 { margin: 0; font-size: .88rem; display: flex; align-items: center; gap: 6px; }
        .section-title h3 ha-icon { --mdc-icon-size: 17px; color: var(--ad-accent,#00ffcc); }
        /* Tách hẳn khỏi khu tìm kiếm/kết quả: khung riêng, viền + nền neon nhạt
           giống các khối khác của card, để không bị lẫn với ô tìm kiếm phía dưới. */
        .speaker-section {
          margin: 10px 0 4px;
          padding: 10px 10px 8px;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.2);
          border-radius: 14px;
          background: rgba(var(--ad-c1,0,204,204),0.05);
        }
        .players {
          display: flex; flex-wrap: wrap; align-content: flex-start; gap: 8px;
          height: 132px; overflow-y: auto; overflow-x: hidden; padding-right: 4px;
          /* Firefox */
          scrollbar-width: thin; scrollbar-color: rgba(var(--ad-c1,0,204,204),0.5) transparent;
        }
        /* Chrome/Safari/Edge: thanh scroll mảnh, màu theo theme, bo tròn thay vì
           thanh xám mặc định của trình duyệt. */
        .players::-webkit-scrollbar { width: 6px; }
        .players::-webkit-scrollbar-track { background: transparent; }
        .players::-webkit-scrollbar-thumb { background: rgba(var(--ad-c1,0,204,204),0.5); border-radius: 999px; }
        .players::-webkit-scrollbar-thumb:hover { background: rgba(var(--ad-c1,0,204,204),0.75); }
        .players-columns { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        /* ===== Thanh loa gọn: loa đang chỉnh âm lượng + nút Đổi loa bung/thu danh sách ===== */
        .spk-bar {
          display: flex; align-items: center; justify-content: space-between; gap: 10px;
          padding: 8px 10px; border-radius: 14px;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.2);
          background: rgba(var(--ad-c1,0,204,204),0.08);
        }
        .spk-bar-main { display: flex; align-items: center; gap: 9px; min-width: 0; }
        .spk-bar-icon { --mdc-icon-size: 20px; color: var(--ad-accent,#00ffcc); }
        .spk-bar-copy { min-width: 0; }
        /* Nhãn PHẢI có luật chống xuống dòng. Thiếu nó thì ở khung hẹp «LOA PHÁT
           NHẠC» rơi xuống ba dòng, đội khung cao lên và đè vào nút «Đổi loa» —
           đúng chỗ vỡ trong ảnh chụp. Nút thì flex:none nên không co được, vậy
           phần phải nhường là nhãn. */
        .spk-bar-label {
          font-size: .68rem; font-weight: 700; letter-spacing: .04em;
          text-transform: uppercase; color: var(--secondary-text-color);
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .spk-bar-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .95rem; font-weight: 600; }
        .spk-toggle {
          display: inline-flex; align-items: center; gap: 4px; flex: none;
          padding: 5px 10px; border-radius: 999px; cursor: pointer;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.25);
          background: transparent; color: inherit; font: inherit; font-size: .82rem;
        }
        .spk-toggle ha-icon { --mdc-icon-size: 17px; transition: transform .18s ease; }
        /* ===== Nút chọn bố cục dọc/ngang ngay trên card ===== */
        .header-tools { display: flex; align-items: center; gap: 8px; }
        .layout-switch {
          display: inline-flex; gap: 2px; padding: 2px; border-radius: 999px;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.2);
        }
        .layout-pick {
          display: grid; place-items: center; width: 28px; height: 28px;
          border: 0; border-radius: 999px; cursor: pointer;
          background: transparent; color: var(--secondary-text-color);
        }
        .layout-pick ha-icon { --mdc-icon-size: 18px; }
        .layout-pick.on { background: rgba(var(--ad-c1,0,204,204),0.18); color: var(--ad-accent,#00ffcc); }
        /* Màn hình hẹp luôn xếp một cột, nên nút chọn bố cục không còn ý nghĩa. */
        @container ytcard (max-width: 639px) { .layout-switch { display: none; } }
        .spk-toggle.open ha-icon { transform: rotate(180deg); }
        .spk-volume { margin-top: 8px; }
        .spk-volume:empty { display: none; }
        .spk-list { margin-top: 10px; }
        /* Loa đang được chỉnh âm lượng: TÔ NỀN chứ không viền — nhìn ra ngay.
           Phải thêm «.players» phía trước mới thắng được luật
           «.player-chip:has(input:checked)» — luật đó nằm phía DƯỚI trong tệp này
           nhưng có độ ưu tiên (0,2,1), vì :has() tính theo phần tử cụ thể nhất bên
           trong. Một mình «.player-chip.is-volume-target» (0,2,0) sẽ THUA dù viết
           trước hay sau: ở đây thứ tự không cứu được, chỉ độ ưu tiên mới quyết định.
           Thêm một lớp nữa thành (0,3,0) mới đè được cả nền lẫn màu chữ.
           Màu chữ lấy từ --ad-on-accent, do độ sáng của màu nhấn quyết định. */
        .players .player-chip.is-volume-target {
          background: var(--ad-accent, #00ffcc);
          border-color: var(--ad-accent, #00ffcc);
          color: var(--ad-on-accent, #0b0f17);
          box-shadow: 0 0 12px 1px rgba(var(--ad-c1,0,204,204),0.45);
        }
        .players .player-chip.is-volume-target .player-name,
        .players .player-chip.is-volume-target .device-icon,
        .players .player-chip.is-volume-target .hide-player,
        .players .player-chip.is-volume-target .move-player { color: inherit; }
        .player-name {
          border: 0; background: transparent; color: inherit; font: inherit;
          padding: 0; cursor: pointer; text-align: left;
        }
        .players-col-title {
          display: flex; align-items: center; gap: 5px; margin-bottom: 5px;
          font-size: .76rem; font-weight: 650; color: rgba(255,255,255,.6); text-transform: uppercase; letter-spacing: .02em;
        }
        .players-col-title ha-icon { --mdc-icon-size: 15px; color: var(--ad-accent,#00ffcc); }
        .players-empty-col { padding: 6px 2px; text-align: left; font-size: .8rem; }
        .player-chip {
          display: flex;
          align-items: center;
          gap: 7px;
          max-width: 100%;
          padding: 5px 9px;
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.2);
          border-radius: 999px;
          background: rgba(var(--ad-c1,0,204,204),0.08);
          cursor: pointer;
        }
        /* Loa ĐÃ TÍCH (sẽ phát): tô nền mờ của màu nhấn, không chỉ viền — trước đây
           chỉ đổi viền nên nhìn lướt không thấy loa nào đang được chọn. Vẫn khác
           với loa ĐANG CHỈNH ÂM LƯỢNG bên dưới: chỗ đó tô đặc và có viền ngoài. */
        .player-chip:has(input:checked) {
          border-color: var(--ad-accent,#00ffcc);
          background: rgba(var(--ad-c1,0,204,204),0.30);
          color: var(--ad-text,#fff);
          box-shadow: 0 0 10px 1px rgba(var(--ad-c1,0,204,204),0.35);
        }
        .player-chip.source-incompatible { opacity: .62; }
        .player-chip input { accent-color: var(--ad-accent,#00ffcc); }
        .player-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .device-icon { --mdc-icon-size: 17px; color: var(--secondary-text-color); }
        .hide-player {
          display: grid;
          place-items: center;
          width: 22px;
          height: 22px;
          margin: -2px -4px -2px 0;
          padding: 0;
          border: 0;
          border-radius: 50%;
          color: var(--secondary-text-color);
          background: transparent;
          --mdc-icon-size: 15px;
        }
        .hide-player:hover { color: var(--ad-danger,#ff6b81); background: rgba(var(--ad-c1,0,204,204),0.15); }
        .move-player {
          display: grid;
          place-items: center;
          width: 22px;
          height: 22px;
          margin: -2px 0;
          padding: 0;
          border: 0;
          border-radius: 50%;
          color: var(--ad-accent,#00ffcc);
          background: transparent;
          opacity: .55;
          --mdc-icon-size: 14px;
        }
        .move-player:hover { opacity: 1; background: rgba(var(--ad-c1,0,204,204),0.18); }
        .hidden-players { margin-top: 4px; }
        .hidden-toggle {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 2px;
          border: 0;
          color: var(--secondary-text-color);
          background: transparent;
          font-size: .82rem;
        }
        .hidden-toggle ha-icon { --mdc-icon-size: 16px; transition: transform .15s; }
        .hidden-toggle[aria-expanded="true"] ha-icon { transform: rotate(180deg); }
        .hidden-list { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
        .restore-player {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          max-width: 100%;
          padding: 5px 10px;
          border: 1px dashed var(--divider-color);
          border-radius: 999px;
          color: var(--secondary-text-color);
          background: transparent;
          font-size: .82rem;
          --mdc-icon-size: 15px;
        }
        .restore-player:hover { border-color: var(--ad-accent,#00ffcc); color: var(--ad-accent,#00ffcc); }
        .restore-player span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .player {
          /* Làm MỐC ĐỊNH VỊ cho lớp nền mờ của chế độ chỉ nghe. Không thể tô lên
             «.stage» vì nó là display: contents — không phải một hộp thật, các con
             của nó do chính «.player» xếp. Thêm mốc ở đây an toàn: thứ duy nhất neo
             tuyệt đối bên trong là «.picture-note», mà nó neo vào «.video-frame» vốn
             đã có mốc riêng. */
          position: relative;
          margin-top: 12px;
          padding: 6px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: transparent;
        }
        .video-frame {
          position: relative;
          width: 100%;
          aspect-ratio: 16 / 9;
          margin-bottom: 8px;
          overflow: hidden;
          border-radius: 10px;
          background: #000;
        }
        .video-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
        /* YouTube refused the embed: our own picture (or the thumbnail) replaces it. */
        .video-frame.no-embed { background: #000 var(--poster, none) center / contain no-repeat; }
        .video-frame.no-embed iframe { visibility: hidden; }
        .video-frame video.picture { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; background: #000; }
        /* KHUNG CHỈ MANG TIẾNG: thu còn một điểm ảnh. KHÔNG được dùng «display: none»
           hay thuộc tính «hidden» — cả hai làm trình duyệt dừng phát, tức mất đúng
           thứ khung này sinh ra để làm. Cách thu nhỏ chép của thẻ «phicomm-r1-card»
           (khối «.video-theater-stage.is-hidden» bên ấy). */
        .video-frame.chi-tieng {
          /* Thu bằng «max-width/max-height», KHÔNG bằng «width/height»: bề rộng của
             khung do một luật sáu lớp của bố cục hai cột đặt, luật một lớp ở đây thua
             — đo trong Chrome 20/09/2026: đặt «width: 1px» mà khung vẫn rộng 497px.
             Chặn trên là thuộc tính KHÁC nên không phải tranh độ ưu tiên với nó. */
          position: absolute;
          max-width: 1px;
          max-height: 1px;
          margin: 0;
          opacity: 0.001;
          pointer-events: none;
          overflow: hidden;
          clip-path: inset(50%);
        }
        .picture-note {
          position: absolute;
          left: 8px;
          right: 8px;
          bottom: 8px;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 6px 10px;
          padding: 6px 10px;
          border-radius: 9px;
          color: var(--ad-text,#fff);
          background: rgba(0, 0, 0, .75);
          font-size: 12px;
        }
        .picture-note button { border: 0; border-radius: 999px; padding: 5px 12px; color: #000; background: #fff; font-weight: 650; }
        .sound-hint {
          position: absolute;
          top: 8px;
          left: 50%;
          transform: translateX(-50%);
          padding: 4px 10px;
          border-radius: 999px;
          background: rgba(0, 0, 0, 0.72);
          color: var(--ad-text,#fff);
          font-size: 12px;
          white-space: nowrap;
          pointer-events: none;
        }
        .now { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 11px; align-items: center; }
        /* .now/.now-cover đã chuyển sang khối .np-zone (sibling của .player) —
           dùng tổ hợp "~" thay cho descendant vì không còn nằm trong .player. */
        .player.video-on ~ .yt-zone-playlist .np-zone .now { grid-template-columns: minmax(0, 1fr); }
        .player.video-on ~ .yt-zone-playlist .np-zone .now-cover { display: none; }
        .now-cover {
          display: grid;
          place-items: center;
          width: 52px;
          height: 52px;
          overflow: hidden;
          border-radius: 9px;
          color: var(--secondary-text-color);
          background: var(--divider-color);
        }
        .now-cover img { width: 100%; height: 100%; object-fit: cover; }
        .now-copy { min-width: 0; }
        .now-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; }
        .now-meta { margin-top: 3px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .8rem; }
        /* control-bar giờ chỉ còn transport-group (đã chuyển sang .np-zone) nên căn giữa. */
        .control-bar { display: flex; align-items: center; justify-content: center; gap: 6px; margin-top: 6px; }
        /* stage-controls: nhóm nút liên quan tới hiển thị video (xem/xoay/phóng to/đóng),
           vẫn ở lại trong .stage, nằm ngay dưới video-frame, căn phải. */
        .stage-controls { display: flex; align-items: center; justify-content: flex-end; gap: 2px; margin-top: 6px; }
        /* Không còn cần luật ẩn cả khối nữa: hai nút «Nghe…» nay nằm CHUNG hàng này,
           nên hàng luôn có nội dung và dải trống cũ tự hết. Giữ luật ẩn lại thì nó
           sẽ ẩn luôn nút «Nghe khi tắt màn hình». */
        /* KHÔNG cho xuống dòng. Trước đây hàng này để flex-wrap: wrap, nên trên điện
           thoại hễ cụm nút chữ không đủ chỗ là bị đẩy hẳn xuống dòng riêng — trông
           đúng như lỗi, và chủ máy đã báo hai lần.
           Cách chữa không dựa vào việc tôi đoán đúng số đo màn hình: cụm biểu tượng
           giữ nguyên cỡ, cụm nút chữ được phép CO lại và cắt bớt chữ khi chật. Nhờ
           vậy chúng luôn nằm chung một hàng ở mọi bề rộng. */
        .stage-controls { flex-wrap: nowrap; }
        .stage-controls > .view-group { flex: 0 0 auto; }
        .stage-controls > .device-row { flex: 1 1 auto; min-width: 0; }
        .device-row .pill { min-width: 0; }
        .device-row .pill span { overflow: hidden; text-overflow: ellipsis; }
        .transport-group, .view-group { display: flex; align-items: center; gap: 2px; }
        .ctl {
          display: grid;
          place-items: center;
          width: 36px;
          height: 36px;
          padding: 0;
          border: 0;
          border-radius: 50%;
          color: var(--primary-text-color);
          background: transparent;
          --mdc-icon-size: 22px;
        }
        .ctl:hover:not(:disabled) { background: rgba(var(--ad-c1,0,204,204),0.15); }
        .ctl.main {
          width: 42px;
          height: 42px;
          margin: 0 2px;
          color: var(--ad-text,#fff);
          background: linear-gradient(145deg, rgba(var(--ad-c1,0,204,204),0.55), rgba(var(--ad-c1,0,204,204),0.2));
          box-shadow: 0 0 14px 2px rgba(var(--ad-c1,0,204,204),0.4);
          --mdc-icon-size: 26px;
        }
        .ctl.main:hover:not(:disabled) { filter: brightness(1.15); }
        /* Nút chuyển bài (trước/sau/dừng) trong bảng "Đang phát" — trước đây nền
           trong suốt + icon màu chữ chính nên rất mờ trên nền tối. Đổi màu về
           accent của theme + thêm viền/đổ bóng kiểu "nổi 3D" (bevel) để bấm dễ
           nhận ra hơn. */
        .control-bar .ctl:not(.main) {
          color: var(--ad-accent, #00ffcc);
          background: linear-gradient(145deg, rgba(255,255,255,.12), rgba(0,0,0,.32));
          border: 1px solid rgba(var(--ad-c1,0,204,204),.6);
          box-shadow:
            0 2px 5px rgba(0,0,0,.4),
            inset 0 1px 0 rgba(255,255,255,.18),
            inset 0 -2px 3px rgba(0,0,0,.4);
        }
        .control-bar .ctl:not(.main):hover:not(:disabled) {
          background: linear-gradient(145deg, rgba(255,255,255,.2), rgba(0,0,0,.26));
          box-shadow:
            0 3px 7px rgba(0,0,0,.45),
            inset 0 1px 0 rgba(255,255,255,.22),
            inset 0 -2px 3px rgba(0,0,0,.4),
            0 0 9px 1px rgba(var(--ad-c1,0,204,204),.55);
        }
        .control-bar .ctl.stop {
          color: #ff8a95;
          border-color: rgba(255,107,129,.6);
        }
        .control-bar .ctl.stop:hover:not(:disabled) {
          box-shadow:
            0 3px 7px rgba(0,0,0,.45),
            inset 0 1px 0 rgba(255,255,255,.22),
            inset 0 -2px 3px rgba(0,0,0,.4),
            0 0 9px 1px rgba(255,107,129,.55);
        }
        .ctl.stop { color: var(--ad-danger,#ff6b81); }
        .view-group .ctl { width: 32px; height: 32px; color: var(--secondary-text-color); --mdc-icon-size: 19px; }
        input[type="range"] { width: 100%; accent-color: var(--ad-accent,#00ffcc); }
        .progress { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; margin-top: 6px; font-size: .74rem; font-variant-numeric: tabular-nums; color: var(--primary-text-color); }
        /* Timeline: trước đây cao 4px + nền mờ theo --divider-color nên khó thấy.
           Thêm viền + bóng đổ trong (inset) để tạo cảm giác "rãnh nổi 3D", fill
           dùng gradient + glow rõ hơn. */
        .progress .bar {
          height: 6px;
          /* MỞ ra cho núm tròn thò khỏi rãnh. Trước đây «overflow: hidden» sẽ cắt
             cụt đúng nửa cái núm. Vệt màu bên trong tự bo góc nên không tràn. */
          overflow: visible;
          border-radius: 4px;
          /* Bấm/kéo để tua. touch-action: none để ngón tay kéo ngang trên thanh không
             bị trình duyệt hiểu nhầm thành cuộn trang. */
          cursor: pointer;
          touch-action: none;
          background: rgba(0,0,0,.38);
          border: 1px solid rgba(var(--ad-c1,0,204,204),.45);
          box-shadow: inset 0 1px 3px rgba(0,0,0,.6);
        }
        .progress .fill {
          position: relative;
          width: 0;
          height: 100%;
          border-radius: 4px;
          /* Chuyển sắc từ màu nhấn PHỤ sang màu nhấn CHÍNH — chưa đặt màu phụ thì rơi
             về đúng dáng cũ, nên thẻ chưa cấu hình gì không đổi gì. */
          background: linear-gradient(90deg, var(--ad-accent2, var(--ad-accent,#00ffcc)), var(--ad-accent,#00ffcc));
          box-shadow: 0 0 8px 1px var(--ad-accent,#00ffcc), inset 0 1px 0 rgba(255,255,255,.4);
          transition: width .9s linear;
        }
        /* Núm tròn ở đầu vệt màu: vừa cho biết đang ở đâu, vừa mời người ta kéo. */
        .progress .fill::after {
          content: "";
          position: absolute;
          right: -7px;
          top: 50%;
          width: 14px;
          height: 14px;
          margin-top: -7px;
          border-radius: 50%;
          background: #fff;
          box-shadow: 0 1px 5px rgba(0,0,0,.5);
        }

        /* ── CHỈ NGHE: KHỐI ĐẶC, KHÔNG LỚP MỜ ────────────────────────────────────
           Làm lại 19/09/2026 sau khi tự chụp ảnh card và nhìn thấy ba lỗi mà ảnh
           chụp tay không lộ ra: lớp nền mờ TRÀN khỏi khu phát và đè lên hai nút
           «Nghe trên máy này» / «Nghe khi tắt màn hình» tới mức không đọc nổi chữ,
           đĩa tròn che mất số phút giây, và khung kính lệch hẳn sang phải.
           Dữ liệu của skill ui-ux-pro-max ghi «Cluttered layout» là thứ phải tránh
           cho nhóm nhạc, mẫu khuyến nghị là nền tối đặc + khối rõ cạnh, và sóng nhạc
           là điểm nhấn được khuyến khích. Nên: bỏ hết lớp chồng, mỗi hàng một việc.
           Thang khoảng cách: 4 / 8 / 12 / 16. Bo góc: 10px cho khối. */
        /* ===== CHỈ NGHE NHẠC: một hàng «đĩa | khung sóng + nút» =====
           Học theo thẻ phicomm-r1 chủ máy gửi 19/09/2026. Điểm mấu chốt của họ mà bản
           cũ của tôi thiếu: khung sóng có CHIỀU CAO CỐ ĐỊNH và hàng nút nằm ngay trong
           khung ấy (justify-content: space-between). Nhờ vậy sóng nhạc không thể cao
           lấn, còn hàng nút luôn nằm đúng đáy khung và tự căn giữa — thay vì hai khối
           rời nhau, mỗi khối một nền, nhìn lỏng lẻo.
           Vạch tiến độ vẫn nằm NGOÀI khung (chủ máy chốt 18/09/2026). */
        .nghe-hang {
          display: grid;
          grid-template-columns: clamp(76px, 24cqw, 112px) minmax(0, 1fr);
          gap: 12px;
          align-items: center;
          margin-top: 10px;
        }
        .nghe-bia {
          display: grid;
          place-items: center;
          aspect-ratio: 1;
          overflow: hidden;
          border: 3px solid rgba(255,255,255,.18);
          border-radius: 50%;
          color: var(--secondary-text-color);
          background: radial-gradient(circle at 30% 25%, rgba(var(--ad-c1,0,204,204),.35), rgba(0,0,0,.55));
          --mdc-icon-size: 34px;
        }
        /* Ảnh và biểu tượng dự phòng chồng đúng một ô lưới, không đẩy nhau. */
        .nghe-bia > * { grid-area: 1 / 1; }
        .nghe-bia img { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
        /* Đĩa bấm được để phát/dừng. Hiệu ứng quay LUÔN gắn sẵn, chỉ bật/tắt bằng
           «animation-play-state» — chủ máy 19/09/2026: "đang quay thì kích vào dừng
           đúng vị trí đó". Nếu gỡ hẳn hiệu ứng lúc dừng thì ảnh bật ngược về góc 0;
           tạm dừng thì trình duyệt giữ nguyên góc hiện tại. */
        .nghe-bia { cursor: pointer; }
        .nghe-bia:focus-visible { outline: 2px solid var(--ad-accent,#00ffcc); outline-offset: 2px; }
        .nghe-bia img:not([hidden]) { animation: nghe-quay 7.2s linear infinite; animation-play-state: paused; }
        /* Nhạc đang chạy thì đĩa quay, TRỪ KHI người dùng tự bấm cho nó dừng. Lớp
           «dung-quay» chỉ ghìm cái đĩa lại, nhạc vẫn phát bình thường. */
        .wrap.is-playing .nghe-bia:not(.dung-quay) img:not([hidden]) { animation-play-state: running; }
        @keyframes nghe-quay { to { transform: rotate(360deg); } }
        .nghe-khung {
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          height: clamp(96px, 26cqw, 120px);
          padding: 10px 12px;
          /* Trong suốt, không viền — chủ máy chốt 19/09/2026. Khung nghe bên ngoài đã
             có viền và nền riêng rồi; lồng thêm một khung nữa bên trong là viền trong
             viền, đúng thứ làm bố cục rối. */
          border: 0;
          border-radius: 14px;
          background: none;
        }
        .nghe-khung > .control-bar { margin-top: 0; }
        /* Xem video: hàng này rút về đúng hàng nút — đĩa ẩn, khung hết viền và nền, để
           nút nằm sát dưới hình như cũ. */
        .player.video-on .nghe-bia { display: none; }
        .player.video-on .nghe-hang { display: block; margin-top: 0; }
        .player.video-on .nghe-khung { display: block; height: auto; padding: 0; border: 0; background: none; }
        /* ===== KHUNG NGHE: ảnh bài hát làm nền, tên bài và đĩa nằm CHUNG một khung =====
           Chủ máy 19/09/2026: "Nền cũng lấy ảnh bài hát, tên bài cũng trên phần khung
           chứa đĩa hát, không có tách riêng".
           Cách pha của phicomm-r1, và đây là chỗ bản cũ của tôi làm sai: họ gần như
           KHÔNG làm mờ (blur 0.4px) — thứ đẩy ảnh xuống làm nền là GIẢM SÁNG còn 58%
           cộng một lớp gradient tối dần từ trên xuống. Bản cũ của tôi làm mờ thật mạnh
           nên nền vừa nhoè vừa vẫn sáng, chữ đè lên không đọc nổi. */
        .nghe-hero {
          position: relative;
          overflow: hidden;
          margin-top: 8px;
          padding: 14px 12px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: rgba(255,255,255,.03);
        }
        .nghe-nen {
          position: absolute;
          inset: 0;
          width: 100%;
          height: 100%;
          object-fit: cover;
          transform: scale(1.02);
          filter: saturate(1.16) brightness(.58) blur(.4px);
          pointer-events: none;
        }
        .nghe-phu-lop {
          position: absolute;
          inset: 0;
          /* Tối MẠNH ngay từ trên xuống. Bản chép nguyên của phicomm bắt đầu ở 12% vì
             bên họ chỗ đó trống; thẻ này đặt TÊN BÀI ngay trên cùng, nên 12% là chữ
             chồng lên hình — đo bằng ảnh chụp 19/09/2026: dòng "Đang phát · YouTube"
             nằm đè lên chữ "ASTLEY" của ảnh nền, không đọc nổi. */
          background: linear-gradient(180deg, rgba(0,0,0,.62) 0%, rgba(0,0,0,.40) 42%, rgba(0,0,0,.72) 100%);
          pointer-events: none;
        }
        /* Ruột nằm trên hai lớp nền. Thiếu z-index là chữ chui xuống dưới lớp phủ. */
        .nghe-ruot { position: relative; z-index: 1; }
        /* Xem video thì khung nền thu lại thành khung trơn: đã có hình chạy rồi. */
        .player.video-on .nghe-hero {
          margin-top: 6px;
          padding: 0;
          border: 0;
          background: none;
        }
        .player.video-on :is(.nghe-nen, .nghe-phu-lop, .nghe-dau) { display: none; }
        /* Hàng tiêu đề của khối nghe: tên bài + ca sĩ bên trái, nhãn nguồn bên phải —
           đúng kiểu «.hero-top» của thẻ phicomm-r1. */
        .nghe-dau {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 12px;
          margin-top: 2px;
        }
        .nghe-chu { min-width: 0; }
        .nghe-ten {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          font-size: 1rem;
          font-weight: 800;
          line-height: 1.2;
        }
        .nghe-phu {
          margin-top: 3px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          /* KHÔNG dùng «--secondary-text-color» ở đây: dòng này nằm trên ẢNH BÀI HÁT
             chứ không nằm trên nền phẳng, màu xám phụ chìm hẳn vào hình. Thẻ
             phicomm-r1 cũng đổi màu riêng cho dòng này vì đúng lý do ấy. */
          color: rgba(255,255,255,.82);
          font-size: .8rem;
        }
        .nghe-nguon {
          flex-shrink: 0;
          padding: 5px 11px;
          border: 1px solid rgba(var(--ad-c1,0,204,204),.35);
          border-radius: 11px;
          background: rgba(var(--ad-c1,0,204,204),.16);
          color: var(--ad-text,#fff);
          font-size: .72rem;
          font-weight: 800;
          letter-spacing: .04em;
          text-transform: uppercase;
          white-space: nowrap;
        }
        /* Ô "đang phát" cũ ở cột phải nay thừa: tên bài đã nằm trong khối nghe. Giữ
           phần tử trong DOM (mã cũ vẫn ghi tên bài vào đó) nhưng không bày ra nữa.
           PHẢI dùng hai lớp «.yt-zone-playlist .np-zone»: luật nền của «.np-zone» khai
           báo XA BÊN DƯỚI trong cùng bảng kiểu và cũng chỉ một lớp, nên viết
           «.np-zone { display: none }» ở đây thì thua theo thứ tự nguồn — đo bằng ảnh
           chụp 19/09/2026: ô cũ vẫn hiện nguyên. */
        .yt-zone-playlist .np-zone { display: none; }
        .join-session { border-style: dashed; color: var(--ad-accent,#00ffcc); }
        .others { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
        .others:empty { display: none; }
        .other-session {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          max-width: 100%;
          padding: 4px 10px 4px 4px;
          border: 1px solid var(--divider-color);
          border-radius: 999px;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
          font-size: .8rem;
          --mdc-icon-size: 16px;
        }
        .other-session img { width: 22px; height: 22px; border-radius: 50%; object-fit: cover; }
        .other-session span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .other-session:hover { border-color: var(--ad-accent,#00ffcc); }
        .speaker-volumes { display: grid; gap: 2px; margin-top: 4px; }
        .speaker-volumes:empty { display: none; }
        .svol-row { display: grid; grid-template-columns: minmax(70px, 30%) 1fr 36px; align-items: center; gap: 8px; }
        .svol-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .8rem; }
        .svol-pct { text-align: right; color: var(--secondary-text-color); font-size: .78rem; font-variant-numeric: tabular-nums; }
        .results { display: grid; gap: 6px; max-height: 330px; margin-top: 10px; overflow: auto; padding-right: 2px; }
        .results:empty { display: none; }
        .results-toggle {
          display: flex; align-items: center; gap: 6px; width: 100%; margin-top: 10px;
          padding: 8px 10px; border: 1px solid var(--divider-color, rgba(255,255,255,.12));
          border-radius: 10px; background: none; color: var(--secondary-text-color);
          font: inherit; font-size: .82rem; text-align: left; cursor: pointer;
        }
        .results-toggle:hover { color: var(--primary-text-color); }
        .results-toggle-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .result {
          display: grid;
          grid-template-columns: 48px minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
          padding: 6px;
          border-radius: 10px;
          background: rgba(var(--ad-c1,0,204,204),0.08);
          border: 1px solid rgba(var(--ad-c1,0,204,204),0.12);
        }
        .cover { width: 48px; height: 48px; border-radius: 7px; object-fit: cover; background: var(--divider-color); }
        .track { min-width: 0; }
        .track-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; font-size: .92rem; }
        .track-meta { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .78rem; margin-top: 3px; }
        .play-result {
          display: grid;
          place-items: center;
          width: 34px;
          height: 34px;
          padding: 0;
          border: 0;
          border-radius: 50%;
          color: var(--ad-text,#fff);
          background: linear-gradient(145deg, rgba(var(--ad-c1,0,204,204),0.6), rgba(var(--ad-c1,0,204,204),0.22));
          box-shadow: 0 0 8px 0 rgba(var(--ad-c1,0,204,204),0.4);
          --mdc-icon-size: 20px;
        }
        .result-actions { display: flex; align-items: center; gap: 6px; }
        .icon-button {
          display: grid;
          place-items: center;
          width: 30px;
          height: 30px;
          padding: 0;
          border: 0;
          border-radius: 50%;
          color: var(--secondary-text-color);
          background: transparent;
          --mdc-icon-size: 18px;
        }
        .icon-button:hover:not(:disabled) { color: var(--primary-text-color); background: var(--divider-color); }
        .icon-button.danger:hover:not(:disabled) { color: var(--ad-danger,#ff6b81); }
        .save-playlist {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          width: 100%;
          margin-top: 8px;
          padding: 7px 10px;
          border: 1px dashed var(--ad-accent,#00ffcc);
          border-radius: 11px;
          color: var(--ad-accent,#00ffcc);
          background: transparent;
          font-weight: 650;
          --mdc-icon-size: 18px;
        }
        .add-menu { grid-column: 1 / -1; display: grid; gap: 4px; padding: 6px; border-radius: 9px; background: var(--card-background-color, var(--secondary-background-color)); }
        .add-menu button.add-to { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border: 0; border-radius: 7px; color: var(--primary-text-color); background: transparent; text-align: left; --mdc-icon-size: 16px; }
        .add-menu button.add-to:hover { background: var(--divider-color); }
        .add-menu .count, .playlist-count { color: var(--secondary-text-color); font-size: .78rem; }
        .add-menu .add-to span:first-of-type { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .add-menu form, .playlist-panel form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px; }
        .playlist-panel { display: grid; gap: 8px; margin-top: 10px; }
        .playlist-panel input, .add-menu input {
          min-width: 0;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          padding: 8px 11px;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
          outline: none;
        }
        .playlist { border: 1px solid rgba(var(--ad-c1,0,204,204),0.18); border-radius: 12px; overflow: hidden; background: rgba(var(--ad-c1,0,204,204),0.05); }
        .playlist-head { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 6px; padding: 6px 6px 6px 8px; }
        .playlist-toggle { display: flex; align-items: center; gap: 6px; min-width: 0; padding: 0; border: 0; color: var(--primary-text-color); background: transparent; text-align: left; --mdc-icon-size: 18px; }
        .playlist-toggle ha-icon { transition: transform .15s; color: var(--secondary-text-color); }
        .playlist-toggle[aria-expanded="true"] ha-icon { transform: rotate(180deg); }
        .playlist-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 650; }
        .playlist-tools { display: flex; align-items: center; gap: 2px; }
        .playlist-items { display: grid; gap: 2px; padding: 4px 6px 6px; border-top: 1px solid var(--divider-color); }
        .playlist-item { display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: center; gap: 6px; padding: 3px 0; }
        .playlist-item .num { text-align: right; color: var(--secondary-text-color); font-size: .74rem; font-variant-numeric: tabular-nums; }
        .playlist-item .title { display: -webkit-box; overflow: hidden; -webkit-line-clamp: 2; -webkit-box-orient: vertical; font-size: .86rem; line-height: 1.25; }
        .playlist-item .meta { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .74rem; }
        .playlist-item .play-result { width: 30px; height: 30px; --mdc-icon-size: 17px; }
        .playlist-empty { padding: 12px 6px; text-align: center; color: var(--secondary-text-color); font-size: .84rem; }
        .play-result.listen { color: var(--ad-accent,#00ffcc); background: rgba(var(--ad-c1,0,204,204),0.2); box-shadow: 0 0 8px 0 rgba(var(--ad-c1,0,204,204),0.3); }
        /* Bỏ margin-top: nó nay là phần tử cùng hàng với sáu biểu tượng, không phải
           một dòng riêng nữa. «margin-right: auto» đẩy nó sang trái để sáu biểu tượng
           vẫn dồn phải như trước. */
        .device-row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-right: auto; }
        .pill {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          height: 28px;
          padding: 0 10px;
          border: 1px solid var(--divider-color);
          border-radius: 999px;
          color: var(--secondary-text-color);
          background: transparent;
          font-size: .76rem;
          font-weight: 600;
          white-space: nowrap;
          --mdc-icon-size: 15px;
        }
        .pill[aria-pressed="true"] { border-color: var(--ad-accent,#00ffcc); color: var(--ad-text,#fff); background: linear-gradient(145deg, rgba(var(--ad-c1,0,204,204),0.55), rgba(var(--ad-c1,0,204,204),0.2)); box-shadow: 0 0 8px 0 rgba(var(--ad-c1,0,204,204),0.35); }
        .empty { padding: 14px 8px; text-align: center; color: var(--secondary-text-color); font-size: .88rem; }
        /* Phóng to / toàn màn hình: cả khối phát (video + nút + âm lượng) phủ màn hình. */
        /* Expanded or fullscreen: the picture fills the screen like YouTube's own player
           (16:9, never cropped) with the title floating over its top and the progress and
           buttons over its lower edge, all fading out when idle. Owner 15/09/2026: YouTube's
           fullscreen filled the monitor while the card left black bands for its controls. */
        .player.expanded,
        .player:fullscreen {
          position: fixed;
          inset: 0;
          z-index: 10;
          margin: 0;
          border: 0;
          border-radius: 0;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 0;
          color: var(--ad-text,#fff);
          background: #000;
        }
        /* The stage only groups the player's parts so they can be turned together. */
        .stage { display: contents; }
        /* Turning the picture only helps a phone held upright. */
        @media (orientation: landscape) { .ctl.video-rotate { display: none; } }
        .player:is(.expanded, :fullscreen) > .stage > .video-frame {
          width: min(100%, calc(100dvh * 16 / 9));
          margin: 0 auto;
          border-radius: 0;
        }
        .player:is(.expanded, :fullscreen) > .stage > :is(.speaker-volumes, .device-row, .others) { display: none; }
        /* «.device-row» giờ nằm TRONG «.stage-controls» nên luật trên (con trực tiếp
           của .stage) không còn với tới nó. Thiếu dòng này là lúc phóng to/toàn màn
           hình hai nút «Nghe…» lọt vào giữa màn hình. */
        .player:is(.expanded, :fullscreen) > .stage > .stage-controls > .device-row { display: none; }
        /* Nhóm nút màn hình (view-group) vẫn ở trong .stage — nổi ở góc trên-phải video. */
        .player:is(.expanded, :fullscreen) > .stage > .stage-controls {
          position: absolute;
          /* Nút của card nằm bên TRÁI, không phải bên phải. YouTube đặt cụm bánh răng,
             phụ đề và phóng to ở cạnh phải; mà khi xoay ngang thì cả khung phát quay
             90° nên hàng nút của card quay theo và rơi đúng vào cụm ấy — chủ máy báo
             18/09/2026: "nút trên card che nút setting trên youtube". */
          top: 0;
          left: 0;
          z-index: 2;
          margin: 0;
          padding: max(10px, env(safe-area-inset-top)) 12px;
          transition: opacity .3s;
        }
        /* now/progress/control-bar giờ nằm trong .np-zone — là sibling của .player (không
           còn là con của .stage) nên khi player mở rộng/toàn màn hình, dùng tổ hợp "~"
           để nổi cả khối .np-zone lên trên video, thay cho "> .stage >" như bản cũ. */
        /* PHÓNG TO THÌ ẨN HẲN CẢ CỘT PHẢI. Chủ máy gửi ảnh 19/09/2026: trên iPhone,
           lúc mở hết màn thì hàng nguồn và ô tìm kiếm HIỆN ĐÈ lên video đang xoay.
           Nói thẳng: lỗi này KHÔNG dựng lại được trong Chrome — đo ở khổ 390px, hỏi
           «phần tử trên cùng tại tâm ô tìm kiếm» thì trả về «.video-frame», tức lớp
           phủ che đúng. Đây là đặc thù WebKit mà tôi chưa chứng minh được cơ chế.
           Nên luật này KHÔNG nhắm vào cơ chế, nó GỠ BỎ CHẾ ĐỘ HỎNG: lớp phủ chạy
           đúng thì mấy khối này vốn đã khuất, chẳng mất gì; lớp phủ hụt thì chúng
           đã ẩn nên không còn gì để đè lên video.
           ẨN TẤT, không chừa «.np-zone»: dải ấy ĐÃ có luật ẩn riêng khi phóng to
           (xem luật cùng tên phía dưới) theo đúng yêu cầu 18/09/2026 — "phóng to
           toàn màn hình thì ẩn hết, lúc này dùng bằng YouTube là được". Chừa nó ra
           chỉ tạo một ngoại lệ không có thật rồi đánh lừa người đọc sau. Đường
           thoát vẫn còn: hàng biểu tượng «.stage-controls» nằm TRONG khung phát.
           Viết theo NGUYÊN TẮC («mọi con trực tiếp») chứ không liệt kê bảy lớp:
           thêm khối mới vào cột sau này thì tự được che, không ai phải nhớ. */
        .player:is(.expanded, :fullscreen) ~ .yt-zone-playlist .yt-playlist-inner > * {
          display: none;
        }
        .player:is(.expanded, :fullscreen):not(.picture-on) ~ .yt-zone-playlist .np-zone .now { display: none; }
        .player:is(.expanded, :fullscreen) ~ .yt-zone-playlist .np-zone {
          position: fixed;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 11;
          margin: 0;
          padding: 0;
          border: 0;
          border-radius: 0;
          background: transparent;
          transition: opacity .3s;
        }
        /* Ba khối này nay là con của «.stage», nên bộ chọn anh-em cũ không còn với tới.
           Đây đúng là chỗ lần trước phải viết lại theo chiều ngược — xem chú thích trên. */
        .player:is(.expanded, :fullscreen) .np-wave { display: none; }
        /* Đang xem video thì ẩn sóng nhạc: đã có hình chạy rồi, thêm sóng trang trí chỉ
           tốn chỗ. Dùng bộ chọn HẬU DUỆ chứ không phải «> .stage >»: 19/09/2026 sóng
           nhạc đã chuyển vào trong «.nghe-khung», nên đường con-trực-tiếp cũ sẽ đứt. */
        .player.video-on .np-wave { display: none; }
        .player:is(.expanded, :fullscreen) ~ .yt-zone-playlist .np-zone .now {
          padding: max(12px, env(safe-area-inset-top)) 16px 8px;
          background: linear-gradient(rgba(0, 0, 0, .7), transparent);
        }
        /* TOÀN MÀN HÌNH: ẩn hẳn thanh tiến trình và hàng nút phát của card.
           Chủ máy chốt 18/09/2026: "khi phóng to toàn màn hình tôi muốn ẩn hết các cái
           này vì lúc này dùng bằng youtube là được" — trình phát YouTube đã có đủ thanh
           tua và nút của nó, bày thêm một bộ nữa chỉ che mất hình.
           GIỮ LẠI hàng biểu tượng góc trên-phải («.stage-controls»): đó là đường thoát
           chắc chắn của card, và nó vốn đã tự mờ khi để yên (xem luật «.idle» ngay bên
           dưới) nên không choán hình. */
        /* «:not(.picture-on)» — HÌNH CỦA CHÍNH THẺ thì giữ lại thanh tiến trình và
           hàng nút phát. Luật ẩn này sinh ra vì khung nhúng YouTube đã có bộ nút
           riêng nên thẻ nhường chỗ (yêu cầu 18/09: "lúc này dùng bằng YouTube là
           được"). Nhưng video Facebook chạy bằng phần tử «<video>» do thẻ dựng, và
           «_tryPicture» dựng nó KHÔNG có bộ nút gốc — nhường chỗ cho một bộ nút
           không tồn tại, nên phóng to là mất sạch đường tua. Chủ máy báo 20/09/2026.
           Tua bằng thanh của thẻ còn ĐÚNG hơn bộ nút gốc: «_seekFraction» dời CẢ
           tiếng lẫn hình nên hai thứ không lệch nhau, trong khi bộ nút gốc chỉ dời
           mỗi hình rồi bị vòng đồng bộ kéo ngược về. */
        .player:is(.expanded, :fullscreen):not(.picture-on) :is(.progress, .control-bar, .nghe-hang) { display: none; }
        /* Ở phóng to / toàn màn hình, BỎ NỐT hàng biểu tượng — chủ máy 18/09/2026:
           "phóng to toàn màn vẫn thấy các icon rác mà tôi kêu bỏ đi". Ở 0.20.4 tôi cố
           ý giữ lại làm đường thoát và có nói "muốn ẩn nốt thì bảo"; nay bảo rồi.
           GIỮ LẠI ĐÚNG NÚT ĐÓNG: bỏ sạch thì đường ra chỉ còn nút của YouTube và phím
           Esc, mà chủ máy vừa báo trình phát không chạy — không nên để lối thoát duy
           nhất phụ thuộc vào đúng thứ đang trục trặc.
           Lớp chữ và nhãn nguồn của chế độ chỉ nghe cũng ẩn ở đây, để phòng khi JS
           chưa kịp cập nhật. */
        .player:is(.expanded, :fullscreen) > .stage > .stage-controls .ctl:not(.video-close) { display: none; }
        /* TOÀN MÀN HÌNH THẬT: card không vẽ gì lên hình nữa, kể cả nút đóng. Chủ máy
           19/09/2026: "không hiện thanh điều khiển thời gian, thanh điều khiển play
           stop, các icon góc trên cùng bên phải… điều khiển trực tiếp trên video luôn,
           kể cả thu nhỏ màn hình về card".
           Bỏ hết vẫn có đường ra, và cả hai đều KHÔNG phải nút của card: phím Esc của
           trình duyệt, và nút thu nhỏ của chính YouTube — bộ xử lý «fullscreenchange»
           bên dưới đưa thẻ về đúng kích thước cũ.
           «.expanded» KHÔNG áp luật này: đó là kiểu phủ kín trang dùng cho máy không
           có element fullscreen (iPhone), ở đó không có phím Esc — bỏ nốt nút đóng là
           nhốt người dùng trong một màn hình không lối ra. */
        /* «:not(.picture-on)» — hình của CHÍNH THẺ thì giữ lại hàng biểu tượng.
           Ba luật ẩn ở vùng này sinh ra vì KHUNG YOUTUBE có bộ nút riêng nên thẻ
           nhường chỗ. Video Facebook chạy bằng phần tử «<video>» của thẻ, vốn dựng
           KHÔNG có bộ nút gốc — lý do nhường chỗ không còn, mà luật vẫn áp, nên chủ
           máy báo 20/09/2026: phóng to Facebook thì "không có nút thoát màn và chỉnh
           thời gian". «picture-on» do «_attachPicture» đặt, đúng khi hình là của thẻ. */
        .player:fullscreen:not(.picture-on) > .stage > .stage-controls { display: none; }
        /* Idle: the overlays fade out after a few seconds without a touch while the video
           plays; the shield catches the next touch (taps inside the YouTube frame never
           reach the card) and only brings them back. */
        .idle-shield { display: none; }
        .player.idle:is(.expanded, :fullscreen) { cursor: none; }
        .player.idle:is(.expanded, :fullscreen) > .idle-shield { display: block; position: absolute; inset: 0; z-index: 3; }
        .player.idle:is(.expanded, :fullscreen) > .stage > .stage-controls { opacity: 0; pointer-events: none; }
        /* Thanh tiến trình và hàng nút phát nay CŨNG hiện ở toàn màn hình khi hình là
           của chính thẻ (0.26.11) — nên phải mờ theo CÙNG NHỊP với hàng biểu tượng.
           Không nối vào thì nút thoát mờ đi trong khi thanh điều khiển nằm lì, và
           chủ máy báo đúng thế 20/09/2026: "chưa có chế độ sau 3s ẩn thanh điều
           khiển" và "chưa có nút x thoát màn". Nút thoát vẫn ở đó, chỉ là đã mờ. */
        /* HÌNH CỦA CHÍNH THẺ Ở TOÀN MÀN HÌNH: hình LẤP KÍN, điều khiển NỔI LÊN TRÊN.
           Bản 0.26.11 cho thanh tiến trình và khối nghe hiện lại nhưng để nguyên
           TRONG LUỒNG bố cục, nên chúng bóp hẹp khung hình — chủ máy báo 20/09/2026:
           "thanh điều khiển không chiếm chỗ khi mở toàn màn, như bây giờ đang chiếm".
           Chữa bằng cách đưa KHUNG HÌNH ra khỏi luồng cho nó lấp kín, chứ không phải
           thu nhỏ điều khiển: làm ngược thì mai thêm một nút nữa là lại chiếm chỗ.
           Cũng đúng ở chế độ xoay ngang, nơi «.stage» thành hộp thật và chính nó là
           gốc định vị cho khung hình. */
        .player:is(.expanded, :fullscreen).picture-on,
        .player:is(.expanded, :fullscreen).picture-on.rotated > .stage { justify-content: flex-end; }
        .player:is(.expanded, :fullscreen).picture-on > .stage > .video-frame {
          position: absolute;
          inset: 0;
          width: 100%;
          /* «height» và «aspect-ratio» PHẢI khai ở đây. Khung hình vốn bị ràng buộc
             tỉ lệ 16:9, nên chỉ «inset: 0» thì chiều cao vẫn tính từ bề rộng — đo
             được 485×273 trên khung phát 485×757, tức vẫn hụt hai phần ba. Gỡ ràng
             buộc tỉ lệ rồi cho cao hết khung; phần thừa do video không đúng tỉ lệ
             màn đã có «object-fit: contain» lo, không méo hình. */
          height: 100%;
          aspect-ratio: auto;
          margin: 0;
        }
        .player:is(.expanded, :fullscreen).picture-on > .stage > .video-frame .picture {
          width: 100%;
          height: 100%;
          object-fit: contain;
        }
        .player:is(.expanded, :fullscreen).picture-on > .stage > :is(.nghe-hero, .progress) {
          position: relative;
          z-index: 2;
        }
        /* Dải dưới rút gọn: bỏ đĩa và ảnh nền, chỉ còn tên bài + hàng nút trên nền mờ.
           Đĩa quay và ảnh nền là của chế độ CHỈ NGHE — chồng lên một video đang chạy
           thì vừa thừa vừa che hình. */
        .player:is(.expanded, :fullscreen).picture-on :is(.nghe-nen, .nghe-phu-lop, .nghe-bia) {
          display: none;
        }
        .player:is(.expanded, :fullscreen).picture-on .nghe-hang {
          grid-template-columns: minmax(0, 1fr);
          margin-top: 0;
        }
        .player:is(.expanded, :fullscreen).picture-on .nghe-khung { height: auto; padding: 4px 8px; }
        .player:is(.expanded, :fullscreen).picture-on > .stage > .nghe-hero {
          border: 0;
          border-radius: 0;
          background: linear-gradient(transparent, rgba(0, 0, 0, .78));
        }
        .player:is(.expanded, :fullscreen) :is(.progress, .control-bar) { transition: opacity .3s; }
        .player.idle:is(.expanded, :fullscreen) :is(.progress, .control-bar) { opacity: 0; pointer-events: none; }
        .player.idle:is(.expanded, :fullscreen) ~ .yt-zone-playlist .np-zone { opacity: 0; pointer-events: none; }
        /* Dải thông tin bài hát dưới đáy cũng ẩn ở toàn màn hình — YouTube đã hiện tên
           bài ngay trên hình. Đặt SAU khối định vị và sau luật «.idle» ở trên, cùng độ
           ưu tiên nên luật đứng sau thắng; viết trước chúng thì không ăn. */
        .player:is(.expanded, :fullscreen) ~ .yt-zone-playlist .np-zone { display: none; }
        /* Phone held upright in an app or browser that can't turn the screen (the Home
           Assistant app's WebView refuses screen.orientation.lock, and turning the phone
           re-renders HA and leaves fullscreen), or turned by the rotate button: the stage
           is turned 90°, so the phone is simply held sideways. */
        @media (orientation: portrait) {
          .player.rotated > .stage {
            position: absolute;
            top: 50%;
            left: 50%;
            display: flex;
            flex-direction: column;
            justify-content: center;
            width: 100vh;
            height: 100vw;
            transform: translate(-50%, -50%) rotate(90deg);
          }
          .player.rotated > .stage > .video-frame { width: min(100%, calc(100vw * 16 / 9)); }
        }
        /* Hai nửa bộ chọn anh-em đã bỏ: các nút «.ctl» nay là CON của «.player», nên
           hai dòng dưới đã bao trùm chúng. Giữ lại chỉ là luật chết. */
        .player.expanded .ctl:not(.main),
        .player:fullscreen .ctl:not(.main) { color: var(--ad-text,#fff); }
        .player.expanded .ctl.stop,
        .player:fullscreen .ctl.stop { color: var(--ad-danger,#ff8a80); }
        .player.expanded ~ .yt-zone-playlist .np-zone .now-meta,
        .player:fullscreen ~ .yt-zone-playlist .np-zone .now-meta,
        .player.expanded .svol-name,
        .player:fullscreen .svol-name { color: rgba(255, 255, 255, .72); }
        /* ============ Bố cục ngang 2×2 cho popup (video / danh sách phát / loa / đang phát) ============ */
        .yt-layout {
          /* --yt-result-row: chiều cao 1 dòng kết quả (ảnh 48 + padding + viền + gap)
             --yt-col-min-h : chiều cao tối thiểu của cột phải khi video đang đóng */
          --yt-result-row: 68px;
          --yt-col-min-h: 640px;
          display: grid;
          grid-template-columns: minmax(0, 1.4fr) minmax(300px, 1fr);
          grid-template-areas:
            "video    playlist"
            "speakers playlist";
          /* Hàng trên ôm đúng nội dung, phần dư dồn hết xuống hàng dưới. Thiếu dòng
             này thì hai hàng tự chia nhau phần dư của cột phải (cao cứng 640px), nên
             khối phát bị kéo giãn và hở một mảng trống giữa nó với thanh loa. Trước
             đây danh sách gợi ý lấp đầy cột phải nên không ai thấy; từ lúc gợi ý đóng
             sẵn thì lộ hẳn — đo bằng ảnh chụp 19/09/2026. Khối loa đã có
             «align-self: start» nên nó bám đúng mép trên hàng dưới, tức nằm ngay dưới
             khối phát. */
          grid-template-rows: auto 1fr;
          column-gap: 12px;
          row-gap: 8px;
          align-items: start;
          margin-top: 12px;
        }
        /* Hai cột đọc như HAI THẺ liền nhau chứ không phải một khối lớn: mỗi cột có
           nền, viền và bo góc riêng. Chỉ áp khi CHÍNH CARD rộng từ 640px — card hẹp
           xếp dọc một cột thì viền lồng trong viền trông rối. */
        @container ytcard (min-width: 640px) {
          .yt-layout > .player,
          .yt-layout > .yt-zone-playlist {
            background: rgba(var(--ad-c2,13,21,37),0.38);
            border: 1px solid rgba(var(--ad-c1,0,204,204),0.16);
            border-radius: 16px;
            padding: 10px;
          }
        }
        .yt-layout > .player { grid-area: video; margin-top: 0; }
        /* Video lấp đầy toàn bộ chiều rộng của khung .player (trước đây bị bó hẹp
           theo --yt-video-max-h nên 2 bên thừa viền đen/rỗng) — chiều cao tự theo
           đúng tỉ lệ 16:9 của chiều rộng thật, không còn letterbox. */
        .yt-layout > .player:not(.expanded):not(:fullscreen) > .stage > .video-frame {
          width: 100%;
          margin-inline: 0;
        }
        /* Danh sách loa/màn hình thấp hơn một nhịp (vẫn cuộn riêng bên trong) */
        .yt-layout .players { height: 112px; }
        /* Cột phải trải trên 2 row (ngang bằng video + loa/màn cộng lại) và tự
           cuộn bên trong nếu kết quả tìm kiếm dài hơn — nhờ vậy chiều cao của
           cột trái mới là thứ quyết định layout, khối "speakers" luôn bám sát
           ngay dưới video thay vì bị đẩy xuống theo độ dài danh sách kết quả. */
        .yt-zone-playlist {
          grid-area: playlist;
          position: relative;      /* mốc cho .yt-playlist-inner định vị tuyệt đối */
          /* Khung đo RIÊNG cho cột phải. Cần nó vì bề rộng cột này KHÔNG theo bề rộng
             thẻ: đo 19/09/2026, thẻ rộng 860px thì cột phải chỉ 337px — hẹp hơn cả
             thẻ trên điện thoại (374px). Luật nào gác theo bề rộng THẺ để quyết bố
             cục bên trong cột này đều sai; hàng chọn nguồn đã dính đúng lỗi đó. */
          container-type: inline-size;
          container-name: ytcot;
          min-width: 0;
          /* CAO THEO NỘI DUNG, CHẶN TRÊN — trước đây đặt «height» cứng nên thu gọn kết
             quả tìm kiếm xong cột phải vẫn chiếm trọn 640px. Chủ máy gửi ảnh
             21/09/2026: một ô rỗng to tướng ngay dưới nút "Xem 20 kết quả tìm kiếm".
             Đo trong Chrome ở thẻ rộng 1100px: nội dung cao 173px mà cột vẫn 660px.
             Chặn trên vẫn giữ nguyên ý cũ — danh sách dài không được phép kéo giãn bố
             cục, phần dư thì cuộn bên trong. */
          max-height: var(--yt-col-min-h, 640px);
          align-self: start;
          overflow: hidden;
        }
        /* Toàn bộ nội dung cột phải nằm trong một lớp position:absolute nên nó
           KHÔNG đóng góp chiều cao cho grid nữa: chiều cao 2 hàng "video" +
           "speakers" do cột trái quyết định, cột phải chỉ việc trải đúng bằng
           chừng đó (inset:0). Nhờ vậy dù tìm được 20-30 bài thì bố cục vẫn cân,
           khối "Loa / màn hình" không bị kéo giãn thành khung rỗng nữa. */
        .yt-playlist-inner {
          /* Nằm theo dòng chảy bình thường (trước là «absolute; inset:0» để khỏi đóng
             góp chiều cao) — nay chính nội dung quyết chiều cao cột, còn chặn trên của
             «.yt-zone-playlist» lo việc không cho nó kéo giãn bố cục. Bố cục hẹp vốn
             đã chạy kiểu này từ trước, nên không phải đường mới. */
          display: flex;
          flex-direction: column;
          min-height: 0;
          overflow: auto;
        }
        .yt-zone-playlist .source-switch { margin-top: 0; }
        /* Danh sách kết quả: chiếm phần trống còn lại của cột phải, cao tối đa
           bằng 15 bài — dài hơn thì tự cuộn bên trong, không đẩy layout. */
        .yt-zone-playlist .results,
        .yt-zone-playlist .playlist-list {
          flex: 0 1 auto;
          min-height: 0;
          max-height: calc(var(--yt-result-row, 68px) * 10 - 20px);
          overflow-y: auto;
          overscroll-behavior: contain;
          scrollbar-width: thin;
          scrollbar-color: rgba(var(--ad-c1,0,204,204),0.5) transparent;
        }
        .yt-zone-playlist .playlist-panel { flex: 1 1 auto; min-height: 0; grid-template-rows: auto minmax(0, 1fr); }
        .yt-zone-playlist .results::-webkit-scrollbar,
        .yt-zone-playlist .playlist-list::-webkit-scrollbar { width: 6px; }
        .yt-zone-playlist .results::-webkit-scrollbar-track,
        .yt-zone-playlist .playlist-list::-webkit-scrollbar-track { background: transparent; }
        .yt-zone-playlist .results::-webkit-scrollbar-thumb,
        .yt-zone-playlist .playlist-list::-webkit-scrollbar-thumb { background: rgba(var(--ad-c1,0,204,204),0.5); border-radius: 999px; }
        /* Các khối cố định phía trên (tabs / nguồn / ô tìm kiếm / status) không co lại */
        .yt-playlist-inner > .source-switch,
        .yt-playlist-inner > form,
        .yt-playlist-inner > .save-playlist,
        .yt-playlist-inner > .status,
        .yt-playlist-inner > .np-zone { flex: 0 0 auto; }
        /* Khối loa giữ đúng chiều cao thật của nó, không stretch theo hàng grid */
        .yt-layout > .speaker-section { grid-area: speakers; margin: 0; align-self: start; }
        .np-zone {
          position: relative;
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 2px;
          margin-top: 8px;
          padding: 14px 16px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: transparent;
          overflow: hidden;
        }
        /* Sóng nhạc "đá đá" — nằm ngang, full-width, ngay trên thanh timeline (giữa .now
           và .progress), giống vị trí .wave-area trong phicomm-r1-card.js. Có 3 kiểu,
           chọn qua config wave_style (mặc định "bars"): bars | simple | dots.
           CSS ở đây chỉ định hình dáng/độ mờ mặc định (đứng yên) + class "is-playing"
           để làm sáng lên. Chuyển động thật sự do _toggleWaveAnimation() (JS) đổi
           trực tiếp transform mỗi ~220ms khi đang phát — không dùng @keyframes/:has()
           vì một số WebView/chế độ tiết kiệm pin chặn CSS animation khiến sóng đứng im
           dù nhạc vẫn đang chạy. */
        /* Sóng nhạc cao hơn hẳn (26px → 40px) theo yêu cầu "tăng wave" 18/09/2026. */
        .np-wave { display: flex; align-items: flex-end; justify-content: space-between; height: 40px; margin: 2px 0 6px; pointer-events: none; }

        /* --- Kiểu 1: bars (mặc định) — nhiều thanh cao thấp khác nhau, có gradient + phát sáng --- */
        .np-wave--bars span {
          width: 3px;
          height: var(--h, 40%);
          border-radius: 3px;
          background: linear-gradient(180deg, var(--ad-accent, #00ffcc), rgba(var(--ad-c1,0,204,204),.45));
          box-shadow: 0 0 6px 0 rgba(var(--ad-c1,0,204,204),.6);
          transform-origin: bottom;
          transform: scaleY(.3);
          opacity: .5;
          transition: opacity .2s, transform .2s ease-in-out;
        }
        .wrap.is-playing .np-wave--bars span { opacity: .95; }

        /* --- Kiểu 2: simple — ít thanh, đều nhau, không gradient/glow, chỉ nảy + mờ-tỏ nhẹ --- */
        .np-wave--simple { justify-content: space-between; }
        .np-wave--simple span {
          width: 4px;
          height: 100%;
          border-radius: 2px;
          background: var(--ad-accent, #00ffcc);
          transform-origin: bottom;
          transform: scaleY(.35);
          opacity: .35;
          transition: opacity .2s, transform .2s ease-in-out;
        }
        .wrap.is-playing .np-wave--simple span { opacity: .9; }

        /* --- Kiểu 3: dots — mỗi cột có 1 điểm "max" cố định ở đỉnh, chấm tròn đá đá nhảy lên chạm tới --- */
        .np-wave--dots { justify-content: space-between; }
        .wv-col { position: relative; width: 8px; height: 100%; display: flex; align-items: flex-end; justify-content: center; }
        .wv-max {
          position: absolute; top: 0; left: 50%; transform: translateX(-50%);
          width: 5px; height: 5px; border-radius: 50%;
          background: rgba(var(--ad-c1,0,204,204), .35);
          box-shadow: 0 0 4px rgba(var(--ad-c1,0,204,204), .45);
        }
        .wv-dot {
          width: 7px; height: 7px; border-radius: 50%;
          background: var(--ad-accent, #00ffcc);
          box-shadow: 0 0 6px rgba(var(--ad-c1,0,204,204),.7);
          opacity: .55;
          transition: opacity .2s, transform .2s ease-in-out;
        }
        .wrap.is-playing .wv-dot { opacity: 1; }
        @container ytcard (max-width: 639px) {
          /* «minmax(0, 1fr)» chứ KHÔNG phải «1fr». Viết «1fr» là viết tắt của
             «minmax(auto, 1fr)», mà mức tối thiểu «auto» bằng chiều rộng nội dung tối
             thiểu của cột — chỉ cần một khối con không co được là cột phình to hơn cả
             khung chứa và kéo cả thẻ tràn ra ngoài màn hình. Đo 19/09/2026 ở cửa sổ
             400px: mép phải của thẻ nằm ở 473px, «.player» rộng 497px. */
          .yt-layout {
            grid-template-columns: minmax(0, 1fr);
            grid-template-areas:
              "video"
              "speakers"
              "playlist";
          }
          /* Một cột: trả nội dung về luồng bình thường, danh sách vẫn giới hạn 15 bài */
          /* height: auto BẮT BUỘC có. Luật gốc ép cột cao cứng 640px cho bố cục hai
             cột; khối này gỡ position và min-height nhưng QUÊN gỡ height, nên ở card
             hẹp cột vẫn cao 640px — mở Playlist chỉ có một dòng mà phía dưới trống
             toang một mảng. */
          /* «max-height: none» PHẢI có, cùng lý do với «height: auto» ở trên. Bản
             0.26.41 đổi luật gốc từ «height» sang «max-height» để cột thôi rỗng khi thu
             gọn kết quả — nhưng quên rằng khối gỡ chặn này chỉ gỡ «height». Hậu quả đo
             được 21/09/2026 ở bề rộng 412px với cấu hình thật của nhà: cột bị chặn
             640px trong khi nội dung cao 701px, nên danh sách tràn ra và ĐÈ LÊN khối
             loa 53px — đúng ảnh chồng chữ chủ máy gửi. */
          .yt-zone-playlist { position: static; height: auto; max-height: none; min-height: 0; overflow: visible; }
          .yt-playlist-inner { overflow: visible; }
          /* Giữ flex column (KHÔNG dùng display:block) để còn xếp lại thứ tự được.
             Bản cũ đổi về block, nên mọi khối rơi về đúng thứ tự trong tài liệu và
             khối "Đang phát" — vốn nằm CUỐI cột, sau cả dải gợi ý lẫn lưới kết quả —
             bị đẩy xuống quá sâu, trên điện thoại phải cuộn rất lâu mới thấy nút
             phát/dừng. Màn hình rộng không lộ ra vì cột phải cao cố định và khối này
             được ghim đáy. */
          .yt-playlist-inner { position: static; display: flex; flex-direction: column; }
          /* Nút điều khiển lên ngay đầu cột, nằm dưới thanh chọn loa. */
          .yt-playlist-inner > .np-zone { order: -1; margin-bottom: 10px; }
          .yt-zone-playlist .results,
          .yt-zone-playlist .playlist-list { max-height: calc(var(--yt-result-row, 68px) * 10 - 20px); }
        }
        @container ytcard (max-width: 520px) {
          /* Phones (and the app's larger font scale): keep the search on one row
             and shrink text so the card isn't a column of oversized boxes. */
          .wrap { padding: 12px; }
          h2 { font-size: 1.02rem; }
          /* Số cột do khung đo của CỘT CHỨA quyết định (xem «@container ytcot» ở
             trên), không quyết ở đây theo bề rộng thẻ — đó chính là chỗ bản trước làm
             sai. Ở đây chỉ còn việc thu lề. */
          .source-switch { margin: 10px 0 8px; }
          .source-button { padding: 6px 4px; font-size: .8rem; }
          input[type="search"] { padding: 7px 10px; font-size: .9rem; }
          .primary { padding: 7px 11px; }
          .search-label { display: none; }
          .player { padding: 8px; }
          .now { grid-template-columns: 44px minmax(0, 1fr); gap: 9px; }
          .now-meta, .status { font-size: .76rem; }
          .section-title h3 { font-size: .82rem; }
          .player-chip { gap: 5px; padding: 3px 8px; font-size: .84rem; }
          .players-columns { grid-template-columns: 1fr; gap: 6px; }
          .result { font-size: .88rem; }
          .np-zone { padding: 10px 12px; }
          .np-wave { height: 32px; }
        }
        /* Bề rộng cột video theo «player_width». BẮT BUỘC bọc trong @media min-width:
           640px. Luật này viết SAU khối điểm ngắt hẹp và cùng độ ưu tiên (0,1,0), nên
           để trần thì nó đè mất «grid-template-columns: 1fr» của card hẹp: card nhận
           lưới 2 cột trong khi grid-template-areas đã xếp dọc một cột — đó chính là
           lúc bố cục vỡ. */
        @container ytcard (min-width: 640px) {
          .yt-layout { grid-template-columns: var(--yt-video-col, minmax(0, 1.4fr)) minmax(240px, 1fr); }
        }
        /* «layout: horizontal» do người dùng CHỌN — ép hai cột kể cả card hẹp. Hai lớp
           cho độ ưu tiên (0,2,0) nên thắng luật một lớp «.yt-layout» của khối điểm ngắt
           hẹp, bất kể thứ tự. Cột phải hạ xuống 200px để ở ~550px vẫn đủ chỗ hai cột. */
        .yt-layout.yt-layout--ngang {
          grid-template-columns: var(--yt-video-col, minmax(0, 1.2fr)) minmax(200px, 1fr);
          grid-template-areas:
            "video    playlist"
            "speakers playlist";
        }
        /* «layout: vertical» — xếp dọc một cột, cho dashboard cột hẹp. */
        .yt-layout.yt-layout--doc {
          grid-template-columns: minmax(0, 1fr);
          grid-template-areas: "video" "playlist" "speakers";
        }
        /* Người dùng tự chọn bố cục DỌC thì cột danh sách cũng nằm theo dòng chảy —
           chặn trên 640px chỉ dành cho bố cục hai cột. */
        .yt-layout--doc > .yt-zone-playlist {
          position: static;
          height: auto;
          max-height: none;
          overflow: visible;
        }
        .yt-layout--doc .yt-playlist-inner { overflow: visible; }

        .yt-suggested-section { --text-muted: var(--secondary-text-color, rgba(235,235,245,.6)); }
        .yt-suggested-section {
          grid-column: 1 / -1;
          display: flex;
          flex-direction: column;
          gap: 10px;
          margin-top: 4px;
        }

        .yt-suggested-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 2px 4px;
          flex-wrap: wrap;
          gap: 6px;
        }
        /* Hai nút tự tạo từ khoá / mục. Không cho co để nhãn bên trái nhường chỗ
           trước — cùng bài học với thanh «Loa phát nhạc» bị đè chữ. */
        .yt-suggest-tools { display: flex; align-items: center; gap: 4px; flex: 0 0 auto; }
        .yt-suggest-add { --mdc-icon-size: 18px; color: var(--ad-accent,#00ffcc); }
        /* Thu gọn danh sách gợi ý: đóng lại thì chỉ còn đúng hàng tiêu đề kèm mũi tên,
           bấm mũi tên là mở ra. Mặc định đóng. */
        .yt-suggest-gap { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
        .yt-goi-y-than { display: flex; flex-direction: column; gap: 10px; }
        .yt-suggested-section.goi-y-dong .yt-goi-y-than { display: none; }

        .yt-suggested-title {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          font-weight: 800;
          color: #e2e8f0;
          letter-spacing: 0.5px;
        }

        .yt-suggested-subtitle {
          font-size: 11px;
          color: var(--text-muted);
        }

        .yt-quick-search-pills {
          display: flex;
          flex-wrap: nowrap;
          gap: 6px;
          overflow-x: auto;
          scrollbar-width: none;
          -webkit-overflow-scrolling: touch;
          padding: 2px 0 6px;
        }

        .yt-quick-search-pills::-webkit-scrollbar {
          display: none;
        }

        .yt-search-pill {
          /* Cùng lý do như .yt-cat-btn: không co thì hàng mới tràn và cuộn được. */
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 5px 12px;
          border-radius: 999px;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #cbd5e1;
          font-size: 11.5px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
          user-select: none;
          white-space: nowrap;
          flex-shrink: 0;
        }

        .yt-search-pill ha-icon {
          --mdc-icon-size: 12px;
          color: var(--primary-color, #ff9f09);
        }

        .yt-search-pill:hover {
          background: rgba(255, 159, 9, 0.2);
          border-color: var(--primary-color, #ff9f09);
          color: var(--ad-text,#fff);
          transform: translateY(-1px);
        }

        /* Chip XUỐNG DÒNG, không cuộn ngang. Hàng cuộn chỉ vuốt được bằng cảm ứng:
           chuột không kéo ngang được mà thanh cuộn lại bị ẩn, nên phần lớn mục coi
           như không với tới.
           Luật này đặt SAU luật gốc của .yt-quick-search-pills (dòng ~1726, nó khai
           flex-wrap: nowrap và overflow-x: auto) nên đè được lên, cùng độ ưu tiên mà
           đứng sau thì thắng. Còn .yt-category-tabs thì KHÔNG còn luật gốc nào khai
           display nữa — đo bằng grep, chỉ sót mỗi ::-webkit-scrollbar mồ côi — nên
           chỗ này phải khai đủ display và gap cho nó, không chỉ đè flex-wrap. */
        .yt-quick-search-pills,
        .yt-category-tabs {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          overflow-x: visible;
          padding: 2px 0 6px;
        }
        /* Tên và dấu × là hai vùng bấm RIÊNG trong cùng một chip. */
        .chip-ten {
          display: inline-flex; align-items: center; gap: 5px;
          border: 0; background: transparent; color: inherit; font: inherit;
          padding: 0; cursor: pointer; min-width: 0;
        }
        .chip-x {
          display: grid; place-items: center; flex: 0 0 auto;
          width: 20px; height: 20px; margin-left: 2px;
          border: 0; border-radius: 999px; cursor: pointer;
          background: transparent; color: var(--ad-danger,#ff8a80); --mdc-icon-size: 15px;
        }
        .chip-x:hover { background: rgba(255,82,82,.22); }
        /* Màu đỏ phải đặt THẲNG lên ha-icon, không thể trông vào thừa kế từ .chip-x:
           luật .yt-search-pill ha-icon ở trên đã tô cam mọi biểu tượng trong chip, mà
           một khai báo trực tiếp thì luôn thắng giá trị thừa kế, bất kể độ ưu tiên.
           Viết kèm tên chip cho thành (0,2,1) để hơn (0,1,1) của hai luật kia, nhờ vậy
           không phụ thuộc vào việc luật này đứng trước hay sau chúng trong file. */
        .yt-search-pill .chip-x ha-icon,
        .yt-cat-btn .chip-x ha-icon { color: var(--ad-danger,#ff8a80); --mdc-icon-size: 15px; }
        /* Nút gỡ ghim nằm đè góc ảnh bài hát đã gắn. */
        .yt-card-unpin {
          position: absolute; top: 4px; right: 4px; z-index: 2;
          display: grid; place-items: center; width: 24px; height: 24px;
          border: 0; border-radius: 999px; cursor: pointer;
          color: var(--ad-text,#fff); background: rgba(0,0,0,.6);
          --mdc-icon-size: 16px;
        }
        .yt-card-unpin:hover { background: rgba(255,82,82,.85); }

        .yt-category-tabs::-webkit-scrollbar {
          display: none;
        }

        .yt-cat-btn {
          /* Không cho co lại. Con của flex mặc định CO được (flex-shrink: 1), nên
             chúng bị bóp cho vừa khung thay vì tràn ra — khung có overflow-x: auto
             mà chẳng có gì để cuộn, chữ thì bị cắt cụt. Đây là lý do dải gợi ý
             không vuốt ngang được. */
          flex: 0 0 auto;
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 8px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.08);
          color: var(--text-muted);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.2s;
        }

        .yt-cat-btn ha-icon {
          --mdc-icon-size: 14px;
        }

        .yt-cat-btn:hover {
          color: var(--ad-text,#fff);
          border-color: rgba(255, 159, 9, 0.4);
        }

        .yt-cat-btn.active {
          background: linear-gradient(135deg, rgba(255, 159, 9, 0.35) 0%, rgba(255, 107, 53, 0.25) 100%);
          border-color: var(--primary-color, #ff9f09);
          color: var(--ad-text,#fff);
          box-shadow: 0 2px 8px rgba(255, 85, 51, 0.25);
        }

        /* Ô nhỏ lại: 150px trên cột rộng của máy tính cho ra ảnh rất to. 118px thì
           máy tính xếp được nhiều bài hơn mà điện thoại vẫn đủ 2 cột. */
        .yt-song-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
          gap: 10px;
        }

        .yt-song-card {
          display: flex;
          flex-direction: column;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.08);
          border-radius: 10px;
          overflow: hidden;
          cursor: pointer;
          transition: all 0.22s ease;
          user-select: none;
        }

        .yt-song-card:hover {
          border-color: rgba(255, 159, 9, 0.5);
          transform: translateY(-2px);
          box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35);
          background: rgba(255, 255, 255, 0.1);
        }

        .yt-song-card:active {
          transform: scale(0.98);
        }

        .yt-card-thumb-wrap {
          position: relative;
          width: 100%;
          aspect-ratio: 16 / 9;
          overflow: hidden;
          background: #000;
        }

        .yt-card-thumb {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
          transition: transform 0.3s ease;
        }

        .yt-song-card:hover .yt-card-thumb {
          transform: scale(1.05);
        }

        .yt-play-overlay {
          position: absolute;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          background: rgba(0, 0, 0, 0.3);
          opacity: 0;
          transition: opacity 0.2s ease;
        }

        .yt-play-overlay ha-icon {
          --mdc-icon-size: 28px;
          color: var(--ad-text,#fff);
          filter: drop-shadow(0 2px 6px rgba(0,0,0,0.6));
        }

        .yt-song-card:hover .yt-play-overlay {
          opacity: 1;
        }

        .yt-card-duration {
          position: absolute;
          bottom: 4px;
          right: 4px;
          background: rgba(0, 0, 0, 0.75);
          color: #f1f5f9;
          font-size: 10px;
          font-weight: 600;
          padding: 1px 4px;
          border-radius: 3px;
        }

        .yt-card-info {
          padding: 8px;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }

        .yt-card-title {
          font-size: 11px;
          font-weight: 700;
          color: #f8fafc;
          line-height: 1.3;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .yt-card-artist {
          font-size: 10px;
          color: #94a3b8;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
      </style>
      <ha-card>
        <div class="wrap">
          <header>
            <div>
              <h2 class="visually-hidden"></h2>
            </div>
            <div class="header-tools">
              <div class="layout-switch" role="group" aria-label="Kiểu bố cục">
                <button class="layout-pick" type="button" data-layout="horizontal" aria-pressed="false" title="Xếp ngang" aria-label="Xếp ngang"><ha-icon icon="mdi:view-split-vertical"></ha-icon></button>
                <button class="layout-pick" type="button" data-layout="vertical" aria-pressed="false" title="Xếp dọc" aria-label="Xếp dọc"><ha-icon icon="mdi:view-agenda"></ha-icon></button>
              </div>
            </div>
          </header>

          <div class="yt-layout">
            <section class="player" aria-label="Đang phát">
              <div class="idle-shield" aria-hidden="true"></div>
              <div class="stage">
              <div class="video-frame" hidden></div>
              <!-- BỎ lớp nền mờ, đĩa quay và lớp chữ đè (19/09/2026). Tự soi bằng ảnh
                   chụp mới thấy: lớp nền neo vào «.player» mà «.stage» là
                   display: contents nên không khung nào chặn — nó tràn ra nửa card và
                   đè lên hai nút «Nghe trên máy này» / «Nghe khi tắt màn hình» tới mức
                   không đọc được chữ; đĩa thì che mất số phút giây.
                   Dữ liệu của skill ui-ux-pro-max cũng ghi thẳng «Cluttered layout» là
                   thứ phải tránh cho nhóm nhạc, và mẫu khuyến nghị là khối đặc rõ cạnh.
                   Tên bài nay dùng lại khối «.now» sẵn có thay vì một lớp chữ thứ hai. -->
              <!-- Sóng nhạc, thanh tiến trình và nút điều khiển nằm NGAY DƯỚI khung video.
                   Xem video thì điều khiển ở sát dưới hình (sóng nhạc tự ẩn); chỉ nghe nhạc
                   thì khung video ẩn nên sóng nhạc chiếm đúng chỗ trống đó — không phóng to
                   theo video, giữ nguyên cỡ. Kiểu sóng (bars/simple/dots) lấy từ cấu hình. -->
              <!-- CHỈ NGHE NHẠC: ảnh bìa tròn và khung "sóng + nút" xếp thành MỘT HÀNG,
                   theo đúng cách thẻ phicomm-r1 làm (chủ máy gửi tệp này 19/09/2026 để
                   tham khảo): lưới «đĩa | khung», và hàng nút nằm BÊN TRONG khung sóng
                   chứ không tách ra thành khối thứ hai — nhờ vậy nút luôn nằm đúng đáy
                   khung, sóng không thể cao lấn.
                   Hai lần trước tôi đặt đĩa bằng position:absolute nên nó tràn ra đè lên
                   chữ; nay đĩa là một CỘT THẬT của lưới, không thể tràn.
                   Xem video thì cả hàng rút gọn lại: đĩa ẩn, khung mất viền và nền, chỉ
                   còn hàng nút nằm sát dưới hình. -->
              <!-- Tên bài, ca sĩ và NHÃN NGUỒN nằm ngay đầu khối nghe. Chủ máy
                   19/09/2026: "Tên bài hát cho trong đó luôn, tách ra làm gì, hiện cả
                   nguồn phát luôn cơ mà". Ô «.np-zone» cũ ở cột bên phải vì thế bị ẩn
                   đi (vẫn còn trong DOM để mã cũ ghi vào không lỗi). -->
              <div class="nghe-hero">
                <img class="nghe-nen" alt="" hidden />
                <div class="nghe-phu-lop"></div>
                <div class="nghe-ruot">
                  <div class="nghe-dau">
                    <div class="nghe-chu">
                      <div class="nghe-ten">Chưa phát bài nào</div>
                      <div class="nghe-phu">Chọn một bài trong kết quả để bắt đầu.</div>
                    </div>
                    <span class="nghe-nguon" hidden></span>
                  </div>
                  <div class="nghe-hang">
                    <div class="nghe-bia" role="button" tabindex="0" aria-pressed="false" aria-label="Dừng hoặc cho đĩa quay lại" title="Bấm để dừng đĩa">
                      <ha-icon icon="mdi:music-note"></ha-icon>
                      <img alt="" hidden />
                    </div>
                    <div class="nghe-khung">
                      ${this._renderWave()}
                      <div class="control-bar">
                        <div class="transport-group" role="group" aria-label="Điều khiển phát">
                          <button class="ctl previous" type="button" aria-label="Bài trước" title="Bài trước"><ha-icon icon="mdi:skip-previous"></ha-icon></button>
                          <button class="ctl main play-pause" type="button" aria-label="Phát" title="Phát"><ha-icon icon="mdi:play"></ha-icon></button>
                          <button class="ctl next" type="button" aria-label="Bài tiếp theo" title="Bài tiếp theo"><ha-icon icon="mdi:skip-next"></ha-icon></button>
                          <button class="ctl stop" type="button" aria-label="Dừng" title="Dừng"><ha-icon icon="mdi:stop"></ha-icon></button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <!-- Thanh tiến trình đặt DƯỚI hàng nút, không kẹp giữa sóng nhạc và nút.
                   Chủ máy chốt 18/09/2026: "vạch tiến độ bài hát đang ở giữa", và ảnh mẫu
                   anh gửi cũng để nó dưới cùng, chạy hết bề ngang.
                   Đổi thứ tự NGAY TRONG BẢN DỰNG THẺ chứ không dùng thuộc tính «order»
                   của CSS: «.stage» là display: contents còn «.player» là khối thường,
                   không phải khung linh hoạt, nên «order» sẽ không có tác dụng gì cả. -->
              <div class="progress" hidden>
                <span class="elapsed">0:00</span>
                <div class="bar"><div class="fill"></div></div>
                <span class="total">0:00</span>
              </div>
              <div class="stage-controls">
                <div class="view-group">
                  <button class="ctl watch" type="button" aria-label="Xem video trên thẻ" title="Xem video trên thẻ" hidden><ha-icon icon="mdi:television-play"></ha-icon></button>
                  <button class="ctl video-listen" type="button" aria-label="Chỉ nghe (tắt hình, tiếng chạy tiếp)" title="Chỉ nghe — tắt hình, tiếng chạy tiếp" hidden><ha-icon icon="mdi:headphones"></ha-icon></button>
                  <button class="ctl video-rotate" type="button" aria-label="Xoay ngang 90°" title="Xoay ngang 90° (máy đang khoá xoay)" hidden><ha-icon icon="mdi:phone-rotate-landscape"></ha-icon></button>
                  <button class="ctl video-expand" type="button" aria-label="Phóng to video" title="Phóng to" hidden><ha-icon icon="mdi:arrow-expand"></ha-icon></button>
                  <button class="ctl video-fullscreen" type="button" aria-label="Xem toàn màn hình" title="Toàn màn hình" hidden><ha-icon icon="mdi:fullscreen"></ha-icon></button>
                  <button class="ctl video-close" type="button" aria-label="Đóng video" title="Đóng video" hidden><ha-icon icon="mdi:close"></ha-icon></button>
                </div>
                <div class="device-row">
                  <button class="pill device-sound" type="button" aria-pressed="false" hidden><ha-icon icon="mdi:volume-off"></ha-icon><span>Nghe trên máy này</span></button>
                  <button class="pill screen-off" type="button" aria-pressed="false"><ha-icon icon="mdi:cellphone-off"></ha-icon><span>Nghe khi tắt màn hình</span></button>
                </div>
              </div>
              <div class="speaker-volumes"></div>
              <div class="others" aria-label="Nhóm loa khác đang phát"></div>
              </div>
            </section>

            <div class="yt-zone-playlist">
              <div class="yt-playlist-inner">
              <div class="source-switch" role="group" aria-label="Nguồn nhạc và playlist">
                <button class="source-button" type="button" data-source="youtube"><ha-icon icon="mdi:youtube"></ha-icon><span>YouTube</span></button>
                <button class="source-button" type="button" data-source="zing">Zing MP3</button>
                <button class="source-button" type="button" data-source="facebook"><ha-icon icon="mdi:facebook"></ha-icon><span>Facebook</span></button>
                <button class="source-button" type="button" data-view="playlists"><ha-icon icon="mdi:playlist-music"></ha-icon><span class="playlists-tab-label">Playlist</span></button>
              </div>

              <form>
                <input type="search" maxlength="2048" autocomplete="off" aria-label="Tìm tên bài hát hoặc ca sĩ" placeholder="Tìm tên bài hát, ca sĩ hoặc dán link YouTube…" required />
                <button class="primary search-button" type="submit" aria-label="Tìm kiếm" title="Tìm kiếm"><ha-icon icon="mdi:magnify"></ha-icon><span class="search-label">Tìm kiếm</span></button>
              </form>
              <button class="save-playlist" type="button" hidden><ha-icon icon="mdi:playlist-plus"></ha-icon><span>Lưu cả playlist này vào Playlist</span></button>
              <div class="playlist-panel" hidden>
                <form class="playlist-form">
                  <input type="text" class="playlist-input" maxlength="300000" autocomplete="off" aria-label="Link playlist, mã chia sẻ hoặc tên playlist mới" placeholder="Dán link playlist YouTube, album Zing, mã chia sẻ — hoặc gõ tên để tạo mới" />
                  <button class="primary playlist-submit" type="submit">Lưu</button>
                </form>
                <div class="playlist-list"></div>
              </div>
              <p class="status" role="status" aria-live="polite"></p>

              <div class="yt-suggested-section"></div>
          <button class="results-toggle" type="button" hidden aria-expanded="true"><ha-icon icon="mdi:chevron-up"></ha-icon><span class="results-toggle-text"></span></button>
          <div class="results"></div>

              <div class="np-zone" aria-label="Đang phát">
                <div class="now">
                  <div class="now-cover">
                    <ha-icon icon="mdi:music-note"></ha-icon>
                    <img alt="" hidden />
                  </div>
                  <div class="now-copy">
                    <div class="now-title">Chưa phát bài nào</div>
                    <div class="now-meta">Chọn một bài trong kết quả để bắt đầu.</div>
                  </div>
                </div>
              </div>
              </div>
            </div>

            <section class="section speaker-section">
              <div class="spk-bar">
                <div class="spk-bar-main">
                  <ha-icon class="spk-bar-icon" icon="mdi:speaker-multiple"></ha-icon>
                  <div class="spk-bar-copy">
                    <div class="spk-bar-label">Loa phát nhạc</div>
                    <div class="spk-bar-name">Chưa chọn loa</div>
                  </div>
                </div>
                <button class="spk-toggle" type="button" aria-expanded="false">
                  <span>Đổi loa</span><ha-icon icon="mdi:chevron-down"></ha-icon>
                </button>
              </div>
              <div class="spk-volume"></div>
              <div class="spk-list" hidden>
              <div class="section-title">
                <h3><ha-icon icon="mdi:speaker-multiple"></ha-icon> Loa / màn hình</h3>
                <span class="hint selected-count">0 đã chọn</span>
              </div>
              <div class="players-columns">
                <div class="players-col">
                  <div class="players-col-title"><ha-icon icon="mdi:speaker"></ha-icon> Loa</div>
                  <div class="players players-audio"></div>
                </div>
                <div class="players-col">
                  <div class="players-col-title"><ha-icon icon="mdi:television"></ha-icon> Màn hình</div>
                  <div class="players players-video"></div>
                </div>
              </div>
              <div class="hidden-players"></div>
              </div>
            </section>
          </div>
        </div>
      </ha-card>`;
    this.shadowRoot.querySelector("h2").textContent = this._config.title;
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll(".source-button").forEach((button) => {
      button.addEventListener("click", () => {
        // Nút Playlist nằm chung hàng với nguồn nhạc nhưng KHÔNG phải một nguồn —
        // nó chỉ đổi khung đang xem. Phân biệt bằng data-view.
        if (button.dataset.view) {
          this._showView("playlists");
          return;
        }
        this._source = button.dataset.source;
        this._results = [];
        this._queue = [];
        this._queueIndex = -1;
        this._showView("search");
        this._updateSourceButtons();
        this._syncPlayers();
        this._renderResults();
        this._syncSavePlaylist();
        this._setStatus("");
      });
    });
    this.shadowRoot.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      this._search();
    });
    /* Bấm hoặc kéo trên thanh tiến trình để TUA. Trước đây thanh chỉ để nhìn — chủ
       máy hỏi "sao không tua được nhỉ", và đúng là chưa bao giờ làm chứ không phải
       hỏng. Dùng nhóm sự kiện pointer nên chuột và cảm ứng chung một đường; bắt con
       trỏ lại (setPointerCapture) để kéo ra ngoài thanh vẫn theo được. */
    const thanh = this.shadowRoot.querySelector(".progress .bar");
    if (thanh) {
      const tiLeTai = (event) => {
        const o = thanh.getBoundingClientRect();
        if (!o.width) return 0;
        return Math.max(0, Math.min(1, (event.clientX - o.left) / o.width));
      };
      const veTam = (ti) => {
        const fill = thanh.querySelector(".fill");
        if (fill) fill.style.width = `${Math.round(ti * 1000) / 10}%`;
      };
      let dangKeo = false;
      thanh.addEventListener("pointerdown", (event) => {
        dangKeo = true;
        try { thanh.setPointerCapture(event.pointerId); } catch (_error) { /* trình duyệt cũ */ }
        veTam(tiLeTai(event));
      });
      thanh.addEventListener("pointermove", (event) => {
        if (dangKeo) veTam(tiLeTai(event));
      });
      thanh.addEventListener("pointerup", (event) => {
        if (!dangKeo) return;
        dangKeo = false;
        this._seekFraction(tiLeTai(event));
      });
      thanh.addEventListener("pointercancel", () => { dangKeo = false; });
    }
    const searchInput = this.shadowRoot.querySelector('input[type="search"]');
    searchInput.addEventListener("input", () => this._syncSavePlaylist());
    this.shadowRoot.querySelector(".save-playlist").addEventListener("click", () => this._importPlaylist(searchInput.value, true));
    const playlistInput = this.shadowRoot.querySelector(".playlist-input");
    playlistInput.addEventListener("input", () => this._syncPlaylistSubmit());
    this.shadowRoot.querySelector(".playlist-form").addEventListener("submit", (event) => {
      event.preventDefault();
      const text = playlistInput.value.trim();
      if (!text) return;
      // Anything that looks like a link or a code goes to the server, which says what
      // it can't read; only plain words name a new playlist.
      if (PLAYLIST_LINK.test(text) || /^(https?:\/\/|TTPL)/i.test(text)) this._importPlaylist(text, false);
      else this._playlistCommand({ action: "create", name: text, items: [] }, (payload) => {
        playlistInput.value = "";
        this._openPlaylist = payload.playlist.id;
        return `Đã tạo “${payload.playlist.name}”. Bấm + ở kết quả tìm để thêm bài.`;
      });
    });
    this.shadowRoot.querySelector(".previous").addEventListener("click", () => this._skip(-1));
    this.shadowRoot.querySelector(".play-pause").addEventListener("click", () => this._togglePlay());
    /* Bấm đĩa CHỈ dừng hoặc cho quay lại CÁI ĐĨA — không đụng tới nhạc.
       Bản đầu tôi nối nút này vào «_togglePlay» là hiểu sai yêu cầu: chủ máy
       19/09/2026 báo ngay "dừng đĩa lại dừng cả nhạc là sao". Đĩa là thứ trang trí,
       nút phát/dừng nhạc đã có riêng ở hàng dưới.
       Phần "dừng đúng vị trí" do CSS lo bằng «animation-play-state»; ở đây chỉ bật
       tắt một lớp. Bàn phím theo đúng nếp thẻ bài hát: Enter và dấu cách. */
    const dia = this.shadowRoot.querySelector(".nghe-bia");
    if (dia) {
      const doiQuay = () => {
        const dung = dia.classList.toggle("dung-quay");
        dia.setAttribute("aria-pressed", dung ? "true" : "false");
        dia.title = dung ? "Đĩa đang dừng — bấm để quay lại" : "Bấm để dừng đĩa";
      };
      dia.addEventListener("click", doiQuay);
      dia.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          doiQuay();
        }
      });
    }
    this.shadowRoot.querySelector(".next").addEventListener("click", () => this._skip(1));
    this.shadowRoot.querySelector(".stop").addEventListener("click", () => this._stop());
    this.shadowRoot.querySelector(".watch").addEventListener("click", () => this._watchCurrent());
    this.shadowRoot.querySelector(".results-toggle").addEventListener("click", () => {
      this._ketQuaThuGon = !this._ketQuaThuGon;
      this._syncKetQuaThuGon();
    });
    this.shadowRoot.querySelector(".device-sound").addEventListener("click", () => this._toggleSoundHere());
    this.shadowRoot.querySelector(".screen-off").addEventListener("click", () => this._toggleScreenOff());
    this.shadowRoot.querySelector(".video-expand").addEventListener("click", () => this._toggleVideoExpanded());
    this.shadowRoot.querySelector(".video-fullscreen").addEventListener("click", () => this._videoFullscreen());
    this.shadowRoot.querySelector(".video-close").addEventListener("click", () => {
      /* Ở TOÀN MÀN HÌNH, X là THOÁT TOÀN MÀN — không đóng video, không đổi chế độ.
         Chủ máy chốt 20/09/2026: "nút x phải là thoát toàn màn hình chứ không phải
         chuyển chế độ gì cả". Trước đây nó gọi thẳng «_closeVideo»: hình đóng nhưng
         tiếng vẫn chạy trên máy, nên người dùng rơi vào chế độ chỉ-nghe mà họ không
         hề chọn. Ở toàn màn hình đây lại là nút DUY NHẤT còn hiện (luật
         «.ctl:not(.video-close)» ẩn hết phần còn lại), nên nó càng phải đúng nghĩa.
         Ngoài toàn màn hình thì X vẫn là đóng video như cũ. */
      const player = this.shadowRoot.querySelector(".player");
      if (this.shadowRoot.fullscreenElement === player) {
        document.exitFullscreen?.();
      } else if (player.classList.contains("expanded")) {
        player.classList.remove("expanded", "rotated");
        this._syncVideoExpandButton();
      } else {
        this._closeVideo();
      }
    });
    this.shadowRoot.querySelector(".video-listen").addEventListener("click", () => this._listenOnly());
    this.shadowRoot.querySelector(".video-rotate").addEventListener("click", () => this._toggleRotated());
    this.shadowRoot.querySelector(".spk-toggle").addEventListener("click", () => {
      this._speakerListOpen = !this._speakerListOpen;
      this._syncSpeakerBar();
    });
    this.shadowRoot.querySelectorAll(".layout-pick").forEach((button) => {
      button.addEventListener("click", () => {
        setLayoutChoice(this._config.entity, button.dataset.layout);
        this._applyLayout();
      });
    });
    const player = this.shadowRoot.querySelector(".player");
    for (const name of ["pointerdown", "pointermove", "keydown"]) {
      player.addEventListener(name, () => this._wakeControls());
    }
    this.shadowRoot.querySelector(".idle-shield").addEventListener("pointerdown", (event) => {
      // This touch only brings the controls back.
      event.preventDefault();
      event.stopPropagation();
      this._wakeControls();
    });
  }

  _entryId() {
    return (
      this._config.entry_id ||
      this._hass?.states?.[this._config.entity]?.attributes?.config_entry_id ||
      ""
    );
  }

  _applySharedOutputs() {
    // Once the user hand-picks speakers on this card, stop mirroring the shared
    // session's outputs so their selection (and joins/leaves) stays put.
    if (this._manualSelection) return;
    const attributes = this._hass?.states?.[this._config.entity]?.attributes || {};
    const sharedOutputs = Array.isArray(attributes.output_entity_ids)
      ? attributes.output_entity_ids.filter((entityId) => this._hass.states[entityId])
      : [];
    const marker = `${attributes.session_revision ?? attributes.session_updated_at ?? ""}:${sharedOutputs.join(",")}`;
    /* CHỮ KÝ KHÔNG ĐỔI VẪN PHẢI CHỌN LẠI NẾU LỰA CHỌN ĐÃ TRÔI MẤT. Chuỗi gây lỗi,
       chủ máy báo 20/09/2026 — khởi động lại Home Assistant thì nhạc vẫn chạy nhưng
       thẻ trắng trơn:
         1. Home Assistant khởi động lại → loa biến mất một lúc (Cast dò lại).
         2. «_syncPlayers» thấy loa «unavailable» liền XOÁ nó khỏi «_selectedPlayers».
         3. Loa trở lại — nhưng phiên vẫn là phiên cũ nên chữ ký Y HỆT, cổng canh
            thoát sớm, và loa KHÔNG BAO GIỜ được chọn lại.
       Chữ ký sinh ra để khỏi vẽ lại thừa, không phải để chặn lần cần vẽ lại thật.
       Nên chỉ bỏ qua khi CẢ HAI cùng khớp: chữ ký chưa đổi VÀ lựa chọn hiện tại vẫn
       đủ loa của phiên. Lỗi nằm ở thẻ nên add-on và c2a dính y như nhau. */
    const duLoa = sharedOutputs.every((entityId) => this._selectedPlayers.has(entityId));
    if (!sharedOutputs.length || (marker === this._sharedSessionMarker && duLoa)) return;
    this._selectedPlayers = new Set(sharedOutputs);
    this._sharedSessionMarker = marker;
    this._defaultsApplied = true;
  }

  // device_class do integration khai báo thường KHÔNG đáng tin cậy (nhiều loa/TV
  // không set, hoặc set sai) — nên ưu tiên device_class trước, sau đó fallback
  // dò theo tên thiết bị (tiếng Việt lẫn tiếng Anh) trước khi mặc định coi là Loa.
  _isAudioOnly(entityId, state) {
    const override = getDeviceKindOverride(entityId);
    if (override) return override === "audio";
    const dc = state.attributes.device_class;
    if (dc === "speaker") return true;
    if (dc === "tv") return false;
    const name = `${state.attributes.friendly_name || ""} ${entityId}`.toLowerCase();
    const looksVideo = /\btv\b|tivi|television|man\s*hinh|màn\s*hình|display|nest\s*hub|chromecast/.test(name);
    const looksAudio = /\bloa\b|speaker|amply|amplifier|receiver|echo\b|homepod|home\s*mini/.test(name);
    if (looksVideo && !looksAudio) return false;
    if (looksAudio && !looksVideo) return true;
    // Không đoán được: mặc định xếp vào Loa (đa số media_player không gắn màn
    // hình điều khiển được, và mục đích chính của card là phát âm thanh).
    return true;
  }

  _syncPlayers() {
    if (!this._hass) return;
    const virtualEntity = this._config.entity;
    const allPlayers = Object.entries(this._hass.states)
      // The integration's own virtual players (this entry and others, e.g. one
      // connected to c2a) are not speakers.
      .filter(([entityId]) => entityId.startsWith("media_player.") && entityId !== virtualEntity
        && this._hass.entities?.[entityId]?.platform !== "tritue_youtube_player")
      .sort((left, right) => this._friendlyName(left).localeCompare(this._friendlyName(right), "vi"));
    // Devices that lost their connection stay off the card (and out of the
    // selection) until Home Assistant reports them again.
    const connected = allPlayers.filter(([, state]) => state.state !== "unavailable");
    const players = connected.filter(([entityId]) => !this._hiddenPlayers.has(entityId));

    if (!this._defaultsApplied) {
      const configuredDefaults = Array.isArray(this._config.entities)
        ? this._config.entities
        : [this._hass.states[virtualEntity]?.attributes?.target_entity_id].filter(Boolean);
      configuredDefaults.forEach((entityId) => this._selectedPlayers.add(entityId));
      this._defaultsApplied = true;
    }
    const available = new Set(players.map(([entityId]) => entityId));
    [...this._selectedPlayers].forEach((entityId) => {
      if (!available.has(entityId)) this._selectedPlayers.delete(entityId);
    });

    const audioContainer = this.shadowRoot.querySelector(".players-audio");
    const videoContainer = this.shadowRoot.querySelector(".players-video");
    /* Danh sách chip loa gần như KHÔNG đổi giữa hai lần đổi trạng thái thường, nhưng
       hàm này chạy mỗi lần «set hass» — nhiều lần mỗi giây trong nhà đang chạy. Dựng
       lại vô điều kiện là xoá rồi tạo lại từng chip cùng listener của nó, làm mất cú
       cuộn đang dở và cả ô tích người dùng vừa chạm. Chỉ dựng lại khi CHỮ KÝ đổi.
       Phần đuôi (âm lượng, nút điều khiển, đang phát) vẫn chạy mỗi lượt vì nó phản
       ánh trạng thái sống — nên cổng canh chỉ bọc đúng phần dựng chip. */
    const chuKyLoa = JSON.stringify([
      players.map(([id, st]) => [
        id,
        st.attributes.friendly_name || id,
        this._isAudioOnly(id, st) ? "a" : "v",
        this._capabilities.get(id)?.transport || "",
        this._supportsSource(id, this._source) ? 1 : 0,
      ]),
      [...this._selectedPlayers].sort(),
      [...this._hiddenPlayers].sort(),
      connected.length,
      allPlayers.length,
    ]);
    if (chuKyLoa !== this._dsLoaChuKy) {
    this._dsLoaChuKy = chuKyLoa;
    audioContainer.replaceChildren();
    videoContainer.replaceChildren();
    if (!players.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = connected.length
        ? "Mọi thiết bị đang ẩn — mở mục Đã ẩn để khôi phục."
        : allPlayers.length
          ? "Chưa có loa hay tivi nào đang kết nối — thiết bị tự hiện khi kết nối lại."
          : "Không tìm thấy media_player nào khác.";
      audioContainer.append(empty);
    }
    let audioCount = 0;
    let videoCount = 0;
    for (const [entityId, state] of players) {
      // KHÔNG dùng <label>: bấm bất cứ đâu bên trong một <label> đều bật/tắt ô tích,
      // nên không thể tách "chọn loa để chỉnh âm lượng" khỏi "cho loa này phát".
      const label = document.createElement("div");
      label.className = "player-chip";
      label.dataset.entity = entityId;
      const isAudioOnly = this._isAudioOnly(entityId, state);
      if (isAudioOnly) audioCount++; else videoCount++;
      const capability = this._capabilities.get(entityId);
      const incompatible = !this._supportsSource(entityId, this._source);
      label.classList.toggle("source-incompatible", incompatible);
      label.title = incompatible
        ? "Thiết bị này không hỗ trợ play_media nên không nhận nguồn nào."
        : this._transportLabel(capability?.transport, isAudioOnly);
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = this._selectedPlayers.has(entityId);
      checkbox.addEventListener("change", () => {
        this._manualSelection = true;
        if (checkbox.checked) {
          this._selectedPlayers.add(entityId);
          this._lastTicked = entityId;
          this._onSpeakerAdded(entityId);
        } else {
          this._selectedPlayers.delete(entityId);
          this._onSpeakerRemoved(entityId);
        }
        this._updateSelectedCount();
        this._updateTransportState();
        this._syncNowPlaying();
        // Playlist buttons read "play on the speakers" or "listen here".
        if (this._view === "playlists") this._renderPlaylists();
      });
      const name = document.createElement("button");
      name.type = "button";
      name.className = "player-name";
      name.textContent = state.attributes.friendly_name || entityId;
      name.title = `Chỉnh âm lượng ${name.textContent}`;
      name.addEventListener("click", () => {
        this._volumeTarget = entityId;
        this._syncSpeakerBar();
      });
      const deviceIcon = document.createElement("ha-icon");
      deviceIcon.className = "device-icon";
      deviceIcon.setAttribute("icon", capability?.transport === "dlna"
        ? "mdi:cast-audio"
        : isAudioOnly ? "mdi:speaker" : "mdi:television-play");
      const hide = document.createElement("button");
      hide.type = "button";
      hide.className = "hide-player";
      hide.title = `Ẩn ${name.textContent} khỏi thẻ (khôi phục ở mục Đã ẩn)`;
      hide.setAttribute("aria-label", hide.title);
      const hideIcon = document.createElement("ha-icon");
      hideIcon.setAttribute("icon", "mdi:close");
      hide.append(hideIcon);
      hide.addEventListener("click", (event) => {
        // The button sits inside the chip's <label>: keep the click from toggling the checkbox.
        event.preventDefault();
        event.stopPropagation();
        this._setHidden([entityId], true);
      });
      const move = document.createElement("button");
      move.type = "button";
      move.className = "move-player";
      move.title = isAudioOnly ? "Chuyển sang cột Màn hình" : "Chuyển sang cột Loa";
      move.setAttribute("aria-label", move.title);
      const moveIcon = document.createElement("ha-icon");
      moveIcon.setAttribute("icon", isAudioOnly ? "mdi:television" : "mdi:speaker");
      move.append(moveIcon);
      move.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        setDeviceKindOverride(entityId, isAudioOnly ? "video" : "audio");
        this._syncPlayers();
      });
      label.append(checkbox, name, deviceIcon, move, hide);
      (isAudioOnly ? audioContainer : videoContainer).append(label);
    }
    if (players.length && !audioCount) {
      const empty = document.createElement("div");
      empty.className = "empty players-empty-col";
      empty.textContent = "Không có loa nào.";
      audioContainer.append(empty);
    }
    if (players.length && !videoCount) {
      const empty = document.createElement("div");
      empty.className = "empty players-empty-col";
      empty.textContent = "Không có màn hình nào.";
      videoContainer.append(empty);
    }
    }
    this._renderHiddenPlayers(connected.filter(([entityId]) => this._hiddenPlayers.has(entityId)));
    this._updateSelectedCount();
    this._updateTransportState();
    this._syncNowPlaying();
  }

  _renderHiddenPlayers(hiddenPlayers) {
    const container = this.shadowRoot.querySelector(".hidden-players");
    container.replaceChildren();
    if (!hiddenPlayers.length) {
      // Always start collapsed: the next hide must not reopen an old expanded list.
      this._showHidden = false;
      return;
    }
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "hidden-toggle";
    toggle.setAttribute("aria-expanded", String(this._showHidden));
    const chevron = document.createElement("ha-icon");
    chevron.setAttribute("icon", "mdi:chevron-down");
    toggle.append(chevron, document.createTextNode(`Đã ẩn (${hiddenPlayers.length})`));
    toggle.addEventListener("click", () => {
      this._showHidden = !this._showHidden;
      this._syncPlayers();
    });
    container.append(toggle);
    if (!this._showHidden) return;
    const list = document.createElement("div");
    list.className = "hidden-list";
    const restoreButton = (label, entityIds) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "restore-player";
      button.title = entityIds.length === 1 ? entityIds[0] : "Khôi phục mọi thiết bị đã ẩn";
      const icon = document.createElement("ha-icon");
      icon.setAttribute("icon", "mdi:backup-restore");
      const text = document.createElement("span");
      text.textContent = label;
      button.append(icon, text);
      button.addEventListener("click", () => this._setHidden(entityIds, false));
      return button;
    };
    for (const player of hiddenPlayers) {
      list.append(restoreButton(this._friendlyName(player), [player[0]]));
    }
    if (hiddenPlayers.length > 1) {
      list.append(restoreButton("Khôi phục tất cả", hiddenPlayers.map(([entityId]) => entityId)));
    }
    container.append(list);
  }

  /** Tải từ khoá và video gắn sẵn. Theo đúng nếp _loadHiddenPlayers: có cờ canh để
      không gọi chồng, và nuốt lỗi CÓ LÝ DO — tích hợp bản cũ chưa có đường này thì
      card vẫn chạy với danh sách dựng sẵn. */
  async _loadSuggestions() {
    if (this._goiY || this._goiYLoading || !this._hass) return;
    this._goiYLoading = true;
    try {
      const payload = await this._hass.callApi("GET", "tritue_youtube_player/suggestions");
      this._goiY = {
        tags: Array.isArray(payload?.tags) ? payload.tags : [],
        groups: Array.isArray(payload?.groups) ? payload.groups : [],
        seeded: Boolean(payload?.seeded),
      };
      /* Lần đầu: đẩy danh sách dựng sẵn VÀO KHO, rồi từ đó kho là nguồn duy nhất —
         nhờ vậy xoá mới xoá được dữ liệu thật. Chỉ quản trị mới ghi được, nên người
         xem thường sẽ bị từ chối; lúc đó card vẫn bày danh sách dựng sẵn để dùng. */
      if (!this._goiY.seeded) {
        try {
          const doc = await this._hass.callApi("POST", "tritue_youtube_player/suggestions", {
            action: "seed",
            tags: QUICK_SEARCH_TAGS,
            groups: YOUTUBE_SUGGESTED_CATEGORIES,
          });
          this._goiY = {
            tags: Array.isArray(doc?.tags) ? doc.tags : [],
            groups: Array.isArray(doc?.groups) ? doc.groups : [],
            seeded: Boolean(doc?.seeded),
          };
        } catch (_loi) {
          // Không phải quản trị, hoặc tích hợp bản cũ: giữ danh sách dựng sẵn.
        }
      }
      this._renderSuggestions();
    } catch (_error) {
      // Tích hợp đang khởi động, hoặc bản cũ chưa có đường này: dùng danh sách dựng sẵn.
      this._goiY = { tags: [], groups: [] };
    } finally {
      this._goiYLoading = false;
    }
  }

  /** Gửi một thay đổi (thêm từ khoá, tạo mục, gắn/gỡ video) rồi vẽ lại. Máy chủ trả
      về toàn bộ tài liệu mới nên card không phải tự đoán kết quả. */
  async _saveSuggestion(payload, thanhCong) {
    try {
      const doc = await this._hass.callApi("POST", "tritue_youtube_player/suggestions", payload);
      /* «seeded» PHẢI mang theo. Bỏ nó là sau mỗi lần lưu cờ thành undefined, card
         tưởng chưa nạp rồi rơi về hằng số dựng sẵn — thứ vừa xoá hiện lại ngay. */
      this._goiY = {
        tags: Array.isArray(doc?.tags) ? doc.tags : [],
        groups: Array.isArray(doc?.groups) ? doc.groups : [],
        seeded: Boolean(doc?.seeded),
      };
      this._renderSuggestions();
      if (thanhCong) this._setStatus(thanhCong);
    } catch (error) {
      const ma = String(error?.body?.error || error?.error || error?.message || "");
      const loi = {
        admin_required: "Chỉ tài khoản quản trị mới sửa được mục gợi ý.",
        too_many_tags: "Đã đủ số từ khoá tối đa.",
        too_many_groups: "Đã đủ số mục tối đa.",
        too_many_songs: "Mục này đã đủ số bài tối đa.",
        group_exists: "Mục này đã có rồi.",
        invalid_text: "Tên từ khoá không hợp lệ.",
        invalid_group: "Tên mục không hợp lệ.",
        unknown_group: "Không tìm thấy mục này.",
      }[ma];
      this._setStatus(loi || "Không lưu được mục gợi ý.", true);
    }
  }

  async _loadHiddenPlayers() {
    if (this._hiddenLoaded || this._hiddenLoading || !this._hass) return;
    this._hiddenLoading = true;
    try {
      const payload = await this._hass.callApi("GET", "tritue_youtube_player/hidden_players");
      this._hiddenPlayers = new Set(Array.isArray(payload.entity_ids) ? payload.entity_ids : []);
      this._hiddenLoaded = true;
      this._syncPlayers();
    } catch (_error) {
      // Integration still loading (or an older version without the view): show every player.
    } finally {
      this._hiddenLoading = false;
    }
  }

  async _setHidden(entityIds, hidden) {
    try {
      const payload = await this._hass.callApi("POST", "tritue_youtube_player/hidden_players", {
        entity_ids: entityIds,
        hidden,
      });
      this._hiddenPlayers = new Set(Array.isArray(payload.entity_ids) ? payload.entity_ids : []);
      this._hiddenLoaded = true;
      if (hidden) entityIds.forEach((entityId) => this._selectedPlayers.delete(entityId));
      this._syncPlayers();
      const names = entityIds.map((entityId) => this._hass.states[entityId]?.attributes?.friendly_name || entityId);
      this._setStatus(hidden
        ? `Đã ẩn ${names.join(", ")}. Khôi phục ở mục Đã ẩn.`
        : `Đã khôi phục ${names.length > 3 ? `${names.length} thiết bị` : names.join(", ")}.`);
    } catch (error) {
      const message = String(error?.body?.error || error?.error || error?.message || "");
      this._setStatus(
        message === "admin_required"
          ? "Chỉ tài khoản quản trị mới ẩn hoặc khôi phục được thiết bị."
          : message || "Không lưu được danh sách thiết bị ẩn.",
        true,
      );
    }
  }

  _friendlyName([entityId, state]) {
    return state.attributes.friendly_name || entityId;
  }

  _updateSelectedCount() {
    this.shadowRoot.querySelector(".selected-count").textContent = `${this._selectedPlayers.size} đã chọn`;
    this._syncSpeakerBar();
  }

  /* Thanh gọn phía trên danh sách loa: tên loa đang được chỉnh âm lượng, và nút
     «Đổi loa» bung/thu danh sách. Loa nào PHÁT do ô tích quyết định; loa nào đang
     được CHỈNH ÂM LƯỢNG do bấm vào tên — hai việc độc lập, nên loa chưa tích vẫn
     chỉnh được âm lượng. Đích chỉ đổi khi thiết bị biến mất khỏi Home Assistant. */
  _syncSpeakerBar() {
    if (!this.shadowRoot) return;
    const list = this.shadowRoot.querySelector(".spk-list");
    const toggle = this.shadowRoot.querySelector(".spk-toggle");
    const nameBox = this.shadowRoot.querySelector(".spk-bar-name");
    if (!list || !toggle || !nameBox) return;
    if (!this._volumeTarget || !this._hass?.states?.[this._volumeTarget]) {
      this._volumeTarget = [...this._selectedPlayers][0] || "";
    }
    list.hidden = !this._speakerListOpen;
    toggle.setAttribute("aria-expanded", this._speakerListOpen ? "true" : "false");
    toggle.classList.toggle("open", this._speakerListOpen);
    const state = this._volumeTarget ? this._hass?.states?.[this._volumeTarget] : null;
    nameBox.textContent = state
      ? state.attributes.friendly_name || this._volumeTarget
      : "Chưa chọn loa";
    for (const chip of this.shadowRoot.querySelectorAll(".player-chip")) {
      chip.classList.toggle("is-volume-target", chip.dataset.entity === this._volumeTarget);
    }
    this._renderSpeakerVolumes();
  }

  _supportsFeature(entityId, feature) {
    const value = Number(this._hass?.states?.[entityId]?.attributes?.supported_features || 0);
    return Boolean(value & feature);
  }

  async _loadCapabilities() {
    const entryId = this._entryId();
    if (!entryId || this._capabilitiesLoading || this._capabilityEntryId === entryId) return;
    this._capabilitiesLoading = true;
    this._capabilityEntryId = entryId;
    try {
      const payload = await this._hass.callApi("GET", `tritue_youtube_player/capabilities?entry_id=${encodeURIComponent(entryId)}`);
      const items = Array.isArray(payload.items) ? payload.items : [];
      this._capabilities = new Map(items.map((item) => [item.entity_id, item]));
      this._syncPlayers();
    } catch (_error) {
      // Fall back to state attributes when the integration is still loading.
      this._capabilityEntryId = "";
    } finally {
      this._capabilitiesLoading = false;
    }
  }

  _supportsSource(entityId, source) {
    const capability = this._capabilities.get(entityId);
    if (capability) return Array.isArray(capability.sources) && capability.sources.includes(source);
    // Before the capability matrix loads, any play_media entity can take every
    // source: TVs play YouTube natively, other speakers get it as an audio stream.
    return this._supportsFeature(entityId, 512);
  }

  _transportLabel(transport, isAudioOnly) {
    const labels = {
      google_cast_video: "Google Cast TV/box · YouTube + audio",
      google_cast_audio: "Google Cast audio · Zing/HTTP",
      android_tv: "Android TV/box · YouTube + audio",
      dlna: "DLNA · Zing/HTTP",
      generic_audio: "Media player HTTP audio",
      google_cast_unknown: "Google Cast chưa rõ loại · Zing/HTTP",
    };
    return labels[transport] || (isAudioOnly ? "Thiết bị phát âm thanh" : "Media player");
  }

  _targetsForService(service) {
    const featureByService = {
      media_previous_track: 16,
      media_next_track: 32,
      media_stop: 4096,
      volume_set: 4,
    };
    // Nothing selected: the buttons act on the latest session's speakers.
    const candidates = this._selectedPlayers.size
      ? [...this._selectedPlayers]
      : this._focusedSession()?.output_entity_ids || [];
    return candidates.filter((entityId) => {
      const state = this._hass?.states?.[entityId];
      if (!state || state.state === "unavailable") return false;
      if (service === "media_play_pause") {
        return this._supportsFeature(entityId, 1) || this._supportsFeature(entityId, 16384);
      }
      return this._supportsFeature(entityId, featureByService[service] || 0);
    });
  }

  _playTargets(source = this._source) {
    return [...this._selectedPlayers].filter((entityId) => {
      const state = this._hass?.states?.[entityId];
      if (!state || state.state === "unavailable" || !this._supportsFeature(entityId, 512)) return false;
      return this._supportsSource(entityId, source);
    });
  }

  _isVideoItem(item, source = item?.source || this._source) {
    const ma = String(item?.id || "");
    // Mã Facebook là chuỗi số, không phải mã 11 ký tự của YouTube.
    if (source === "facebook") return FB_VIDEO_ID.test(ma);
    return source === "youtube" && VIDEO_ID.test(ma);
  }

  _sessions() {
    const value = this._hass?.states?.[this._config.entity]?.attributes?.sessions;
    return Array.isArray(value) ? value.filter((session) => session && session.output_entity_ids?.length) : [];
  }

  /** The session the card shows and controls: the one of the speaker ticked last,
   * else any ticked speaker's session, else (nothing ticked) the latest. */
  _focusedSession() {
    const sessions = this._sessions();
    if (this._lastTicked && this._selectedPlayers.has(this._lastTicked)) {
      const own = sessions.find((session) => session.output_entity_ids.includes(this._lastTicked));
      if (own) return own;
    }
    return sessions.find((session) => session.output_entity_ids.some((id) => this._selectedPlayers.has(id)))
      || (this._selectedPlayers.size ? null : sessions[0] || null);
  }

  /** Position of a speaker now, from HA's last report plus the time since. */
  /** Whether a speaker already reports this session's song (see streamTarget). */
  _speakerPlaysItem(state, session) {
    const target = streamTarget(state?.attributes?.media_content_id);
    if (target === null || !session) return true;
    const id = String(session.id || "");
    return target === id || target === String(session.url || "") || (!!id && target.includes(id));
  }

  _speakerPosition(entityId, session = this._focusedSession()) {
    const state = this._hass?.states?.[entityId];
    const position = Number(state?.attributes?.media_position);
    if (!state || !Number.isFinite(position)) return null;
    // Right after a new song is sent the speaker still reports the previous
    // song's second for a few seconds; showing it made the bar and the picture
    // jump there before starting over from the beginning.
    if (!this._speakerPlaysItem(state, session)) return null;
    if (state.state !== "playing") return position;
    const updatedAt = Date.parse(state.attributes.media_position_updated_at || "");
    return position + (Number.isFinite(updatedAt) ? Math.max(0, (Date.now() - updatedAt) / 1000) : 0);
  }

  /* Card có BA nguồn thời gian: tiếng phát trên máy này, video xem trên thẻ, và loa.
     Việc chọn nguồn nào vốn nằm trong _updateProgress; nay việc TUA cũng cần đúng lựa
     chọn ấy, nên tách ra một chỗ dùng chung thay vì chép lại lần thứ hai — chép hai
     bản là kiểu sai về sau, sửa một bên quên bên kia. */
  _progressState() {
    if (deviceAudio.item) {
      const heard = deviceAudio.position();
      return { kieu: "may", viTri: heard ? heard.time : null, tong: heard?.duration || 0 };
    }
    if (this._video.open && !this._video.withSpeakers) {
      return {
        kieu: "video",
        viTri: this._video.state === -1 ? null : this._videoTimeNow(),
        tong: Number(this._video.item?.duration || 0),
      };
    }
    const session = this._focusedSession();
    const lead = session?.output_entity_ids.find((id) => this._speakerPosition(id) !== null);
    if (session && lead) {
      return {
        kieu: "loa",
        viTri: this._speakerPosition(lead),
        tong: Number(this._hass.states[lead].attributes.media_duration || session.duration || 0),
        session,
      };
    }
    return { kieu: "", viTri: null, tong: 0 };
  }

  /** Tua tới tỉ lệ 0..1 trên thanh, gửi đúng lệnh cho đúng nguồn đang phát. */
  _seekFraction(tiLe) {
    const trang = this._progressState();
    const tong = Number(trang.tong || 0);
    if (!tong || !Number.isFinite(tong)) {
      this._setStatus("Bài này không cho tua.", true);
      return;
    }
    const giay = Math.max(0, Math.min(tong, tiLe * tong));
    if (trang.kieu === "may") {
      const audio = deviceAudio.real();
      if (audio) audio.currentTime = giay;
      if (this._video.open) this._seekPicture(giay);
      return;
    }
    if (trang.kieu === "video") {
      this._seekPicture(giay);
      return;
    }
    if (trang.kieu !== "loa") return;
    // Bit 2 của supported_features là SEEK; loa không có thì nói thẳng, đừng gửi rồi im.
    const dich = (trang.session.output_entity_ids || []).filter((id) => this._supportsFeature(id, 2));
    if (!dich.length) {
      this._setStatus("Loa đang phát không hỗ trợ tua.", true);
      return;
    }
    /* Ngưng nhịp đồng bộ một lúc: Home Assistant còn đẩy vài bản trạng thái mang vị
       trí CŨ trước khi loa kịp báo lại, mà nhịp đó sẽ lôi hình về chỗ cũ. */
    this._mirrorHoldUntil = Date.now() + 6000;
    this._lastVideoSeekAt = Date.now();
    this._hass.callService("media_player", "media_seek", {
      entity_id: dich,
      seek_position: Math.round(giay),
    }).catch((error) => this._setStatus(error?.message || "Không tua được.", true));
    if (this._video.open) this._seekPicture(giay);
  }

  _updateProgress() {
    if (!this.shadowRoot?.querySelector(".progress") || !this._hass) return;
    const bar = this.shadowRoot.querySelector(".progress");
    const { viTri: position, tong: duration } = this._progressState();
    bar.hidden = position === null;
    if (position === null) return;
    const clamped = duration ? Math.min(position, duration) : position;
    bar.querySelector(".elapsed").textContent = this._formatDuration(clamped) || "0:00";
    bar.querySelector(".total").textContent = this._formatDuration(duration) || "–";
    bar.querySelector(".fill").style.width = duration ? `${Math.round((clamped / duration) * 1000) / 10}%` : "0";
  }

  _activeSpeakers() {
    const outputs = this._focusedSession()?.output_entity_ids || [...this._selectedPlayers];
    return outputs.filter((entityId) =>
      ["playing", "paused", "buffering"].includes(this._hass?.states?.[entityId]?.state));
  }

  /** Giây của loa này có phải SỐ ĐO còn tươi không, hay chỉ là phép ngoại suy.
   *
   * «_speakerPosition» trả về «media_position» CỘNG thời gian trôi kể từ mốc Home
   * Assistant ghi nhận. Đo trong nhà chủ máy 20/09/2026, loa Google Home đang phát:
   *
   *     media_position = 0, mốc thời gian KHÔNG đổi suốt 25 giây, bài dài 10684s
   *
   * Loa không báo lại vị trí bao giờ, nên con số suy ra chỉ là "bao lâu đã trôi kể
   * từ lần báo cuối" — và mốc ấy có thể đã cũ hàng phút.
   *
   * Giả lập trên chính mã này, dựng đúng số đo trên: hình đang ở giây 1–8 thì bị
   * quăng tới giây 91 rồi 97, cứ ~5 giây một lần. Đó chính là "lỗi video" chủ máy
   * thấy khi vừa ra loa vừa nghe trên máy — cú tua vẫn xảy ra cả khi chỉ ra loa,
   * nhưng lúc hình còn câm thì không ai để ý.
   *
   * CHỈ dùng cho vòng kéo HÌNH. Vòng kéo TIẾNG cố ý KHÔNG chốt: nó là thứ duy nhất
   * giữ tiếng trên máy đi cùng loa, và đặt lại giây của phần tử âm thanh thì rẻ,
   * trong khi tua khung YouTube là một cú nạp lại thấy được bằng mắt. Bản 0.26.22
   * chốt cả hai nên làm hỏng đồng bộ; bản 0.26.24 gỡ cả hai nên hình lại bị quăng.
   */
  _nhipDoDuoc(entityId) {
    const luc = Date.parse(this._hass?.states?.[entityId]?.attributes?.media_position_updated_at || "");
    return Number.isFinite(luc) && Date.now() - luc <= 10000;
  }

  _loaDanNhip(session = this._focusedSession()) {
    const outputs = session?.output_entity_ids || [...this._selectedPlayers];
    return outputs.find((entityId) =>
      ["playing", "paused", "buffering"].includes(this._hass?.states?.[entityId]?.state)
      && this._speakerPosition(entityId, session) !== null) || null;
  }

  /** Đồng hồ dẫn có THẬT SỰ tiến không — chắn trước khi cho nó kéo ai.
   *
   * Dùng cho CẢ BỐN đường đồng bộ, vì cả bốn hỏng theo đúng một kiểu: tin một đồng
   * hồ không đi tới đâu, rồi cứ vài giây lại lôi thứ đang chạy bình thường về chỗ
   * nó đứng. Hai kiểu "không đi tới đâu" mà phép thử này phải bắt được:
   *
   * - ĐỨNG IM MÀ TRÔNG NHƯ ĐANG CHẠY (loa): «_speakerPosition» cộng thêm thời gian
   *   trôi kể từ mốc Home Assistant báo, nên loa cứ báo mãi một con số nhưng mốc
   *   thời gian làm mới liên tục sẽ cho ra một giây TỤT về chỗ cũ sau mỗi nhịp đẩy.
   * - CỨ KHỞI ĐỘNG LẠI (tiếng trên máy, iOS): luồng bị WebKit cắt rồi chạy lại từ
   *   đầu, nên giây chạy 0 → 0,2 → 0 → 0,3 → 0… Phép thử "có ĐỔI không" cho nó lọt
   *   hết, vì nó đổi liên tục; phải hỏi "có TIẾN không" mới chặn được.
   *
   * Phép thử là so với chính nó ở nhịp trước: phải tiến được ít nhất một nửa quãng
   * thời gian thật đã trôi. Kẹt, tụt về đầu, hay nhảy loạn đều trượt; rung nhẹ vài
   * phần mười giây thì vẫn qua. Chưa đủ nửa giây giữa hai nhịp thì GIỮ mốc cũ chứ
   * không ghi đè — ghi đè thì mốc luôn mới tinh, quãng trôi không bao giờ đủ lớn
   * để kết luận, và vòng đồng bộ chết hẳn.
   *
   * Mỗi đường giữ mốc riêng theo «khoa»: nhiều đường cùng chạy trong một nhịp đẩy
   * trạng thái, xài chung một mốc thì đường sau luôn thấy quãng trôi bằng 0.
   */
  _dongHoChay(khoa, ai, giay) {
    const so = this._nhipDan || (this._nhipDan = {});
    const truoc = so[khoa];
    const luc = Date.now();
    /* Mốc quá cũ thì lấy mốc mới, mất đúng một nhịp. Không có lối này thì sau một
       lần tạm dừng dài, mốc nằm lại tít phía sau và đồng hồ dù đã chạy lại đàng
       hoàng vẫn phải đuổi cả phút mới được tin. */
    if (!truoc || truoc.ai !== ai || luc - truoc.luc > 5000) {
      so[khoa] = { ai, giay, luc };
      return false;
    }
    const troi = (luc - truoc.luc) / 1000;
    if (troi < 0.5) return false;
    /* CHỈ LÀM MỚI MỐC KHI ĐỒNG HỒ ĐÃ TỰ CHỨNG MINH. Đây là chỗ bản đầu của chính
       hàm này sai, và số đo chỉ ra: đồng hồ cứ chạy lại từ đầu vẫn lọt 1/6 lần.
       Vì mỗi nhịp lại vứt mốc cũ đi, nên lần nào cũng chỉ so trên một quãng ngắn
       — mà trên quãng ngắn thì một cú nhảy 0 → 0,3 trông y hệt chạy thật. Nới hay
       siết ngưỡng đều không chữa được: cái sai nằm ở ĐỘ DÀI QUÃNG SO, không phải
       ở con số ngưỡng.
       Nay chưa chứng minh được thì GIỮ NGUYÊN mốc cũ, nên quãng so cứ dài thêm
       mãi. Đồng hồ nhảy loạn quanh 0 không bao giờ đuổi kịp một quãng đang dài
       ra, còn đồng hồ chạy thật thì đạt ngay ở lần so đầu tiên. */
    const chay = giay - truoc.giay >= troi * 0.5;
    if (chay) so[khoa] = { ai, giay, luc };
    return chay;
  }

  /** Whether what the card shows is playing (this device, the video alone, or the speakers). */
  _playingNow() {
    if (deviceAudio.item) return deviceAudio.playing();
    if (this._video.open && !this._video.withSpeakers) return [1, 3].includes(this._video.state);
    const outputs = this._focusedSession()?.output_entity_ids || [...this._selectedPlayers];
    return outputs.some((entityId) => this._hass?.states?.[entityId]?.state === "playing");
  }

  /** Controls back on; fullscreen hides them again after 3 s without a touch while playing. */
  _wakeControls() {
    const player = this.shadowRoot?.querySelector(".player");
    if (!player) return;
    player.classList.remove("idle");
    clearTimeout(this._idleTimer);
    const big = () => player.classList.contains("expanded") || this.shadowRoot.fullscreenElement === player;
    if (!big()) return;
    this._idleTimer = setTimeout(() => {
      if (!big()) return;
      if (this._video.open && this._playingNow()) player.classList.add("idle");
      else this._wakeControls(); // paused: keep them, look again later
    }, 3000);
  }

  _updateTransportState() {
    if (!this.shadowRoot || !this._hass) return;
    const listening = !!deviceAudio.item;
    const videoAlone = this._video.open && !this._video.withSpeakers;
    const session = this._focusedSession();
    const outputs = session?.output_entity_ids || [...this._selectedPlayers];
    const playing = this._playingNow();
    const playPause = this.shadowRoot.querySelector(".play-pause");
    playPause.querySelector("ha-icon").setAttribute("icon", playing ? "mdi:pause" : "mdi:play");
    playPause.setAttribute("aria-label", playing ? "Tạm dừng" : "Phát");
    playPause.title = playing ? "Tạm dừng" : "Phát";
    // Sóng nhạc "đá đá": trước đây chỉ dựa vào CSS animation (kích hoạt qua
    // :has() hoặc class is-playing) — trên một số thiết bị/trình duyệt (WebView
    // cũ, chế độ tiết kiệm pin tắt animation hệ thống...) CSS animation không
    // chạy dù mọi thứ khác đúng. Để chắc chắn "nhảy" được ở mọi nơi, JS tự đổi
    // transform theo một interval riêng — không phụ thuộc animation/transition
    // CSS nào cả.
    /* «is-playing» đặt lên «.wrap» — tổ tiên chung của cả «.player» lẫn «.np-zone».
       Trước đây đặt trên «.np-zone», nhưng sóng nhạc nay nằm trong «.player» nên các
       luật «.np-zone.is-playing .np-wave…» sẽ không còn với tới: sóng hết sáng khi
       đang phát, mà node --check không bắt được loại lỗi này. */
    const wrap = this.shadowRoot.querySelector(".wrap");
    if (wrap) wrap.classList.toggle("is-playing", playing);
    this._toggleWaveAnimation(playing);
    playPause.disabled = !listening && !this._video.open && !this._targetsForService("media_play_pause").length;
    const canSkip = (step) => {
      if (listening) return deviceAudio.index >= 0 && !!deviceAudio.queue[deviceAudio.index + step];
      if (videoAlone) {
        const target = this._queueIndex + step;
        return this._queueIndex >= 0 && target >= 0 && target < this._queue.length && this._isVideoItem(this._queue[target]);
      }
      if (!session) return false;
      const target = Number(session.queue_index) + step;
      if (Number(session.queue_index) >= 0 && target >= 0 && target < Number(session.queue_size || 0)) return true;
      // Phiên của loa chỉ có một bài mà thẻ còn giữ hàng đợi: vẫn qua bài được, thẻ tự
      // gửi bài kế cho loa. Xem «_skip».
      return this._hangCuaTheDungDuoc(step);
    };
    this.shadowRoot.querySelector(".previous").disabled = !canSkip(-1);
    this.shadowRoot.querySelector(".next").disabled = !canSkip(1);
    this.shadowRoot.querySelector(".stop").disabled = !listening && !session && !this._video.open && !this._selectedPlayers.size;
    this._renderSpeakerVolumes();
  }

  /** Chạy/dừng sóng nhạc bằng JS timer (không dùng @keyframes) — set thẳng
   * transform mỗi tick nên luôn thấy "nhảy", bất kể trình duyệt/thiết bị có
   * chặn CSS animation hay không. */
  _toggleWaveAnimation(playing) {
    if (!this.shadowRoot) return;
    if (!playing) {
      clearInterval(this._waveTimer);
      this._waveTimer = null;
      this.shadowRoot.querySelectorAll(".np-wave--bars span, .np-wave--simple span, .wv-dot")
        .forEach((el) => { el.style.transform = ""; });
      return;
    }
    if (this._waveTimer) return; // đã chạy rồi, khỏi tạo interval mới
    const tick = () => {
      const bars = this.shadowRoot?.querySelectorAll(".np-wave--bars span");
      const simple = this.shadowRoot?.querySelectorAll(".np-wave--simple span");
      const dots = this.shadowRoot?.querySelectorAll(".wv-dot");
      bars?.forEach((el) => { el.style.transform = `scaleY(${(0.28 + Math.random() * 0.72).toFixed(2)})`; });
      simple?.forEach((el) => { el.style.transform = `scaleY(${(0.3 + Math.random() * 0.7).toFixed(2)})`; });
      dots?.forEach((el) => { el.style.transform = `translateY(-${Math.round(2 + Math.random() * 14)}px)`; });
    };
    tick();
    this._waveTimer = setInterval(tick, 220);
  }

  /* MỘT thanh âm lượng duy nhất, cho đúng loa đang chọn ở thanh «Loa phát nhạc» —
     thay cho cả chồng thanh trượt trước đây. Giữ lại hai điều bản cũ làm đúng:
     chỉ dựng lại khi ĐỔI loa, và không giật thanh khi người dùng đang kéo. */
  _renderSpeakerVolumes() {
    if (!this.shadowRoot || !this._hass) return;
    const container = this.shadowRoot.querySelector(".spk-volume");
    if (!container) return;
    const entityId = this._volumeTarget;
    const state = entityId ? this._hass.states[entityId] : null;
    // supported_features bit 4 = VOLUME_SET; loa không có thì không bày thanh trượt.
    const usable = Boolean(state) && state.state !== "unavailable" && this._supportsFeature(entityId, 4);
    if (!usable) {
      container.replaceChildren();
      this._volumeRowsSig = "";
      return;
    }
    const value = Number(state.attributes?.volume_level ?? 0.35);

    if (this._volumeRowsSig !== entityId) {
      this._volumeRowsSig = entityId;
      container.replaceChildren();
      const row = document.createElement("div");
      row.className = "svol-row";
      row.dataset.entity = entityId;
      const name = document.createElement("span");
      name.className = "svol-name";
      /* Ghi RÕ TÊN LOA đang chỉnh, không phải chữ "Âm lượng" chung chung. Loa đích
         chỉ đổi khi chạm vào TÊN loa, còn tích ô vuông thì không — hai thao tác độc
         lập theo đúng yêu cầu. Nhưng trước đây màn hình không nói loa nào đang được
         chỉnh, nên tích loa B mà thanh vẫn đang chỉnh loa A thì trông y như thanh
         trượt báo sai mức. */
      name.textContent = state.attributes?.friendly_name || entityId;
      const range = document.createElement("input");
      range.type = "range";
      range.min = "0";
      range.max = "1";
      range.step = "0.01";
      range.className = "svol-range";
      range.value = String(value);
      range.setAttribute("aria-label", `Âm lượng ${state.attributes?.friendly_name || entityId}`);
      const pct = document.createElement("span");
      pct.className = "svol-pct";
      pct.textContent = `${Math.round(value * 100)}%`;
      range.addEventListener("input", () => {
        this._activeVolumeEntity = entityId;
        pct.textContent = `${Math.round(Number(range.value) * 100)}%`;
      });
      range.addEventListener("change", async () => {
        const mucDat = Number(range.value);
        /* Nhớ mức VỪA ĐẶT. Bỏ chốt ngay khi lệnh trả về là sai: Home Assistant còn
           đẩy tiếp vài bản trạng thái mang giá trị CŨ trước khi loa kịp báo lại, và
           thanh trượt bị ghi đè ngược — kéo về 0 thì nhảy về chỗ cũ. Giữ mức mong
           đợi cho tới khi trạng thái khớp, hoặc quá 5 giây thì thôi chờ. */
        this._volumeMongDoi = {
          entityId,
          muc: mucDat,
          luc: Date.now(),
          // Mốc báo cáo của loa NGAY TRƯỚC khi gửi: chờ nó đổi là biết loa đã lên tiếng.
          moc: this._hass?.states?.[entityId]?.last_updated || "",
        };
        try {
          await this._hass.callService("media_player", "volume_set", {
            entity_id: entityId,
            volume_level: mucDat,
          });
        } catch (error) {
          this._volumeMongDoi = null;
          this._setStatus(error?.message || "Không đổi được âm lượng.", true);
        } finally {
          this._activeVolumeEntity = null;
        }
      });
      row.append(name, range, pct);
      container.append(row);
      return;
    }

    // Vẫn loa cũ: cập nhật số theo trạng thái, trừ khi người dùng đang kéo thanh.
    const row = container.querySelector(".svol-row");
    if (!row || entityId === this._activeVolumeEntity || !Number.isFinite(value)) return;
    const range = row.querySelector(".svol-range");
    const pct = row.querySelector(".svol-pct");
    if (this.shadowRoot.activeElement === range) return;
    /* Chờ tới khi LOA THẬT SỰ LÊN TIẾNG, thay vì đếm ngược 5 giây rồi thả.
       Bản cũ giữ mức vừa đặt đúng 5 giây; loa nào báo lại chậm hơn thế là thanh trượt
       bị ghi đè bằng giá trị cũ — và vì sao chỉ "thi thoảng" mới thấy: loa nhanh hơn
       5 giây thì không ai để ý.
       Cách nhận biết loa đã lên tiếng: mốc «last_updated» của nó ĐỔI so với lúc gửi
       lệnh. So hai mốc CỦA CÙNG MỘT NGUỒN nên không phụ thuộc đồng hồ; nếu đem mốc
       của Home Assistant so với đồng hồ trình duyệt thì chỉ cần hai máy lệch giờ là
       hỏng. Vẫn giữ một hạn chót 15 giây phòng khi lệnh rơi mất và loa không bao giờ
       báo — hạn này tính trên cùng đồng hồ trình duyệt nên an toàn. */
    const cho = this._volumeMongDoi;
    if (cho && cho.entityId === entityId) {
      const moc = state.last_updated || "";
      if (Math.abs(value - cho.muc) < 0.01) this._volumeMongDoi = null;
      else if (moc === cho.moc && Date.now() - cho.luc < 15000) return;
      else this._volumeMongDoi = null;
    }
    range.value = String(value);
    pct.textContent = `${Math.round(value * 100)}%`;
  }

  _syncNowPlaying() {
    if (!this.shadowRoot || !this._hass) return;
    const names = (entityIds) => entityIds
      .map((entityId) => this._hass.states[entityId]?.attributes?.friendly_name || entityId)
      .filter(Boolean);
    const video = this._video;
    /* Tên bài và dòng phụ nay nằm TRONG khối nghe («.nghe-ten» / «.nghe-phu») chứ không
       còn ở ô riêng bên cột phải. Trỏ thẳng hai biến này sang phần tử mới là đủ cho CẢ
       BA nhánh bên dưới (đang xem video / nghe trên máy này / phát ra loa); nếu đi đồng
       bộ hai bản thì chỉ cần quên một nhánh là tên bài đứng hình ở bài cũ. */
    const titleNode = this.shadowRoot.querySelector(".nghe-ten");
    const metaNode = this.shadowRoot.querySelector(".nghe-phu");
    const session = this._focusedSession();
    /* LẤY SẴN ĐỊA CHỈ LUỒNG CỦA BÀI LOA ĐANG PHÁT.
       Chủ máy đo 20/09/2026 trên Android: bấm "nghe trên máy này" thì "mất 4s đến
       10s mới có tiếng". Phần lớn quãng ấy là một lượt hỏi máy chủ xin địa chỉ
       luồng (đo trước đó: 1,5–2,6 giây) rồi mới tới lúc tải dữ liệu. Lấy trước thì
       lúc bấm «streamUrl» trả ra ngay từ bộ nhớ, không còn lượt hỏi nào.
       Gọi mỗi lần vẽ lại không tốn gì: «chuanBi» tự bỏ qua bài đã có trong bộ nhớ,
       nên mỗi bài chỉ hỏi máy chủ đúng một lần. */
    if (session?.title && !deviceAudio.item) {
      deviceAudio.entryId = this._entryId();
      deviceAudio.chuanBi({
        source: session.source,
        id: session.id,
        url: session.url,
        duration: session.duration,
      });
    }
    /* Nhãn nguồn (YouTube / Zing MP3 / Link) đặt ở ĐÚNG MỘT chỗ, lấy theo thứ đang
       phát thật — ba nhánh dưới đều thoát sớm nên rải ra đó là kiểu chắc chắn sót. */
    const nguonDangPhat = video.open
      ? (video.item?.source || "youtube")
      : deviceAudio.item
        ? deviceAudio.item.source
        : session?.source;
    const nhanNguon = this.shadowRoot.querySelector(".nghe-nguon");
    nhanNguon.textContent = TEN_NGUON[nguonDangPhat] || "";
    nhanNguon.hidden = !nhanNguon.textContent;
    /* «soundOnly» = khung mở ra CHỈ để mang tiếng: nó phải còn nằm trong trang và
       còn chạy, nhưng thẻ phải trông y như lúc chưa mở hình. Nên mọi thứ thuộc về
       phần NHÌN đi theo «hienHinh», còn phần SỐNG của khung đi theo «video.open». */
    const hienHinh = video.open && !video.soundOnly;
    this.shadowRoot.querySelector(".player").classList.toggle("video-on", hienHinh);
    const khungHinh = this.shadowRoot.querySelector(".video-frame");
    khungHinh.hidden = !video.open;
    khungHinh.classList.toggle("chi-tieng", video.open && !!video.soundOnly);
    /* «.video-rotate» PHẢI có trong danh sách này. Thẻ của nó khai sẵn `hidden`, mà
       trước đây không chỗ nào gỡ ra — nên nút xoay ngang KHÔNG BAO GIỜ hiện. Thiếu
       sót có sẵn, không phải do lần sửa nào gây ra; chủ máy báo 18/09/2026 "làm mất
       nút quay ngang rồi". Luật ẩn theo hướng máy ở CSS vẫn giữ: máy đã nằm ngang thì
       xoay thêm là vô nghĩa. */
    for (const selector of [".video-listen", ".video-rotate", ".video-expand",
      ".video-fullscreen", ".video-close"]) {
      this.shadowRoot.querySelector(selector).hidden = !hienHinh;
    }
    // "Nghe trên máy này": speakers play, and this device plays the sound too (the
    // picture's own sound, or an audio element following the speakers).
    const soundOn = deviceAudio.along || (video.open && video.withSpeakers && video.soundHere);
    const sound = this.shadowRoot.querySelector(".device-sound");
    /* ẨN NÚT KHI KHÔNG CÓ LOA NÀO ĐỂ CHẠY THEO — chỉ thế thôi.
       Điều kiện cũ ẩn luôn khi «deviceAudio.item» có giá trị, tức khi máy đang nghe
       một mình. Hồi ấy đúng, vì nghe một mình thì chưa có loa. Nhưng từ khi tích loa
       mà VẪN GIỮ tiếng trên máy (chủ máy chốt 21/09/2026), trạng thái "một mình" còn
       nguyên trong khi thực tế đã là loa + máy — và nút biến mất đúng lúc cần nó
       nhất. Nay nút hiện bất cứ khi nào có loa đang phát, để tắt tiếng máy được. */
    sound.hidden = video.open ? !video.withSpeakers : !session?.title;
    sound.setAttribute("aria-pressed", String(soundOn));
    sound.querySelector("ha-icon").setAttribute("icon", soundOn ? "mdi:volume-high" : "mdi:volume-off");
    sound.title = soundOn ? "Tắt tiếng trên máy này — chỉ nghe loa" : "Nghe cả trên máy này, chạy theo loa";
    const screenOff = this.shadowRoot.querySelector(".screen-off");
    screenOff.setAttribute("aria-pressed", String(listenScreenOff()));
    screenOff.title = listenScreenOff()
      ? "Đang bật: tắt màn hình vẫn nghe tiếp trên máy này. Bấm để tắt."
      : "Đang tắt: tắt màn hình thì tiếng trên máy này dừng. Bấm để nghe tiếp cả khi tắt màn hình.";
    this._renderOtherSessions(session);

    if (video.open && video.withSpeakers && session && session.id !== video.item?.id) {
      // Ticked another speaker: the picture switches to that speaker's song and
      // seeks to where that speaker is.
      if (session.source === "youtube" && VIDEO_ID.test(String(session.id || ""))) {
        this._lastVideoSeekAt = 0;
        this._openVideo(
          { id: session.id, url: session.url, title: session.title, channel: session.artist, duration: session.duration },
          // Loa đổi bài thì giữ nguyên vai của khung: đang mang tiếng thì vẫn mang tiếng.
          { withSpeakers: true, soundHere: video.soundHere, soundOnly: video.soundOnly },
        );
        return;
      }
      this._closeVideo();
      this._setStatus("Loa này đang phát Zing/link audio — không có video.");
      return;
    }
    if (hienHinh) {
      // The video replaces the cover; its caption is the now-playing line.
      const speakers = video.withSpeakers ? names(session?.output_entity_ids || this._activeSpeakers()) : [];
      titleNode.textContent = video.item.title;
      metaNode.textContent = [
        video.item.channel,
        this._formatDuration(video.item.duration),
        speakers.length
          ? `Tiếng ra ${speakers.join(", ")}${soundOn ? " và máy này" : ""}`
          : video.followsDevice
            ? listenScreenOff() ? "Tiếng từ máy này, cả khi tắt màn hình" : "Tiếng từ máy này"
            : "Xem trên thẻ",
      ].filter(Boolean).join(" · ");
      this._nowWatchItem = null;
      this.shadowRoot.querySelector(".watch").hidden = true;
      return;
    }
    /* CHỈ NGHE BẰNG KHUNG THÌ TRÔNG NHƯ NGHE NHẠC, không phải như xem video.
       Chủ máy chốt 21/09/2026: "kích xem video là xem video, nghe nhạc là nghe nhạc".
       Trên máy nhà Táo, khung chỉ là cái máy phát vô hình — thẻ vẫn phải hiện tên
       bài, ảnh bìa và giữ nút Xem để còn chuyển sang xem được. Thiếu nhánh này thì
       ô đang-phát báo "Chưa phát bài nào" ngay giữa lúc nhạc đang chạy (đúng ảnh
       chụp chủ máy gửi lúc 18:30). */
    if (video.open && video.soundOnly && video.item && !video.withSpeakers) {
      const item = { source: "youtube", ...video.item };
      titleNode.textContent = item.title || item.id;
      metaNode.textContent = [
        TEN_NGUON[item.source] || "",
        item.channel || item.artist,
        this._formatDuration(item.duration),
        this._queue.length > 1 ? `${this._queueIndex + 1}/${this._queue.length}` : "",
        listenScreenOff() ? "Nghe trên máy này, cả khi tắt màn hình" : "Nghe trên máy này",
      ].filter(Boolean).join(" · ");
      this._nowWatchItem = this._isVideoItem(item) ? item : null;
      this.shadowRoot.querySelector(".watch").hidden = !this._nowWatchItem;
      this._showCover(item.thumbnail);
      return;
    }
    if (deviceAudio.item) {
      const item = deviceAudio.item;
      titleNode.textContent = item.title || item.id;
      metaNode.textContent = [
        TEN_NGUON[item.source] || "",
        item.channel || item.artist,
        this._formatDuration(item.duration),
        deviceAudio.queue.length > 1 ? `${deviceAudio.index + 1}/${deviceAudio.queue.length}` : "",
        listenScreenOff() ? "Nghe trên máy này, cả khi tắt màn hình" : "Nghe trên máy này",
      ].filter(Boolean).join(" · ");
      // Listening to a YouTube song: "watch" opens its video at the second being heard.
      this._nowWatchItem = this._isVideoItem(item) ? item : null;
      this.shadowRoot.querySelector(".watch").hidden = !this._nowWatchItem;
      this._showCover(item.thumbnail);
      return;
    }

    const outputs = session?.output_entity_ids || [];
    const lead = outputs.map((entityId) => this._hass.states[entityId]).find(Boolean);
    const state = lead?.state;
    const title = session?.title || "";
    const queuePosition = Number(session?.queue_size) > 1 && Number(session?.queue_index) >= 0
      ? `${Number(session.queue_index) + 1}/${session.queue_size}`
      : "";
    const stateText = state === "playing" ? "Đang phát" : state === "paused" ? "Tạm dừng" : title ? "Đã gửi" : "";
    titleNode.textContent = title || "Chưa phát bài nào";
    metaNode.textContent = title
      ? [stateText, TEN_NGUON[session?.source] || "", session.artist,
        this._formatDuration(session.duration), queuePosition,
        names(outputs).join(", ") + (soundOn ? " và máy này" : "")]
        .filter(Boolean).join(" · ")
      : this._selectedPlayers.size
        ? "Chọn một bài trong kết quả để phát ra loa."
        : "Chọn loa để phát ra loa, hoặc bấm nút nghe / xem video của một bài để phát ngay trên máy này.";

    /* «source» PHẢI có trong bản ghi: cửa vào của «_openVideo» rẽ nhánh theo đúng
       trường này. Thiếu nó thì mục Facebook rơi vào đường nhúng YouTube rồi bị chặn
       vì mã không phải 11 ký tự — hỏng ở một chỗ chẳng liên quan gì tới nguyên nhân. */
    const maPhien = String(session?.id || "");
    const xemDuoc = Boolean(title) && (
      (session.source === "youtube" && VIDEO_ID.test(maPhien))
      || (session.source === "facebook" && FB_VIDEO_ID.test(maPhien))
    );
    this._nowWatchItem = xemDuoc
      ? {
        id: session.id,
        url: session.url,
        title,
        channel: session.artist,
        duration: session.duration,
        source: session.source,
      }
      : null;
    this.shadowRoot.querySelector(".watch").hidden = !this._nowWatchItem;

    this._showCover(session?.thumbnail || "");
  }

  /** Ảnh bìa hiện ở HAI chỗ: ô vuông nhỏ cạnh tên bài, và đĩa tròn của chế độ chỉ
      nghe nhạc. Cùng một đường dữ liệu cho cả hai để đĩa không bao giờ lệch với bài
      đang phát — nếu tách hai đường thì chỉ cần một chỗ quên gọi là đĩa đứng hình ở
      bài cũ. Không có ảnh thì hiện biểu tượng nốt nhạc dự phòng. */
  _showCover(imageUrl) {
    const co = /^https?:\/\//.test(imageUrl);
    for (const selector of [".now-cover", ".nghe-bia"]) {
      const khung = this.shadowRoot.querySelector(selector);
      if (!khung) continue;
      const image = khung.querySelector("img");
      const icon = khung.querySelector("ha-icon");
      image.hidden = !co;
      icon.hidden = !image.hidden;
      if (!image.hidden && image.src !== imageUrl) image.src = imageUrl;
    }
    /* Ảnh nền của khung nghe. Tách khỏi vòng lặp trên vì nó KHÔNG có biểu tượng dự
       phòng: không có ảnh thì khung để trơn, chứ bày một nốt nhạc to cỡ cả khung thì
       thành vết bẩn giữa thẻ. */
    const nen = this.shadowRoot.querySelector(".nghe-nen");
    if (nen) {
      nen.hidden = !co;
      if (co && nen.src !== imageUrl) nen.src = imageUrl;
    }
  }


  /** Other groups of speakers playing something else: tap one to control it. */
  _renderOtherSessions(focused) {
    const container = this.shadowRoot.querySelector(".others");
    const others = this._sessions().filter((session) => session.session_id !== focused?.session_id);
    // Ticked speakers outside the shown session can join it without restarting it.
    const joiners = focused
      ? [...this._selectedPlayers].filter((id) => !focused.output_entity_ids.includes(id)
        && this._hass.states[id] && this._hass.states[id].state !== "unavailable")
      : [];
    const signature = `${focused?.session_id}:${joiners.join(",")}|` + others.map((s) => `${s.session_id}:${s.revision}`).join("|");
    if (container.dataset.sig === signature) return;
    container.dataset.sig = signature;
    container.replaceChildren();
    if (joiners.length) {
      const join = document.createElement("button");
      join.type = "button";
      join.className = "other-session join-session";
      const icon = document.createElement("ha-icon");
      icon.setAttribute("icon", "mdi:speaker-multiple");
      const text = document.createElement("span");
      const joinerNames = joiners.map((id) => this._hass.states[id]?.attributes?.friendly_name || id);
      text.textContent = `Cho ${joinerNames.join(", ")} nghe cùng`;
      join.append(icon, text);
      join.addEventListener("click", () => this._joinSession(focused, joiners));
      container.append(join);
    }
    for (const session of others) {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "other-session";
      const speakers = session.output_entity_ids
        .map((entityId) => this._hass.states[entityId]?.attributes?.friendly_name || entityId);
      chip.title = `${speakers.join(", ")}: ${session.title || ""}`;
      if (/^https?:\/\//.test(session.thumbnail || "")) {
        const image = document.createElement("img");
        image.alt = "";
        image.src = session.thumbnail;
        chip.append(image);
      } else {
        const icon = document.createElement("ha-icon");
        icon.setAttribute("icon", "mdi:speaker");
        chip.append(icon);
      }
      const text = document.createElement("span");
      text.textContent = `${speakers.join(", ")} · ${session.title || ""}`;
      chip.append(text);
      chip.addEventListener("click", () => {
        this._manualSelection = true;
        this._selectedPlayers = new Set(session.output_entity_ids);
        this._lastTicked = session.output_entity_ids[0];
        this._syncPlayers();
      });
      container.append(chip);
    }
  }

  /** Một hàng gộp: hai nguồn nhạc và nút Playlist. Nút nào sáng là do khung đang
      xem quyết định — đang mở Playlist thì nút Playlist sáng, ngược lại là nguồn
      đang chọn. */
  /** Các nguồn còn hiện theo cấu hình, đúng thứ tự của hàng nút. */
  _nguonHienThi() {
    return ["youtube", "zing", "facebook"].filter((ma) => this._config[`show_${ma}`] !== false);
  }

  /** Hiện/ẩn từng mục của hàng nguồn theo cấu hình, và chỉnh SỐ CỘT theo số mục còn lại. */
  _applySourceVisibility() {
    const hang = this.shadowRoot?.querySelector(".source-switch");
    if (!hang) return;
    const conLai = this._nguonHienThi();
    const hienPlaylist = this._config.show_playlist !== false;
    let dem = 0;
    hang.querySelectorAll(".source-button").forEach((nut) => {
      // Nút Playlist nằm chung hàng nhưng không phải một nguồn — phân biệt bằng data-view.
      const an = nut.dataset.view ? !hienPlaylist : !conLai.includes(nut.dataset.source);
      nut.hidden = an;
      if (!an) dem += 1;
    });
    hang.classList.remove("so-1", "so-2", "so-3", "so-4");
    if (dem >= 1 && dem <= 4) hang.classList.add(`so-${dem}`);
    // Ẩn hết thì giấu luôn cả khung, để khỏi còn một dải rỗng có viền.
    hang.hidden = dem === 0;
    /* Ẩn đúng nguồn đang mở thì phải dời sang nguồn còn hiện: để nguyên thì ô tìm
       kiếm vẫn gửi đi cái nguồn mà người dùng vừa bảo là không muốn thấy, và danh
       sách kết quả cũ cũng không còn nút nào ứng với nó. */
    if (conLai.length && !conLai.includes(this._source)) {
      this._source = conLai[0];
      this._results = [];
      this._renderResults();
    }
    if (!hienPlaylist && this._view === "playlists") this._showView("search");
    this._updateSourceButtons();
    this._syncSavePlaylist();
  }

  _updateSourceButtons() {
    if (!this.shadowRoot) return;
    const playlists = this._view === "playlists";
    this.shadowRoot.querySelectorAll(".source-button").forEach((button) => {
      const dangChon = button.dataset.view
        ? playlists
        : !playlists && button.dataset.source === this._source;
      button.setAttribute("aria-pressed", String(dangChon));
    });
    const input = this.shadowRoot.querySelector('input[type="search"]');
    const submit = this.shadowRoot.querySelector(".search-button");
    /* Facebook nói rõ là CHỈ dán link: Facebook không có đường tìm kiếm công khai để
       gọi, nên mời người dùng gõ từ khoá là hứa một thứ chắc chắn không chạy. Link
       chia sẻ cũng nhận được — máy phát tự lần ra mã video từ trang. */
    input.placeholder = this._source === "youtube"
      ? "Tìm tên bài hát, ca sĩ hoặc dán link YouTube…"
      : this._source === "facebook"
        ? "Dán link video Facebook (reel, watch hoặc link chia sẻ)…"
        : "Tìm tên bài hát hoặc ca sĩ…";
    input.setAttribute("aria-label", "Tìm tên bài hát hoặc ca sĩ");
    input.maxLength = this._source === "zing" ? 120 : 2048;
    submit.querySelector(".search-label").textContent = "Tìm kiếm";
    submit.setAttribute("aria-label", "Tìm kiếm");
    submit.title = "Tìm kiếm";
    submit.querySelector("ha-icon").setAttribute("icon", "mdi:magnify");
    /* Dòng mô tả nguồn ở đầu card đã BỎ theo yêu cầu chủ máy: nó chiếm nguyên một
       dòng ngang đầu thẻ chỉ để nhắc lại thứ mà hàng nút nguồn ngay bên dưới đã nói. */
  }

  async _search() {
    const query = this.shadowRoot.querySelector('input[type="search"]').value.trim();
    if (!query) return;
    const button = this.shadowRoot.querySelector(".search-button");
    button.disabled = true;
    this._setStatus("Đang tìm kiếm…");
    try {
      const entryId = this._entryId();
      if (!entryId) throw new Error("Không tìm thấy config entry. Hãy tải lại integration.");
      const payload = await this._hass.callApi("GET", `tritue_youtube_player/search?entry_id=${encodeURIComponent(entryId)}&source=${encodeURIComponent(this._source)}&q=${encodeURIComponent(query)}&limit=20`);
      this._results = Array.isArray(payload.items) ? payload.items : [];
      this._saveSearch(query);
      this._renderResults();
      this._setStatus(
        this._results.length
          ? `Tìm thấy ${this._results.length} bài.`
          : "Không tìm thấy bài phù hợp.",
      );
    } catch (error) {
      this._results = [];
      this._renderResults();
      /* Hiện ĐÚNG mã lỗi phía sau trả về. Câu chung chung "Không thể tìm kiếm lúc này"
         nuốt mất thông tin duy nhất giúp truy nguyên — chủ máy 19/09/2026 dán link
         Facebook và chỉ thấy đúng câu ấy, không biết là máy phát cũ hay link hỏng. */
      const ma = String(error?.body?.error || error?.error || "");
      const loi = {
        invalid_search_source: "Máy phát chưa hỗ trợ nguồn này — hãy cập nhật add-on"
          + " TriTue YouTube Player (HACS chỉ cập nhật tích hợp và thẻ).",
        invalid_search_query: "Nguồn Facebook chỉ nhận LINK dán vào, không tìm theo từ khoá.",
        facebook_share_unreadable: "Không đọc được link chia sẻ này — Facebook có thể đã"
          + " đổi trang. Thử dán link dạng /reel/… hoặc /watch?v=…",
        search_unavailable: "Máy phát không tra cứu được lúc này.",
        search_provider_failed: "Máy phát không đọc được link này.",
        search_process_failed: "Máy phát thiếu công cụ yt-dlp hoặc gọi không được.",
      }[ma];
      this._setStatus(loi || error?.message || (ma ? `Lỗi: ${ma}` : "Không thể tìm kiếm lúc này."), true);
    } finally {
      button.disabled = false;
    }
  }

  /** Bài gợi ý của R1 -> hình dạng mục nhạc mà `_playResult` đọc được.
      R1 ghi `thumbnail_url`/`duration_seconds`, card này đọc `thumbnail`/`duration`
      — chép thẳng là ảnh trắng và thời lượng rỗng. */
  _ytSongToItem(song) {
    const id = song.video_id || song.id;
    /* Bài ghim nay MANG THEO NGUỒN. Bản ghi cũ không có trường này nên rơi về
       YouTube — đúng thứ đã lưu trước khi có Facebook, không phải đoán. Thiếu chỗ
       này thì bài Facebook ghim xong bấm phát lại sẽ đi vào đường YouTube và chết
       ở cửa chặn mã 11 ký tự. */
    const nguon = song.source === "facebook" ? "facebook" : "youtube";
    return {
      id,
      url: nguon === "facebook"
        ? `https://www.facebook.com/watch/?v=${id}`
        : "https://www.youtube.com/watch?v=" + id,
      title: song.title,
      channel: song.artist,
      duration: song.duration_seconds,
      thumbnail: song.thumbnail_url,
      source: nguon,
    };
  }

  /** Khối gợi ý: chip từ khoá, tab nhóm, lưới thẻ có ảnh (học từ card R1).
      Dựng bằng createElement và gắn listener NGAY LÚC TẠO, đúng nếp
      `_renderResults`: card này không vẽ lại toàn bộ giao diện, nên gắn listener
      một lần ở `_bindEvents` là chúng chết sau lần vẽ lại đầu tiên.
      Dùng textContent nên không cần hàm mã hoá HTML như R1 phải làm. */
  /** «layout» và «player_width» trong YAML của chủ máy: bản card1 vốn bỏ qua hai
      khoá này, nên cấu hình đang dùng sẽ âm thầm mất tác dụng nếu không nối vào.
      «horizontal» (mặc định) = lưới 2×2 của «.yt-layout»; «vertical» = một cột.
      «player_width» (20–80) đặt bề rộng cột video. */
  /** Đổi «#rrggbb» thành bộ ba «r,g,b» — mọi màu trong card đều dùng dạng này
      bên trong rgba(), để còn pha độ trong suốt. Màu hỏng thì trả về rỗng và
      card giữ nguyên màu mặc định, không vỡ giao diện. */
  _rgbTriplet(hex) {
    const found = /^#?([0-9a-f]{6})$/i.exec(String(hex || "").trim());
    if (!found) return "";
    const n = parseInt(found[1], 16);
    return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
  }

  /** Diện mạo: màu nền, màu nhấn, độ trong suốt, thu phóng. Đặt biến CSS lên
      chính thẻ card nên mọi chỗ trong giao diện đổi theo, khỏi sửa từng luật. */
  _applyTheme() {
    const host = this.shadowRoot && this.shadowRoot.querySelector("ha-card");
    if (!host) return;
    const config = this._config || {};

    const nen = this._rgbTriplet(config.bg_color);
    if (nen) host.style.setProperty("--ad-c2", nen);
    else host.style.removeProperty("--ad-c2");

    const nhan = this._rgbTriplet(config.accent_color);
    if (nhan) {
      host.style.setProperty("--ad-c1", nhan);
      host.style.setProperty("--ad-accent", `rgb(${nhan})`);
    } else {
      host.style.removeProperty("--ad-c1");
      host.style.removeProperty("--ad-accent");
    }

    /* Chữ nằm TRÊN nền màu nhấn (loa đang chỉnh âm lượng) phải tương phản với
       chính màu đó, nếu không sẽ chìm nghỉm. Màu nhấn sáng thì chữ tối, và
       ngược lại — tính theo độ sáng cảm nhận, không đoán theo mắt. */
    const [r, g, b] = (nhan || "0,204,204").split(",").map(Number);
    const doSang = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    host.style.setProperty("--ad-on-accent", doSang > 0.6 ? "#0b0f17" : "#ffffff");

    /* BỘ MÀU MỞ RỘNG. Nguyên tắc: CHƯA CHỌN thì KHÔNG ĐỤNG GÌ.
       Mỗi màu vừa đặt biến riêng của card (--ad-text…, để các luật CSS đã đổi sang
       biến dùng tới), vừa đặt đè biến giao diện chuẩn của Home Assistant tương ứng.
       Đặt đè như vậy là cách rẻ nhất: card gọi --secondary-text-color 24 lần,
       --divider-color 14 lần, --primary-text-color 9 lần — gán một chỗ là hơn năm
       mươi chỗ đổi theo, khỏi sửa tay từng luật rồi bỏ sót.
       Nhưng CHỈ đặt khi người dùng thật sự chọn màu: khai sẵn trong CSS thì lúc chưa
       chọn, giá trị dự phòng sẽ THAY giá trị của giao diện đang dùng và làm đổi diện
       mạo ngoài ý muốn. */
    const dat = (bien, mau, ...dongBo) => {
      const hex = String(mau || "").trim();
      if (/^#[0-9a-f]{6}$/i.test(hex)) {
        host.style.setProperty(bien, hex);
        for (const ten of dongBo) host.style.setProperty(ten, hex);
      } else {
        host.style.removeProperty(bien);
        for (const ten of dongBo) host.style.removeProperty(ten);
      }
    };
    dat("--ad-text", config.text_color, "--primary-text-color");
    dat("--ad-text-dim", config.text_dim_color, "--secondary-text-color", "--text-muted");
    dat("--ad-danger", config.danger_color);
    dat("--ad-accent2", config.accent2_color);
    dat("--ad-surface", config.surface_color, "--card-background-color", "--secondary-background-color");
    dat("--ad-line", config.line_color, "--divider-color");


    /* Độ đục phải áp cho CẢ lớp chuyển sắc, không riêng lớp màu phẳng. Lớp chuyển
       sắc vẽ ĐÈ lên màu nền và các mốc màu của nó có độ đục cố định sẵn trong CSS
       (0.22 và 0.97); hạ độ đục mà chỉ sửa lớp dưới thì nền dashboard lẫn qua lớp
       trên và cho ra một màu KHÁC HẲN thay vì mờ đi — đó chính là lúc nền chuyển
       thành tím/đỏ. Nên khi ở kiểu chuyển sắc, dựng lại luôn ảnh nền với các mốc
       đã nhân theo mức người dùng chọn. */
    const kieu = String(config.bg_style || "gradient");
    const doDuc = Number(config.opacity);
    const muc = Number.isFinite(doDuc) ? Math.min(100, Math.max(0, doDuc)) / 100 : 1;

    if (kieu === "none") {
      host.style.setProperty("--ad-bg-image", "none");
      host.style.setProperty("--ad-bg-alpha", "0");
    } else if (kieu === "solid") {
      host.style.setProperty("--ad-bg-image", "none");
      host.style.setProperty("--ad-bg-alpha", String((0.97 * muc).toFixed(3)));
    } else {
      const mo = (goc) => (goc * muc).toFixed(3);
      host.style.setProperty(
        "--ad-bg-image",
        `radial-gradient(circle at 94% 2%, rgba(var(--ad-c1,0,204,204), ${mo(0.22)}), transparent 34%), ` +
        `linear-gradient(135deg, rgba(var(--ad-c1,0,204,204), ${mo(0.22)}) 0%, rgba(var(--ad-c2,13,21,37), ${mo(0.97)}) 55%)`);
      host.style.setProperty("--ad-bg-alpha", String((0.97 * muc).toFixed(3)));
    }

    const phong = Number(config.zoom);
    if (Number.isFinite(phong) && phong > 0 && phong !== 100) {
      host.style.setProperty("font-size", `${Math.min(150, Math.max(50, phong))}%`);
    } else {
      host.style.removeProperty("font-size");
    }
  }

  _applyLayout() {
    const grid = this.shadowRoot && this.shadowRoot.querySelector(".yt-layout");
    if (!grid) return;
    // Nút bấm trên card thắng «layout» trong YAML; chưa bấm thì theo YAML. Điện
    // thoại vẫn luôn một cột nhờ media query, không cần đo bề rộng bằng JS.
    const saved = layoutChoice(this._config && this._config.entity);
    const chon = saved || (this._config && this._config.layout) || "";
    const doc = chon === "vertical";
    grid.classList.toggle("yt-layout--doc", doc);
    /* Người dùng CHỌN ngang thì tôn trọng, kể cả khi card hẹp. Luật tự động xếp một
       cột chỉ để giúp lúc chưa ai chọn — nó không được đè lên ý người dùng, vì đó
       đúng là lúc chủ máy thấy "chỉnh ngang mất tác dụng". Chỉ tính là đã chọn khi
       bấm nút trên card, hoặc khai «layout» thật trong cấu hình. */
    const roRang = Boolean(saved) || this._layoutRo === true;
    grid.classList.toggle("yt-layout--ngang", roRang && chon === "horizontal");
    for (const button of this.shadowRoot.querySelectorAll(".layout-pick")) {
      const on = (button.dataset.layout === "vertical") === doc;
      button.classList.toggle("on", on);
      button.setAttribute("aria-pressed", on ? "true" : "false");
    }
    const raw = Number(this._config && this._config.player_width);
    if (!doc && Number.isFinite(raw) && raw > 0) {
      const pct = Math.min(80, Math.max(20, raw));
      grid.style.setProperty("--yt-video-col", pct + "%");
    } else {
      grid.style.removeProperty("--yt-video-col");
    }
  }

  /** Dán link video rồi gắn thẳng vào một mục gợi ý.
      KHÔNG tự bóc link ở đây: gửi nguyên văn vào ĐÚNG đường tìm kiếm sẵn có. Máy chủ
      đã biết đọc link YouTube ở mọi dạng người ta hay dán — đo 19/09/2026: nhận được
      `watch`, `youtu.be`, `shorts`, `embed`, và `watch` kèm tham số playlist (lúc đó
      lấy đúng một bài, không lấy cả playlist). Chép logic bóc link sang thẻ là cùng
      một việc nằm hai nơi, tức hai chỗ phải sửa mỗi lần YouTube đổi dạng link.
      Cùng phép đo đó: link Zing và link Facebook KHÔNG được nhận, nên báo thẳng thay
      vì để người dùng ngồi đoán vì sao không có gì xảy ra. */
  async _ghimTuLink() {
    const link = (window.prompt("Dán link video YouTube hoặc Facebook để gắn vào mục gợi ý:") || "").trim();
    if (!link) return;
    /* Nguồn suy từ CHÍNH cái link, không hỏi thêm một bước: người dán link Facebook
       thì ý đã rõ rồi. Bản trước ghi cứng «source=youtube» nên link Facebook luôn bị
       máy phát đọc bằng bộ giải YouTube rồi trả rỗng — đó là lý do chủ máy báo
       20/09/2026 rằng Facebook chưa có phần lưu link để sau nghe lại. */
    const nguonLink = /facebook\.com|fb\.watch/i.test(link) ? "facebook" : "youtube";
    /* Chỉ mục CỦA NHÀ mới gắn thêm bài được; mục dựng sẵn nằm trong mã nguồn. Ưu tiên
       mục đang mở, không phải mục của nhà thì lấy mục đầu. */
    const mucNha = this._goiY?.groups || [];
    if (!mucNha.length) {
      this._setStatus("Chưa có mục nào để gắn vào — bấm nút hình thư mục để tạo một mục trước.", true);
      return;
    }
    const muc = mucNha.find((nhom) => nhom.id === this._ytSuggestedCategory) || mucNha[0];
    this._setStatus("Đang đọc link…");
    try {
      const entryId = this._entryId();
      if (!entryId) throw new Error("Không tìm thấy config entry. Hãy tải lại integration.");
      const payload = await this._hass.callApi("GET",
        `tritue_youtube_player/search?entry_id=${encodeURIComponent(entryId)}`
        + `&source=${nguonLink}&q=${encodeURIComponent(link)}&limit=1`);
      const bai = Array.isArray(payload.items) ? payload.items[0] : null;
      if (!bai) {
        this._setStatus("Không đọc được link này. Ô này nhận link YouTube và Facebook"
          + " (kể cả link chia sẻ); link Zing thì máy phát chưa có đường đọc link.", true);
        return;
      }
      if ((muc.songs || []).some((daCo) => daCo.id === bai.id)) {
        this._setStatus(`“${bai.title}” đã có sẵn trong mục “${muc.name}”.`);
        return;
      }
      await this._saveSuggestion({
        action: "pin_song",
        id: muc.id,
        item: {
          video_id: bai.id,
          source: nguonLink,
          title: bai.title,
          artist: bai.channel,
          thumbnail_url: bai.thumbnail,
          duration_seconds: bai.duration,
        },
      }, `Đã gắn “${bai.title}” vào mục “${muc.name}”.`);
    } catch (error) {
      this._setStatus(error?.message || "Không đọc được link lúc này.", true);
    }
  }

  _renderSuggestions() {
    const box = this.shadowRoot && this.shadowRoot.querySelector(".yt-suggested-section");
    if (!box) return;
    // Mục dựng sẵn cộng mục của nhà. Mục nhà đứng sau nhưng tìm theo id nên bấm vào
    // đâu cũng đúng; trùng id thì mục nhà thắng vì nó cụ thể hơn.
    /* Đã nạp một lần rồi thì KHO LÀ NGUỒN DUY NHẤT — tuyệt đối không ghép thêm hằng
       số dựng sẵn vào nữa. Còn ghép thì thứ vừa xoá sẽ hiện lại ngay lần vẽ sau và
       việc xoá thành vô nghĩa; đó đúng là lý do bản trước phải bày ra danh sách ẩn.
       Chưa nạp (hoặc chưa gọi được tích hợp) thì mới lấy danh sách dựng sẵn, để card
       không trống trơn lúc mới cài. */
    const daNap = Boolean(this._goiY?.seeded);
    const mucGoiY = daNap ? (this._goiY.groups || []) : YOUTUBE_SUGGESTED_CATEGORIES;
    const tuKhoa = daNap ? (this._goiY.tags || []) : QUICK_SEARCH_TAGS;
    // «?.» bắt buộc: xoá hết mục thì danh sách rỗng, mucGoiY[0] là undefined.
    this._ytSuggestedCategory = this._ytSuggestedCategory || mucGoiY[0]?.id || "";
    /* Khối này KHÔNG đọc gì từ trạng thái nhà — nội dung chỉ phụ thuộc bốn thứ dưới
       đây, còn bài hát thì lấy từ hằng số. Nhưng nó được gọi từ «set hass», tức mỗi
       lần bất kỳ thực thể nào đổi trạng thái: dựng lại vô điều kiện là xoá rồi dựng
       hơn 60 nút (kể cả các thẻ ảnh) để cho ra kết quả y hệt, nhiều lần mỗi giây.
       Hệ quả thấy được: cú vuốt ngang đang dở bị xoá mất nên dải gợi ý khó cuộn. */
    const chuKy = [
      this._ytSuggestedCategory,
      this._results.length ? "1" : "0",
      this._source,
      this._view,
      // BẮT BUỘC có phần này: dữ liệu của nhà về sau lần vẽ đầu, nếu chữ ký không
      // đổi theo thì đúng lúc nhận được từ khoá mới lại là lúc bỏ qua việc vẽ lại.
      this._goiY ? JSON.stringify(this._goiY) : "",
    ].join("|");
    if (chuKy === this._goiYChuKy) return;
    this._goiYChuKy = chuKy;
    box.replaceChildren();
    // Có kết quả rồi thì nhường chỗ; nguồn khác YouTube hoặc đang ở tab Playlist thì gợi ý vô nghĩa.
    if (this._results.length || this._source !== "youtube" || this._view !== "search") return;

    const el = (tag, cls, text) => {
      const node = document.createElement(tag);
      if (cls) node.className = cls;
      if (text !== undefined) node.textContent = text;
      return node;
    };
    const icon = (name) => {
      const i = document.createElement("ha-icon");
      i.setAttribute("icon", name);
      return i;
    };

    const header = el("div", "yt-suggested-header");
    const title = el("div", "yt-suggested-title");
    title.append(icon("mdi:youtube"), el("span", "", "BÀI HÁT GỢI Ý YOUTUBE"));
    header.append(title, el("span", "yt-suggested-subtitle", "Chạm để phát ngay trên loa đã chọn"));

    /* Tự tạo từ khoá và mục của nhà. Dùng window.prompt cho gọn — card này đã dùng
       nó sẵn ở chỗ chia sẻ playlist, nên không đẻ thêm lối nhập liệu thứ hai. Máy
       chủ mới là nơi kiểm dữ liệu; ở đây chỉ chặn chuỗi rỗng. */
    const themNut = (bieuTuong, nhan, chay) => {
      const nut = document.createElement("button");
      nut.type = "button";
      nut.className = "icon-button yt-suggest-add";
      nut.title = nhan;
      nut.setAttribute("aria-label", nhan);
      const bt = document.createElement("ha-icon");
      bt.setAttribute("icon", bieuTuong);
      nut.append(bt);
      nut.addEventListener("click", chay);
      return nut;
    };
    const congCu = el("div", "yt-suggest-tools");
    congCu.append(
      themNut("mdi:tag-plus-outline", "Thêm từ khoá tìm nhanh", () => {
        const text = (window.prompt("Từ khoá mới (ví dụ: Bolero trữ tình):") || "").trim();
        if (text) this._saveSuggestion({ action: "add_tag", text }, `Đã thêm từ khoá “${text}”.`);
      }),
      themNut("mdi:folder-plus-outline", "Thêm mục gợi ý để gắn video", () => {
        const name = (window.prompt("Tên mục mới (ví dụ: Nhạc tối):") || "").trim();
        if (name) this._saveSuggestion({ action: "add_group", name }, `Đã tạo mục “${name}”.`);
      }),
      themNut("mdi:link-plus", "Dán link video để gắn thẳng vào mục", () => this._ghimTuLink()),
    );
    /* Nút thu gọn. Viết thẳng chứ không mượn «themNut» vì còn phải đổi biểu tượng
       mũi tên ngay trong lúc bấm, mà «themNut» giấu phần tử biểu tượng bên trong.
       Bấm chỉ bật/tắt một lớp CSS trên «box», KHÔNG dựng lại khối: dựng lại sẽ xoá
       rồi tạo hơn 60 nút và ảnh chỉ để cho ra đúng nội dung cũ. */
    const dangMo = suggestOpen(this._config.entity);
    const nutThuGon = document.createElement("button");
    nutThuGon.type = "button";
    nutThuGon.className = "icon-button yt-suggest-gap";
    const muiTen = document.createElement("ha-icon");
    const veNut = (mo) => {
      muiTen.setAttribute("icon", mo ? "mdi:chevron-up" : "mdi:chevron-down");
      nutThuGon.title = mo ? "Thu gọn danh sách gợi ý" : "Mở danh sách gợi ý";
      nutThuGon.setAttribute("aria-label", nutThuGon.title);
      nutThuGon.setAttribute("aria-expanded", mo ? "true" : "false");
    };
    veNut(dangMo);
    nutThuGon.append(muiTen);
    nutThuGon.addEventListener("click", () => {
      const mo = box.classList.contains("goi-y-dong");
      box.classList.toggle("goi-y-dong", !mo);
      setSuggestOpen(this._config.entity, mo);
      veNut(mo);
    });
    congCu.append(nutThuGon);
    box.classList.toggle("goi-y-dong", !dangMo);
    header.append(congCu);
    box.append(header);

    /* Thân khối gợi ý (chip từ khoá + chip mục + lưới bài) gom vào MỘT lớp để thu
       gọn được bằng một luật CSS duy nhất. Chủ máy 19/09/2026: "List gợi ý có thể
       xoá và kích mới ra, không đưa hết ra màn". */
    const than = el("div", "yt-goi-y-than");

    /* DANH SÁCH CHIP, mỗi mục có dấu × NGAY BÊN CẠNH — thay cho ô thả xuống kèm một
       nút xoá dùng chung. Hai lý do, đều là lỗi thật đã gặp:
       1. Ô thả xuống mở ra ở dòng gợi ý (giá trị rỗng) nên nút xoá bị khoá; muốn bật
          phải chọn, mà chọn xong thì khối này bị xoá sạch — không bao giờ bấm được.
          Dấu × gắn sẵn từng mục thì bấm được ngay, không cần chọn trước.
       2. Hàng cuộn ngang thì chuột không kéo được. Chip ở đây **xuống dòng**, không
          cuộn, nên mọi mục đều với tới bằng chuột lẫn cảm ứng. */
    const themX = (nhan, chay) => {
      const x = document.createElement("button");
      x.type = "button";
      x.className = "chip-x";
      x.title = nhan;
      x.setAttribute("aria-label", nhan);
      x.append(icon("mdi:close"));
      x.addEventListener("click", (ev) => {
        // Nút nằm trong chip mà chip cũng bấm được — phải chặn nổi bọt.
        ev.preventDefault();
        ev.stopPropagation();
        chay();
      });
      return x;
    };

    const hangTuKhoa = el("div", "yt-quick-search-pills");
    tuKhoa.forEach((tag) => {
      const chip = el("div", "yt-search-pill");
      const ten = document.createElement("button");
      ten.type = "button";
      ten.className = "chip-ten";
      ten.title = `Tìm “${tag}”`;
      ten.append(icon("mdi:magnify"), el("span", "", tag));
      ten.addEventListener("click", () => {
        const input = this.shadowRoot.querySelector('input[type="search"]');
        input.value = tag;
        this._syncSavePlaylist();
        this._search();
      });
      chip.append(ten, themX(`Xoá từ khoá “${tag}”`, () =>
        this._saveSuggestion({ action: "remove_tag", text: tag }, `Đã xoá từ khoá “${tag}”.`)));
      hangTuKhoa.append(chip);
    });
    if (tuKhoa.length) than.append(hangTuKhoa);
    // «mucCuaNha» dùng riêng cho nút gỡ ghim phía dưới: chỉ mục của nhà mới sửa
    // được danh sách bài bên trong.
    const mucCuaNha = (this._goiY?.groups || []).find((g) => g.id === this._ytSuggestedCategory);

    const hangMuc = el("div", "yt-category-tabs");
    mucGoiY.forEach((cat) => {
      const chip = el("div", cat.id === this._ytSuggestedCategory ? "yt-cat-btn active" : "yt-cat-btn");
      const ten = document.createElement("button");
      ten.type = "button";
      ten.className = "chip-ten";
      ten.title = `Xem mục “${cat.name}”`;
      ten.append(icon(cat.icon || "mdi:music"), el("span", "", cat.name));
      ten.addEventListener("click", () => {
        if (this._ytSuggestedCategory === cat.id) return;
        this._ytSuggestedCategory = cat.id;
        this._renderSuggestions();
      });
      chip.append(ten, themX(`Xoá mục “${cat.name}”`, () => {
        if (!window.confirm(`Xoá mục “${cat.name}” khỏi danh sách gợi ý?`)) return;
        if (this._ytSuggestedCategory === cat.id) this._ytSuggestedCategory = "";
        this._saveSuggestion({ action: "remove_group", id: cat.id },
          `Đã xoá mục “${cat.name}”.`);
      }));
      hangMuc.append(chip);
    });
    if (mucGoiY.length) than.append(hangMuc);

    const found = mucGoiY.find((c) => c.id === this._ytSuggestedCategory);
    // Xoá hết mục thì không còn gì để lấy — cho một mục rỗng để khỏi nổ ở current.songs.
    const current = found || mucGoiY[0] || { songs: [] };
    const grid = el("div", "yt-song-grid");
    (current.songs || []).forEach((song) => {
      const card = el("div", "yt-song-card");
      card.setAttribute("role", "button");
      card.tabIndex = 0;
      card.title = "Bấm để phát: " + song.title;
      const wrap = el("div", "yt-card-thumb-wrap");
      const img = document.createElement("img");
      img.className = "yt-card-thumb";
      img.alt = "";
      img.loading = "lazy";
      if (/^https?:\/\//.test(song.thumbnail_url || "")) img.src = song.thumbnail_url;
      const overlay = el("div", "yt-play-overlay");
      overlay.append(icon("mdi:play"));
      wrap.append(img, overlay, el("span", "yt-card-duration", this._formatDuration(song.duration_seconds)));
      const info = el("div", "yt-card-info");
      info.append(el("div", "yt-card-title", song.title), el("div", "yt-card-artist", song.artist));
      /* Gỡ ghim — chỉ hiện ở mục của nhà. Mục dựng sẵn nằm trong mã, không gỡ được;
         gọi lên máy chủ sẽ bị từ chối vì không tìm thấy mục. */
      if (mucCuaNha) {
        const goGhim = document.createElement("button");
        goGhim.type = "button";
        goGhim.className = "yt-card-unpin";
        goGhim.title = `Gỡ “${song.title}” khỏi mục “${mucCuaNha.name}”`;
        goGhim.setAttribute("aria-label", goGhim.title);
        const goIcon = document.createElement("ha-icon");
        goIcon.setAttribute("icon", "mdi:close");
        goGhim.append(goIcon);
        goGhim.addEventListener("click", (ev) => {
          // Nút nằm TRONG thẻ bài hát, thẻ này bấm là phát — phải chặn nổi bọt.
          ev.preventDefault();
          ev.stopPropagation();
          this._saveSuggestion(
            { action: "unpin_song", id: mucCuaNha.id, video_id: song.id || song.video_id },
            `Đã gỡ “${song.title}” khỏi mục “${mucCuaNha.name}”.`);
        });
        wrap.append(goGhim);
      }
      card.append(wrap, info);
      const play = () => this._playResult(this._ytSongToItem(song), card, -1, true);
      card.addEventListener("click", play);
      card.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); play(); }
      });
      grid.append(card);
    });
    than.append(grid);
    box.append(than);
  }

  /** Chọn xong một bài thì THU GỌN danh sách kết quả; bấm thanh tóm tắt để mở lại.
   *
   * Chủ máy yêu cầu 20/09/2026: "sau khi tìm kiếm mà chọn phát 1 bài xong thì ẩn
   * phần danh sách tìm kiếm đi, sau đó muốn thay đổi bài thì kích vào".
   * Danh sách KHÔNG bị xoá — nó vẫn là hàng chờ phát tiếp, chỉ thôi chiếm màn hình.
   */
  _thuGonKetQua(item) {
    if (!this._results.length) return;
    this._ketQuaThuGon = true;
    this._tenDaChon = String(item?.title || item?.id || "");
    this._syncKetQuaThuGon();
  }

  _syncKetQuaThuGon() {
    const results = this.shadowRoot?.querySelector(".results");
    const toggle = this.shadowRoot?.querySelector(".results-toggle");
    if (!results || !toggle) return;
    const dem = this._results.length;
    const thuGon = Boolean(this._ketQuaThuGon) && dem > 0;
    results.hidden = thuGon;
    toggle.hidden = !dem;
    toggle.setAttribute("aria-expanded", String(!thuGon));
    toggle.querySelector(".results-toggle-text").textContent = thuGon
      ? (this._tenDaChon
        ? `Đã chọn “${this._tenDaChon}” — bấm để đổi bài (${dem} kết quả)`
        : `Xem ${dem} kết quả tìm kiếm`)
      : `Ẩn ${dem} kết quả tìm kiếm`;
    toggle.querySelector("ha-icon").setAttribute("icon", thuGon ? "mdi:chevron-down" : "mdi:chevron-up");
  }

  _renderResults() {
    const container = this.shadowRoot.querySelector(".results");
    container.replaceChildren();
    if (this._results.some((item) => this._isVideoItem(item, item.source || this._source))) this._warmFrame();
    /* LẤY SẴN ĐỊA CHỈ LUỒNG cho vài bài đầu — điều kiện bắt buộc để iOS chịu phát.
       Apple: "no data is loaded until the user initiates it", nên lượt tải phải nằm
       TRONG cú chạm; mà hỏi máy chủ mất 1,5–2,6 giây thì cú chạm đã trôi qua từ lâu.
       Có sẵn thì «deviceAudio.listen» dựng phần tử ngay, không chờ gì.
       Chỉ ba bài đầu: đủ cho thao tác thường gặp mà không nã máy chủ cả trang. */
    deviceAudio.entryId = this._entryId();
    /* Lấy sẵn cho CẢ bài video, đừng lọc ra. Bài video vẫn có nút "Nghe trên máy
       này" — mà đó đúng là đường hay bị chờ nhất, vì người dùng đang xem rồi mới
       chuyển sang nghe. Lọc chúng ra là bỏ sót đúng ca cần nhất. */
    this._results.slice(0, 3)
      .forEach((item) => deviceAudio.chuanBi({ ...item, source: item.source || this._source }));
    // Gợi ý hiện khi chưa có kết quả, tự ẩn khi có — xem `_renderSuggestions`.
    this._renderSuggestions();
    this._results.forEach((item, index) => {
      const row = document.createElement("article");
      row.className = "result";
      const image = document.createElement("img");
      image.className = "cover";
      image.alt = "";
      image.loading = "lazy";
      if (/^https?:\/\//.test(item.thumbnail || "")) image.src = item.thumbnail;
      const track = document.createElement("div");
      track.className = "track";
      const title = document.createElement("div");
      title.className = "track-title";
      title.textContent = item.title || item.id || "Không rõ tên";
      const meta = document.createElement("div");
      meta.className = "track-meta";
      const duration = this._formatDuration(item.duration);
      meta.textContent = [item.channel, duration].filter(Boolean).join(" · ");
      track.append(title, meta);
      // Two buttons, as on c2a: watch the video and listen (sound only). With speakers
      // ticked both play on them (watching adds the muted picture here); without,
      // this device plays it.
      const actions = document.createElement("div");
      actions.className = "result-actions";
      const action = (icon, label, watch) => {
        const button = document.createElement("button");
        button.className = watch ? "play-result" : "play-result listen";
        button.type = "button";
        button.title = `${label}: ${title.textContent}`;
        button.setAttribute("aria-label", button.title);
        const buttonIcon = document.createElement("ha-icon");
        buttonIcon.setAttribute("icon", icon);
        button.append(buttonIcon);
        button.addEventListener("click", () => this._playResult(item, button, index, watch));
        actions.append(button);
      };
      if ((item.source || this._source) !== "http") {
        const add = document.createElement("button");
        add.type = "button";
        add.className = "icon-button add-playlist";
        add.title = `Thêm “${title.textContent}” vào playlist`;
        add.setAttribute("aria-label", add.title);
        const addIcon = document.createElement("ha-icon");
        addIcon.setAttribute("icon", "mdi:playlist-plus");
        add.append(addIcon);
        add.addEventListener("click", () => this._toggleAddMenu(row, { ...item, source: item.source || this._source }));
        actions.append(add);
        /* Bấm ghim thì MỞ BẢNG CHỌN MỤC ngay tại dòng bài hát, chứ không ghim thẳng.
           Trước đây nút này dùng mục đã chọn sẵn bên khu gợi ý, mà khu đó biến mất
           ngay khi có kết quả tìm — nên đúng lúc bấm thì không nhìn thấy đích đến,
           cũng không đổi được; chưa chọn gì thì bài rơi âm thầm vào mục ĐẦU TIÊN, và
           tên mục chỉ nằm trong thuộc tính title, thứ điện thoại không hiện ra.
           Điều kiện «nhà đã có mục» cũng bỏ luôn: bảng chọn tạo được mục mới tại chỗ,
           nên không còn cảnh chưa có mục nào thì nút ghim không thèm hiện. */
        // Facebook ghim được y như YouTube — bản ghi mang theo nguồn nên phát lại
        // vẫn đi đúng đường. Zing thì chưa, vì máy phát chưa có đường đọc link Zing.
        if (["youtube", "facebook"].includes(item.source || this._source)) {
          const ghim = document.createElement("button");
          ghim.type = "button";
          ghim.className = "icon-button pin-suggestion";
          ghim.title = `Gắn “${title.textContent}” vào một mục gợi ý`;
          ghim.setAttribute("aria-label", ghim.title);
          const ghimIcon = document.createElement("ha-icon");
          ghimIcon.setAttribute("icon", "mdi:pin-outline");
          ghim.append(ghimIcon);
          ghim.addEventListener("click", () => this._toggleGhimMenu(row, item, title.textContent));
          actions.append(ghim);
        }
      }
      if (this._isVideoItem(item, item.source || this._source)) action("mdi:television-play", "Xem video", true);
      action("mdi:headphones", "Nghe (chỉ tiếng)", false);
      row.append(image, track, actions);
      container.append(row);
    });
    // Kết quả MỚI thì luôn mở ra — người vừa tìm là đang muốn nhìn danh sách.
    this._ketQuaThuGon = false;
    this._tenDaChon = "";
    this._syncKetQuaThuGon();
  }

  /** Xem video Facebook ngay trên thẻ.
   *
   * KHÁC hẳn đường YouTube: Facebook không cho nhúng trình phát, nên thẻ xin máy phát
   * một địa chỉ luồng rồi chiếu thẳng vào phần tử «<video>» sẵn có («_tryPicture»).
   * Vì thế KHÔNG gọi «_openVideo» — hàm đó dựng khung nhúng và chặn cứng mã không
   * phải 11 ký tự kiểu YouTube.
   *
   * Tiếng đi ĐƯỜNG RIÊNG, đúng yêu cầu "nghe và xem tách riêng": ra loa nếu có chọn
   * loa, hoặc qua bộ phát tiếng của máy này. Phần tử hình luôn tắt tiếng — giống hệt
   * đường hình của YouTube khi bị từ chối nhúng, nên không đẻ thêm lối phát tiếng
   * thứ hai để rồi chồng tiếng.
   */
  async _xemFacebook(item, { withSpeakers, followsDevice = false }) {
    const id = String(item?.id || "");
    if (!FB_VIDEO_ID.test(id)) {
      this._setStatus("Link Facebook này không có mã video.", true);
      return;
    }
    if (this._video.picture) this._leavePicture();
    const frame = this.shadowRoot.querySelector(".video-frame");
    frame.hidden = false;
    // «no-embed» cho khung nền đen; KHÔNG đặt «--poster» vì đó là ảnh của YouTube.
    frame.classList.add("no-embed");
    const pending = { item };
    /* Khung hình Facebook LUÔN câm: phần tử <video> mà «_tryPicture» dựng ra đặt
       muted = true. Không có loa thì phải có người phát tiếng, nếu không thẻ chạy
       hình câm — đúng lỗi "mặc định tắt tiếng" trên iPhone, nơi tuỳ chọn "nghe khi
       tắt màn hình" mặc định TẮT nên đây chính là đường mặc định.
       KHÔNG đẻ nhánh tiếng riêng cho Facebook: dùng lại đúng kiến trúc YouTube vẫn
       dùng khi khung nhúng không phát được tiếng (xem «_embedRefused») — máy này
       phát tiếng, hình câm bám theo. Cờ bám-tiếng còn tắt luôn nhánh tự chuyển bài
       trong «_setVideoState» (nhánh ấy chỉ chạy khi KHÔNG loa và KHÔNG bám tiếng),
       vốn biến một lần hình kết thúc sớm thành vòng mở lại bài từ giây 0. */
    const theoTieng = followsDevice || !withSpeakers;
    this._video = {
      ...this._idleVideo(),
      open: true,
      item: {
        id,
        title: String(item.title || id),
        channel: String(item.channel || ""),
        duration: Number(item.duration || 0),
        url: String(item.url || `https://www.facebook.com/watch/?v=${id}`),
        thumbnail: String(item.thumbnail || ""),
        source: "facebook",
      },
      withSpeakers,
      followsDevice: theoTieng,
      soundHere: false,
      picture: pending,
      moUL: Date.now(),
    };
    /* Chỉ gọi SAU khi «this._video» đã là bài mới: «listen» báo ngay cho bên nghe,
       mà «_deviceAudioChanged» so mã bài của tiếng với mã bài của hình — gọi trước
       thì hai mã lệch nhau và nó mở lại video. Người gọi đã bật tiếng sẵn
       (followsDevice) thì không phát lại từ đầu. */
    if (theoTieng && !followsDevice) {
      const mucTieng = { ...item, id, source: "facebook" };
      deviceAudio.entryId = this._entryId();
      deviceAudio.listen(mucTieng, this._queue.length ? this._queue : [mucTieng], Math.max(0, this._queueIndex));
    }
    this._pictureNote("Đang lấy hình…");
    this._syncNowPlaying();
    this._updateTransportState();
    let info = null;
    try {
      info = await this._hass.callApi("POST", "tritue_youtube_player/stream", {
        entry_id: this._entryId(),
        source: "facebook_video",
        target: item.url || id,
        max_height: this._pictureHeight(),
      });
    } catch (_error) {
      info = null;
    }
    // Người dùng đã bỏ đi hoặc mở bài khác trong lúc chờ.
    if (this._video.picture !== pending) return;
    if (!info?.stream_url) {
      this._pictureNote("Không lấy được hình của video này");
      this._setStatus("Không lấy được hình video Facebook — vẫn nghe được tiếng.", true);
      return;
    }
    const mo = await this._tryPicture(info.stream_url, pending, 20000);
    if (this._video.picture !== pending) return;
    if (!mo) {
      this._pictureNote("Không mở được hình");
      return;
    }
    this._pictureNote("");
    if (!this._videoTimer) this._videoTimer = setInterval(() => this._syncVideo(), 2000);
  }

  _watchCurrent() {
    if (!this._nowWatchItem) return;
    /* ĐANG CHỈ NGHE BẰNG KHUNG: bấm Xem chỉ là bung khung ấy ra, KHÔNG dựng lại.
       Dựng lại là xoá quyền phát và nhạc đứng im — xem «_ngheBangKhungMotMinh». */
    if (this._video.open && this._video.soundOnly && !this._video.withSpeakers) {
      this._daHienKhungDeCham = true;
      this._video.soundOnly = false;
      clearInterval(this._henThuKhung);
      this._syncNowPlaying();
      return;
    }
    if (deviceAudio.item) {
      // Listening here: the sound keeps playing and the muted picture opens at the
      // second being heard, then follows it.
      this._queue = deviceAudio.queue;
      this._queueIndex = deviceAudio.index;
      this._openVideo(deviceAudio.item, {
        withSpeakers: false,
        followsDevice: true,
        startSeconds: deviceAudio.position()?.time || 0,
      });
      return;
    }
    // Already playing on the speakers: keep their sound, show the picture here muted.
    this._openVideo(this._nowWatchItem, { withSpeakers: this._activeSpeakers().length > 0 });
  }

  /** Watching → listening only: the picture closes, the sound goes on from the same second. */
  _listenOnly() {
    const video = this._video;
    if (!video.open || !video.item) return;
    if (video.withSpeakers || video.followsDevice) {
      // The speakers or this device already carry the sound: only the picture goes.
      const speakers = video.withSpeakers;
      this._closeVideo();
      this._setStatus(speakers ? "Đã tắt hình, loa vẫn phát." : "Đã tắt hình, đang nghe trên máy này.");
      return;
    }
    const item = { source: "youtube", ...video.item };
    const at = this._videoTimeNow();
    deviceAudio.entryId = this._entryId();
    // Inside the tap, before the picture goes: the audio element is unlocked here.
    deviceAudio.listen(item, this._queue.length ? this._queue : [item], Math.max(0, this._queueIndex), at);
    this._closeVideo();
    this._setStatus(`Đang nghe “${item.title}” trên máy này từ ${this._formatDuration(at) || "0:00"}.`);
  }

  /** Same song (by id or link). */
  _sameSong(left, right) {
    return !!left && !!right && ((left.url || left.id) === (right.url || right.id) || (!!left.id && left.id === right.id));
  }

  _openVideo(item, { withSpeakers, followsDevice = false, startSeconds = 0, soundHere = null, soundOnly = false }) {
    /* MỘT CỬA VÀO duy nhất cho việc mở hình. Nguồn Facebook rẽ ngay tại đây, KHÔNG vá
       ở từng chỗ gọi: hàm này được gọi từ sáu nơi (hàng kết quả, hàng đợi, nút xem,
       khôi phục phiên…), sửa theo danh sách thì sót một nơi là bấm vào đó hỏng, mà
       lỗi lại hiện ra ở chỗ khác hẳn.
       Facebook không cho nhúng trình phát nên đi đường chiếu thẳng luồng; xem
       «_xemFacebook». Rẽ trước cả dòng chặn bên dưới, nên dòng ấy giữ nguyên ý nghĩa
       cũ: nó chỉ còn nói về đường NHÚNG. */
    const nguonMuc = item?.source || this._source;
    if (nguonMuc === "facebook") {
      /* GỠ HẲN KHUNG CŨ TRƯỚC. «_xemFacebook» dựng lại trạng thái video và dùng lại
         chính ô «.video-frame», nhưng KHÔNG gỡ thẻ khung YouTube đang nằm trong đó —
         nên YouTube hát tiếp bên dưới hình Facebook. Người dùng báo 21/09/2026: "khi
         đang nghe youtube mà mở face thì tiếng vẫn còn". Trên iOS lỗi này nặng hơn vì
         từ 0.26.50 tiếng của máy nằm HẲN trong khung, không còn ở phần tử âm thanh. */
      if (this._video.open) this._closeVideo();
      this._xemFacebook(item, { withSpeakers, followsDevice });
      return;
    }
    const id = String(item?.id || "");
    if (!VIDEO_ID.test(id)) {
      this._setStatus("Chỉ xem được video YouTube trên thẻ.", true);
      return;
    }
    const frame = this.shadowRoot.querySelector(".video-frame");
    // A picture shown for a refused video: try the embed again for this one.
    if (this._video.picture) this._leavePicture();
    /* XOÁ MỐC THỜI GIAN CỦA BÀI TRƯỚC. Thiếu dòng này là sinh ra đúng lỗi chủ máy
       báo 18/09/2026: "Lần đầu phát bị về 0s mất 2, 3 lần" — bài mới thừa hưởng mốc
       của bài cũ, «_videoTimeNow()» suy ra một con số lớn, trong khi trình phát mới
       báo về gần 0; bộ dò tự-tua thấy lệch quá ngưỡng liền hiểu nhầm là người dùng
       vừa tua về 0 rồi gửi lệnh nhảy về 0 cho cả loa lẫn tiếng trên máy.
       «moUL» ghi lúc mở để biết trình phát còn đang khởi động hay đã chạy ổn định. */
    this._video.time = 0;
    this._video.timeAt = 0;
    this._video.moUL = Date.now();
    let iframe = frame.querySelector("iframe");
    this._video.item = {
      id,
      title: String(item.title || id),
      channel: String(item.channel || ""),
      duration: Number(item.duration || 0),
      url: String(item.url || `https://www.youtube.com/watch?v=${id}`),
      thumbnail: String(item.thumbnail || ""),
    };
    if (withSpeakers && !this._video.withSpeakers) this._video.soundHere = false;
    if (!withSpeakers) this._video.soundHere = true;
    this._video.withSpeakers = withSpeakers;
    // Following this device's audio element (screen-off listening): the picture stays muted.
    this._video.followsDevice = followsDevice;
    if (followsDevice) this._video.soundHere = false;
    /* NGƯỜI GỌI NÓI RÕ THÌ LỜI ẤY THẮNG. Hai dòng suy đoán bên trên chỉ đúng cho
       đường xem video; đường «nghe trên máy này bằng khung» cần khung CÓ TIẾNG dù
       loa đang phát, nên phải nói thẳng ra được. «soundOnly» giữ khung ở dạng thu
       bé một điểm ảnh: có tiếng mà thẻ trông y như lúc chưa mở hình. */
    if (soundHere !== null) this._video.soundHere = Boolean(soundHere);
    this._video.soundOnly = Boolean(soundOnly) && this._video.soundHere;
    const start = Math.max(0, Math.floor(Number(startSeconds) || 0));
    /* Đường nhanh (đổi bài trong cùng trình phát) giữ được toàn màn hình, nhưng
       CHỈ dùng khi không phải bật tiếng cho một khung đang câm: động tác ấy làm
       trình duyệt dừng video, xem «_batTiengKhung» để biết vì sao. */
    const phaiBatTieng = this._video.soundHere && this._video.muted !== false;
    if (iframe && this._video.ready && !phaiBatTieng) {
      // Same player: switch video without reloading, so fullscreen and mute stay put.
      this._videoCommand("loadVideoById", [{ videoId: id, startSeconds: start }]);
      if (!this._video.soundHere) this._videoCommand("mute");
    } else {
      if (!iframe) {
        iframe = document.createElement("iframe");
        // Home Assistant sends "Referrer-Policy: no-referrer", and YouTube refuses
        // embeds without a Referer ("Error 153 — Video player configuration error").
        // The iframe's own policy overrides the page's; it must be set before src.
        iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
        iframe.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen");
        iframe.setAttribute("allowfullscreen", "");
        iframe.title = "Video YouTube";
        iframe.addEventListener("load", () => this._frameLoaded());
        const hint = document.createElement("div");
        hint.className = "sound-hint";
        hint.hidden = true;
        frame.append(iframe, hint);
      }
      this._video.ready = false;
      // enablejsapi + origin let the card drive the player over postMessage.
      /* cc_load_policy=0: phụ đề TẮT mặc định. iv_load_policy=3: tắt chú thích nổi.
         Hai thứ KHÔNG làm được, nói thẳng để khỏi hứa suông: YouTube đã bỏ tác dụng
         của «modestbranding» nên logo vẫn còn, và không cho đặt độ phân giải qua
         khung nhúng — người xem tự chọn ở nút bánh răng của trình phát. */
      this._video.muted = null;
      iframe.setAttribute("src", this._ytEmbedSrc(id, { muted: !this._video.soundHere, start }));
    }
    this._video.open = true;
    this._video.state = -1;
    this._soundHintShown = false;
    clearTimeout(this._soundCheckTimer);
    if (this._video.soundHere) {
      this._thucTiengKhung();
      // Khung chỉ mang tiếng: canh tới lúc có câu trả lời dứt khoát, đừng hỏi một lần.
      if (this._video.soundOnly) this._canhKhungChiTieng();
      else this._soundCheckTimer = setTimeout(() => this._checkVideoSound(), 2500);
    }
    window.addEventListener("message", this._onVideoMessage);
    if (!this._videoTimer) this._videoTimer = setInterval(() => this._syncVideo(), 2000);
    this._syncNowPlaying();
    this._updateTransportState();
    const player = this.shadowRoot.querySelector(".player");
    // Khung chỉ mang tiếng thì không có gì để nhìn, đừng kéo màn hình của người dùng.
    if (!this._video.soundOnly && !player.classList.contains("expanded")) {
      player.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    }
  }

  /** Địa chỉ khung nhúng — một chỗ duy nhất, để mọi đường dựng khung giống nhau. */
  _ytEmbedSrc(id, { muted = false, start = 0 } = {}) {
    /* cc_load_policy=0: phụ đề TẮT mặc định. iv_load_policy=3: tắt chú thích nổi.
       Hai thứ KHÔNG làm được, nói thẳng để khỏi hứa suông: YouTube đã bỏ tác dụng
       của «modestbranding» nên logo vẫn còn, và không cho đặt độ phân giải qua
       khung nhúng — người xem tự chọn ở nút bánh răng của trình phát.
       enablejsapi + origin để thẻ điều khiển được trình phát qua postMessage. */
    const params = new URLSearchParams({
      enablejsapi: "1",
      autoplay: "1",
      rel: "0",
      playsinline: "1",
      cc_load_policy: "0",
      iv_load_policy: "3",
      origin: location.origin,
    });
    if (muted) params.set("mute", "1");
    if (start) params.set("start", String(Math.max(0, Math.floor(start))));
    return `${EMBED_ORIGIN}/embed/${id}?${params}`;
  }

  /** THÚC TIẾNG SAU KHI KHUNG VỪA NẠP — bậc thang 0 / 300 / 800 / 2000 mili giây.
   *
   * Chép từ thẻ «phicomm-r1-card» chủ máy đưa ngày 20/09/2026 (dòng 1904-1908 của
   * thẻ ấy), kèm lời xác nhận của chủ máy rằng thẻ ấy nghe nhạc và xem video trên
   * iPhone đều bình thường. Vì sao phải gửi bốn lần: giao diện lập trình của trình
   * phát YouTube chưa nhận lệnh ngay lúc khung vừa nạp, nên gửi đúng một lần thì
   * rơi vào khoảng chưa ai nghe. Đây là chỗ chữa lời chủ máy "trên iPhone phải tự
   * bật biểu tượng loa mới nghe được, mặc định tắt tiếng".
   *
   * Khác với «unMute» trong «_batTiengKhung» ở chỗ nào: ở đây khung sinh ra vốn đã
   * KHÔNG có tham số «mute», nên đây không phải động tác câm-rồi-bật; ta chỉ đang
   * gỡ cái câm mà chính YouTube tự đặt để được phép tự phát trên điện thoại.
   */
  _thucTiengKhung() {
    this._dungThucTieng();
    const thuc = () => {
      const video = this._video;
      if (!video.open || !video.soundHere || video.pictureEl) return;
      this._videoCommand("unMute");
      this._videoCommand("setVolume", [100]);
    };
    thuc();
    this._thucTiengTimers = [300, 800, 2000].map((cho) => setTimeout(thuc, cho));
  }

  _dungThucTieng() {
    (this._thucTiengTimers || []).forEach((id) => clearTimeout(id));
    this._thucTiengTimers = [];
  }

  /** BẬT TIẾNG CHO KHUNG — dựng lại khung, KHÔNG gửi lệnh «unMute».
   *
   * Cú bấm của người dùng nằm ở trang THẺ, còn trình phát nằm trong khung
   * «youtube.com» khác miền. Lệnh «unMute» đi qua postMessage nên cử chỉ ấy không
   * đi theo: với trình duyệt, một video đang tự phát ở chế độ câm bỗng bật tiếng
   * mà không ai chạm vào nó — và cách nó xử là TẠM DỪNG video.
   *
   * Chủ máy đo được đúng chuyện này trên Android ngày 20/09/2026: "nghe trên máy
   * này mà đang phát ra loa thì bị dừng video, nhưng chọn cả nghe khi tắt màn hình
   * thì không sao". Hai nhánh ấy chỉ khác một điều: nhánh tắt-màn-hình để khung
   * câm nguyên và cho phần tử âm thanh mang tiếng, còn nhánh kia gửi «unMute».
   *
   * Thẻ «phicomm-r1-card» chạy được trên cả Android lẫn iPhone vì nó KHÔNG BAO GIỜ
   * làm động tác câm-rồi-bật: khung của nó sinh ra đã có tiếng sẵn, địa chỉ nhúng
   * không hề có tham số «mute» (dòng 1896 của thẻ ấy).
   *
   * Nên ở đây ta dựng lại khung bằng địa chỉ không có «mute», kèm «start» ở đúng
   * giây đang xem. Khung mới nạp ngay trong cú bấm nên được quyền phát kèm tiếng.
   */
  _batTiengKhung() {
    const video = this._video;
    video.soundHere = true;
    // Hình của chính thẻ (thẻ «video» của ta) thì không dính luật của khung nhúng.
    if (video.pictureEl) return;
    if (video.muted === false) {
      // Khung đang có tiếng sẵn: nạp lại chỉ tổ mất toàn màn hình và mất mấy giây.
      this._videoCommand("playVideo");
      return;
    }
    const iframe = this.shadowRoot?.querySelector(".video-frame iframe");
    const id = video.item?.id;
    if (!iframe || !id) return;
    const giay = Math.max(0, Math.floor(this._videoTimeNow() || 0));
    video.ready = false;
    video.muted = null;
    video.time = giay;
    video.timeAt = 0;
    video.moUL = Date.now();
    iframe.setAttribute("src", this._ytEmbedSrc(id, { muted: false, start: giay }));
    this._thucTiengKhung();
  }

  /** NGHE MỘT MÌNH BẰNG KHUNG (máy nhà Táo) — dùng chung cho mọi lối vào.
   *
   *  Trả về «true» nghĩa là đã nhận việc, bên gọi đừng đụng tới phần tử âm thanh nữa.
   */
  _ngheBangKhungMotMinh(item, queue, index, batDau = 0) {
    if (!item || deviceAudio.laTrucTiep(item)) return false;
    if (Array.isArray(queue) && queue.length) {
      this._queue = queue;
      this._queueIndex = Math.max(0, Number(index) || 0);
    }
    /* ĐANG MỞ ĐÚNG BÀI ẤY RỒI THÌ ĐỪNG MỞ LẠI.
       Dựng lại khung là XOÁ LUÔN quyền phát mà cú chạm vừa cấp, nên trình phát tụt
       về «chưa bắt đầu» và không bao giờ chạy. Hộp đen iPhone chủ máy 21/09/2026 bắt
       được nhiều cặp mở hai lần cách nhau chưa tới một giây — 21:06:30 hai lần,
       21:08:15 rồi 21:08:16, 21:06:39 rồi 21:06:40 — và gần như lần nào cũng kết thúc
       ở «trangthai=-1» vĩnh viễn. Đó là lý do lúc chạy lúc không, rất ngẫu nhiên.
       Hàm này có HAI lối gọi (nhánh «bấm chỉ nghe» và cửa chặn trong
       «deviceAudio.listen»), nên phải tự bảo vệ chứ không đi sửa từng lối. */
    const dangMo = this._video;
    if (dangMo.open && dangMo.soundHere && !dangMo.withSpeakers
      && String(dangMo.item?.id || "") === String(item.id || "")) {
      return true;
    }
    /* MỞ ẨN SẴN. Chủ máy chốt 21/09/2026: "kích tai nghe lại ra video… tôi cần
       không báo gì, chỉ cần chạy thôi, kích là chạy". Địa chỉ khung được gán NGAY
       TRONG cú bấm kèm «autoplay=1», nên phần lớn trường hợp nó tự chạy mà không cần
       ai chạm — hộp đen 21:04:10 và 21:08:27 đều lên «trangthai=1» sau đúng một giây.
       Chỉ khi quá 2,5 giây vẫn nằm im thì mới hiện khung ra để còn chạm được; xem
       «_thuKhungKhiDaChay». */
    this._daHienKhungDeCham = false;
    this._openVideo(item, {
      withSpeakers: false,
      soundHere: true,
      soundOnly: true,
      startSeconds: Math.max(0, Math.floor(Number(batDau) || 0)),
    });
    /* DÒNG IM LẶNG GIỮ NỀN CHỈ ĐƯỢC CHẠY SAU KHI KHUNG ĐÃ PHÁT.
       iOS chỉ cho MỘT luồng chạy một lúc. Bật trước là nó giành mất chỗ của khung,
       và khung không bao giờ khởi động. Hộp đen trên iPhone chủ máy 21/09/2026 bắt
       đúng tương quan ấy:
         21:04:09 (chưa bật giữ nền)      → trangthai 1 sau một giây, nhạc chạy
         21:04:15 bật nghe-khi-tắt-màn
         21:05:02 và 21:05:22 (đã bật)    → trangthai=-1 suốt 8 giây, không chạy
       Nên việc giữ nền chuyển sang «_thuKhungKhiDaChay», đúng nhịp trình phát báo
       đang chạy. */
    this._hopDenKhungTheoDoi("nghe một mình bằng khung (nhà Táo)");
    this._thuKhungKhiDaChay();
    return true;
  }

  /** THU KHUNG LẠI KHI NÓ ĐÃ THẬT SỰ CHẠY — và bung ra nếu thu xong bị tắt tiếng.
   *
   *  Chỉ thu khi trình phát báo «đang chạy» (mã 1), vì lúc chưa chạy thì thu bé là
   *  giết luôn cơ hội chạm. Thu xong còn kiểm lại một nhịp: nếu WebKit dừng vì phần
   *  tử không còn nhìn thấy thì trả khung về như cũ, thà thấy video còn hơn mất tiếng.
   */
  _thuKhungKhiDaChay() {
    clearInterval(this._henThuKhung);
    const batDau = Date.now();
    this._henThuKhung = setInterval(() => {
      const v = this._video;
      if (!v.open || v.soundOnly) {
        clearInterval(this._henThuKhung);
        return;
      }
      if (Date.now() - batDau > 90000) {
        clearInterval(this._henThuKhung);
        return;
      }
      if (v.state !== 1) {
        /* QUÁ 2,5 GIÂY VẪN KHÔNG CHẠY thì hiện khung ra — đó là lúc iOS đòi một cú
           chạm vào chính video, mà khung ẩn thì không ai chạm được. Chạy được thì
           người dùng không thấy gì cả, đúng ý "kích là chạy, không báo gì". */
        if (v.soundOnly && Date.now() - batDau > 2500 && !this._daHienKhungDeCham) {
          this._daHienKhungDeCham = true;
          v.soundOnly = false;
          this._syncNowPlaying();
          this._setStatus("Chạm một lần vào video để bắt đầu.");
          deviceAudio.hass = this._hass;
          deviceAudio.ghiThang(`khung không tự chạy sau 2,5s, hiện ra để chạm — trangthai=${v.state}`);
        }
        return;
      }
      clearInterval(this._henThuKhung);
      this._daHienKhungDeCham = false;
      v.soundOnly = true;
      this._syncNowPlaying();
      // Giờ khung đã phát thì mới được thêm dòng im lặng giữ nền (xem lý do ở
      // «_ngheBangKhungMotMinh»).
      if (listenScreenOff()) this._giuTiengNen();
      deviceAudio.hass = this._hass;
      deviceAudio.ghiThang("thu khung lại sau khi đã chạy");
      setTimeout(() => {
        if (!this._video.open) return;
        if (this._video.state === 1) {
          this._setStatus("Đang nghe trên máy này.");
          deviceAudio.ghiThang(`thu khung xong, vẫn chạy — trangthai=${this._video.state}`);
          return;
        }
        this._video.soundOnly = false;
        this._syncNowPlaying();
        deviceAudio.ghiThang(`thu khung xong thì TẮT — trangthai=${this._video.state}, bung lại`);
        this._setStatus("Máy này cần thấy video mới giữ được tiếng — để nguyên khung nhé.");
      }, 2500);
    }, 500);
  }

  /** HỘP ĐEN CHO ĐƯỜNG KHUNG — cùng bốn mốc như đường phần tử âm thanh.
   *
   *  «trangthai» là mã của trình phát YouTube: -1 chưa bắt đầu, 0 hết bài, 1 đang
   *  chạy, 2 tạm dừng, 3 đang nạp, 5 đã nạp sẵn chờ lệnh. Chủ máy 21/09/2026: "không
   *  tự động phát video nhỉ, phải kích vào" — nếu đúng thì ở đây sẽ thấy «trangthai»
   *  đứng ở -1 hoặc 5 mà không bao giờ sang 1.
   */
  _hopDenKhungTheoDoi(nhan) {
    (this._hopDenKhungTimers || []).forEach((id) => clearTimeout(id));
    const ghi = (moc) => {
      const v = this._video;
      deviceAudio.hass = this._hass;
      deviceAudio.ghiThang(`${nhan} ${moc} — mo=${v.open ? 1 : 0} chitieng=${v.soundOnly ? 1 : 0}`
        + ` san=${v.ready ? 1 : 0} trangthai=${v.state} giay=${Number(v.time || 0).toFixed(1)}`);
    };
    ghi("(ngay lúc bấm)");
    this._hopDenKhungTimers = [1000, 3000, 8000].map((cho) =>
      setTimeout(() => ghi(`(+${cho / 1000}s)`), cho));
  }

  _toggleSoundHere() {
    const video = this._video;
    const pictureSound = video.open && video.withSpeakers && video.soundHere;
    if (deviceAudio.along || pictureSound) {
      if (deviceAudio.along) deviceAudio.stopAlong();
      if (pictureSound) {
        if (video.soundOnly) {
          // Khung mở ra chỉ để mang tiếng: tắt tiếng là đóng hẳn, đừng để nó chạy câm.
          this._closeVideo();
          this._syncSoundHint();
          this._syncNowPlaying();
          return;
        }
        video.soundHere = false;
        this._videoCommand("mute");
      }
    } else if (video.open && video.withSpeakers && !video.picture && laTao()) {
      /* CHỈ MÁY NHÀ TÁO ĐI ĐƯỜNG KHUNG — và đây là chỗ tôi đã sai ở 0.26.34.
         Tôi gộp hai nền tảng làm một vì đoán rằng đổi khung sang «www.youtube.com»
         thì Chrome sẽ cho tự phát kèm tiếng. Chủ máy gửi ảnh chụp Android
         21/09/2026: khung vẫn hiện nút play đỏ của YouTube kèm dòng "Chạm vào video
         để phát có tiếng" — tức Chrome CHẶN, và khung có hiện hay thu bé cũng thế.
         Giả thuyết ấy sai; đường của Android là phần tử âm thanh, như trước. */
      this._batTiengKhung();
      clearTimeout(this._soundCheckTimer);
      this._soundCheckTimer = setTimeout(() => this._checkVideoSound(), 1500);
    } else if (laTao() && this._ngheBangKhung()) {
      // Đã nhận việc bên trong; xem «_ngheBangKhung».
    } else if (this._focusedSession()?.title) {
      /* ANDROID VÀ MỌI MÁY CÒN LẠI (và mọi nguồn không phải YouTube) đi đường phần
         tử âm thanh — và phải gọi NGAY TRONG CÚ BẤM này.
         Đây là chỗ hỏng thứ hai của 0.26.34–0.26.37: tôi cho thử khung trước rồi mới
         lùi về phần tử âm thanh sau 2,5–8 giây, tức mở khoá phần tử ấy NGOÀI cú bấm.
         Chrome từ chối, và chủ máy nhận đúng dòng "Trình duyệt chặn tự phát có tiếng
         — bấm lại «Nghe trên máy này»" trong ảnh chụp 21/09/2026: mất tiếng hoàn
         toàn, tệ hơn cả bản cũ vốn chỉ chậm. */
      const phien = this._focusedSession();
      const nhip = this._loaDanNhip(phien);
      const giay = nhip ? this._speakerPosition(nhip, phien) : null;
      deviceAudio.entryId = this._entryId();
      deviceAudio.startAlong(phien && {
        source: phien.source,
        id: phien.id,
        url: phien.url,
        title: phien.title,
        channel: phien.artist,
        duration: phien.duration,
        thumbnail: phien.thumbnail,
      }, Math.max(0, Math.floor(Number(giay) || 0)));
      this._syncAlong();
    }
    this._syncSoundHint();
    this._syncNowPlaying();
  }

  /** NGHE BÀI CỦA LOA BẰNG CHÍNH KHUNG YOUTUBE — đường nhanh, chép cách thẻ
   *  «phicomm-r1-card» làm (chủ máy đưa thẻ ấy 20/09/2026 kèm một câu đo được:
   *  "card này thì quá nhanh").
   *
   *  VÌ SAO KHÔNG DÙNG PHẦN TỬ ÂM THANH: đường ấy phải hỏi máy chủ lấy địa chỉ
   *  luồng, rồi tải tiếng QUA máy chủ nhà mình, rồi tua tới giây của loa — mỗi cú
   *  tua là một lượt xin lại dữ liệu và nạp đệm lại từ chỗ mới. Chủ máy đo
   *  20/09/2026: "mất 4s đến 10s mới có tiếng", rồi "đồng bộ quá lâu". Khung YouTube
   *  lấy thẳng từ Google và vào đúng giây ngay trong địa chỉ nhúng («start»), nên
   *  không còn bước nào để chậm. Thẻ «phicomm-r1-card» KHÔNG BAO GIỜ phát nhạc bằng
   *  thẻ «audio» — phần tử âm thanh duy nhất của nó là một dòng im lặng để iOS coi
   *  trang là đang có tiếng.
   *
   *  Trả về true nếu đã nhận việc; false thì người gọi đi đường cũ. */
  _ngheBangKhung() {
    const session = this._focusedSession();
    const id = String(session?.id || "");
    if (!session?.title || session.source !== "youtube" || !VIDEO_ID.test(id)) return false;
    /* TẮT MÀN HÌNH LÀ RÀNG BUỘC MẠNH HƠN TỐC ĐỘ. Trang bị ẩn thì Chrome trên Android
       treo khung nhúng, nên máy không phải nhà Táo mà đang bật "nghe khi tắt màn hình"
       thì vẫn phải đi phần tử âm thanh — chậm hơn, nhưng là thứ duy nhất còn chạy khi
       màn hình đã tắt. Máy nhà Táo thì ngược lại: phần tử ấy đo được là không bao giờ
       tải, còn khung thì sống tiếp nếu có một dòng im lặng giữ trang («_giuTiengNen»). */
    if (listenScreenOff() && !laTao()) return false;
    // Vào thẳng giây loa đang ở, nên không cần vòng tua nào để "đồng bộ" nữa.
    const nhip = this._loaDanNhip(session);
    const giay = nhip ? this._speakerPosition(nhip, session) : null;
    this._openVideo(
      {
        id,
        url: session.url,
        title: session.title,
        channel: session.artist,
        duration: session.duration,
        thumbnail: session.thumbnail,
      },
      {
        withSpeakers: true,
        soundHere: true,
        soundOnly: true,
        startSeconds: Math.max(0, Math.floor(Number(giay) || 0)),
      },
    );
    // Máy nhà Táo có bật nghe-khi-tắt-màn: giữ trang "đang có tiếng" cho khung khỏi bị cắt.
    if (listenScreenOff()) this._giuTiengNen();
    return true;
  }

  /** GIỮ TRANG "ĐANG CÓ TIẾNG" CHO iOS — chép từ một bản cài ĐÃ CHẠY ĐƯỢC.
   *
   * Chủ máy đưa thẻ «phicomm-r1-card» ngày 20/09/2026 kèm một câu quyết định:
   * "dùng trên iPhone nghe nhạc, xem video trên iPhone bình thường". Đọc mã của
   * nó thì ra điều tôi tìm cả ngày: **nó không phát nhạc bằng thẻ «audio» bao
   * giờ**. Nhạc luôn nằm trong khung YouTube; phần tử âm thanh chỉ phát một dòng
   * IM LẶNG lặp vô hạn, để iOS coi trang là đang có tiếng và không cắt khi tắt màn.
   *
   * Vì sao từng chi tiết có mặt (giữ nguyên như bản gốc, đừng "dọn" cho gọn):
   *   - dao động 20 Hz, âm lượng 0,0001 → thực tế vô thanh, nhưng là tiếng THẬT
   *     nên iOS không coi là im lặng giả; lùi về tệp WAV im lặng khi máy không có
   *     Web Audio.
   *   - «loop» → dòng này không bao giờ kết thúc, nên trạng thái "đang phát" không
   *     rụng giữa chừng.
   *   - «playsinline» VÀ «webkit-playsinline» → Safari đời cũ chỉ hiểu cái thứ hai.
   *   - nằm TRONG trang, 1×1 điểm ảnh, mờ 0,01 — KHÔNG dùng «display:none», vì
   *     WebKit bỏ qua phần tử media bị ẩn hẳn.
   */
  async _giuTiengNen() {
    if (!laTao()) return;
    try {
      if (!this._nenAudio) {
        let dong = null;
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (Ctx) {
          this._nenCtx = this._nenCtx || new Ctx();
          if (this._nenCtx.state === "suspended") await this._nenCtx.resume();
          if (this._nenCtx.createMediaStreamDestination) {
            const osc = this._nenCtx.createOscillator();
            osc.frequency.setValueAtTime(20, this._nenCtx.currentTime);
            const gain = this._nenCtx.createGain();
            gain.gain.setValueAtTime(0.0001, this._nenCtx.currentTime);
            osc.connect(gain);
            const dich = this._nenCtx.createMediaStreamDestination();
            gain.connect(dich);
            osc.start();
            dong = dich.stream;
          }
        }
        const nen = document.createElement("audio");
        nen.setAttribute("playsinline", "");
        nen.setAttribute("webkit-playsinline", "");
        nen.loop = true;
        Object.assign(nen.style, {
          position: "fixed", top: "-9999px", left: "-9999px",
          width: "1px", height: "1px", opacity: "0.01",
        });
        if (dong) nen.srcObject = dong;
        else nen.src = SILENCE;
        document.body.appendChild(nen);
        this._nenAudio = nen;
      }
      if (this._nenAudio.paused) await this._nenAudio.play();
      if ("wakeLock" in navigator && !this._khoaThuc) {
        this._khoaThuc = await navigator.wakeLock.request("screen");
        this._khoaThuc.addEventListener("release", () => { this._khoaThuc = null; });
      }
    } catch (_error) {
      // Máy không cho thì thôi — đường xem vẫn chạy, chỉ là tắt màn sẽ dừng.
    }
  }

  _thoiGiuTiengNen() {
    try { this._nenAudio?.pause(); } catch (_error) { /* đã chết thì thôi */ }
    try { this._khoaThuc?.release(); } catch (_error) { /* đã nhả rồi */ }
    this._khoaThuc = null;
  }

  _toggleScreenOff() {
    const on = !listenScreenOff();
    setListenScreenOff(on);
    const video = this._video;
    /* HỘP ĐEN CHO CÔNG TẮC NÀY. Người dùng báo 21/09/2026 "kích vào nghe khi tắt màn
       hình không được" trên iOS, mà nhánh xử lý thì im lặng hoàn toàn — không cách
       nào biết nó rơi vào nhánh nào, hay khung có bị tắt tiếng vì dòng im lặng giữ
       nền tranh mất chỗ phát (iOS chỉ cho một luồng chạy một lúc). */
    deviceAudio.hass = this._hass;
    deviceAudio.ghiThang(`bật/tắt nghe-khi-tắt-màn: bật=${on ? 1 : 0}`
      + ` khung mo=${video.open ? 1 : 0} tieng-o-day=${video.soundHere ? 1 : 0}`
      + ` chitieng=${video.soundOnly ? 1 : 0} trangthai=${video.state}`
      + ` co-bai=${video.item ? 1 : 0} loa=${video.withSpeakers ? 1 : 0}`);
    setTimeout(() => {
      deviceAudio.ghiThang(`sau bật/tắt nghe-khi-tắt-màn (+3s) — khung mo=${this._video.open ? 1 : 0}`
        + ` trangthai=${this._video.state} giay=${Number(this._video.time || 0).toFixed(1)}`);
    }, 3000);
    /* ĐIỀU KIỆN LÀ NỀN TẢNG, KHÔNG PHẢI "CÓ LOA HAY KHÔNG". Trước đây nhánh này còn
       đòi «!video.withSpeakers», nên đang vừa phát ra loa vừa nghe trên máy nhà Táo mà
       bật nghe-khi-tắt-màn là rơi xuống nhánh giao tiếng cho phần tử âm thanh — đúng
       thứ không bao giờ tải trên WebKit, tức mất tiếng. Có loa hay không thì WebKit vẫn
       thế. */
    if (on && laTao() && video.open && video.soundHere && video.item && video.state === 1) {
      /* iOS: GIỮ TIẾNG TRONG KHUNG, đừng chuyển sang phần tử âm thanh.
         Đó là chỗ mọi bản trước hỏng — đo được phần tử ấy không bao giờ tải trên
         iOS. Thẻ «phicomm-r1-card» của chủ máy chạy được chính vì nó không bao giờ
         làm thế; nó chỉ giữ một dòng im lặng cho trang khỏi bị cắt. */
      this._giuTiengNen();
      this._setStatus("Bật nghe khi tắt màn hình: giữ tiếng trong video, tắt màn vẫn nghe tiếp.");
      this._syncNowPlaying();
      return;
    }
    if (!on) this._thoiGiuTiengNen();
    if (on && video.open && !video.withSpeakers && !video.followsDevice && video.item) {
      // Watching with sound: the sound moves to the audio element from the second
      // being watched, and the picture follows it muted.
      deviceAudio.entryId = this._entryId();
      const item = { source: "youtube", ...video.item };
      const queue = this._queue.length ? this._queue : [item];
      deviceAudio.listen(item, queue, Math.max(0, this._queueIndex), this._videoTimeNow());
      video.followsDevice = true;
      video.soundHere = false;
      this._videoCommand("mute");
    } else if (on && video.open && video.withSpeakers && video.soundHere) {
      // Khung mở ra chỉ để mang tiếng: giao việc cho phần tử âm thanh xong là đóng hẳn,
      // để lại một khung câm vô hình thì vòng đồng bộ vẫn tua nó mà chẳng ai nghe.
      if (video.soundOnly) this._closeVideo();
      video.soundHere = false;
      this._videoCommand("mute");
      deviceAudio.entryId = this._entryId();
      deviceAudio.startAlong();
      // Nạp NGAY, đừng chờ nhịp đồng bộ sau — mỗi nhịp là 2 giây chờ thêm vô ích.
      this._syncAlong();
    }
    this._setStatus(on
      ? "Bật nghe khi tắt màn hình: tắt màn hình hay chuyển ứng dụng vẫn nghe tiếp trên máy này."
      : "Đã tắt: tắt màn hình thì tiếng trên máy này dừng, mở lại thì phát tiếp.");
    this._syncNowPlaying();
  }

  /** Listening along: the speakers' song, paused/playing with them, re-synced past 2 seconds. */
  _syncAlong() {
    if (!deviceAudio.along || !this._hass) return;
    const session = this._focusedSession();
    if (!session?.title) {
      deviceAudio.stopAlong();
      return;
    }
    /* Tính giây của loa TRƯỚC khi nạp, để phần tử âm thanh vào thẳng chỗ ấy. */
    const nhip = this._loaDanNhip(session);
    const speakerTime = nhip ? this._speakerPosition(nhip, session) : null;
    deviceAudio.loadAlong({
      source: session.source,
      id: session.id,
      url: session.url,
      title: session.title,
      channel: session.artist,
      duration: session.duration,
      thumbnail: session.thumbnail,
    }, Math.max(0, Math.floor(Number(speakerTime) || 0)));
    const audio = deviceAudio.real();
    if (!audio || (document.visibilityState === "hidden" && !listenScreenOff())) return;
    const lead = session.output_entity_ids.find((entityId) =>
      ["playing", "paused", "buffering"].includes(this._hass.states[entityId]?.state));
    const speaker = lead && this._hass.states[lead];
    if (!speaker || !this._speakerPlaysItem(speaker, session)) return;
    if (speaker.state === "paused" && !audio.paused) audio.pause();
    if (speaker.state === "playing" && audio.paused) audio.play().catch(() => {});
    /* ĐỒNG HỒ có thể nằm ở loa KHÁC loa dẫn trạng thái — xem «_loaDanNhip». Đọc
       giây của đúng loa đầu danh sách rồi thấy rỗng là thoát, nghĩa là cả phiên
       nhiều loa mất canh tiếng chỉ vì loa đầu không báo giây. */
    if (speaker.state !== "playing" || speakerTime === null || Date.now() < this._alongSeekHold) return;
    /* VỪA LOA VỪA NGHE TRÊN MÁY: loa báo kẹt thì dòng dưới lôi tiếng trên máy về
       chỗ kẹt ấy — cứ 4 giây một lần, tức bài tự phát lại mãi. Đúng lời chủ máy
       ngay đầu đợt này: "mặc định tắt tiếng và restart liên tục thời gian về 0". */
    if (!this._dongHoChay("tieng", nhip, speakerTime)) return;
    /* KHÔNG chốt "phải là số đo" ở đây — và đó là bài học của bản 0.26.22.
       Bản ấy chặn cả vòng này, nên tiếng trên máy không còn được canh theo loa
       nữa và hai bên trôi khỏi nhau: chủ máy báo ngay "tiếng loa và thiết bị
       không đồng bộ, cái trước cái sau".
       Vì sao vòng HÌNH chốt được mà vòng TIẾNG thì không: hai bên trả giá khác
       hẳn nhau. Tua khung YouTube là một cú nạp lại thấy được bằng mắt, nên thà
       để hình trôi còn hơn giật. Còn đây là thứ DUY NHẤT giữ tiếng trên máy đi
       cùng loa — chặn nó đi thì chế độ vừa-loa-vừa-máy mất luôn lý do tồn tại.
       Giây suy ra tuy không phải số đo, nhưng nó neo vào đúng lúc Home Assistant
       báo lần cuối, nên với một loa phát liên tục thì nó vẫn bám sát sự thật. */
    if (Math.abs(speakerTime - audio.currentTime) > 2) {
      audio.currentTime = speakerTime;
      this._alongSeekHold = Date.now() + 4000;
    }
  }

  /** Máy này không phát được tiếng: trả tiếng về cho khung, chờ một cú chạm.
   *
   * Dùng cho HAI tình huống, nên tách ra thay vì chép đôi: luồng lấy KHÔNG ĐƯỢC
   * (phần tử âm thanh bắn «error»), và luồng MỞ ĐƯỢC NHƯNG KHÔNG CHẢY — ca thứ
   * hai không bắn sự kiện nào cả, «_syncVideo» phải tự đo mới thấy.
   */
  _traTiengVeKhung() {
    const video = this._video;
    video.followsDevice = false;
    video.soundHere = true;
    // Dừng và bỏ tắt tiếng, để cú chạm vào video khởi động nó kèm tiếng của chính nó.
    this._videoCommand("pauseVideo");
    this._videoCommand("unMute");
    this._soundHintShown = true;
    this._syncSoundHint();
  }

  _deviceAudioChanged(message, isError) {
    if (!this.shadowRoot || !this._hass) return;
    const video = this._video;
    // The picture follows the device's sound: a new song there (the next one when a
    // song ends) changes the picture too.
    if (video.open && video.followsDevice && isError && !video.picture) {
      // The device's sound couldn't start (no stream from the player server): the
      // picture keeps its own sound, and a tap inside the video starts it.
      this._traTiengVeKhung();
    } else if (video.open && video.followsDevice && deviceAudio.item?.id !== video.item?.id) {
      if (deviceAudio.item && this._isVideoItem(deviceAudio.item)) {
        this._openVideo(deviceAudio.item, { withSpeakers: false, followsDevice: true });
      } else {
        this._closeVideo();
      }
    }
    if (message) this._setStatus(message, isError);
    this._syncNowPlaying();
    this._updateTransportState();
    this._updateProgress();
  }

  _saveSearch(query) {
    try {
      localStorage.setItem(SEARCH_KEY + this._config.entity, JSON.stringify({
        source: this._source,
        query,
        results: this._results.slice(0, 30),
      }));
    } catch (_error) {
      // Storage full or blocked: the list is only kept while the page stays open.
    }
  }

  /** Leaving the dashboard: keep the search and what plays; the music goes on without the card. */
  _remember() {
    const video = this._video;
    const previous = cardMemory.get(this._config.entity);
    if (previous?.handoff) clearTimeout(previous.handoff);
    const memory = {
      source: this._source,
      query: this.shadowRoot?.querySelector('input[type="search"]')?.value || "",
      results: this._results,
      queue: this._queue,
      queueIndex: this._queueIndex,
      video: null,
      handoff: null,
    };
    if (video.open && video.item) {
      const saved = {
        item: video.item,
        withSpeakers: video.withSpeakers,
        followsDevice: video.followsDevice,
        time: this._videoTimeNow(),
        at: Date.now(),
        playing: [1, 3].includes(video.state),
      };
      memory.video = saved;
      if (!saved.withSpeakers && !saved.followsDevice && saved.playing) {
        // The picture goes away with the card. Unless the card is back at once (the
        // dashboard only moved it), its sound carries on from the same second here.
        const item = { source: "youtube", ...video.item };
        const queue = this._queue.length ? this._queue : [item];
        const index = Math.max(0, this._queueIndex);
        const entryId = this._entryId();
        memory.handoff = setTimeout(() => {
          memory.handoff = null;
          deviceAudio.entryId = entryId;
          deviceAudio.listen(item, queue, index, saved.time + (Date.now() - saved.at) / 1000);
          saved.followsDevice = true;
        }, 1500);
      }
    }
    cardMemory.set(this._config.entity, memory);
  }

  _restore() {
    let memory = cardMemory.get(this._config.entity);
    cardMemory.delete(this._config.entity);
    if (memory?.handoff) clearTimeout(memory.handoff);
    if (!memory) {
      // A new page (the app reopened): the last search on this device.
      try {
        memory = JSON.parse(localStorage.getItem(SEARCH_KEY + this._config.entity) || "null");
      } catch (_error) {
        memory = null;
      }
    }
    /* Nguồn đã bị ẩn trong cấu hình thì KHÔNG khôi phục lần tìm cũ của nó: khôi phục
       xong sẽ hiện một danh sách kết quả mà hàng nút không còn mục nào ứng với nó,
       và bấm phát thì gửi đi đúng cái nguồn người dùng vừa bảo là không muốn thấy. */
    const nguonNho = ["youtube", "zing", "facebook", "http"].includes(memory?.source) ? memory.source : "youtube";
    if (memory && !this._results.length && Array.isArray(memory.results) && memory.results.length
      && this._nguonHienThi().includes(nguonNho)) {
      this._source = nguonNho;
      this._results = memory.results;
      this.shadowRoot.querySelector('input[type="search"]').value = String(memory.query || "");
      this._updateSourceButtons();
      this._renderResults();
      this._syncPlayers();
    }
    if (memory && !this._queue.length && Array.isArray(memory.queue)) {
      this._queue = memory.queue;
      this._queueIndex = Number.isInteger(memory.queueIndex) ? memory.queueIndex : -1;
    }
    const saved = memory?.video;
    if (saved && !this._video.open) {
      const session = this._focusedSession();
      if (saved.withSpeakers) {
        if (session && String(session.id) === String(saved.item.id)) this._openVideo(saved.item, { withSpeakers: true });
      } else if (saved.followsDevice || deviceAudio.item) {
        if (deviceAudio.item && this._isVideoItem(deviceAudio.item)) {
          this._openVideo(deviceAudio.item, { withSpeakers: false, followsDevice: true });
        }
      } else {
        // Back at once: the video goes on where it was.
        const startSeconds = saved.playing ? saved.time + (Date.now() - saved.at) / 1000 : saved.time;
        this._openVideo(saved.item, { withSpeakers: false, startSeconds });
      }
    }
    this._syncNowPlaying();
    this._updateTransportState();
    this._updateProgress();
  }

  /** Khung vua nap trang moi: trang do chua nghe lenh nao, ma loi cua trang bi
      thay da danh dau san-sang va dung bat tay, nen player moi bo qua moi lenh.
      Khong dung _frameReady nhu ban cu: bat tay o day canh theo _video.ready. */
  _frameLoaded() {
    this._video.ready = false;
    this._videoHandshake();
  }

  /** Nap san khung rong khi ket qua tim co video: bam phat thi hinh len ngay. */
  _warmFrame() {
    const frame = this.shadowRoot?.querySelector(".video-frame");
    if (!frame || frame.querySelector("iframe")) return;
    const iframe = document.createElement("iframe");
    iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
    iframe.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen");
    iframe.setAttribute("allowfullscreen", "");
    iframe.title = "Video YouTube";
    iframe.addEventListener("load", () => this._frameLoaded());
    const hint = document.createElement("div");
    hint.className = "sound-hint";
    hint.hidden = true;
    frame.append(iframe, hint);
    // Khung hình đi kèm cũng phát video thật khi loa dẫn nhịp, nên phụ đề và chú
    // thích nổi phải tắt giống khung chính — để lệch nhau thì cùng một bài, xem ở
    // hai chỗ lại ra hai kiểu.
    const params = new URLSearchParams({
      enablejsapi: "1", rel: "0", playsinline: "1",
      cc_load_policy: "0", iv_load_policy: "3", origin: location.origin,
    });
    iframe.setAttribute("src", `${EMBED_ORIGIN}/embed/?` + params);
  }

  /** Tua hinh ve dung moc tieng. Gom tu hai cho von lam y het trong _syncVideo. */
  _seekPicture(soundTime) {
    this._videoCommand("seekTo", [soundTime, true]);
    this._lastVideoSeekAt = Date.now();
  }

  /** Chủ máy TỰ tua trong khung YouTube: giữ đúng chỗ họ chọn, và kéo loa theo. */
  _nguoiDungTuTua(giay) {
    /* Ngưng mọi nhịp kéo hình về theo loa. Dùng lại đúng hai cái phanh sẵn có
       (_mirrorHoldUntil và _lastVideoSeekAt) chứ không đẻ phanh thứ ba, vì ba chỗ
       đồng bộ hiện thời đều chỉ biết hai biến này. */
    this._mirrorHoldUntil = Date.now() + 8000;
    this._lastVideoSeekAt = Date.now();
    const audio = deviceAudio.real();
    if (audio && deviceAudio.item && Math.abs(audio.currentTime - giay) > 2) audio.currentTime = giay;
    const session = this._focusedSession();
    const dich = (session?.output_entity_ids || []).filter((id) => this._supportsFeature(id, 2));
    if (!dich.length || !this._hass) return;
    this._hass.callService("media_player", "media_seek", {
      entity_id: dich,
      seek_position: Math.round(giay),
    }).catch(() => {});
  }

  _videoHandshake() {
    // The embed reports its state only after the page says it is listening.
    clearInterval(this._videoHandshakeTimer);
    let tries = 0;
    this._videoHandshakeTimer = setInterval(() => {
      if (this._video.ready || !this._video.open || ++tries > 40) {
        clearInterval(this._videoHandshakeTimer);
        return;
      }
      this._videoPost({ event: "listening" });
      this._videoCommand("addEventListener", ["onStateChange"]);
      this._videoCommand("addEventListener", ["onError"]);
    }, 250);
  }

  _videoPost(message) {
    const iframe = this.shadowRoot?.querySelector(".video-frame iframe");
    iframe?.contentWindow?.postMessage(JSON.stringify({ ...message, id: 1, channel: "widget" }), EMBED_ORIGIN);
  }

  _videoCommand(func, args = []) {
    const picture = this._video.pictureEl;
    if (!picture) {
      this._videoPost({ event: "command", func, args });
      return;
    }
    // Our own picture (no sound: the speakers or this device carry it).
    if (func === "playVideo") picture.play().catch(() => {});
    else if (func === "pauseVideo") picture.pause();
    else if (func === "stopVideo") {
      picture.pause();
      picture.currentTime = 0;
    } else if (func === "seekTo" && Number.isFinite(args[0])) picture.currentTime = args[0];
  }

  _videoTimeNow() {
    const video = this._video;
    if (video.pictureEl) return video.pictureEl.currentTime;
    return video.time + (video.state === 1 && video.timeAt ? (Date.now() - video.timeAt) / 1000 : 0);
  }

  _handleVideoMessage(event) {
    const iframe = this.shadowRoot?.querySelector(".video-frame iframe");
    if (!iframe || event.source !== iframe.contentWindow || event.origin !== EMBED_ORIGIN) return;
    let data;
    try {
      data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
    } catch (_error) {
      return;
    }
    if (!data || typeof data !== "object" || this._video.picture) return;
    this._video.ready = true;
    if (data.event === "onError") {
      this._embedRefused();
      return;
    }
    const info = data.info;
    if (["infoDelivery", "initialDelivery"].includes(data.event) && info && typeof info === "object") {
      if (Number.isFinite(info.currentTime)) {
        /* Bắt lúc CHỦ MÁY TỰ TUA trong khung YouTube: thời gian báo về nhảy một quãng
           lớn so với mức suy ra từ nhịp chạy đều. Không bắt được thì nhịp đồng bộ kế
           tiếp thấy lệch và lôi hình về chỗ của loa — đúng cảnh "tua trên video lại
           quay về vị trí đang chạy trên card".
           Lệnh tua do chính card gửi cũng gây nhảy y hệt, nên loại trừ bằng dấu thời
           gian _lastVideoSeekAt mà _seekPicture vừa đặt. */
        /* CHỈ tin một bước nhảy khi trình phát đang chạy ỔN ĐỊNH trên cùng một video.
           Bản 0.20.2 thiếu hai hàng rào dưới nên lúc mới bấm phát, mọi bước nhảy bình
           thường của trình phát đều bị chấm là "người dùng vừa tua":
           - trạng thái phải là 1 (đang chạy); lúc đang nạp (3) hay chưa khởi động
             (-1, 5) thì thời gian báo về không đáng tin;
           - phải qua 5 giây kể từ lúc mở, vì mở video từ giây đang nghe
             («startSeconds») cũng làm trình phát nhảy một quãng lớn và hợp lệ. */
        const onDinh = this._video.state === 1
          && this._video.moUL
          && Date.now() - this._video.moUL > 5000;
        const duKien = onDinh && this._video.timeAt ? this._videoTimeNow() : null;
        const tuTua = Number.isFinite(duKien)
          && Math.abs(info.currentTime - duKien) > 2.5
          && Date.now() >= this._lastVideoSeekAt + 1500;
        this._video.time = info.currentTime;
        this._video.timeAt = Date.now();
        if (tuTua) this._nguoiDungTuTua(info.currentTime);
      }
      if (typeof info.muted === "boolean") this._video.muted = info.muted;
      if (Number.isFinite(info.playerState)) this._setVideoState(info.playerState);
    } else if (data.event === "onStateChange") {
      this._setVideoState(Number(data.info));
    }
    this._syncSoundHint();
  }

  /**
   * Some browsers (phones, the Home Assistant app) only allow sound after a tap
   * inside the video itself: the embed then stays stopped or plays muted, and the
   * card's play button can't start it (owner 15/09/2026: "không phát luôn mà tôi phải
   * kích vào màn hình youtube, kích vào nút play của mình không hoạt động").
   * Watching alone, the sound then comes from the card's audio element (unlocked in
   * the tap that opened the video) and the picture follows muted — muted pictures
   * may play on their own. With speakers, ask once more, then hint to tap the video.
   */
  /** CANH KHUNG CHỈ-MANG-TIẾNG — CHỈ bỏ cuộc khi có BẰNG CHỨNG là bị chặn.
   *
   *  Bản 0.26.36 hỏi đúng MỘT lần ở giây 2,5 rồi kết luận, mà «_soundBlocked» coi
   *  «trạng thái -1» (chưa chạy) là bị chặn. Trên điện thoại khung YouTube mất vài
   *  giây mới nạp xong và báo về, nên thẻ dỡ bỏ một khung SẮP kêu rồi quay về đường
   *  máy chủ — mất thêm cả quãng giải bài và nhảy vào giữa bài. Chủ máy đo
   *  21/09/2026: "bị giật, tiếng thì mất 10s mới có". Đúng phép cộng ấy.
   *
   *  Hai câu trả lời được tính là DỨT KHOÁT, ngoài ra thì đợi tiếp:
   *    - khung báo ĐANG PHÁT mà «câm = true» → bị chặn thật, lùi ngay;
   *    - quá 8 giây vẫn chưa hề kêu → coi như không xong, lùi.
   *  Khung báo đang phát và không câm thì thôi canh, để yên cho nó chạy.
   */
  _canhKhungChiTieng() {
    clearInterval(this._henCanhChiTieng);
    const batDau = Date.now();
    this._henCanhChiTieng = setInterval(() => {
      const video = this._video;
      const thoi = () => {
        clearInterval(this._henCanhChiTieng);
        this._henCanhChiTieng = null;
      };
      if (!video.open || !video.soundOnly || !video.soundHere) return thoi();
      const dangChay = [1, 3].includes(video.state);
      if (dangChay && video.muted === false) return thoi();
      const giay = (Date.now() - batDau) / 1000;
      if (!(dangChay && video.muted === true) && giay < 8) return;
      thoi();
      this._luiVeThePhatTieng(`câm=${video.muted} trạng thái=${video.state} giây=${giay.toFixed(1)}`);
    }, 400);
  }

  /** Khung không mang được tiếng: trả việc về phần tử âm thanh (chậm hơn nhưng còn
   *  nghe được). Nói kèm SỐ ĐO để lần sau biết vì sao, thay vì lại đoán. */
  _luiVeThePhatTieng(chiTiet) {
    this._closeVideo();
    deviceAudio.entryId = this._entryId();
    deviceAudio.startAlong();
    this._syncAlong();
    this._setStatus(`Khung YouTube không tự phát được tiếng (${chiTiet}); đang lấy tiếng qua máy chủ.`);
    this._syncNowPlaying();
  }

  _checkVideoSound() {
    const video = this._video;
    if (!video.open || video.picture || !video.soundHere || !this._soundBlocked()) return;
    /* LỐI LÙI CỦA ĐƯỜNG NHANH. Khung thu bé không có gì để người dùng chạm vào, nên
       bị chặn tiếng ở đây là hết đường — trả việc về phần tử âm thanh (chậm hơn,
       nhưng còn nghe được). Nhờ vậy giả thuyết "đổi sang www.youtube.com thì Chrome
       cho tự phát" sai cũng chỉ mất vài giây, không mất tiếng. */
    if (video.soundOnly) {
      this._luiVeThePhatTieng(`câm=${video.muted} trạng thái=${video.state}`);
      return;
    }
    /* TRÊN iOS THÌ ĐỪNG CƯỚP TIẾNG CỦA KHUNG. «_soundFromDevice» tắt tiếng khung
       rồi giao việc phát cho phần tử âm thanh — mà trên iOS phần tử ấy đo được là
       KHÔNG BAO GIỜ tải (nap=0 mang=2 loi=0, thu được hai lần độc lập). Kết quả:
       khung bị câm, phần tử im, người dùng không nghe gì. Chủ máy gửi ảnh đúng
       cảnh đó 20/09/2026: "trên iP phải bật biểu tượng loa mới nghe được, mặc định
       tắt tiếng" — biểu tượng loa ở đây là nút tắt/bật tiếng của chính trình phát
       YouTube trên điện thoại.
       Ở iOS, đường chạy được là để tiếng NẰM NGUYÊN trong khung rồi nhờ một cú
       chạm — đúng thứ người dùng đang phải tự mò ra. Nên iOS đi cùng nhánh của ca
       có loa: xin phát lại, rồi hiện lời nhắc chạm vào video. */
    if (!video.withSpeakers && !laTao()) {
      this._soundFromDevice();
      return;
    }
    this._thucTiengKhung();
    this._videoCommand("playVideo");
    clearTimeout(this._soundCheckTimer);
    this._soundCheckTimer = setTimeout(() => {
      this._soundHintShown = this._video.open && this._video.soundHere && this._soundBlocked();
      this._syncSoundHint();
    }, 1500);
  }

  /** The frame can't play its sound: this device plays it, the muted picture follows. */
  _soundFromDevice() {
    const video = this._video;
    if (!video.open || !video.item || video.withSpeakers || video.followsDevice) return;
    /* MÁY NHÀ TÁO KHÔNG CÓ ĐƯỜNG TIẾNG NÀO NGOÀI KHUNG.
       Hàm này câm khung lại rồi giao tiếng cho phần tử âm thanh — đúng thứ đo được
       là không bao giờ tải trên WebKit. Nút Phát gọi vào đây khi khung chưa khởi
       động, nên trên iPhone bấm Phát là mất tiếng kèm dòng đỏ; chủ máy 21/09/2026:
       "bấm play báo lỗi, rồi play lại thì nghe được". Ở đây chỉ cần bảo khung chạy. */
    if (laTao()) {
      this._videoCommand("playVideo");
      this._setStatus("Chạm một lần vào video để bắt đầu — iPhone bắt buộc vậy.");
      return;
    }
    const item = { source: "youtube", ...video.item };
    deviceAudio.entryId = this._entryId();
    deviceAudio.listen(item, this._queue.length ? this._queue : [item], Math.max(0, this._queueIndex), this._videoTimeNow());
    video.followsDevice = true;
    video.soundHere = false;
    clearTimeout(this._soundCheckTimer);
    this._soundHintShown = false;
    this._syncSoundHint();
    this._videoCommand("mute");
    this._videoCommand("playVideo");
    this._syncNowPlaying();
  }

  _soundBlocked() {
    return this._video.muted === true || [-1, 5].includes(this._video.state);
  }

  _syncSoundHint() {
    const hint = this.shadowRoot?.querySelector(".sound-hint");
    if (!hint) return;
    if (this._soundHintShown && (!this._video.soundHere || !this._soundBlocked())) this._soundHintShown = false;
    hint.textContent = this._video.state === 1 ? "🔇 Chạm vào video để bật tiếng" : "▶ Chạm vào video để phát có tiếng";
    hint.hidden = !this._soundHintShown;
  }

  /**
   * YouTube refuses some videos inside the card: record-label (VEVO) videos when
   * Home Assistant is opened by IP address. The sound goes on (the speakers, or this
   * device), and the card shows the video's picture from the player server instead:
   * - at home the browser fetches it straight from YouTube (the link is bound to the
   *   home's Internet address), costing nothing more than YouTube itself;
   * - that failing means the viewer is away from home: the picture would leave the
   *   home's connection, so it stays off until the viewer turns it on and agrees.
   */
  async _embedRefused() {
    const video = this._video;
    if (!video.open || !video.item || video.picture) return;
    /* MÁY NHÀ TÁO ĐANG NGHE BẰNG KHUNG: đừng câm khung, đừng đi mở hình.
       Nhánh này vốn giao tiếng cho phần tử âm thanh rồi mở hình bằng luồng thẳng, và
       khi luồng ấy không mở được thì KẾT LUẬN "ở ngoài mạng nhà" — chủ máy đang ngồi
       ở nhà vẫn bị báo thế (21/09/2026). Trên iOS phần tử âm thanh không bao giờ tải,
       nên câm khung là mất tiếng hẳn, còn dòng thông báo kia thì vừa sai vừa thừa.
       Ở đây chỉ hiện khung ra để người dùng chạm, không báo gì thêm. */
    if (laTao() && video.soundHere && !video.withSpeakers) {
      if (video.soundOnly) {
        video.soundOnly = false;
        this._daHienKhungDeCham = true;
        this._syncNowPlaying();
      }
      deviceAudio.hass = this._hass;
      deviceAudio.ghiThang("YouTube từ chối nhúng, hiện khung ra để chạm");
      return;
    }
    const item = { source: "youtube", ...video.item };
    const host = location.hostname;
    const why = /^[\d.]+$/.test(host) || host.includes(":")
      ? `YouTube không cho nhúng “${item.title}” khi mở Home Assistant bằng địa chỉ IP.`
      : `YouTube không cho nhúng “${item.title}” vào thẻ.`;
    if (!video.withSpeakers && !video.followsDevice) {
      deviceAudio.entryId = this._entryId();
      const queue = this._queue.length ? this._queue : [item];
      deviceAudio.listen(item, queue, Math.max(0, this._queueIndex));
    }
    video.followsDevice = !video.withSpeakers;
    video.soundHere = false;
    clearTimeout(this._soundCheckTimer);
    this._soundHintShown = false;
    this._syncSoundHint();
    const pending = { item: video.item };
    video.picture = pending;
    const frame = this.shadowRoot.querySelector(".video-frame");
    frame.classList.add("no-embed");
    frame.style.setProperty("--poster", `url("https://i.ytimg.com/vi/${item.id}/hqdefault.jpg")`);
    this._pictureNote("Đang nghe tiếng · đang lấy hình…");
    this._syncNowPlaying();
    let info = null;
    try {
      info = await this._hass.callApi("POST", "tritue_youtube_player/stream", {
        entry_id: this._entryId(),
        source: "youtube_video",
        target: item.url || item.id,
        max_height: this._pictureHeight(),
      });
    } catch (_error) {
      info = null;
    }
    if (this._video.picture !== pending) return;
    if (!info?.stream_url) {
      this._pictureNote("Đang nghe tiếng · không lấy được hình của video này");
      this._setStatus(`${why} Không lấy được hình, đang nghe tiếng.`);
      return;
    }
    if (info.direct_url && await this._tryPicture(info.direct_url, pending, 8000)) {
      this._setStatus(`${why} Đang xem hình lấy thẳng từ YouTube.`);
      return;
    }
    if (this._video.picture !== pending) return;
    const perMinute = Math.max(1, Math.round((Number(info.bitrate_kbps) || 1000) * 60 / 8 / 1000));
    const openAway = async () => {
      if (!(await this._tryPicture(info.stream_url, pending, 20000)) && this._video.picture === pending) {
        this._pictureNote("Đang nghe tiếng · không mở được hình");
      }
    };
    /* BẤM CÁI NÀO LÀ CÁI ĐÓ CHẠY, KHÔNG HỎI LẠI.
       Chỗ này vốn hiện một hộp thoại "Xem hình?" kèm ước lượng dung lượng, và nó dựa
       trên suy đoán "ở ngoài mạng nhà" — suy ra từ việc địa chỉ thẳng không mở được,
       chứ không phải biết thật. Chủ máy ngồi ở nhà vẫn bị báo thế, rồi còn bị chặn
       lại bằng một câu hỏi giữa lúc đang nghe (21/09/2026: "tôi cần không báo gì,
       chỉ cần chạy thôi… kích vào cái nào là cái đó chạy luôn, không hỏi bất cứ gì").
       Nay mở thẳng. Dung lượng vẫn ghi ở dòng phụ để ai quan tâm thì biết. */
    this._awayPictureOk = true;
    this._pictureNote(`Đang nghe tiếng · đang mở hình (~${perMinute} MB/phút)`);
    await openAway();
  }

  _pictureHeight() {
    // Phones get 720p, larger screens (and fullscreen on them) 1080p.
    const phone = window.matchMedia?.("(pointer: coarse)").matches && Math.min(screen.width, screen.height) < 600;
    return phone ? 720 : 1080;
  }

  _pictureNote(text, action = "", onAction = null) {
    const frame = this.shadowRoot.querySelector(".video-frame");
    frame.querySelector(".picture-note")?.remove();
    if (!text) return;
    const note = document.createElement("div");
    note.className = "picture-note";
    const label = document.createElement("span");
    label.textContent = text;
    note.append(label);
    if (action && onAction) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = action;
      button.addEventListener("click", onAction);
      note.append(button);
    }
    frame.append(note);
  }

  /** Load a picture stream; resolves true once its first frame is there. */
  _tryPicture(url, pending, timeout) {
    return new Promise((resolve) => {
      const frame = this.shadowRoot.querySelector(".video-frame");
      const element = document.createElement("video");
      element.className = "picture";
      element.muted = true;
      element.playsInline = true;
      element.setAttribute("playsinline", "");
      element.preload = "auto";
      element.style.visibility = "hidden";
      let settled = false;
      const finish = (ok) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        if (!ok) {
          element.removeAttribute("src");
          element.load();
          element.remove();
        }
        resolve(ok);
      };
      const timer = setTimeout(() => finish(false), timeout);
      element.addEventListener("error", () => finish(false), { once: true });
      element.addEventListener("loadeddata", () => {
        if (this._video.picture !== pending) {
          finish(false);
          return;
        }
        this._attachPicture(element, pending);
        finish(true);
      }, { once: true });
      frame.append(element);
      element.src = url;
    });
  }

  _attachPicture(element, pending) {
    const video = this._video;
    video.pictureEl = element;
    video.ready = true;
    this.shadowRoot.querySelector(".player").classList.add("picture-on");
    video.state = -1;
    pending.shown = true;
    element.style.visibility = "";
    const current = () => this._video.pictureEl === element;
    for (const [name, state] of [["playing", 1], ["pause", 2], ["waiting", 3], ["ended", 0]]) {
      element.addEventListener(name, () => {
        if (current()) this._setVideoState(element.ended ? 0 : state);
      });
    }
    element.addEventListener("error", () => {
      if (!current()) return;
      // The link expired or the connection dropped: keep the sound, drop the picture.
      element.remove();
      video.pictureEl = null;
      this._pictureNote("Đang nghe tiếng · hình bị ngắt");
    });
    this._pictureNote("");
    this._syncVideo();
    this._updateTransportState();
  }

  _leavePicture() {
    const video = this._video;
    const frame = this.shadowRoot?.querySelector(".video-frame");
    if (video.pictureEl) {
      video.pictureEl.pause();
      video.pictureEl.removeAttribute("src");
      video.pictureEl.load();
      video.pictureEl.remove();
    }
    frame?.querySelector(".picture-note")?.remove();
    frame?.classList.remove("no-embed");
    this.shadowRoot?.querySelector(".player")?.classList.remove("picture-on");
    video.picture = null;
    video.pictureEl = null;
    video.ready = false;
  }

  _setVideoState(state) {
    if (!Number.isFinite(state) || state === this._video.state) return;
    const previous = this._video.state;
    this._video.state = state;
    this._updateTransportState();
    // 0 = ended. With speakers the speakers drive auto-advance; alone, the video does.
    if (state !== 0 || previous === 0 || this._video.withSpeakers || this._video.followsDevice) return;
    if (this._queueIndex >= 0 && this._queueIndex < this._queue.length - 1) this._skip(1);
    else this._setStatus("Đã phát hết hàng đợi.");
  }

  _syncVideo() {
    const video = this._video;
    if (video.open && video.followsDevice && video.ready) {
      // The muted picture follows this device's sound.
      const audio = deviceAudio.real();
      if (!audio) return;
      if (audio.paused && [1, 3].includes(video.state)) this._videoCommand("pauseVideo");
      if (!audio.paused && [-1, 2, 5].includes(video.state)) this._videoCommand("playVideo");
      /* ĐỒNG HỒ DẪN PHẢI ĐANG CHẠY thì mới được kéo đồng hồ theo. Đo trên clip
         quay màn hình iPhone 19/09/2026: phần tử âm thanh báo "không tạm dừng"
         nhưng `currentTime` đứng nguyên ở 0 (luồng bị kẹt trong khung web của
         app Home Assistant). Video YouTube vẫn chạy, nên cứ bò tới 0:02–0:03 là
         lệch quá 2 giây, và dòng dưới tua nó về đúng vị trí của tiếng — tức về
         0. Chu kỳ 4 giây của cái phanh ngay bên dưới chính là chu kỳ giật về 0
         mà chủ máy thấy: 0:01 → 0:02 → 0:03 → 0:00, lặp mãi.
         So với nhịp trước là phép thử "đồng hồ có chạy không" đúng nghĩa, không
         phải một ngưỡng tự nghĩ ra; lần chạy đầu chưa có mốc so nên không tua,
         đúng mong muốn. */
      const giayTieng = audio.currentTime;
      const tiengDangChay = this._tiengGiayTruoc !== undefined && giayTieng !== this._tiengGiayTruoc;
      this._tiengGiayTruoc = giayTieng;
      /* Luồng MỞ ĐƯỢC NHƯNG KHÔNG CHẢY là hỏng hoàn toàn im lặng: phần tử âm thanh
         chỉ bắn «error» khi lấy luồng hỏng, còn kẹt giữa chừng thì nó vẫn báo là
         đang phát. Chủ máy gặp đúng ca này trên iPhone với CẢ HAI máy phát (add-on
         và c2a), tức lỗi ở thẻ chứ không ở máy phát.
         ĐO BẰNG THỜI GIAN THẬT, KHÔNG ĐẾM NHỊP: hàm này còn chạy mỗi lần Home
         Assistant đẩy trạng thái — nhiều lần mỗi giây — nên đếm nhịp thì ba nhịp
         trôi qua trong chưa đầy một giây và báo nhầm ngay. */
      /* CHƯA TẢI XONG KHÁC HẲN VỚI KẸT — bản 0.26.4 gộp hai thứ này làm một, và đó
         là lỗi của chính tôi. Số liệu thật từ máy chủ máy 19/09/2026:
         «nap=0 mang=2 loi=0», tức phần tử ĐANG TẢI và CHƯA nhận được byte nào,
         không hề có lỗi. Đường phục hồi vốn dành cho ca "có dữ liệu mà đồng hồ
         đứng"; nổ trong lúc chưa có dữ liệu là cướp tiếng của một luồng có thể
         đang chạy tốt, rồi đưa về khung YouTube — mà khung ấy iOS treo khi tắt
         màn hình, nên chính bản sửa lại làm mất đúng tính năng người dùng cần.
         Nay tách hai đường: CÓ dữ liệu mà không nhúc nhích thì mới trả tiếng về
         khung; còn đang tải mà chưa có gì thì CHỜ, và chỉ nói thật là chưa lấy
         được tiếng — không tự ý đổi nguồn phát của người dùng. */
      const coDuLieu = audio.readyState >= 2;   // HAVE_CURRENT_DATA trở lên
      if (tiengDangChay || audio.paused || this._tiengChayLuc === undefined) this._tiengChayLuc = Date.now();
      const doiQua = Date.now() - this._tiengChayLuc;
      if (!audio.paused && !coDuLieu && doiQua > 12000) {
        /* ĐANG TẢI MÀ 12 GIÂY CHƯA CÓ MỘT BYTE NÀO — trong khi máy chủ giao byte
           đầu tiên sau 0,16 giây. Đo 20/09/2026 trên CHÍNH đường trình duyệt đi,
           gồm cả chặng vé đã ký qua Home Assistant: mã 206, Content-Range đầy đủ.
           Và lỗi xảy ra GIỐNG HỆT ở add-on lẫn c2a, ở Safari lẫn app — máy phát
           vô can, byte có sẵn ở đầu kia mà WebKit không kéo về.
           Thứ duy nhất còn tranh chỗ là KHUNG YOUTUBE đang phát ngay trên trang:
           iOS chỉ cho một phần tử phát chạy thật, nên khung video chiếm đường và
           phần tử âm thanh xếp hàng mãi — không lỗi, không dữ liệu, đúng bộ số
           «nap=0 mang=2 loi=0» thu được hai lần độc lập.
           GỠ ĐỐI THỦ, ĐỪNG ĐẦU HÀNG. Bản 0.26.4 trả tiếng về cho khung, mà iOS
           treo khung nhúng lúc tắt màn — tức nó vứt đúng thứ người dùng vừa chọn.
           Ở đây làm ngược lại: đóng hình, giữ tiếng trên máy, vì phần tử âm thanh
           mới là thứ sống sót qua lúc tắt màn. Dùng lại «_listenOnly» vốn đã làm
           đúng việc đó (đóng hình, giữ tiếng) — không viết đường thứ hai.
           BẢN SỬA NÀY TỰ CHỨNG MINH: nghe được tiếng thì giả thuyết đúng; vẫn im
           thì nó sai, và dòng nhắn nói rõ để chủ máy báo lại. */
        this._tiengChayLuc = Date.now();
        if (video.open && video.followsDevice) {
          /* ĐỪNG CƯỚP CÁI NGƯỜI DÙNG VỪA BẤM. Bản 0.26.9 đóng hình để nhường đường
             cho tiếng, và chủ máy báo ngay: "bật video để xem thì không được trên
             iOS". Ghép với báo cáo trước đó ("nghe khi tắt màn hình không chạy") thì
             ra gốc rễ: iPhone KHÔNG cho vừa chạy khung nhúng vừa chạy phần tử âm
             thanh riêng. Hai bản sửa trước đều tự ý quyết thay người dùng — 0.26.4
             giữ hình nên mất tiếng lúc tắt màn, 0.26.9 giữ tiếng nên mất hình.
             CHỌN THEO Ý ĐỊNH ĐÃ NÊU, đó là thứ duy nhất không phải đoán: họ bấm
             "xem" thì GIỮ HÌNH và trả tiếng về chính khung ấy. Còn muốn nghe khi tắt
             màn thì đã có nút tai nghe — đường đó «_closeVideo» trước rồi mới phát
             nên không có gì tranh chỗ. Nói thẳng giới hạn ra, kèm lối đi thay thế,
             thay vì lặng lẽ vứt một nửa yêu cầu.
             Thứ tự BẮT BUỘC: trả tiếng về khung TRƯỚC, rồi mới dừng bộ phát — «stop»
             báo ngay cho bên nghe, mà lúc ấy cờ bám-tiếng phải đã tắt, nếu không
             «_deviceAudioChanged» lại đi đóng video. */
          this._traTiengVeKhung();
          deviceAudio.stop();
          /* LỜI NHẮN PHẢI ĐÚNG MÁY ĐANG CẦM. Chủ máy gửi ảnh 20/09/2026: điện thoại
             Android mà hiện câu nói về iPhone — vừa sai vừa làm người đọc đi tìm
             nhầm chỗ. Giới hạn "một luồng một lúc" là của iOS; trên Android mà nhánh
             này nổ thì nguyên nhân KHÁC, nên phải nói khác và phải kèm số đo.
             Đây là chỗ tách nền tảng còn sót lại sau 0.26.22 — xem «laIOS». */
          this._setStatus(laIOS()
            ? "iPhone không cho vừa xem video vừa nghe khi tắt màn hình."
              + " Đang ưu tiên xem — chạm vào video để nghe."
              + " Muốn nghe cả khi tắt màn thì bấm nút tai nghe."
            : "Chưa lấy được tiếng để nghe khi tắt màn hình — đang trả tiếng về video."
              + " Chạm vào video để nghe."
              + ` [nap=${audio.readyState} mang=${audio.networkState}`
              + ` loi=${audio.error ? audio.error.code : 0}`
              + ` nguon=${audio.currentSrc ? 1 : 0} dom=${audio.isConnected ? 1 : 0}]`, true);
          return;
        }
        /* Thêm hai số nữa vì bốn số cũ chưa đủ phân định: «nguon» cho biết phần tử
           đã CHỌN ĐƯỢC nguồn phát chưa (rỗng ⇒ nó chưa hề bắt đầu lấy địa chỉ), và
           «dom» cho biết nó có nằm trong trang không — đúng hai thứ nghi ngờ còn lại
           sau khi gỡ khung video mà tiếng vẫn không chạy. */
        this._setStatus(
          `Chưa lấy được tiếng từ máy phát — vẫn đang tải. [nap=${audio.readyState}`
          + ` mang=${audio.networkState} loi=${audio.error ? audio.error.code : 0}`
          + ` nguon=${audio.currentSrc ? 1 : 0} dom=${audio.isConnected ? 1 : 0}]`, true);
      }
      if (!audio.paused && coDuLieu && doiQua > 8000) {
        this._tiengChayLuc = undefined;
        // Trả tiếng về khung TRƯỚC khi dừng bộ phát: «stop» báo cho bên nghe ngay,
        // mà lúc ấy cờ bám-tiếng phải đã tắt, nếu không nó lại đi mở lại video.
        /* IN KÈM SỐ LIỆU CỦA CHÍNH PHẦN TỬ ÂM THANH. Tới đây đã biết "tiếng không
           chạy", nhưng KHÔNG biết vì sao, mà bốn con số dưới đây phân biệt được ba
           nguyên nhân dẫn tới ba cách sửa khác hẳn nhau:
             nap=0  (HAVE_NOTHING) + mang=2 (LOADING) → đang chờ dữ liệu, nghẽn mạng
             nap>=2 + giây đứng yên                    → có dữ liệu mà bị chặn phát,
                                                         tức chuỗi cử chỉ người dùng
             loi!=0                                    → lỗi tải/giải mã thật
           Không có bốn số này thì chỉ còn đường đoán, mà đoán mò về hành vi WebKit
           đã sai ba lần trong ngày. Người dùng tái hiện một lần là biết chắc. */
        const soLieu = `nap=${audio.readyState} mang=${audio.networkState}`
          + ` loi=${audio.error ? audio.error.code : 0} giay=${giayTieng.toFixed(1)}`;
        this._traTiengVeKhung();
        deviceAudio.stop();
        this._setStatus(
          `Máy này mở được tiếng nhưng không chạy — chạm vào video để nghe. [${soLieu}]`, true);
        return;
      }
      /* CÓ ĐỔI KHÔNG ≠ CÓ TIẾN KHÔNG — và đúng khe hở này là ca iOS của chủ máy.
         Chủ máy chốt 20/09/2026: "tôi đang nói iOS, chứ Android lại bình thường".
         Hàng rào cũ («tiengDangChay») chỉ hỏi giây có KHÁC nhịp trước không. Trên
         iPhone, WebKit cắt luồng rồi cho chạy lại từ đầu, nên giây bò 0 → 0,2 → 0
         → 0,3 → 0… tức ĐỔI liên tục mà chẳng đi tới đâu. Phép thử cũ cho lọt hết,
         cửa mở, và dòng dưới kéo hình về gần 0 cứ bốn giây một lần — đúng cảnh
         "video reset về 0 liên tục". Android không dựng lại được vì bộ phát của nó
         không cắt luồng kiểu ấy, nên lỗi chỉ hiện ở một phía.
         «_dongHoChay» hỏi đúng câu còn thiếu: có tiến được ít nhất một nửa quãng
         thời gian thật đã trôi không. Vẫn giữ «tiengDangChay» cho bộ dò kẹt bên
         trên, vì ở đó "nhúc nhích một cái là chưa chết" mới là câu hỏi đúng. */
      if (!audio.paused && tiengDangChay && Date.now() >= this._lastVideoSeekAt + 4000
        && this._dongHoChay("tieng-may", "may", giayTieng)
        && Math.abs(giayTieng - this._videoTimeNow()) > 2) {
        this._seekPicture(giayTieng);
      }
      return;
    }
    if (!video.open || !video.withSpeakers || !video.ready || !this._hass) return;
    const pending = this._pendingSpeakerSeek;
    if (pending) {
      const speaker = this._hass.states[pending.entityId];
      if (Date.now() - pending.at > 60000) {
        this._pendingSpeakerSeek = null;
      } else if (speaker?.state === "playing") {
        this._pendingSpeakerSeek = null;
        if (this._supportsFeature(pending.entityId, 2)) {
          // The speaker joined a video already playing here: move the speaker, not the picture.
          this._hass.callService("media_player", "media_seek", {
            entity_id: pending.entityId,
            seek_position: Math.round(pending.from + (Date.now() - pending.at) / 1000),
          }).catch(() => {});
          this._lastVideoSeekAt = Date.now() + 5000;
        }
      }
      return;
    }
    const primary = this._activeSpeakers()[0];
    if (!primary) return;
    const speaker = this._hass.states[primary];
    if (Date.now() < this._mirrorHoldUntil || !this._speakerPlaysItem(speaker, this._focusedSession())) return;
    if (speaker.state === "paused" && [1, 3].includes(video.state)) this._videoCommand("pauseVideo");
    if (speaker.state === "playing" && [-1, 2, 5].includes(video.state)) this._videoCommand("playVideo");
    // Đồng hồ lấy ở loa DẪN NHỊP, cùng một loa mà thanh tiến trình đang đọc.
    const nhip = this._loaDanNhip();
    const speakerTime = nhip ? this._speakerPosition(nhip) : null;
    if (speaker.state !== "playing" || speakerTime === null || Date.now() < this._lastVideoSeekAt + 5000) return;
    // The speaker starts a few seconds after the picture (its stream is prepared
    // server-side), so the muted picture follows the speaker's reported position.
    /* NHƯNG CHỈ KHI ĐỒNG HỒ LOA THẬT SỰ CHẠY. Loa báo kẹt (hoặc báo mãi một con
       số) thì hình đang chạy tới 0:03 là lệch quá 2 giây, và dòng dưới kéo nó về
       chỗ kẹt — cứ 5 giây một lần, đúng cảnh "video reset về 0 liên tục". Nhánh
       nghe-trên-máy đã có hàng rào này từ 19/09; nhánh loa thì chưa, nên lỗi cũ
       vẫn còn nguyên một nửa. */
    if (!this._dongHoChay("hinh", nhip, speakerTime)) return;
    // Số NGOẠI SUY thì không được tua hình — xem «_nhipDoDuoc». Thiếu chốt này,
    // giả lập cho thấy hình đang ở giây 1–8 bị quăng tới giây 91 rồi 97.
    if (!this._nhipDoDuoc(nhip)) return;
    /* KHUNG ĐANG MANG TIẾNG thì mỗi cú tua là một lần tiếng nhảy trong tai người
       nghe. Khung câm lệch 2 giây thì tua cho khớp môi; khung có tiếng chỉ chữa khi
       lệch tới mức nghe ra là hai nơi đang ở hai chỗ khác nhau. */
    /* KHUNG VỪA MỞ THÌ ĐỪNG TUA. Trình phát mất vài giây mới chạy ổn định; tua vào
       quãng ấy là cú giật đầu tiên người nghe gặp, mà lệch lúc đó chỉ là do nó chưa
       kịp chạy. «moUL» ghi lúc mở khung. */
    if (video.soundOnly && Date.now() - video.moUL < 6000) return;
    const nguongLech = video.soundHere ? 5 : 2;
    if (Math.abs(speakerTime - this._videoTimeNow()) > nguongLech) {
      this._seekPicture(speakerTime);
    }
  }

  _toggleVideoExpanded() {
    const player = this.shadowRoot.querySelector(".player");
    const expand = !player.classList.contains("expanded");
    player.classList.toggle("expanded", expand);
    if (!expand) player.classList.remove("rotated");
    // Some dashboard layouts contain their cards, which traps a fixed overlay
    // inside the card; fall back to the browser's fullscreen mode there.
    if (expand && player.getBoundingClientRect().width < window.innerWidth * 0.9) {
      player.classList.remove("expanded");
      this._videoFullscreen();
      return;
    }
    this._syncVideoExpandButton();
  }

  /** The rotate button: for phones whose rotation is locked (the card can't turn the screen). */
  _toggleRotated() {
    const player = this.shadowRoot.querySelector(".player");
    if (!player.classList.contains("expanded") && this.shadowRoot.fullscreenElement !== player) return;
    player.classList.toggle("rotated");
    this._syncVideoExpandButton();
  }

  _syncVideoExpandButton() {
    const button = this.shadowRoot.querySelector(".video-expand");
    const expanded = this.shadowRoot.querySelector(".player").classList.contains("expanded");
    button.querySelector("ha-icon").setAttribute("icon", expanded ? "mdi:arrow-collapse" : "mdi:arrow-expand");
    button.setAttribute("aria-label", expanded ? "Thu nhỏ video" : "Phóng to video");
    button.title = expanded ? "Thu nhỏ" : "Phóng to";
    const player = this.shadowRoot.querySelector(".player");
    const big = expanded || this.shadowRoot.fullscreenElement === player;
    if (!big) player.classList.remove("rotated");
    const rotate = this.shadowRoot.querySelector(".video-rotate");
    const rotated = player.classList.contains("rotated");
    rotate.hidden = !(big && this._video.open);
    rotate.querySelector("ha-icon").setAttribute("icon", rotated ? "mdi:phone-rotate-portrait" : "mdi:phone-rotate-landscape");
    rotate.setAttribute("aria-label", rotated ? "Xoay lại dọc" : "Xoay ngang 90°");
    rotate.title = rotated ? "Xoay lại dọc" : "Xoay ngang 90° (máy đang khoá xoay)";
    // Expanded or not any more: controls on, and the hide timer (re)starts when expanded.
    this._wakeControls();
  }

  _videoFullscreen() {
    const player = this.shadowRoot.querySelector(".player");
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
      return;
    }
    if (player.classList.contains("rotated")) {
      // Leaving the turned page-cover used where the browser has no fullscreen.
      player.classList.remove("rotated", "expanded");
      this._syncVideoExpandButton();
      return;
    }
    // The whole player goes fullscreen so the card's buttons stay usable there.
    const request = player.requestFullscreen || player.webkitRequestFullscreen;
    if (!request) {
      // iPhone browsers and apps: no element fullscreen. Cover the page and turn the
      // picture while the phone is upright.
      player.classList.add("expanded", "rotated");
      this._syncVideoExpandButton();
      return;
    }
    Promise.resolve(request.call(player, { navigationUI: "hide" }))
      .then(async () => {
        // Phones: landscape for the 16:9 picture. Chrome on Android turns the screen;
        // where the lock is refused or missing (the Home Assistant app), turn the picture.
        try {
          if (!screen.orientation?.lock) throw new Error("orientation_lock_unsupported");
          await screen.orientation.lock("landscape");
        } catch (_error) {
          if (document.fullscreenElement) player.classList.add("rotated");
        }
        this._syncVideoExpandButton();
      })
      .catch(() => {
        if (!document.fullscreenElement) {
          this._setStatus("Không mở được toàn màn hình — dùng nút toàn màn hình trong khung video.", true);
        }
      });
  }

  _closeVideo() {
    if (this._video.picture) this._leavePicture();
    this._awayPictureOk = false;
    clearInterval(this._henNhuongTieng);
    this._henNhuongTieng = null;
    clearInterval(this._henCanhChiTieng);
    this._henCanhChiTieng = null;
    this._dungThucTieng();
    clearTimeout(this._soundCheckTimer);
    this._soundHintShown = false;
    clearInterval(this._videoTimer);
    clearInterval(this._videoHandshakeTimer);
    this._videoTimer = null;
    window.removeEventListener("message", this._onVideoMessage);
    this._pendingSpeakerSeek = null;
    this._video = this._idleVideo();
    const player = this.shadowRoot?.querySelector(".player");
    if (!player) return;
    this.shadowRoot.querySelector(".video-frame").replaceChildren();
    player.classList.remove("expanded", "rotated");
    this._syncVideoExpandButton();
    this._syncNowPlaying();
    this._updateTransportState();
  }

  async _playResult(item, button, index = -1, watch = true, playlist = null) {
    const source = item.source || this._source;
    const requestedCount = this._selectedPlayers.size;
    const isVideo = this._isVideoItem(item, source);
    // Đã chọn xong bài: nhường màn hình cho phần đang phát, danh sách thu về một thanh.
    this._thuGonKetQua(item);
    if (!requestedCount) {
      // No speaker ticked: listen or watch right here, with the results (or the
      // playlist) as the queue.
      const queue = (playlist ? playlist.items : this._results.includes(item) ? this._results : [item])
        .map((entry) => ({ ...entry, source: entry.source || source }));
      const position = Math.max(0, index >= 0
        ? index
        : queue.findIndex((entry) => (entry.url || entry.id) === (item.url || item.id)));
      deviceAudio.entryId = this._entryId();
      const name = item.title || item.id;
      if (watch && isVideo && this._sameSong(deviceAudio.item, item)) {
        // The song being heard: open its video where the sound is, don't start over.
        this._watchCurrent();
        return;
      }
      /* BÀI TRỰC TIẾP: bấm nghe thì CHUYỂN SANG XEM, đừng bỏ qua.
         Chủ máy chốt 20/09/2026: "thì sẽ không phải bỏ qua". Đúng — bài trực tiếp
         chỉ có bản kê luồng HLS, mà thẻ «audio» của Chrome không phát được, nhưng
         KHUNG YOUTUBE thì phát tốt. Nên thay vì báo lỗi rồi đứng im, mở hình lên là
         có tiếng ngay.
         (Loa thì không vướng gì: đo 20/09/2026, bản kê dùng địa chỉ TUYỆT ĐỐI nên
         loa Cast tự đi lấy từng đoạn được — đường ra loa vẫn đi như cũ.) */
      if (!watch && isVideo && deviceAudio.laTrucTiep(item)) {
        this._queue = queue;
        this._queueIndex = position;
        if (deviceAudio.item || deviceAudio.along) deviceAudio.stop();
        this._openVideo(item, { withSpeakers: false });
        this._setStatus(`“${name}” đang phát trực tiếp nên không nghe riêng tiếng`
          + " được — đã mở hình để nghe.");
        return;
      }
      if (watch && isVideo) {
        this._queue = queue;
        this._queueIndex = position;
        if (listenScreenOff() && !laTao()) {
          // The sound comes from the audio element (it goes on with the screen off),
          // the picture follows it muted.
          deviceAudio.listen(queue[position], queue, position);
          this._openVideo(item, { withSpeakers: false, followsDevice: true });
          this._setStatus(`Đang xem “${name}”, tiếng phát trên máy này cả khi tắt màn hình.`);
          return;
        }
        /* MÁY NHÀ TÁO: bấm XEM trong lúc công tắc "nghe khi tắt màn hình" đang bật
           thì ĐỪNG giao tiếng cho phần tử âm thanh — giữ nguyên trong khung.
           Đây chính là đường đã đưa chủ máy vào cảnh trong ảnh chụp Safari trên
           iMac ngày 20/09/2026: hình chạy, phần tử âm thanh đứng ở «mang=3»
           (NETWORK_NO_SOURCE) nên không có tiếng, và thẻ phải xin một cú chạm.
           Xem «laSafari» để biết vì sao máy Mac để bàn trước đây lọt ra ngoài. */
        if (listenScreenOff() && laTao()) {
          /* KHÔNG gọi «deviceAudio.unlock» ở đây, dù nhánh xem thường có gọi: nó
             phát một dòng im lặng qua phần tử âm thanh, mà iOS chỉ cho MỘT luồng
             chạy một lúc (Apple ghi rõ) — đúng thứ sẽ tranh chỗ với tiếng trong
             khung. Dòng im lặng duy nhất được phép chạy là của «_giuTiengNen»,
             vì nó lặp vô hạn và là thứ giữ cho trang không bị cắt khi tắt màn. */
          if (deviceAudio.item || deviceAudio.along) deviceAudio.stop();
          this._openVideo(item, { withSpeakers: false });
          this._giuTiengNen();
          this._setStatus(`Đang xem “${name}”; tiếng giữ trong video nên tắt màn hình vẫn nghe tiếp.`);
          return;
        }
        if (deviceAudio.item || deviceAudio.along) deviceAudio.stop();
        // Unlocked inside this tap: if YouTube refuses the video here, its sound plays instead.
        deviceAudio.unlock();
        this._openVideo(item, { withSpeakers: false });
        this._setStatus(`Đang xem “${name}” trên thẻ. Chọn loa để phát tiếng ra loa.`);
        return;
      }
      /* MÁY NHÀ TÁO NGHE BẰNG KHUNG, KHÔNG BẰNG PHẦN TỬ ÂM THANH.
         Đo trên iPhone của chủ máy 21/09/2026, sau khi đã sửa xong tốc độ luồng:
         phần tử âm thanh nằm ở «nap=0 mang=2 loi=0 phat=cho» — tức lệnh phát không
         bị từ chối mà cũng không được chấp nhận, nó treo chờ dữ liệu, và dữ liệu
         không bao giờ tới. Tôi đã loại từng nghi can một, mỗi cái bằng một phép đo:
           · định dạng: itag 140, m4a/AAC — iPhone giải mã thừa sức
           · chữ ký: địa chỉ tự mang «authSig», sống 1 giờ, không hết hạn
           · cú bấm: «cuchi=1», cử chỉ còn hiệu lực
           · tranh chấp: «dem=1m/0k», đúng một phần tử, không khung nào
           · đường truyền: cùng địa chỉ ấy, «fetch» của chính trang lấy được (206,
             ~120ms); đo lại qua Cloudflare với danh tính Safari VÀ AppleCoreMedia
             đều lấy 3,45 MB trong 1,4 giây
         Không còn nghi can nào ngoài chính trình phát của iOS. Mà khung YouTube thì
         chạy — chủ máy xác nhận cùng ngày: "nghe bài ghim bằng video được luôn".
         Nên máy nhà Táo đi đường khung, thu còn một điểm ảnh để chỉ còn tiếng. Đây
         cũng đúng cách thẻ «phicomm-r1-card» làm, thứ chạy được trên máy chủ máy.
         Nguồn không phải YouTube (Zing, Facebook) không có khung để mượn, đành giữ
         phần tử âm thanh — chưa có đường nào khác. */
      if (laTao() && isVideo && source === "youtube" && VIDEO_ID.test(String(item.id || ""))
        && !deviceAudio.laTrucTiep(item)) {
        this._queue = queue;
        this._queueIndex = position;
        if (deviceAudio.item || deviceAudio.along) deviceAudio.stop();
        /* HIỆN KHUNG RA ĐÃ, THU LẠI SAU KHI NÓ ĐÃ CHẠY.
           0.26.50 mở thẳng ở chế độ một điểm ảnh, và hộp đen trên iPhone của chủ máy
           18:24 ngày 21/09/2026 cho thấy đó là ngõ cụt:
             chitieng=1 (thu bé)  → trangthai=-1 suốt 8 giây, chưa hề bắt đầu
             chitieng=0 (hiện ra) → trangthai=1, giay=2.4, đang chạy
           iOS đòi một cú chạm vào CHÍNH video, mà khung một điểm ảnh thì không ai
           chạm vào được — kể cả chủ máy: "không tự động phát video nhỉ, phải kích
           vào". Nên mở ra cho chạm, rồi tự thu khi đã chạy. */
        this._ngheBangKhungMotMinh(item, queue, position);
        this._setStatus(`Đang nghe “${name}” trên máy này.`);
        return;
      }
      if (this._video.open) this._closeVideo();
      deviceAudio.listen(queue[position], queue, position);
      this._setStatus(`Đang nghe “${name}” trên máy này.`);
      return;
    }
    const entityIds = this._playTargets(source);
    const session = this._focusedSession();
    if (watch && isVideo && !this._video.open && session && this._sameSong(session, item)
      && entityIds.length && entityIds.every((entityId) => session.output_entity_ids.includes(entityId))) {
      // The ticked speakers already play this song: show the picture where they are,
      // don't send the song again from the start.
      this._openVideo(item, { withSpeakers: true });
      return;
    }
    if (!entityIds.length) {
      this._setStatus("Thiết bị đã chọn không hỗ trợ nguồn này.", true);
      return;
    }
    const entryId = this._entryId();
    if (!entryId) {
      this._setStatus("Không tìm thấy config entry của integration.", true);
      return;
    }
    button.disabled = true;
    this._setStatus(`Đang phát “${item.title || item.id}”…`);
    try {
      // The selected speakers become one session (they leave any other session);
      // the integration plays the session's next songs when each one ends.
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source,
        target: item.url || item.id,
        entity_id: entityIds,
        media_content_type: item.media_content_type,
        // A saved playlist: the speakers' queue is the whole playlist.
        ...(playlist ? { playlist_id: playlist.id } : {}),
      });
      if (deviceAudio.item) deviceAudio.stop();
      if (watch && isVideo) {
        // The picture follows the speakers: the next video synced.
        this._openVideo(item, { withSpeakers: true });
      } else if (this._video.open) {
        /* BẤM "NGHE (CHỈ TIẾNG)" LÀ NÓI RÕ KHÔNG MUỐN HÌNH — đóng hình lại.
           Trước đây dòng điều kiện gộp cả hai ý làm một: hễ đang mở hình thì bài
           mới cũng mở hình, bất kể người dùng bấm nút nào. Kết quả đúng như chủ
           máy báo 20/09/2026: "giờ chọn chỉ nghe, hình tai nghe, nó lại ra mặc
           định video". Ý định đã nêu rõ ở nút bấm thì không được đoán lại. */
        this._closeVideo();
      }
      const ignored = requestedCount - entityIds.length;
      this._setStatus(
        ignored
          ? `Đã gửi tới ${entityIds.length} thiết bị; bỏ qua ${ignored} thiết bị không tương thích.`
          : `Đã gửi tới ${entityIds.length} thiết bị.`,
      );
    } catch (error) {
      this._setStatus(error?.message || "Không thể phát bài đã chọn.", true);
    } finally {
      button.disabled = false;
    }
  }

  /** Thẻ còn hàng đợi dùng được cho phiên loa hiện tại không?
   *
   *  Chỉ đúng khi phiên bên máy chủ có ĐÚNG MỘT bài — tức bài ấy do thẻ giao sang chứ
   *  không phải do máy chủ dựng cả hàng đợi. Phiên nào có hàng đợi thật thì để máy chủ
   *  lo, thẻ đừng tranh.
   */
  _hangCuaTheDungDuoc(step) {
    const session = this._focusedSession();
    if (!session || Number(session.queue_size || 0) > 1) return false;
    const target = this._queueIndex + step;
    return this._queueIndex >= 0 && target >= 0 && target < this._queue.length;
  }

  /** Gửi một bài của hàng đợi thẻ tới đúng những loa của phiên đang xem. */
  async _guiBaiToiLoa(item, entityIds) {
    const entryId = this._entryId();
    if (!item || !entryId || !entityIds?.length) return;
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source: item.source || "youtube",
        target: item.url || item.id,
        entity_id: [...entityIds],
      });
      this._setStatus(`Đang gửi “${item.title || item.id}” tới loa…`);
    } catch (error) {
      this._setStatus(error?.message || "Không chuyển được bài.", true);
    }
  }

  async _skip(step) {
    if (deviceAudio.item) {
      if (!deviceAudio.next(step)) this._setStatus(step > 0 ? "Đã ở cuối hàng đợi." : "Đã ở đầu hàng đợi.");
      return;
    }
    if (this._video.open && !this._video.withSpeakers) {
      const target = this._queueIndex + step;
      if (this._queueIndex < 0 || target < 0 || target >= this._queue.length) {
        this._setStatus(step > 0 ? "Đã ở cuối hàng đợi." : "Đã ở đầu hàng đợi.");
        return;
      }
      this._queueIndex = target;
      /* GIỮ NGUYÊN VAI CỦA KHUNG. Đang nghe bằng khung thu nhỏ (đường của máy nhà
         Táo) mà qua bài thì bài sau phải vẫn là "chỉ nghe", không bung thành video —
         nếu không, mỗi lần chuyển bài là màn hình lại hiện video mà người dùng không
         hề yêu cầu. */
      const dangChiNghe = this._video.soundOnly;
      /* MỞ RA ĐÃ, RỒI TỰ THU — y như bài đầu. Mở thẳng ở dạng thu nhỏ là đánh cược
         rằng iOS cho chạy tiếp mà không cần chạm; cược sai thì người dùng kẹt với một
         khung một điểm ảnh không chạm vào được. Mở ra rồi thu lại khi trình phát báo
         đang chạy thì đúng trong cả hai trường hợp. */
      this._openVideo(this._queue[target], {
        withSpeakers: false,
        soundHere: true,
        soundOnly: false,
      });
      if (dangChiNghe) this._thuKhungKhiDaChay();
      return;
    }
    const session = this._focusedSession();
    if (!session) return;
    if (this._hangCuaTheDungDuoc(step)) {
      const target = this._queueIndex + step;
      const item = this._queue[target];
      this._queueIndex = target;
      await this._guiBaiToiLoa(item, session.output_entity_ids);
      return;
    }
    try {
      await this._hass.callService("tritue_youtube_player", "skip", {
        entry_id: this._entryId(),
        session_id: session.session_id,
        step,
      });
    } catch (error) {
      this._setStatus(error?.message || "Không chuyển được bài.", true);
    }
  }

  async _onSpeakerAdded(entityId) {
    // Watching a video alone: the ticked speaker takes over its sound. Otherwise
    // ticking only focuses the speaker (see "Cho … nghe cùng" to join a song).
    if (this._video.open && !this._video.withSpeakers) {
      await this._speakerJoinsVideo(entityId);
      return;
    }
    /* CHỈ NGHE trên máy mà tích loa: loa nhận bài ngay. Trước đây nhánh này không
       tồn tại nên tích loa xong không có gì xảy ra — chủ máy phải bấm lại bài mới
       ra tiếng. Yêu cầu 20/09/2026: "đang phát mà chọn loa thì phát được luôn âm
       thanh, không cần phải chuyển bài".
       «along» là đang nghe GHÉP theo loa, tức loa đã có bài rồi — không đụng vào. */
    if (deviceAudio.item && !deviceAudio.along) {
      await this._loaNhanBaiDangNghe(entityId);
    }
  }

  async _loaNhanBaiDangNghe(entityId) {
    const item = deviceAudio.item;
    const state = this._hass?.states?.[entityId];
    const name = state?.attributes?.friendly_name || entityId;
    const entryId = this._entryId();
    if (!item || !state || state.state === "unavailable" || !entryId) return;
    const nguon = item.source || "youtube";
    if (!this._supportsFeature(entityId, 512) || !this._supportsSource(entityId, nguon)) {
      this._setStatus(`${name} không nhận tiếng ${TEN_NGUON[nguon] || nguon}.`, true);
      return;
    }
    // Giây đang nghe, để loa vào đúng chỗ ấy chứ không phát lại từ đầu bài.
    const giay = Number(deviceAudio.audio()?.currentTime) || 0;
    const moc = Date.now();
    const ten = item.title || item.id;
    this._setStatus(`Đang chuyển “${ten}” sang ${name}…`);
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source: nguon,
        target: item.url || item.id,
        entity_id: [entityId],
      });
      this._dongBoLoaVeGiay(entityId, giay, moc);
      /* GIỮ LẠI HÀNG ĐỢI CỦA MÁY. Phiên bên máy chủ chỉ có ĐÚNG MỘT bài (ta gửi một
         bài), nên không giữ thì hai nút qua bài / lùi bài bị khoá ngay khi giao xong —
         chủ máy báo 21/09/2026: "mất cả nút qua bài hoặc lùi bài", và nói rõ là nút vẫn
         hiện nhưng bấm không được. Xem «_hangCuaTheDungDuoc». */
      if (deviceAudio.queue.length > 1 && deviceAudio.index >= 0) {
        this._queue = deviceAudio.queue.slice();
        this._queueIndex = deviceAudio.index;
      }
      /* GIỮ LUÔN TIẾNG TRÊN MÁY. Chủ máy chốt 21/09/2026: tích loa lúc đang nghe thì
         "giữ luôn cả trên máy". Trước đây thẻ tắt tiếng máy ngay khi loa lên tiếng, nên
         muốn nghe cả hai lại phải bấm thêm một nút — mà đúng nút ấy đang hỏng. Nay
         không tắt gì cả: máy hát tiếp bài của nó, loa hát cùng bài từ cùng chỗ. */
      /* ĐỔI VAI: từ «nghe một mình» thành «nghe cùng loa» — mà KHÔNG đụng vào tiếng
         đang chạy (không đặt lại «src», không gọi phát lại, nên không có quãng hụt).
         Thiếu bước này thì thẻ vẫn tự coi là đang nghe MỘT MÌNH trong khi thực tế đã
         có loa, nên nút «Nghe trên máy này» không bao giờ hiện lại — chủ máy báo
         21/09/2026 kèm ảnh chụp lúc 17:24: "đang chỉ nghe, tích vào loa sao không ra
         chế độ nghe trên máy này".
         «alongKey» đặt đúng bài đang chạy để vòng chạy theo loa («loadAlong») biết bài
         này đã có rồi mà không nạp lại. */
      deviceAudio.along = true;
      deviceAudio.alongKey = deviceAudio.khoaLuong(item);
      deviceAudio.item = null;
      this._syncNowPlaying();
      this._updateTransportState();
      this._setStatus(`${name} đang phát “${ten}” tiếp từ chỗ đang nghe.`);
    } catch (error) {
      this._setStatus(error?.message || `Không phát được ra ${name}.`, true);
    }
  }

  /** NHƯỜNG TIẾNG CHO LOA ĐÚNG LÚC LOA LÊN TIẾNG, ĐỪNG CẮT TRƯỚC.
   *
   *  Gửi bài cho loa xong mà tắt tiếng trên máy ngay thì sinh một quãng IM LẶNG: máy
   *  chủ còn giải bài, loa còn nạp đệm. Đo trên máy chủ 20/09/2026: riêng việc giải
   *  một bài YouTube đã mất 1,59 giây, chưa kể loa Cast còn vài giây nữa mới kêu. Với
   *  người nghe thì quãng ấy đúng là "mất tiếng".
   *
   *  Nên giữ tiếng trên máy tới nhịp ĐẦU TIÊN loa thật sự báo "playing". Quá 15 giây
   *  loa vẫn chưa lên tiếng thì thôi, không nhường nữa — loa hỏng thì ít nhất người
   *  dùng còn nghe được trên máy, thay vì mất cả hai.
   */
  _nhuongTiengChoLoa(entityId, nhuong) {
    clearInterval(this._henNhuongTieng);
    const batDau = Date.now();
    this._henNhuongTieng = setInterval(() => {
      const trangThai = this._hass?.states?.[entityId]?.state;
      if (trangThai !== "playing" && Date.now() - batDau < 15000) return;
      clearInterval(this._henNhuongTieng);
      this._henNhuongTieng = null;
      if (trangThai === "playing") nhuong();
    }, 400);
  }

  /** Đưa loa về đúng giây người dùng đang nghe — MỘT cú tua, ở nhịp đầu tiên loa
   *  thật sự báo "playing". Loa Cast mất vài giây mới bắt đầu, nên phải chờ thay
   *  vì tua ngay; và chỉ tua một lần, vì tua liên tiếp là sinh ra giật. */
  _dongBoLoaVeGiay(entityId, giay, moc) {
    if (giay < 3 || !this._supportsFeature(entityId, 2)) return;
    let xong = false;
    [1200, 2400, 3800, 6000].forEach((cho) => setTimeout(() => {
      if (xong || this._hass?.states?.[entityId]?.state !== "playing") return;
      xong = true;
      this._hass.callService("media_player", "media_seek", {
        entity_id: entityId,
        seek_position: Math.round(giay + (Date.now() - moc) / 1000),
      }).catch(() => {});
    }, cho));
  }

  async _joinSession(session, entityIds) {
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: this._entryId(),
        source: session.source,
        target: session.url || session.id,
        entity_id: entityIds,
        session_id: session.session_id,
        join: true,
      });
      this._setStatus("Đã cho nghe cùng bài đang phát.");
    } catch (error) {
      this._setStatus(error?.message || "Không thêm được loa vào bài đang phát.", true);
    }
  }

  async _speakerJoinsVideo(entityId) {
    // Watching on the card, then ticking a speaker: the speaker takes over the
    // sound, the card keeps the picture muted, and the two stay in step.
    const state = this._hass?.states?.[entityId];
    const name = state?.attributes?.friendly_name || entityId;
    const item = this._video.item;
    const entryId = this._entryId();
    if (!state || state.state === "unavailable" || !item || !entryId) return;
    /* Nguồn lấy từ CHÍNH bài đang xem, không gắn cứng "youtube": đang xem video
       Facebook mà tích loa thì hai dòng dưới vừa hỏi sai khả năng của loa, vừa gửi
       địa chỉ Facebook kèm nhãn nguồn YouTube — loa nhận một thứ nó không hiểu. */
    const nguon = item.source || "youtube";
    if (!this._supportsFeature(entityId, 512) || !this._supportsSource(entityId, nguon)) {
      this._setStatus(`${name} không nhận tiếng ${TEN_NGUON[nguon] || nguon}.`, true);
      return;
    }
    const videoTime = this._videoTimeNow();
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source: nguon,
        target: item.url,
        entity_id: [entityId],
      });
      this._pendingSpeakerSeek = { entityId, from: videoTime, at: Date.now() };
      this._video.withSpeakers = true;
      this._video.followsDevice = false;
      // Khung giữ tiếng tới lúc loa kêu rồi mới câm — xem «_nhuongTiengChoLoa».
      this._nhuongTiengChoLoa(entityId, () => {
        this._video.soundHere = false;
        this._videoCommand("mute");
        if (deviceAudio.item) deviceAudio.stop();
        this._syncNowPlaying();
      });
      this._syncNowPlaying();
      this._updateTransportState();
      this._setStatus(`${name} sắp phát; tiếng giữ trên thẻ tới khi loa kêu rồi tự tắt.`);
    } catch (error) {
      this._setStatus(error?.message || `Không phát được ra ${name}.`, true);
    }
  }

  async _onSpeakerRemoved(_entityId) {
    if (this._video.open && this._video.withSpeakers && !this._selectedPlayers.size) {
      // No speaker ticked any more: the card's video plays on its own with sound.
      this._video.withSpeakers = false;
      this._pendingSpeakerSeek = null;
      // Cùng lớp lỗi với «_toggleSoundHere»: dựng lại khung, đừng gửi «unMute».
      this._batTiengKhung();
      this._syncNowPlaying();
    }
  }

  async _togglePlay() {
    if (deviceAudio.item) {
      deviceAudio.toggle();
      return;
    }
    if (this._video.open && !this._video.withSpeakers) {
      if (!this._video.followsDevice && !this._video.picture && [-1, 5].includes(this._video.state)) {
        // Not started: the frame won't start without a tap inside it — this tap starts
        // the card's own sound and the muted picture follows.
        this._soundFromDevice();
        return;
      }
      this._videoCommand([1, 3].includes(this._video.state) ? "pauseVideo" : "playVideo");
      return;
    }
    const speakers = this._targetsForService("media_play_pause");
    if (!speakers.length) {
      this._setStatus("Chọn loa hoặc mở video để điều khiển.", true);
      return;
    }
    if (this._video.open) {
      const pausing = speakers.some((entityId) => this._hass.states[entityId]?.state === "playing");
      this._videoCommand(pausing ? "pauseVideo" : "playVideo");
      // HA reports the speakers' new state a moment later; don't let the sync undo this press meanwhile.
      this._mirrorHoldUntil = Date.now() + 4000;
    }
    await this._transport("media_play_pause");
  }

  async _transport(service) {
    const entityIds = this._targetsForService(service);
    if (!entityIds.length) {
      this._setStatus("Không có thiết bị đã chọn hỗ trợ lệnh này.", true);
      return;
    }
    const button = this.shadowRoot.querySelector(".play-pause");
    button.disabled = true;
    try {
      await this._hass.callService("media_player", service, { entity_id: entityIds });
      this._setStatus(`Đã gửi lệnh phát/tạm dừng tới ${entityIds.length} thiết bị.`);
    } catch (error) {
      this._setStatus(error?.message || "Không thể điều khiển thiết bị.", true);
    } finally {
      this._updateTransportState();
    }
  }

  async _stop() {
    if (deviceAudio.item) {
      deviceAudio.stop();
      if (this._video.open) this._closeVideo();
      this._setStatus("Đã dừng nghe trên máy này.");
      return;
    }
    /* KHUNG ĐANG MANG TIẾNG CHO MÁY NÀY thì "dừng" nghĩa là ĐÓNG HẲN, không phải
       gửi mỗi lệnh «stopVideo» rồi để khung nằm đó.
       Từ 0.26.50, máy nhà Táo nghe bằng khung nên «deviceAudio.item» rỗng — nhánh
       dừng ở trên không còn khớp, và nhánh này chỉ gửi một lệnh vào khung rồi đi
       tiếp. Người dùng báo 21/09/2026: "stop bằng nút điều khiển không dừng video". */
    if (!deviceAudio.item && this._video.open && this._video.soundHere
      && !this._video.withSpeakers) {
      this._closeVideo();
      this._thoiGiuTiengNen();
      this._setStatus("Đã dừng nghe trên máy này.");
      return;
    }
    if (this._video.open) this._videoCommand("stopVideo");
    const session = this._focusedSession();
    try {
      if (session) {
        // Stop the ticked speakers; the session ends only when all its speakers stop.
        const ticked = session.output_entity_ids.filter((id) => this._selectedPlayers.has(id));
        if (ticked.length && ticked.length < session.output_entity_ids.length) {
          await this._hass.callService("tritue_youtube_player", "remove_players", {
            entry_id: this._entryId(),
            entity_id: ticked,
          });
          this._setStatus(`Đã dừng ${ticked.length} loa; loa còn lại phát tiếp.`);
          return;
        }
        await this._hass.callService("tritue_youtube_player", "stop_session", {
          entry_id: this._entryId(),
          session_id: session.session_id,
        });
        this._setStatus(`Đã dừng ${session.output_entity_ids.length} thiết bị${this._video.open ? " và video" : ""}.`);
        return;
      }
      const entityIds = this._targetsForService("media_stop");
      if (!entityIds.length) {
        this._setStatus(this._video.open ? "Đã dừng video." : "Không có gì đang phát.", !this._video.open);
        return;
      }
      await this._hass.callService("media_player", "media_stop", { entity_id: entityIds });
      this._setStatus(`Đã dừng ${entityIds.length} thiết bị.`);
    } catch (error) {
      this._setStatus(error?.message || "Không thể dừng thiết bị.", true);
    }
  }

  _formatDuration(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value) || value <= 0) return "";
    const hours = Math.floor(value / 3600);
    const minutes = Math.floor((value % 3600) / 60);
    const rest = String(Math.floor(value % 60)).padStart(2, "0");
    return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
  }

  _showView(view) {
    /* MỘT CỬA VÀO duy nhất cho việc đổi khung. Lưu một playlist xong cũng tự nhảy
       sang khung Playlist, nên chặn ở đây thay vì vá từng chỗ gọi: Playlist bị ẩn
       trong cấu hình thì mọi đường vào đều quay về khung tìm kiếm. */
    const moPlaylist = view === "playlists" && this._config.show_playlist !== false;
    this._view = moPlaylist ? "playlists" : "search";
    const playlists = this._view === "playlists";
    // Hàng nút đã gộp làm một, nên chính nó lo việc tô sáng mục đang mở.
    this._updateSourceButtons();
    /* KHÔNG ẩn «.source-switch» nữa: nút Playlist giờ nằm trong chính hàng đó.
       Ẩn nó đi là ẩn luôn đường quay về YouTube/Zing — mở Playlist xong sẽ kẹt
       lại, không có nút nào để thoát. Trước đây ẩn được vì hàng tab riêng vẫn còn. */
    for (const selector of ["form", ".results", ".yt-suggested-section"]) {
      this.shadowRoot.querySelector(selector).hidden = playlists;
    }
    this.shadowRoot.querySelector(".playlist-panel").hidden = !playlists;
    this._syncSavePlaylist();
    if (playlists) this._loadPlaylists();
  }

  _syncSavePlaylist() {
    const value = this.shadowRoot.querySelector('input[type="search"]').value.trim();
    this.shadowRoot.querySelector(".save-playlist").hidden =
      this._view !== "search" || this._config.show_playlist === false || !PLAYLIST_LINK.test(value);
  }

  _syncPlaylistSubmit() {
    const value = this.shadowRoot.querySelector(".playlist-input").value.trim();
    const link = PLAYLIST_LINK.test(value) || /^(https?:\/\/|TTPL)/i.test(value);
    this.shadowRoot.querySelector(".playlist-submit").textContent = link ? "Lưu cả playlist" : "Tạo";
  }

  _playlistError(error) {
    const code = String(error?.body?.error || error?.error || error?.message || "");
    return PLAYLIST_ERRORS[code] || code || "Không thực hiện được lệnh playlist.";
  }

  async _loadPlaylists() {
    const entryId = this._entryId();
    if (!entryId || !this._hass) return;
    try {
      const payload = await this._hass.callApi("GET", `tritue_youtube_player/playlists?entry_id=${encodeURIComponent(entryId)}`);
      this._playlists = Array.isArray(payload.playlists) ? payload.playlists : [];
      this._renderPlaylists();
    } catch (error) {
      if (this._view === "playlists") this._setStatus(this._playlistError(error), true);
    }
  }

  /** One playlist command; `done(payload)` returns the status line to show. */
  async _playlistCommand(body, done, busy = null) {
    const entryId = this._entryId();
    if (!entryId) return null;
    if (busy) busy.disabled = true;
    try {
      const payload = await this._hass.callApi("POST", "tritue_youtube_player/playlists", { entry_id: entryId, ...body });
      this._playlists = Array.isArray(payload.playlists) ? payload.playlists : this._playlists;
      const message = done ? done(payload) : "";
      this._renderPlaylists();
      if (this._addMenuFor) this._renderAddMenu();
      if (message) this._setStatus(message);
      return payload;
    } catch (error) {
      this._setStatus(this._playlistError(error), true);
      return null;
    } finally {
      if (busy) busy.disabled = false;
    }
  }

  async _importPlaylist(text, fromSearch) {
    const value = String(text || "").trim();
    if (!value) return;
    const button = this.shadowRoot.querySelector(fromSearch ? ".save-playlist" : ".playlist-submit");
    this._setStatus("Đang đọc playlist — playlist dài có thể mất vài chục giây…");
    const payload = await this._playlistCommand({ action: "import", text: value }, (result) => {
      this._openPlaylist = result.playlist.id;
      if (!fromSearch) this.shadowRoot.querySelector(".playlist-input").value = "";
      return `Đã lưu “${result.playlist.name}” (${result.playlist.items.length} bài) vào Playlist.`;
    }, button);
    if (payload && fromSearch) this._showView("playlists");
  }

  _toggleAddMenu(row, item) {
    const open = this._addMenuFor?.row === row;
    this.shadowRoot.querySelectorAll(".add-menu").forEach((menu) => menu.remove());
    /* Hai bảng dùng CHUNG lớp .add-menu, nên dòng trên xoá luôn bảng chọn mục ghim
       nếu nó đang mở. Không xoá dấu vết của nó thì lần bấm ghim kế tiếp trên cùng
       dòng sẽ tưởng bảng còn mở và chỉ đóng, phải bấm hai lần mới hiện. */
    this._ghimMenuFor = null;
    this._addMenuFor = open ? null : { row, item };
    if (this._addMenuFor) {
      if (this._playlists === null) this._loadPlaylists().then(() => this._renderAddMenu());
      this._renderAddMenu();
    }
  }

  _renderAddMenu() {
    const target = this._addMenuFor;
    if (!target || !target.row.isConnected) return;
    target.row.querySelector(".add-menu")?.remove();
    const menu = document.createElement("div");
    menu.className = "add-menu";
    const done = (payload) => {
      this._addMenuFor = null;
      menu.remove();
      return payload.added
        ? `Đã thêm vào “${payload.playlist.name}”.`
        : `Bài này đã có trong “${payload.playlist.name}”.`;
    };
    for (const playlist of this._playlists || []) {
      const has = playlist.items.some((entry) => entry.source === target.item.source
        && (entry.id === target.item.id || entry.url === target.item.url));
      const button = document.createElement("button");
      button.type = "button";
      button.className = "add-to";
      const icon = document.createElement("ha-icon");
      icon.setAttribute("icon", has ? "mdi:check" : "mdi:playlist-music");
      const name = document.createElement("span");
      name.textContent = playlist.name;
      const count = document.createElement("span");
      count.className = "count";
      count.textContent = String(playlist.items.length);
      button.append(icon, name, count);
      button.addEventListener("click", () =>
        this._playlistCommand({ action: "add", id: playlist.id, items: [target.item] }, done, button));
      menu.append(button);
    }
    const form = document.createElement("form");
    const input = document.createElement("input");
    input.type = "text";
    input.maxLength = 80;
    input.placeholder = this._playlists?.length ? "Playlist mới…" : "Chưa có playlist — đặt tên để tạo…";
    input.setAttribute("aria-label", "Tên playlist mới");
    const create = document.createElement("button");
    create.type = "submit";
    create.className = "primary";
    create.textContent = "Tạo";
    form.append(input, create);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!input.value.trim()) return;
      this._playlistCommand({ action: "add", name: input.value.trim(), items: [target.item] }, done, create);
    });
    menu.append(form);
    target.row.append(menu);
  }

  /* Bảng chọn mục để ghim. Dựng theo đúng khuôn của bảng «thêm vào playlist» ngay ở
     trên: gắn vào chính dòng bài hát, và dùng lại lớp .add-menu nên không phải đẻ
     thêm kiểu dáng nào, trông cũng đồng bộ với thứ chủ máy đã quen. */
  _toggleGhimMenu(row, item, tenBai) {
    const dangMo = this._ghimMenuFor?.row === row;
    this.shadowRoot.querySelectorAll(".add-menu").forEach((menu) => menu.remove());
    this._addMenuFor = null;
    this._ghimMenuFor = dangMo ? null : { row, item, tenBai };
    if (this._ghimMenuFor) this._renderGhimMenu();
  }

  _renderGhimMenu() {
    const dich = this._ghimMenuFor;
    if (!dich || !dich.row.isConnected) return;
    dich.row.querySelector(".add-menu")?.remove();
    const menu = document.createElement("div");
    menu.className = "add-menu";
    const banGhi = {
      video_id: dich.item.id,
      source: dich.item.source || this._source,
      title: dich.item.title,
      artist: dich.item.channel,
      thumbnail_url: dich.item.thumbnail,
      duration_seconds: dich.item.duration,
    };
    const dong = () => {
      this._ghimMenuFor = null;
      menu.remove();
    };
    for (const muc of this._goiY?.groups || []) {
      const daCo = (muc.songs || []).some((bai) => bai.id === dich.item.id);
      const nut = document.createElement("button");
      nut.type = "button";
      nut.className = "add-to";
      const bieuTuong = document.createElement("ha-icon");
      bieuTuong.setAttribute("icon", daCo ? "mdi:check" : (muc.icon || "mdi:folder-music"));
      const ten = document.createElement("span");
      ten.textContent = muc.name;
      const dem = document.createElement("span");
      dem.className = "count";
      dem.textContent = String((muc.songs || []).length);
      nut.append(bieuTuong, ten, dem);
      nut.addEventListener("click", () => {
        dong();
        // Máy chủ lặng lẽ bỏ qua bài trùng; nói thẳng ra còn hơn để người dùng bấm
        // xong chẳng thấy gì đổi.
        if (daCo) {
          this._setStatus(`“${dich.tenBai}” đã có sẵn trong mục “${muc.name}”.`);
          return;
        }
        this._saveSuggestion({ action: "pin_song", id: muc.id, item: banGhi },
          `Đã gắn “${dich.tenBai}” vào mục “${muc.name}”.`);
      });
      menu.append(nut);
    }
    /* Tạo mục mới rồi ghim luôn bài vào đó — hai lệnh nối tiếp, vì máy chủ không có
       lệnh gộp. _saveSuggestion nuốt lỗi và chỉ báo ra dòng trạng thái, nên chờ xong
       tôi KHÔNG bắt được ngoại lệ; cách kiểm chắc chắn là dò lại danh sách xem mục
       vừa đặt tên đã có chưa. Cũng vì thế mà không chép hàm bỏ dấu tiếng Việt của máy
       chủ sang đây để tự đoán mã mục: cùng một logic nằm hai nơi là mầm sai về sau. */
    const form = document.createElement("form");
    const oTen = document.createElement("input");
    oTen.type = "text";
    oTen.maxLength = 80;
    oTen.placeholder = this._goiY?.groups?.length ? "Mục mới…" : "Chưa có mục — đặt tên để tạo…";
    oTen.setAttribute("aria-label", "Tên mục gợi ý mới");
    const tao = document.createElement("button");
    tao.type = "submit";
    tao.className = "primary";
    tao.textContent = "Tạo";
    form.append(oTen, tao);
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const ten = oTen.value.trim();
      if (!ten) return;
      tao.disabled = true;
      await this._saveSuggestion({ action: "add_group", name: ten });
      const moi = (this._goiY?.groups || []).find((muc) => muc.name === ten);
      if (!moi) {
        tao.disabled = false;
        return; // Lý do đã hiện ở dòng trạng thái rồi, đừng đè lên nó.
      }
      dong();
      this._saveSuggestion({ action: "pin_song", id: moi.id, item: banGhi },
        `Đã tạo mục “${ten}” và gắn “${dich.tenBai}” vào đó.`);
    });
    menu.append(form);
    dich.row.append(menu);
  }

  _renderPlaylists() {
    const label = this.shadowRoot.querySelector(".playlists-tab-label");
    label.textContent = this._playlists?.length ? `Playlist (${this._playlists.length})` : "Playlist";
    const container = this.shadowRoot.querySelector(".playlist-list");
    container.replaceChildren();
    if (this._playlists === null) return;
    if (!this._playlists.length) {
      const empty = document.createElement("div");
      empty.className = "playlist-empty";
      empty.textContent = "Chưa có playlist. Dán link playlist để lưu cả danh sách, hoặc bấm + ở kết quả tìm.";
      container.append(empty);
      return;
    }
    const iconButton = (icon, label, onClick, extra = "") => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `icon-button ${extra}`.trim();
      button.title = label;
      button.setAttribute("aria-label", label);
      const glyph = document.createElement("ha-icon");
      glyph.setAttribute("icon", icon);
      button.append(glyph);
      button.addEventListener("click", () => onClick(button));
      return button;
    };
    const speakers = this._selectedPlayers.size > 0;
    for (const playlist of this._playlists) {
      const box = document.createElement("div");
      box.className = "playlist";
      const head = document.createElement("div");
      head.className = "playlist-head";
      const toggle = document.createElement("button");
      toggle.type = "button";
      toggle.className = "playlist-toggle";
      const open = this._openPlaylist === playlist.id;
      toggle.setAttribute("aria-expanded", String(open));
      const chevron = document.createElement("ha-icon");
      chevron.setAttribute("icon", "mdi:chevron-down");
      const text = document.createElement("span");
      text.style.minWidth = "0";
      const name = document.createElement("span");
      name.className = "playlist-name";
      name.textContent = playlist.name;
      const count = document.createElement("span");
      count.className = "playlist-count";
      count.textContent = `${playlist.items.length} bài`;
      text.append(name, count);
      toggle.append(chevron, text);
      toggle.addEventListener("click", () => {
        this._openPlaylist = open ? "" : playlist.id;
        this._renderPlaylists();
      });
      const tools = document.createElement("div");
      tools.className = "playlist-tools";
      const play = document.createElement("button");
      play.type = "button";
      play.className = "play-result listen";
      play.disabled = !playlist.items.length;
      play.title = speakers ? `Phát cả “${playlist.name}” ra loa đã chọn` : `Nghe cả “${playlist.name}” trên máy này`;
      play.setAttribute("aria-label", play.title);
      const playIcon = document.createElement("ha-icon");
      playIcon.setAttribute("icon", speakers ? "mdi:play" : "mdi:headphones");
      play.append(playIcon);
      play.addEventListener("click", () => this._playResult(playlist.items[0], play, 0, false, playlist));
      tools.append(
        play,
        iconButton("mdi:content-copy", `Chép mã chia sẻ “${playlist.name}”`, (button) => this._sharePlaylist(playlist, button)),
        iconButton("mdi:pencil", `Đổi tên “${playlist.name}”`, (button) => {
          const newName = window.prompt("Tên mới của playlist:", playlist.name);
          if (newName && newName.trim() && newName.trim() !== playlist.name) {
            this._playlistCommand({ action: "rename", id: playlist.id, name: newName.trim() }, () => "Đã đổi tên playlist.", button);
          }
        }),
        iconButton("mdi:delete", `Xoá “${playlist.name}”`, (button) => {
          if (window.confirm(`Xoá playlist “${playlist.name}” (${playlist.items.length} bài)?`)) {
            this._playlistCommand({ action: "delete", id: playlist.id }, () => `Đã xoá “${playlist.name}”.`, button);
          }
        }, "danger"),
      );
      head.append(toggle, tools);
      box.append(head);
      if (open) {
        const list = document.createElement("div");
        list.className = "playlist-items";
        if (!playlist.items.length) {
          const empty = document.createElement("div");
          empty.className = "playlist-empty";
          empty.textContent = "Playlist trống — bấm + ở kết quả tìm để thêm bài.";
          list.append(empty);
        }
        playlist.items.forEach((item, index) => {
          const row = document.createElement("div");
          row.className = "playlist-item";
          const number = document.createElement("span");
          number.className = "num";
          number.textContent = String(index + 1);
          const copy = document.createElement("div");
          copy.style.minWidth = "0";
          const title = document.createElement("div");
          title.className = "title";
          title.textContent = item.title || item.id;
          const meta = document.createElement("div");
          meta.className = "meta";
          meta.textContent = [item.channel, this._formatDuration(item.duration)].filter(Boolean).join(" · ");
          copy.append(title, meta);
          const buttons = document.createElement("div");
          buttons.className = "playlist-tools";
          const playButton = (icon, label, watch) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = watch ? "play-result" : "play-result listen";
            button.title = `${label}: ${title.textContent}`;
            button.setAttribute("aria-label", button.title);
            const glyph = document.createElement("ha-icon");
            glyph.setAttribute("icon", icon);
            button.append(glyph);
            button.addEventListener("click", () => this._playResult(item, button, index, watch, playlist));
            buttons.append(button);
          };
          if (this._isVideoItem(item, item.source)) playButton("mdi:television-play", "Xem video", true);
          playButton(speakers ? "mdi:play" : "mdi:headphones", speakers ? "Phát ra loa" : "Nghe", false);
          const up = iconButton("mdi:arrow-up", "Lên", (button) =>
            this._playlistCommand({ action: "move", id: playlist.id, index, to: index - 1 }, null, button));
          up.disabled = index === 0;
          const down = iconButton("mdi:arrow-down", "Xuống", (button) =>
            this._playlistCommand({ action: "move", id: playlist.id, index, to: index + 1 }, null, button));
          down.disabled = index === playlist.items.length - 1;
          buttons.append(up, down, iconButton("mdi:close", `Bỏ “${title.textContent}” khỏi playlist`, (button) =>
            this._playlistCommand({ action: "remove", id: playlist.id, index }, null, button), "danger"));
          row.append(number, copy, buttons);
          list.append(row);
        });
        box.append(list);
      }
      container.append(box);
    }
  }

  async _sharePlaylist(playlist, button) {
    const payload = await this._playlistCommand({ action: "export", id: playlist.id }, null, button);
    if (!payload?.code) return;
    try {
      await navigator.clipboard.writeText(payload.code);
      this._setStatus(`Đã chép mã chia sẻ “${playlist.name}”. Người nhận dán vào ô Playlist (thẻ này hoặc tab c2a).`);
    } catch (_error) {
      // Plain http page or a blocked clipboard: show the code to copy by hand.
      window.prompt("Mã chia sẻ — chép rồi gửi cho người nhận:", payload.code);
    }
  }

  _setStatus(message, error = false) {
    const status = this.shadowRoot.querySelector(".status");
    status.textContent = message;
    status.classList.toggle("error", error);
  }
}

/* ════════════════════════════════════════════════════════════════════════════
   Trình sửa cấu hình bằng giao diện.

   Dựng bằng DOM thuần thay vì ha-form: ha-form là thành phần nội bộ của Home
   Assistant, tên và hình dạng lược đồ của nó đổi theo phiên bản, mà ở đây không
   kiểm chứng được. Input thường thì phiên bản nào cũng chạy.

   Hợp đồng với Home Assistant: HA gọi setConfig(config), gán .hass, rồi lắng
   nghe sự kiện «config-changed». Nút Lưu/Huỷ là của HA, trình sửa không tự vẽ.
   ════════════════════════════════════════════════════════════════════════════ */
class TriTueYouTubePlayerCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._config = {};
    this._tab = "cau-hinh";
    this._built = false;
  }

  setConfig(config) {
    this._config = { ...(config || {}) };
    this._build();
    this._fill();
  }

  set hass(hass) {
    this._hass = hass;
    if (this._built) this._fillEntities();
  }

  /** Gửi cấu hình mới cho Home Assistant. Bỏ các khoá rỗng để YAML khỏi đầy
      những dòng thừa không đổi gì. */
  _emit(key, value) {
    const config = { ...this._config };
    if (value === "" || value === null || value === undefined) delete config[key];
    else config[key] = value;
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  /** Ghi NHIỀU khoá trong MỘT lần phát, cho bộ màu dựng sẵn.
      Gọi _emit bảy lần thì Home Assistant nhận bảy sự kiện liên tiếp, mỗi sự kiện
      mang một bản cấu hình dở dang — vừa chớp giật, vừa dễ lưu nhầm bản giữa chừng. */
  _emitNhieu(doi) {
    const config = { ...this._config };
    for (const [khoa, gia] of Object.entries(doi)) {
      if (gia === "" || gia === null || gia === undefined) delete config[khoa];
      else config[khoa] = gia;
    }
    this._config = config;
    this.dispatchEvent(new CustomEvent("config-changed", {
      detail: { config },
      bubbles: true,
      composed: true,
    }));
  }

  _build() {
    if (this._built) return;
    this._built = true;
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .tabs { display: flex; gap: 4px; border-bottom: 1px solid var(--divider-color, #444); margin-bottom: 14px; }
        .tab {
          padding: 9px 14px; border: 0; background: transparent; cursor: pointer;
          color: var(--secondary-text-color); font: inherit; font-size: .95rem;
          border-bottom: 2px solid transparent; margin-bottom: -1px;
        }
        .tab.on { color: var(--primary-color, #03a9f4); border-bottom-color: var(--primary-color, #03a9f4); }
        .group {
          border: 1px solid var(--divider-color, #444); border-radius: 12px;
          padding: 14px; margin-bottom: 14px;
        }
        .group h4 { margin: 0 0 12px; font-size: 1rem; font-weight: 600; }
        .row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr); gap: 10px; align-items: center; margin-bottom: 12px; }
        .row:last-child { margin-bottom: 0; }
        label { font-size: .92rem; color: var(--primary-text-color); }
        .hint { display: block; font-size: .78rem; color: var(--secondary-text-color); margin-top: 2px; }
        input, select {
          width: 100%; box-sizing: border-box; padding: 8px 10px; font: inherit;
          border-radius: 8px; border: 1px solid var(--divider-color, #555);
          background: var(--card-background-color, #1c1c1c); color: var(--primary-text-color, #fff);
        }
        input[type="color"] { padding: 2px; height: 38px; }
        input[type="range"] { padding: 0; border: 0; background: transparent; }
        /* Luật chung phía trên cho ô nhập «width: 100%», để nguyên thì ô tích kéo dài
           hết hàng trông như một ô trống. */
        input[type="checkbox"] { width: 20px; height: 20px; padding: 0; justify-self: start; accent-color: var(--primary-color, #03a9f4); }
        .slider { display: flex; align-items: center; gap: 8px; }
        .slider output { min-width: 46px; text-align: right; font-variant-numeric: tabular-nums; }
        @media (max-width: 480px) { .row { grid-template-columns: 1fr; gap: 4px; } }
      </style>
      <div class="tabs">
        <button class="tab on" type="button" data-tab="cau-hinh">Cấu hình</button>
        <button class="tab" type="button" data-tab="hien-thi">Hiển thị</button>
        <button class="tab" type="button" data-tab="bo-tri">Bố trí</button>
      </div>

      <div class="page" data-page="cau-hinh">
        <div class="group">
          <h4>⚙️ Cài đặt chung</h4>
          <div class="row">
            <label for="ed-entity">Thiết bị phát <span class="hint">Bắt buộc — entity của tích hợp</span></label>
            <select id="ed-entity"></select>
          </div>
          <div class="row">
            <label for="ed-title">Tiêu đề thẻ <span class="hint">Để trống thì dùng tên mặc định</span></label>
            <input id="ed-title" type="text" placeholder="VD: Nhạc YouTube &amp; Zing" />
          </div>
          <div class="row">
            <label for="ed-wave">Kiểu sóng nhạc</label>
            <select id="ed-wave">
              <option value="bars">Cột (bars)</option>
              <option value="simple">Đơn giản (simple)</option>
              <option value="dots">Chấm (dots)</option>
            </select>
          </div>
        </div>
      </div>

      <div class="page" data-page="hien-thi" hidden>
        <div class="group">
          <h4>🎨 Nền</h4>
          <div class="row">
            <label for="ed-preset">Bộ màu dựng sẵn <span class="hint">Chọn một phát ra cả bảng; mọi ô màu bên dưới vẫn chỉnh riêng được</span></label>
            <select id="ed-preset">
              <option value="">— Chọn bộ màu —</option>
              <option value="than-chi-cam">Than chì · Cam san hô + Xanh cyan</option>
              <option value="mac-dinh">Trả về mặc định</option>
            </select>
          </div>
          <div class="row">
            <label for="ed-bgstyle">Loại nền</label>
            <select id="ed-bgstyle">
              <option value="gradient">Chuyển sắc (gradient)</option>
              <option value="solid">Một màu phẳng</option>
              <option value="none">Trong suốt — ăn theo dashboard</option>
            </select>
          </div>
          <div class="row">
            <label for="ed-bgcolor">Màu nền</label>
            <input id="ed-bgcolor" type="color" value="#0d1525" />
          </div>
          <div class="row">
            <label for="ed-accent">Màu nhấn <span class="hint">Nút, viền, sóng nhạc</span></label>
            <input id="ed-accent" type="color" value="#00ffcc" />
          </div>
          <div class="row">
            <label for="ed-accent2">Màu nhấn phụ <span class="hint">Điểm xuyết bên cạnh màu nhấn chính</span></label>
            <input id="ed-accent2" type="color" value="#12a8cc" />
          </div>
          <div class="row">
            <label for="ed-surface">Màu mặt thẻ con <span class="hint">Bảng chọn, ô nổi bên trong card</span></label>
            <input id="ed-surface" type="color" value="#303130" />
          </div>
          <div class="row">
            <label for="ed-text">Màu chữ chính</label>
            <input id="ed-text" type="color" value="#f2f2f2" />
          </div>
          <div class="row">
            <label for="ed-textdim">Màu chữ phụ <span class="hint">Tên ca sĩ, chú thích</span></label>
            <input id="ed-textdim" type="color" value="#a5a5a5" />
          </div>
          <div class="row">
            <label for="ed-danger">Màu cảnh báo <span class="hint">Nút xoá, nút dừng</span></label>
            <input id="ed-danger" type="color" value="#ff4f62" />
          </div>
          <div class="row">
            <label for="ed-line">Màu viền và đường kẻ</label>
            <input id="ed-line" type="color" value="#8a642f" />
          </div>
          <div class="row">
            <label for="ed-opacity">Độ đục của nền (%)</label>
            <div class="slider">
              <input id="ed-opacity" type="range" min="0" max="100" step="1" value="100" />
              <output id="ed-opacity-out">100%</output>
            </div>
          </div>
        </div>
        <div class="group">
          <h4>👁 Hiện / ẩn mục</h4>
          <div class="row">
            <label for="ed-show-youtube">YouTube <span class="hint">Bỏ tích là ẩn mục này khỏi hàng nguồn; hàng tự dồn lại cho vừa</span></label>
            <input id="ed-show-youtube" type="checkbox" checked />
          </div>
          <div class="row">
            <label for="ed-show-zing">Zing MP3</label>
            <input id="ed-show-zing" type="checkbox" checked />
          </div>
          <div class="row">
            <label for="ed-show-facebook">Facebook</label>
            <input id="ed-show-facebook" type="checkbox" checked />
          </div>
          <div class="row">
            <label for="ed-show-playlist">Playlist <span class="hint">Ẩn cả nút Playlist lẫn nút lưu playlist</span></label>
            <input id="ed-show-playlist" type="checkbox" checked />
          </div>
        </div>
        <div class="group">
          <h4>🔍 Thu phóng</h4>
          <div class="row">
            <label for="ed-zoom">Cỡ chữ và nút (%) <span class="hint">Card vốn tự co theo màn hình; kéo đây để ép to hơn hoặc nhỏ hơn</span></label>
            <div class="slider">
              <input id="ed-zoom" type="range" min="50" max="150" step="5" value="100" />
              <output id="ed-zoom-out">100%</output>
            </div>
          </div>
        </div>
      </div>

      <div class="page" data-page="bo-tri" hidden>
        <div class="group">
          <h4>📐 Bố cục</h4>
          <div class="row">
            <label for="ed-layout">Kiểu xếp <span class="hint">Màn hình hẹp luôn xếp dọc, dù chọn gì</span></label>
            <select id="ed-layout">
              <option value="horizontal">Ngang — hai cột</option>
              <option value="vertical">Dọc — một cột</option>
            </select>
          </div>
          <div class="row">
            <label for="ed-width">Bề rộng cột video (%) <span class="hint">Chỉ áp dụng khi xếp ngang</span></label>
            <div class="slider">
              <input id="ed-width" type="range" min="20" max="80" step="5" value="55" />
              <output id="ed-width-out">55%</output>
            </div>
          </div>
        </div>
      </div>`;

    this.shadowRoot.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        this._tab = tab.dataset.tab;
        this.shadowRoot.querySelectorAll(".tab").forEach((other) =>
          other.classList.toggle("on", other.dataset.tab === this._tab));
        this.shadowRoot.querySelectorAll(".page").forEach((page) => {
          page.hidden = page.dataset.page !== this._tab;
        });
      });
    });

    const on = (id, khoa, doc) => {
      const el = this.shadowRoot.getElementById(id);
      el.addEventListener("change", () => this._emit(khoa, doc(el)));
      return el;
    };
    on("ed-entity", "entity", (el) => el.value);
    on("ed-title", "title", (el) => el.value.trim());
    on("ed-wave", "waveStyle", (el) => el.value);
    on("ed-bgstyle", "bg_style", (el) => el.value);
    on("ed-bgcolor", "bg_color", (el) => el.value);
    on("ed-accent", "accent_color", (el) => el.value);
    on("ed-accent2", "accent2_color", (el) => el.value);
    on("ed-surface", "surface_color", (el) => el.value);
    on("ed-text", "text_color", (el) => el.value);
    on("ed-textdim", "text_dim_color", (el) => el.value);
    on("ed-danger", "danger_color", (el) => el.value);
    on("ed-line", "line_color", (el) => el.value);

    /* Ô tích: BẬT là mặc định, nên khi bật thì phát chuỗi rỗng để «_emit» XOÁ khoá —
       YAML chỉ ghi lại đúng những mục người dùng chọn ẩn, không đầy dòng thừa. */
    const batTat = (id, khoa) => {
      const el = this.shadowRoot.getElementById(id);
      el.addEventListener("change", () => this._emit(khoa, el.checked ? "" : false));
    };
    batTat("ed-show-youtube", "show_youtube");
    batTat("ed-show-zing", "show_zing");
    batTat("ed-show-facebook", "show_facebook");
    batTat("ed-show-playlist", "show_playlist");

    /* Bộ màu dựng sẵn. Chủ máy chốt: "có thêm màu cố định nhưng vẫn nên để cả bảng
       RGB như hiện tại để chọn cho từng mục" — nên đây chỉ là lối tắt điền sẵn cả
       bảng, mọi ô màu bên dưới vẫn sửa riêng được như cũ. */
    const O_MAU = {
      "ed-bgcolor": "bg_color", "ed-surface": "surface_color",
      "ed-accent": "accent_color", "ed-accent2": "accent2_color",
      "ed-danger": "danger_color", "ed-text": "text_color",
      "ed-textdim": "text_dim_color", "ed-line": "line_color",
    };
    const BO_MAU = {
      // Bảng chủ máy đưa 18/09/2026: nền than chì, nhấn cam san hô, phụ xanh cyan.
      "than-chi-cam": {
        bg_style: "gradient", bg_color: "#202120", surface_color: "#303130",
        accent_color: "#ff7045", accent2_color: "#12a8cc", danger_color: "#ff4f62",
        text_color: "#f2f2f2", text_dim_color: "#a5a5a5", line_color: "#8a642f",
      },
      // Xoá hết màu đã chọn: _applyTheme không đặt biến nào nữa, card về diện mạo gốc.
      "mac-dinh": Object.fromEntries(Object.values(O_MAU).map((khoa) => [khoa, ""])),
    };
    const oBoMau = this.shadowRoot.getElementById("ed-preset");
    if (oBoMau) {
      oBoMau.addEventListener("change", () => {
        const bo = BO_MAU[oBoMau.value];
        oBoMau.value = "";  // luôn về dòng gợi ý, để chọn lại cùng bộ vẫn ăn.
        if (!bo) return;
        this._emitNhieu(bo);
        /* Vẽ lại các ô cho khớp. «dat» bỏ qua giá trị rỗng nên khi trả về mặc định
           phải tự đưa ô về màu gốc trong HTML, nếu không ô vẫn hiện màu cũ trong khi
           cấu hình đã sạch — nhìn như lệnh không ăn. */
        this._fill();
        for (const [id, khoa] of Object.entries(O_MAU)) {
          const el = this.shadowRoot.getElementById(id);
          if (el && !bo[khoa]) el.value = el.defaultValue;
        }
      });
    }
    on("ed-layout", "layout", (el) => el.value);
    on("ed-opacity", "opacity", (el) => Number(el.value));
    on("ed-zoom", "zoom", (el) => Number(el.value));
    on("ed-width", "player_width", (el) => Number(el.value));

    // Số bên cạnh thanh trượt chạy theo ngay khi kéo, chưa cần nhả chuột.
    const keo = (id, hau) => {
      const el = this.shadowRoot.getElementById(id);
      const out = this.shadowRoot.getElementById(id + "-out");
      el.addEventListener("input", () => { out.textContent = el.value + hau; });
    };
    keo("ed-opacity", "%");
    keo("ed-zoom", "%");
    keo("ed-width", "%");

    this._fillEntities();
  }

  /** Chỉ dựng lại danh sách khi TẬP THIẾT BỊ thật sự đổi. Home Assistant gán lại
      «.hass» mỗi lần có bất kỳ thực thể nào đổi trạng thái — nhiều lần mỗi giây
      trong một căn nhà đang chạy — nên dựng lại vô điều kiện sẽ thay ruột thẻ
      «select» liên tục, và danh sách đang mở thì nháy rồi đóng. Canh bằng chữ ký,
      đúng cách «_renderSpeakerVolumes» của card đang làm. */
  _fillEntities() {
    const select = this.shadowRoot && this.shadowRoot.getElementById("ed-entity");
    if (!select) return;
    const states = (this._hass && this._hass.states) || {};
    const ids = Object.keys(states).filter((id) => id.startsWith("media_player."));
    // Entity của chính tích hợp này lên đầu — đó là thứ thẻ cần, loa thường không chạy.
    ids.sort((a, b) => {
      const ua = a.includes("tritue_youtube_player") ? 0 : 1;
      const ub = b.includes("tritue_youtube_player") ? 0 : 1;
      return ua - ub || a.localeCompare(b, "vi");
    });
    const ten = (id) => states[id]?.attributes?.friendly_name || id;
    // Chữ ký gồm cả TÊN: đổi tên thiết bị thì danh sách cũng phải đổi theo.
    const chuKy = ids.map((id) => `${id}|${ten(id)}`).join(",");
    const dang = this._config.entity || "";

    if (chuKy !== this._dsChuKy) {
      this._dsChuKy = chuKy;
      select.replaceChildren();
      const trong = document.createElement("option");
      trong.value = "";
      trong.textContent = "— Chọn thiết bị —";
      select.append(trong);
      for (const id of ids) {
        const option = document.createElement("option");
        option.value = id;
        option.textContent = id.includes("tritue_youtube_player") ? `★ ${ten(id)}` : ten(id);
        select.append(option);
      }
    }
    // Gán lại value khi đang đúng cũng làm danh sách đang mở giật, nên chỉ gán khi lệch.
    if (select.value !== dang) select.value = dang;
  }

  _fill() {
    if (!this._built) return;
    const config = this._config || {};
    const dat = (id, giatri) => {
      const el = this.shadowRoot.getElementById(id);
      if (el && giatri !== undefined && giatri !== null && giatri !== "") el.value = String(giatri);
    };
    dat("ed-title", config.title);
    dat("ed-wave", config.waveStyle || "bars");
    dat("ed-bgstyle", config.bg_style || "gradient");
    dat("ed-bgcolor", config.bg_color);
    dat("ed-accent", config.accent_color);
    dat("ed-accent2", config.accent2_color);
    dat("ed-surface", config.surface_color);
    dat("ed-text", config.text_color);
    dat("ed-textdim", config.text_dim_color);
    dat("ed-danger", config.danger_color);
    dat("ed-line", config.line_color);
    dat("ed-layout", config.layout || "horizontal");
    dat("ed-opacity", config.opacity === undefined ? 100 : config.opacity);
    dat("ed-zoom", config.zoom === undefined ? 100 : config.zoom);
    dat("ed-width", config.player_width === undefined ? 55 : config.player_width);
    /* Ô tích dùng «.checked», không phải «.value» — hàm «dat» ở trên không đặt được.
       Chỉ đúng giá trị «false» mới là ẩn, nên khoá thiếu hay rỗng đều ra bật. */
    const tich = (id, giatri) => {
      const el = this.shadowRoot.getElementById(id);
      if (el) el.checked = giatri !== false;
    };
    tich("ed-show-youtube", config.show_youtube);
    tich("ed-show-zing", config.show_zing);
    tich("ed-show-facebook", config.show_facebook);
    tich("ed-show-playlist", config.show_playlist);
    const soDi = (id, hau) => {
      const el = this.shadowRoot.getElementById(id);
      const out = this.shadowRoot.getElementById(id + "-out");
      if (el && out) out.textContent = el.value + hau;
    };
    soDi("ed-opacity", "%");
    soDi("ed-zoom", "%");
    soDi("ed-width", "%");
    this._fillEntities();
  }
}

  /* Mỗi thẻ tự canh tên của CHÍNH nó. Trước đây cả hai lệnh define nằm chung một
     cổng hỏi về «youtube-player-card», nên chỉ cần tên đó đã bị chiếm (tệp card nạp
     hai lần, hoặc một card khác đăng ký trùng tên) là «tritue-youtube-player-card»
     — đúng thẻ người dùng khai trong YAML — không bao giờ được định nghĩa, và
     dashboard báo "Custom element doesn't exist". */
  if (!customElements.get("tritue-youtube-player-card")) {
    customElements.define("tritue-youtube-player-card", TriTueYouTubePlayerCard);
  }
  if (!customElements.get("tritue-youtube-player-card-editor")) {
    customElements.define("tritue-youtube-player-card-editor", TriTueYouTubePlayerCardEditor);
  }
  if (!customElements.get("youtube-player-card")) {
    customElements.define("youtube-player-card", class extends TriTueYouTubePlayerCard {});
  }

  /* Khai đúng tên thẻ đang dùng thì card mới hiện trong danh sách "Thêm thẻ" của
     HA, có ảnh xem trước và nút mở trình sửa như mọi card khác. */
  window.customCards = window.customCards || [];
  if (!window.customCards.some((card) => card.type === "tritue-youtube-player-card")) {
    window.customCards.push({
      type: "tritue-youtube-player-card",
      name: "🎵 TriTue YouTube Player",
      description: 'Xem/nghe YouTube, Zing MP3, phát ra loa — cần tích hợp Python "tritue_youtube_player" cài sẵn.',
      preview: true,
      documentationURL: "https://github.com/TriTue2011/youtube",
    });
  }
})();
