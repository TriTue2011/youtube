const form = document.querySelector("#player-form");
const input = document.querySelector("#youtube-target");
const player = document.querySelector("#youtube-player");
const emptyPlayer = document.querySelector("#empty-player");
const historyList = document.querySelector("#history-list");
const emptyHistory = document.querySelector("#empty-history");
const historySummary = document.querySelector("#history-summary");
const clearHistory = document.querySelector("#clear-history");
const formMessage = document.querySelector("#form-message");
const connectionStatus = document.querySelector("#connection-status");
let currentEmbedUrl = "";

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "request_failed");
  }
  return payload;
}

const embedError = document.querySelector("#embed-error");
const embedErrorText = document.querySelector("#embed-error-text");
const embedErrorLink = document.querySelector("#embed-error-link");
let currentVideoId = "";

/* Ghép «origin» vào địa chỉ khung nhúng.
   Chỉ TRÌNH DUYỆT mới biết trang đang mở bằng địa chỉ nào, máy chủ thì không —
   nên tham số này phải gắn ở đây. Thiếu nó thì «enablejsapi» không bắt tay được
   và trang vẫn mù trước lỗi của khung. */
function themOrigin(url) {
  if (!url) return url;
  const noi = url.includes("?") ? "&" : "?";
  return `${url}${noi}origin=${encodeURIComponent(location.origin)}`;
}

/* YouTube báo lỗi qua postMessage của chính khung nhúng. Mã lỗi:
     2   — tham số sai
     5   — trình phát HTML5 không chạy được bài này
     100 — video không tồn tại hoặc đã bị gỡ
     101 / 150 — CHỦ KÊNH KHÔNG CHO NHÚNG ở nơi khác
     153 — trang nhúng không gửi được thông tin nguồn gốc mà YouTube chấp nhận
   Hai nhóm cuối là thứ chủ máy gặp, và không phải lỗi của add-on. */
function loiNhung(ma) {
  currentEmbedUrl = "";
  player.hidden = true;
  emptyPlayer.hidden = true;
  if (!embedError) return;
  const chung = "Không phải lỗi của add-on — YouTube từ chối nhúng bài này vào trang khác.";
  const theoMa = {
    2: "Địa chỉ video không hợp lệ.",
    5: "Bài này trình phát trong trang không chạy được.",
    100: "Video không tồn tại hoặc đã bị gỡ.",
    101: `Chủ kênh không cho nhúng bài này ra ngoài YouTube. ${chung}`,
    150: `Chủ kênh không cho nhúng bài này ra ngoài YouTube. ${chung}`,
    153: "YouTube không nhận nguồn gốc của trang này. Hay gặp nhất khi mở Home "
      + "Assistant bằng ĐỊA CHỈ IP; mở bằng tên miền thường là hết. "
      + `${chung}`,
  };
  embedErrorText.textContent =
    `${theoMa[ma] || "Khung nhúng YouTube báo lỗi."} (mã ${ma})`;
  if (embedErrorLink && currentVideoId) {
    embedErrorLink.href = `https://www.youtube.com/watch?v=${currentVideoId}`;
    embedErrorLink.hidden = false;
  }
  embedError.hidden = false;
}

window.addEventListener("message", (event) => {
  if (!/^https:\/\/www\.youtube(-nocookie)?\.com$/.test(event.origin)) return;
  let data;
  try {
    data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
  } catch (_error) {
    return;
  }
  if (data && data.event === "onError") loiNhung(Number(data.info));
  if (data && data.event === "onReady" && embedError) embedError.hidden = true;
});

function play(target) {
  if (currentEmbedUrl === target.embed_url && !player.hidden) {
    return;
  }
  if (embedError) embedError.hidden = true;
  if (embedErrorLink) embedErrorLink.hidden = true;
  currentEmbedUrl = target.embed_url;
  currentVideoId = target.kind === "video" ? String(target.id || "") : "";
  player.src = themOrigin(target.embed_url);
  player.hidden = false;
  emptyPlayer.hidden = true;
  input.value = target.id;
  // Bắt tay với khung nhúng: nó chỉ gửi sự kiện sau khi trang lên tiếng trước.
  player.addEventListener("load", () => {
    try {
      player.contentWindow.postMessage(
        JSON.stringify({ event: "listening", id: 1, channel: "widget" }),
        "https://www.youtube-nocookie.com",
      );
    } catch (_error) {
      // Khung chưa sẵn sàng thì thôi; lần phát sau sẽ thử lại.
    }
  }, { once: true });
}

