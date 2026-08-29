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

function play(target) {
  if (currentEmbedUrl === target.embed_url && !player.hidden) {
    return;
  }
  currentEmbedUrl = target.embed_url;
  player.src = target.embed_url;
  player.hidden = false;
  emptyPlayer.hidden = true;
  input.value = target.id;
}

function stopPlayer() {
  if (!currentEmbedUrl && player.hidden) {
    return;
  }
  currentEmbedUrl = "";
  player.src = "";
  player.hidden = true;
  emptyPlayer.hidden = false;
}

function historyLabel(target) {
  if (target.source === "zing") return "Zing MP3";
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