function stopPlayer() {
  if (!currentEmbedUrl && player.hidden) {
    return;
  }
  currentEmbedUrl = "";
  currentVideoId = "";
  player.src = "";
  player.hidden = true;
  emptyPlayer.hidden = false;
  if (embedError) embedError.hidden = true;
}

function historyLabel(target) {
  if (target.source === "zing") return "Zing MP3";
  if (target.source === "facebook") return "Facebook";
  if (target.source === "http") return "HTTP Audio";
  return target.kind === "playlist" ? "Playlist" : "Video";
}

function renderHistory(items) {
  historyList.replaceChildren();
  emptyHistory.hidden = items.length !== 0;
  clearHistory.disabled = items.length === 0;
  historySummary.textContent = items.length
    ? `${items.length} mục được lưu trên thiết bị này`
    : "Chưa có nội dung";

  for (const target of items) {
    const source = target.source || "youtube";
    const item = document.createElement("li");
    item.className = "history-item";
    const button = document.createElement("button");
    button.type = "button";

    const identifier = document.createElement("span");
    identifier.textContent = target.title || target.id;
    const kind = document.createElement("span");
    kind.className = "history-kind";
    kind.textContent = historyLabel(target);

    button.append(identifier, kind);
    button.addEventListener("click", async () => {
      // The web page only owns the YouTube iframe; Zing and HTTP items are played
      // on speakers from Home Assistant, so open their public source instead.
      if (source !== "youtube") {
        if (target.url) window.open(target.url, "_blank", "noopener");
        return;
      }
      try {
        const selected = await api("api/history", {
          method: "POST",
          body: JSON.stringify({ target: target.id }),
        });
        play(selected);
        await refreshHistory();
      } catch (_error) {
        historySummary.textContent = "Không thể phát mục đã chọn.";
      }
    });
    item.append(button);
    historyList.append(item);
  }
}

async function refreshHistory() {
  const history = await api("api/history");
  renderHistory(history.items);
}

async function refreshPlayer() {
  const previousEmbedUrl = currentEmbedUrl;
  const playerState = await api("api/player");
  // Only YouTube sessions carry an embed_url the iframe can show; a Zing or HTTP
  // session is playing on a speaker and must not hijack this page's player.
  if (playerState.state === "playing" && playerState.item?.embed_url) {
    play(playerState.item);
    if (previousEmbedUrl !== playerState.item.embed_url) {
      await refreshHistory();
    }
  } else {
    stopPlayer();
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  formMessage.textContent = "";
  const submit = form.querySelector("button[type='submit']");
  submit.disabled = true;
  submit.textContent = "Đang mở…";
  try {
    const target = await api("api/history", {
      method: "POST",
      body: JSON.stringify({ target: input.value }),
    });
    play(target);
    await refreshHistory();
  } catch (error) {
    formMessage.textContent =
      error.message === "invalid_youtube_target"
        ? "URL hoặc video ID không hợp lệ."
        : "Không thể mở nội dung. Hãy thử lại.";
  } finally {
    submit.disabled = false;
    submit.textContent = "Phát";
  }
});

clearHistory.addEventListener("click", async () => {
  clearHistory.disabled = true;
  try {
    const history = await api("api/history", { method: "DELETE" });
    renderHistory(history.items);
  } catch (_error) {
    historySummary.textContent = "Không thể xóa lịch sử. Hãy thử lại.";
    clearHistory.disabled = false;
  }
});

async function initialize() {
  try {
    const [config] = await Promise.all([
      api("api/config"),
      refreshHistory(),
      refreshPlayer(),
    ]);
    document.querySelector("#app-title").textContent = config.app_title;
    document.title = config.app_title;
    connectionStatus.textContent = "Sẵn sàng";
    connectionStatus.dataset.ready = "true";
  } catch (_error) {
    connectionStatus.textContent = "Mất kết nối";
    historySummary.textContent = "Không tải được lịch sử.";
  }
}

initialize();
setInterval(async () => {
  try {
    await refreshPlayer();
    connectionStatus.textContent = "Sẵn sàng";
    connectionStatus.dataset.ready = "true";
  } catch (_error) {
    connectionStatus.textContent = "Mất kết nối";
    delete connectionStatus.dataset.ready;
  }
}, 2000);
