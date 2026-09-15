const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;
const EMBED_ORIGIN = "https://www.youtube-nocookie.com";
const STREAM_TOKEN = /\/api\/stream\/([A-Za-z0-9_-]+)\.[A-Za-z0-9_-]+/;

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
const SILENCE = "data:audio/wav;base64,UklGRrQBAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YZABAACAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICA";

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
  listeners: new Set(),

  notify(message = "", isError = false) {
    this.listeners.forEach((listener) => listener(message, isError));
  },

  audio() {
    if (this.element) return this.element;
    const audio = new Audio();
    audio.preload = "auto";
    audio.addEventListener("play", () => this.notify());
    audio.addEventListener("pause", () => this.notify());
    audio.addEventListener("ended", () => {
      if (this.real() && this.item && !this.next(1)) this.notify("Đã nghe hết hàng đợi.");
    });
    audio.addEventListener("error", () => {
      if (this.real()) this.notify(`Không phát được tiếng bài này trên máy này (mã lỗi ${audio.error?.code ?? "?"}).`, true);
    });
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        // The Home Assistant app reports the page hidden for a moment while it enters
        // fullscreen (owner 15/09/2026: "phóng to dừng video"); fullscreen is watching,
        // not a screen switched off. It may say hidden before fullscreen has begun, so
        // look again half a second later: a screen switched off is still hidden then.
        clearTimeout(this.hideTimer);
        this.hideTimer = setTimeout(() => {
          if (document.visibilityState !== "hidden" || document.fullscreenElement) return;
          if (!listenScreenOff() && this.real() && !audio.paused) {
            audio.pause();
            this.pausedByHide = true;
          }
        }, 500);
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

  /** Call inside the tap, before any await. */
  unlock() {
    const audio = this.audio();
    audio.src = SILENCE;
    audio.play().catch(() => {});
    return audio;
  },

  urls: new Map(),

  async streamUrl(item) {
    if (item.source === "http") return String(item.url || item.id || "");
    const key = `${item.source}:${item.url || item.id}`;
    const cached = this.urls.get(key);
    // Signed links last an hour on the player server; reuse one for ten minutes.
    if (cached && Date.now() - cached.at < 600000) return cached.url;
    const pending = (async () => {
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
    })();
    this.urls.set(key, { at: Date.now(), url: pending });
    const url = await pending;
    if (url) this.urls.set(key, { at: Date.now(), url });
    else this.urls.delete(key);
    return url;
  },

  /** Get a song's link ready before it is needed (the sound of a video just opened). */
  prefetch(item) {
    if (item && this.hass && item.source !== "http") this.streamUrl(item);
  },

  /** Listen alone; `startAt` = second to start from (the sound of a video watched until now). */
  async listen(item, queue, index, startAt = 0) {
    const audio = this.unlock();
    const generation = ++this.generation;
    Object.assign(this, { item, queue, index, along: false, alongKey: "", pausedByHide: false });
    this.mediaSession(item);
    this.notify();
    const url = await this.streamUrl(item);
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
    audio.play().catch((error) => this.playRefused(error));
    this.notify();
  },

  /** play() refused. AbortError only means a newer song or a pause took over. */
  playRefused(error) {
    if (error?.name === "AbortError") return;
    this.notify(error?.name === "NotAllowedError"
      ? "Trình duyệt chặn tự phát có tiếng — bấm ▶ để nghe."
      : `Máy này không phát được tiếng bài này (${error?.name || "lỗi không rõ"}).`, true);
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
    if (audio.paused) audio.play().catch((error) => this.playRefused(error));
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

  /** Listen along with the speakers; call inside the tap. */
  startAlong() {
    if (this.item) this.stop();
    this.unlock();
    this.along = true;
    this.alongKey = "";
    this.notify();
  },

  stopAlong() {
    this.silence();
    this.along = false;
    this.mediaSession(null);
    this.notify();
  },

  /** Load the speakers' song (nothing to do when it already is). */
  async loadAlong(item) {
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
    audio.src = url;
    audio.play().catch(() => this.notify("Trình duyệt chặn tự phát có tiếng — bấm lại “Nghe trên máy này”.", true));
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

class TriTueYouTubePlayerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._source = "youtube";
    this._selectedPlayers = new Set();
    this._results = [];
    this._rendered = false;
    this._defaultsApplied = false;
    this._capabilities = new Map();
    this._capabilityEntryId = "";
    this._capabilitiesLoading = false;
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
    this._onDeviceAudio = (message, isError) => this._deviceAudioChanged(message, isError);
  }

  _idleVideo() {
    return { open: false, ready: false, item: null, state: -1, time: 0, timeAt: 0, withSpeakers: false, followsDevice: false, soundHere: true, muted: null, picture: null, pictureEl: null };
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string") {
      throw new Error("TriTue card requires a media_player entity");
    }
    this._config = { title: "TriTue Music", ...config };
  }

  set hass(hass) {
    this._hass = hass;
    deviceAudio.hass = hass;
    if (!this._rendered) {
      this._render();
      this._bindEvents();
      this._rendered = true;
    }
    this._applySharedOutputs();
    this._syncPlayers();
    this._updateSourceButtons();
    this._loadCapabilities();
    this._loadHiddenPlayers();
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

  connectedCallback() {
    if (!this._progressTimer) {
      this._progressTimer = setInterval(() => {
        this._updateProgress();
        this._syncAlong();
      }, 1000);
    }
    deviceAudio.listeners.add(this._onDeviceAudio);
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
          player?.classList.remove("rotated", "idle");
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
    if (this._onFullscreenChange) {
      document.removeEventListener("fullscreenchange", this._onFullscreenChange);
      this._onFullscreenChange = null;
    }
    deviceAudio.listeners.delete(this._onDeviceAudio);
    this._remember();
    this._closeVideo();
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        [hidden] { display: none !important; }
        ha-card {
          overflow: hidden;
          color: var(--primary-text-color);
          background:
            radial-gradient(circle at 94% 2%, rgba(255, 64, 86, .16), transparent 34%),
            var(--ha-card-background, var(--card-background-color));
        }
        .wrap { padding: 16px; }
        header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
        h2 { margin: 0; font-size: 1.2rem; line-height: 1.2; }
        .subtitle, .hint { color: var(--secondary-text-color); font-size: .86rem; }
        .subtitle { margin: 3px 0 0; font-size: .8rem; }
        .source-switch {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          padding: 4px;
          margin: 12px 0 10px;
          border-radius: 12px;
          background: var(--secondary-background-color);
        }
        button, input { font: inherit; }
        button { cursor: pointer; }
        .source-button {
          border: 0;
          border-radius: 9px;
          padding: 7px 10px;
          color: var(--secondary-text-color);
          background: transparent;
          font-weight: 600;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .source-button[aria-pressed="true"] {
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
          box-shadow: 0 4px 12px rgba(0, 0, 0, .14);
        }
        form { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 9px; }
        input[type="search"] {
          min-width: 0;
          border: 1px solid var(--divider-color);
          border-radius: 11px;
          padding: 9px 12px;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
          outline: none;
        }
        input[type="search"]:focus { border-color: var(--primary-color); }
        .primary {
          border: 0;
          border-radius: 11px;
          padding: 10px 15px;
          font-weight: 650;
        }
        .primary { color: var(--text-primary-color, #fff); background: var(--primary-color); }
        .search-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; --mdc-icon-size: 19px; }
        button:disabled { cursor: not-allowed; opacity: .45; }
        .status { min-height: 18px; margin: 6px 1px 0; color: var(--secondary-text-color); font-size: .84rem; }
        .status.error { color: var(--error-color); }
        .section { margin-top: 8px; }
        .section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 7px; }
        .section-title h3 { margin: 0; font-size: .88rem; }
        /* The speaker list stays folded until its title is tapped (owner 15/09/2026). */
        .speakers-toggle {
          width: 100%;
          padding: 2px 0;
          border: 0;
          color: var(--primary-text-color);
          background: transparent;
          text-align: left;
        }
        .section-name { display: inline-flex; align-items: center; gap: 4px; font-weight: 650; font-size: .88rem; --mdc-icon-size: 18px; }
        .section-name ha-icon { transition: transform .15s; color: var(--secondary-text-color); }
        .speakers-toggle[aria-expanded="true"] .section-name ha-icon { transform: rotate(180deg); }
        .players { display: flex; flex-wrap: wrap; gap: 8px; max-height: 132px; overflow: auto; }
        .player-chip {
          display: flex;
          align-items: center;
          gap: 7px;
          max-width: 100%;
          padding: 5px 9px;
          border: 1px solid var(--divider-color);
          border-radius: 999px;
          background: var(--secondary-background-color);
          cursor: pointer;
        }
        .player-chip:has(input:checked) { border-color: var(--primary-color); color: var(--primary-color); }
        .player-chip.source-incompatible { opacity: .62; }
        .player-chip input { accent-color: var(--primary-color); }
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
        .hide-player:hover { color: var(--error-color); background: var(--divider-color); }
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
        .restore-player:hover { border-color: var(--primary-color); color: var(--primary-color); }
        .restore-player span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .player {
          margin-top: 12px;
          padding: 10px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: color-mix(in srgb, var(--secondary-background-color) 78%, transparent);
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
          color: #fff;
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
          color: #fff;
          font-size: 12px;
          white-space: nowrap;
          pointer-events: none;
        }
        .now { display: grid; grid-template-columns: 52px minmax(0, 1fr); gap: 11px; align-items: center; }
        .player.video-on .now { grid-template-columns: minmax(0, 1fr); }
        .player.video-on .now-cover { display: none; }
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
        .control-bar { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 6px; }
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
        .ctl:hover:not(:disabled) { background: var(--divider-color); }
        .ctl.main {
          width: 42px;
          height: 42px;
          margin: 0 2px;
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
          --mdc-icon-size: 26px;
        }
        .ctl.main:hover:not(:disabled) { background: var(--primary-color); filter: brightness(1.08); }
        .ctl.stop { color: var(--error-color); }
        .view-group .ctl { width: 32px; height: 32px; color: var(--secondary-text-color); --mdc-icon-size: 19px; }
        input[type="range"] { width: 100%; accent-color: var(--primary-color); }
        .progress { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 8px; margin-top: 6px; font-size: .74rem; font-variant-numeric: tabular-nums; color: var(--secondary-text-color); }
        .progress .bar { height: 4px; overflow: hidden; border-radius: 2px; background: var(--divider-color); }
        .progress .fill { width: 0; height: 100%; background: var(--primary-color); transition: width .9s linear; }
        .join-session { border-style: dashed; color: var(--primary-color); }
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
        .other-session:hover { border-color: var(--primary-color); }
        .speaker-volumes { display: grid; gap: 2px; margin-top: 4px; }
        .speaker-volumes:empty { display: none; }
        .svol-row { display: grid; grid-template-columns: minmax(70px, 30%) 1fr 36px; align-items: center; gap: 8px; }
        .svol-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .8rem; }
        .svol-pct { text-align: right; color: var(--secondary-text-color); font-size: .78rem; font-variant-numeric: tabular-nums; }
        .results { display: grid; gap: 6px; max-height: 330px; margin-top: 10px; overflow: auto; padding-right: 2px; }
        .results:empty { display: none; }
        .result {
          display: grid;
          grid-template-columns: 48px minmax(0, 1fr) auto;
          gap: 10px;
          align-items: center;
          padding: 6px;
          border-radius: 10px;
          background: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
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
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
          --mdc-icon-size: 20px;
        }
        .result-actions { display: flex; align-items: center; gap: 6px; }
        .view-tabs { display: flex; gap: 16px; margin-top: 12px; }
        .view-tab {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 2px 2px 6px;
          border: 0;
          border-bottom: 2px solid transparent;
          color: var(--secondary-text-color);
          background: transparent;
          font-weight: 650;
          --mdc-icon-size: 17px;
        }
        .view-tab[aria-pressed="true"] { border-bottom-color: var(--primary-color); color: var(--primary-text-color); }
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
        .icon-button.danger:hover:not(:disabled) { color: var(--error-color); }
        .save-playlist {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          width: 100%;
          margin-top: 8px;
          padding: 7px 10px;
          border: 1px dashed var(--primary-color);
          border-radius: 11px;
          color: var(--primary-color);
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
        .playlist { border: 1px solid var(--divider-color); border-radius: 12px; overflow: hidden; }
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
        .play-result.listen { color: var(--primary-color); background: color-mix(in srgb, var(--primary-color) 18%, transparent); }
        .device-row { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 6px; margin-top: 6px; }
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
        .pill[aria-pressed="true"] { border-color: var(--primary-color); color: var(--text-primary-color, #fff); background: var(--primary-color); }
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
          color: #fff;
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
        /* The YouTube frame shows its own title; the card's only over its own picture. */
        .player:is(.expanded, :fullscreen):not(.picture-on) > .stage > .now { display: none; }
        .player:is(.expanded, :fullscreen) > .stage > :is(.now, .progress, .control-bar) {
          position: absolute;
          left: 0;
          right: 0;
          z-index: 2;
          margin: 0;
          transition: opacity .3s;
        }
        .player:is(.expanded, :fullscreen) > .stage > .now {
          top: 0;
          padding: max(12px, env(safe-area-inset-top)) 16px 32px;
          background: linear-gradient(rgba(0, 0, 0, .7), transparent);
        }
        .player:is(.expanded, :fullscreen) > .stage > .progress { bottom: 52px; padding: 0 16px; }
        .player:is(.expanded, :fullscreen) > .stage > .control-bar {
          bottom: 0;
          padding: 40px 10px max(6px, env(safe-area-inset-bottom));
          background: linear-gradient(transparent, rgba(0, 0, 0, .8));
        }
        /* Idle: the overlays fade out after a few seconds without a touch while the video
           plays; the shield catches the next touch (taps inside the YouTube frame never
           reach the card) and only brings them back. */
        .idle-shield { display: none; }
        .player.idle:is(.expanded, :fullscreen) { cursor: none; }
        .player.idle:is(.expanded, :fullscreen) > .idle-shield { display: block; position: absolute; inset: 0; z-index: 3; }
        .player.idle:is(.expanded, :fullscreen) > .stage > :is(.now, .progress, .control-bar) { opacity: 0; pointer-events: none; }
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
        .player.expanded .ctl:not(.main),
        .player:fullscreen .ctl:not(.main) { color: #fff; }
        .player.expanded .ctl.stop,
        .player:fullscreen .ctl.stop { color: #ff8a80; }
        .player.expanded .now-meta,
        .player:fullscreen .now-meta,
        .player.expanded .svol-name,
        .player:fullscreen .svol-name { color: rgba(255, 255, 255, .72); }
        @media (max-width: 520px) {
          /* Phones (and the app's larger font scale): keep the search on one row
             and shrink text so the card isn't a column of oversized boxes. */
          .wrap { padding: 12px; }
          h2 { font-size: 1.02rem; }
          .subtitle { font-size: .72rem; }
          .source-switch { margin: 10px 0 8px; }
          .source-button { padding: 6px 4px; font-size: .8rem; }
          input[type="search"] { padding: 7px 10px; font-size: .9rem; }
          .primary { padding: 7px 11px; }
          .search-label { display: none; }
          .player { padding: 8px; }
          .now { grid-template-columns: 44px minmax(0, 1fr); gap: 9px; }
          .now-meta, .status { font-size: .76rem; }
          .section-title h3, .section-name { font-size: .82rem; }
          .player-chip { gap: 5px; padding: 3px 8px; font-size: .84rem; }
          .result { font-size: .88rem; }
        }
      </style>
      <ha-card>
        <div class="wrap">
          <header>
            <div>
              <h2></h2>
              <p class="subtitle"></p>
            </div>
            <ha-icon icon="mdi:music-circle"></ha-icon>
          </header>

          <section class="player" aria-label="Đang phát">
            <div class="idle-shield" aria-hidden="true"></div>
            <div class="stage">
            <div class="video-frame" hidden></div>
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
            <div class="progress" hidden>
              <span class="elapsed">0:00</span>
              <div class="bar"><div class="fill"></div></div>
              <span class="total">0:00</span>
            </div>
            <div class="control-bar">
              <div class="transport-group" role="group" aria-label="Điều khiển phát">
                <button class="ctl previous" type="button" aria-label="Bài trước" title="Bài trước"><ha-icon icon="mdi:skip-previous"></ha-icon></button>
                <button class="ctl main play-pause" type="button" aria-label="Phát" title="Phát"><ha-icon icon="mdi:play"></ha-icon></button>
                <button class="ctl next" type="button" aria-label="Bài tiếp theo" title="Bài tiếp theo"><ha-icon icon="mdi:skip-next"></ha-icon></button>
                <button class="ctl stop" type="button" aria-label="Dừng" title="Dừng"><ha-icon icon="mdi:stop"></ha-icon></button>
              </div>
              <div class="view-group">
                <button class="ctl watch" type="button" aria-label="Xem video trên thẻ" title="Xem video trên thẻ" hidden><ha-icon icon="mdi:television-play"></ha-icon></button>
                <button class="ctl video-listen" type="button" aria-label="Chỉ nghe (tắt hình, tiếng chạy tiếp)" title="Chỉ nghe — tắt hình, tiếng chạy tiếp" hidden><ha-icon icon="mdi:headphones"></ha-icon></button>
                <button class="ctl video-rotate" type="button" aria-label="Xoay ngang 90°" title="Xoay ngang 90° (máy đang khoá xoay)" hidden><ha-icon icon="mdi:phone-rotate-landscape"></ha-icon></button>
                <button class="ctl video-expand" type="button" aria-label="Phóng to video" title="Phóng to" hidden><ha-icon icon="mdi:arrow-expand"></ha-icon></button>
                <button class="ctl video-fullscreen" type="button" aria-label="Xem toàn màn hình" title="Toàn màn hình" hidden><ha-icon icon="mdi:fullscreen"></ha-icon></button>
                <button class="ctl video-close" type="button" aria-label="Đóng video" title="Đóng video" hidden><ha-icon icon="mdi:close"></ha-icon></button>
              </div>
            </div>
            <div class="device-row">
              <button class="pill device-sound" type="button" aria-pressed="false" hidden><ha-icon icon="mdi:volume-off"></ha-icon><span>Nghe trên máy này</span></button>
              <button class="pill screen-off" type="button" aria-pressed="false"><ha-icon icon="mdi:cellphone-off"></ha-icon><span>Nghe khi tắt màn hình</span></button>
            </div>
            <div class="speaker-volumes"></div>
            <div class="others" aria-label="Nhóm loa khác đang phát"></div>
            </div>
          </section>

          <div class="view-tabs" role="group" aria-label="Tìm nhạc hoặc playlist">
            <button class="view-tab" type="button" data-view="search" aria-pressed="true"><ha-icon icon="mdi:magnify"></ha-icon><span>Tìm nhạc</span></button>
            <button class="view-tab" type="button" data-view="playlists" aria-pressed="false"><ha-icon icon="mdi:playlist-music"></ha-icon><span class="playlists-tab-label">Playlist</span></button>
          </div>

          <div class="source-switch" role="group" aria-label="Nguồn nhạc">
            <button class="source-button" type="button" data-source="youtube">YouTube</button>
            <button class="source-button" type="button" data-source="zing">Zing MP3</button>
            <button class="source-button" type="button" data-source="http">Link audio</button>
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

          <section class="section">
            <button class="section-title speakers-toggle" type="button" aria-expanded="false" title="Bấm để hiện danh sách loa / màn hình">
              <span class="section-name"><ha-icon icon="mdi:chevron-down"></ha-icon>Loa / màn hình</span>
              <span class="hint selected-count">0 đã chọn</span>
            </button>
            <div class="speakers-body" hidden>
              <div class="players"></div>
              <div class="hidden-players"></div>
            </div>
          </section>

          <div class="results"></div>
        </div>
      </ha-card>`;
    this.shadowRoot.querySelector("h2").textContent = this._config.title;
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll(".source-button").forEach((button) => {
      button.addEventListener("click", () => {
        this._source = button.dataset.source;
        this._results = [];
        this._queue = [];
        this._queueIndex = -1;
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
    const searchInput = this.shadowRoot.querySelector('input[type="search"]');
    searchInput.addEventListener("input", () => this._syncSavePlaylist());
    this.shadowRoot.querySelectorAll(".view-tab").forEach((tab) => {
      tab.addEventListener("click", () => this._showView(tab.dataset.view));
    });
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
    this.shadowRoot.querySelector(".speakers-toggle").addEventListener("click", () => {
      const toggle = this.shadowRoot.querySelector(".speakers-toggle");
      const open = toggle.getAttribute("aria-expanded") !== "true";
      toggle.setAttribute("aria-expanded", String(open));
      toggle.title = open ? "Bấm để thu gọn danh sách loa / màn hình" : "Bấm để hiện danh sách loa / màn hình";
      this.shadowRoot.querySelector(".speakers-body").hidden = !open;
    });
    this.shadowRoot.querySelector(".previous").addEventListener("click", () => this._skip(-1));
    this.shadowRoot.querySelector(".play-pause").addEventListener("click", () => this._togglePlay());
    this.shadowRoot.querySelector(".next").addEventListener("click", () => this._skip(1));
    this.shadowRoot.querySelector(".stop").addEventListener("click", () => this._stop());
    this.shadowRoot.querySelector(".watch").addEventListener("click", () => this._watchCurrent());
    this.shadowRoot.querySelector(".device-sound").addEventListener("click", () => this._toggleSoundHere());
    this.shadowRoot.querySelector(".screen-off").addEventListener("click", () => this._toggleScreenOff());
    this.shadowRoot.querySelector(".video-expand").addEventListener("click", () => this._toggleVideoExpanded());
    this.shadowRoot.querySelector(".video-fullscreen").addEventListener("click", () => this._videoFullscreen());
    this.shadowRoot.querySelector(".video-close").addEventListener("click", () => this._closeVideo());
    this.shadowRoot.querySelector(".video-listen").addEventListener("click", () => this._listenOnly());
    this.shadowRoot.querySelector(".video-rotate").addEventListener("click", () => this._toggleRotated());
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
    if (!sharedOutputs.length || marker === this._sharedSessionMarker) return;
    this._selectedPlayers = new Set(sharedOutputs);
    this._sharedSessionMarker = marker;
    this._defaultsApplied = true;
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

    const container = this.shadowRoot.querySelector(".players");
    container.replaceChildren();
    if (!players.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = connected.length
        ? "Mọi thiết bị đang ẩn — mở mục Đã ẩn để khôi phục."
        : allPlayers.length
          ? "Chưa có loa hay tivi nào đang kết nối — thiết bị tự hiện khi kết nối lại."
          : "Không tìm thấy media_player nào khác.";
      container.append(empty);
    }
    for (const [entityId, state] of players) {
      const label = document.createElement("label");
      label.className = "player-chip";
      const isAudioOnly = state.attributes.device_class === "speaker";
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
      const name = document.createElement("span");
      name.className = "player-name";
      name.textContent = state.attributes.friendly_name || entityId;
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
      label.append(checkbox, name, deviceIcon, hide);
      container.append(label);
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
    // Folded list: the title still says what is ticked.
    const names = [...this._selectedPlayers].map((entityId) => this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId);
    this.shadowRoot.querySelector(".selected-count").textContent = names.length && names.length <= 2
      ? names.join(", ")
      : `${names.length} đã chọn`;
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
    return source === "youtube" && VIDEO_ID.test(String(item?.id || ""));
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

  _updateProgress() {
    if (!this.shadowRoot?.querySelector(".progress") || !this._hass) return;
    const bar = this.shadowRoot.querySelector(".progress");
    let position = null;
    let duration = 0;
    if (deviceAudio.item) {
      const heard = deviceAudio.position();
      position = heard ? heard.time : null;
      duration = heard?.duration || 0;
    } else if (this._video.open && !this._video.withSpeakers) {
      position = this._video.state === -1 ? null : this._videoTimeNow();
      duration = Number(this._video.item?.duration || 0);
    } else {
      const session = this._focusedSession();
      const lead = session?.output_entity_ids.find((id) => this._speakerPosition(id) !== null);
      if (session && lead) {
        position = this._speakerPosition(lead);
        duration = Number(this._hass.states[lead].attributes.media_duration || session.duration || 0);
      }
    }
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
    playPause.disabled = !listening && !this._video.open && !this._targetsForService("media_play_pause").length;
    const canSkip = (step) => {
      if (listening) return deviceAudio.index >= 0 && !!deviceAudio.queue[deviceAudio.index + step];
      if (videoAlone) {
        const target = this._queueIndex + step;
        return this._queueIndex >= 0 && target >= 0 && target < this._queue.length && this._isVideoItem(this._queue[target]);
      }
      if (!session) return false;
      const target = Number(session.queue_index) + step;
      return Number(session.queue_index) >= 0 && target >= 0 && target < Number(session.queue_size || 0);
    };
    this.shadowRoot.querySelector(".previous").disabled = !canSkip(-1);
    this.shadowRoot.querySelector(".next").disabled = !canSkip(1);
    this.shadowRoot.querySelector(".stop").disabled = !listening && !session && !this._video.open && !this._selectedPlayers.size;
    this._renderSpeakerVolumes();
  }

  _renderSpeakerVolumes() {
    if (!this.shadowRoot || !this._hass) return;
    const container = this.shadowRoot.querySelector(".speaker-volumes");
    if (!container) return;
    const speakers = [...this._selectedPlayers]
      .filter((entityId) => {
        const state = this._hass.states[entityId];
        return state && state.state !== "unavailable" && this._supportsFeature(entityId, 4);
      })
      .sort((left, right) =>
        this._friendlyName([left, this._hass.states[left]])
          .localeCompare(this._friendlyName([right, this._hass.states[right]]), "vi"));
    const signature = speakers.join(",");

    if (signature !== this._volumeRowsSig) {
      this._volumeRowsSig = signature;
      container.replaceChildren();
      if (!speakers.length) return;
      for (const entityId of speakers) {
        const state = this._hass.states[entityId];
        const value = Number(state?.attributes?.volume_level ?? 0.35);
        const row = document.createElement("div");
        row.className = "svol-row";
        row.dataset.entity = entityId;
        const name = document.createElement("span");
        name.className = "svol-name";
        name.textContent = state?.attributes?.friendly_name || entityId;
        const range = document.createElement("input");
        range.type = "range";
        range.min = "0";
        range.max = "1";
        range.step = "0.01";
        range.className = "svol-range";
        range.value = String(value);
        range.setAttribute("aria-label", `Âm lượng ${name.textContent}`);
        const pct = document.createElement("span");
        pct.className = "svol-pct";
        pct.textContent = `${Math.round(value * 100)}%`;
        range.addEventListener("input", () => {
          this._activeVolumeEntity = entityId;
          pct.textContent = `${Math.round(Number(range.value) * 100)}%`;
        });
        range.addEventListener("change", async () => {
          try {
            await this._hass.callService("media_player", "volume_set", {
              entity_id: entityId,
              volume_level: Number(range.value),
            });
            this._setStatus(`Âm lượng ${name.textContent}: ${Math.round(Number(range.value) * 100)}%`);
          } catch (error) {
            this._setStatus(error?.message || "Không đổi được âm lượng.", true);
          } finally {
            this._activeVolumeEntity = null;
          }
        });
        row.append(name, range, pct);
        container.append(row);
      }
      return;
    }

    // Same set of speakers: refresh values from state, but never yank a slider
    // the user is dragging right now.
    for (const row of container.querySelectorAll(".svol-row")) {
      const entityId = row.dataset.entity;
      if (entityId === this._activeVolumeEntity) continue;
      const value = Number(this._hass.states[entityId]?.attributes?.volume_level);
      if (!Number.isFinite(value)) continue;
      const range = row.querySelector(".svol-range");
      const pct = row.querySelector(".svol-pct");
      if (this.shadowRoot.activeElement === range) continue;
      range.value = String(value);
      pct.textContent = `${Math.round(value * 100)}%`;
    }
  }

  _syncNowPlaying() {
    if (!this.shadowRoot || !this._hass) return;
    const names = (entityIds) => entityIds
      .map((entityId) => this._hass.states[entityId]?.attributes?.friendly_name || entityId)
      .filter(Boolean);
    const video = this._video;
    const titleNode = this.shadowRoot.querySelector(".now-title");
    const metaNode = this.shadowRoot.querySelector(".now-meta");
    const session = this._focusedSession();
    this.shadowRoot.querySelector(".player").classList.toggle("video-on", video.open);
    this.shadowRoot.querySelector(".video-frame").hidden = !video.open;
    for (const selector of [".video-listen", ".video-expand", ".video-fullscreen", ".video-close"]) {
      this.shadowRoot.querySelector(selector).hidden = !video.open;
    }
    // "Nghe trên máy này": speakers play, and this device plays the sound too (the
    // picture's own sound, or an audio element following the speakers).
    const soundOn = deviceAudio.along || (video.open && video.withSpeakers && video.soundHere);
    const sound = this.shadowRoot.querySelector(".device-sound");
    sound.hidden = !!deviceAudio.item || (video.open ? !video.withSpeakers : !session?.title);
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
          { withSpeakers: true },
        );
        return;
      }
      this._closeVideo();
      this._setStatus("Loa này đang phát Zing/link audio — không có video.");
      return;
    }
    if (video.open) {
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
    if (deviceAudio.item) {
      const item = deviceAudio.item;
      titleNode.textContent = item.title || item.id;
      metaNode.textContent = [
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
      ? [stateText, session.artist, this._formatDuration(session.duration), queuePosition,
        names(outputs).join(", ") + (deviceAudio.along ? " và máy này" : "")]
        .filter(Boolean).join(" · ")
      : this._selectedPlayers.size
        ? "Chọn một bài trong kết quả để phát ra loa."
        : "Chọn loa để phát ra loa, hoặc bấm nút nghe / xem video của một bài để phát ngay trên máy này.";

    this._nowWatchItem = title && session.source === "youtube" && VIDEO_ID.test(String(session.id || ""))
      ? { id: session.id, url: session.url, title, channel: session.artist, duration: session.duration }
      : null;
    this.shadowRoot.querySelector(".watch").hidden = !this._nowWatchItem;

    this._showCover(session?.thumbnail || "");
  }

  _showCover(imageUrl) {
    const image = this.shadowRoot.querySelector(".now-cover img");
    const icon = this.shadowRoot.querySelector(".now-cover ha-icon");
    image.hidden = !/^https?:\/\//.test(imageUrl);
    icon.hidden = !image.hidden;
    if (!image.hidden && image.src !== imageUrl) image.src = imageUrl;
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

  _updateSourceButtons() {
    if (!this.shadowRoot) return;
    this.shadowRoot.querySelectorAll(".source-button").forEach((button) => {
      button.setAttribute("aria-pressed", String(button.dataset.source === this._source));
    });
    const input = this.shadowRoot.querySelector('input[type="search"]');
    const submit = this.shadowRoot.querySelector(".search-button");
    const isHttp = this._source === "http";
    input.placeholder = isHttp
      ? "Dán URL MP3, AAC, FLAC, OGG hoặc HLS…"
      : this._source === "youtube"
        ? "Tìm tên bài hát, ca sĩ hoặc dán link YouTube…"
        : "Tìm tên bài hát hoặc ca sĩ…";
    input.setAttribute(
      "aria-label",
      isHttp ? "Địa chỉ HTTP audio trực tiếp" : "Tìm tên bài hát hoặc ca sĩ",
    );
    input.maxLength = this._source === "zing" ? 120 : 2048;
    const submitLabel = isHttp ? "Thêm URL" : "Tìm kiếm";
    submit.querySelector(".search-label").textContent = submitLabel;
    submit.setAttribute("aria-label", submitLabel);
    submit.title = submitLabel;
    submit.querySelector("ha-icon").setAttribute("icon", isHttp ? "mdi:link-plus" : "mdi:magnify");
    const hints = {
      youtube: "YouTube · tivi mở ứng dụng, loa nhận tiếng · không chọn loa thì nghe/xem trên máy này",
      zing: "Zing MP3 · bài công khai, không VIP · phát ra loa hoặc nghe trên máy này",
      http: "Link MP3/AAC/FLAC/HLS trực tiếp · phát ra loa hoặc nghe trên máy này",
    };
    this.shadowRoot.querySelector(".subtitle").textContent = hints[this._source] || "";
  }

  async _search() {
    const query = this.shadowRoot.querySelector('input[type="search"]').value.trim();
    if (!query) return;
    const button = this.shadowRoot.querySelector(".search-button");
    button.disabled = true;
    this._setStatus(this._source === "http" ? "Đang kiểm tra URL…" : "Đang tìm kiếm…");
    try {
      if (this._source === "http") {
        this._results = [this._prepareHttpResult(query)];
      } else {
        const entryId = this._entryId();
        if (!entryId) throw new Error("Không tìm thấy config entry. Hãy tải lại integration.");
        const payload = await this._hass.callApi("GET", `tritue_youtube_player/search?entry_id=${encodeURIComponent(entryId)}&source=${encodeURIComponent(this._source)}&q=${encodeURIComponent(query)}&limit=20`);
        this._results = Array.isArray(payload.items) ? payload.items : [];
      }
      this._saveSearch(query);
      this._renderResults();
      this._setStatus(
        this._source === "http"
          ? "URL audio đã sẵn sàng. Nhấn nút phát."
          : this._results.length
            ? `Tìm thấy ${this._results.length} bài.`
            : "Không tìm thấy bài phù hợp.",
      );
    } catch (error) {
      this._results = [];
      this._renderResults();
      this._setStatus(error?.message || "Không thể tìm kiếm lúc này.", true);
    } finally {
      button.disabled = false;
    }
  }

  _prepareHttpResult(value) {
    let url;
    try {
      url = new URL(value);
    } catch (_error) {
      throw new Error("URL audio không hợp lệ.");
    }
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) {
      throw new Error("Chỉ hỗ trợ URL HTTP/HTTPS không chứa tài khoản hoặc mật khẩu.");
    }
    const hostname = url.hostname.toLowerCase().replace(/^www\./, "");
    if (hostname === "youtube.com" || hostname.endsWith(".youtube.com") || hostname === "youtu.be") {
      throw new Error("Đây là trang YouTube, không phải URL audio trực tiếp.");
    }
    const path = url.pathname.toLowerCase();
    const mediaTypes = {
      ".mp3": "audio/mpeg",
      ".aac": "audio/aac",
      ".m4a": "audio/mp4",
      ".flac": "audio/flac",
      ".ogg": "audio/ogg",
      ".opus": "audio/ogg",
      ".wav": "audio/wav",
      ".m3u8": "application/vnd.apple.mpegurl",
    };
    const extension = Object.keys(mediaTypes).find((item) => path.endsWith(item));
    let title = url.pathname.split("/").filter(Boolean).pop() || url.hostname;
    try {
      title = decodeURIComponent(title);
    } catch (_error) {
      // Keep the encoded filename when the URL contains malformed escape sequences.
    }
    return {
      id: url.href,
      url: url.href,
      title,
      channel: "HTTP Audio",
      thumbnail: "",
      duration: 0,
      media_content_type: this._config.http_content_type || mediaTypes[extension] || "audio/mpeg",
    };
  }

  _renderResults() {
    const container = this.shadowRoot.querySelector(".results");
    container.replaceChildren();
    if (this._results.some((item) => this._isVideoItem(item, item.source || this._source))) this._warmFrame();
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
      }
      if (this._isVideoItem(item, item.source || this._source)) action("mdi:television-play", "Xem video", true);
      action("mdi:headphones", "Nghe (chỉ tiếng)", false);
      row.append(image, track, actions);
      container.append(row);
    });
  }

  _watchCurrent() {
    if (!this._nowWatchItem) return;
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

  _openVideo(item, { withSpeakers, followsDevice = false, startSeconds = 0 }) {
    const id = String(item?.id || "");
    if (!VIDEO_ID.test(id)) {
      this._setStatus("Chỉ xem được video YouTube trên thẻ.", true);
      return;
    }
    const frame = this.shadowRoot.querySelector(".video-frame");
    // A picture shown for a refused video: try the embed again for this one.
    if (this._video.picture) this._leavePicture();
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
    const start = Math.max(0, Math.floor(Number(startSeconds) || 0));
    if (iframe && (this._video.ready || this._frameReady)) {
      // Same player (or the one loaded ahead): switch video without reloading, so it
      // starts at once and fullscreen and mute stay put.
      this._video.ready = true;
      this._videoPost({ event: "command", func: "addEventListener", args: ["onError"] });
      this._videoCommand("loadVideoById", [{ videoId: id, startSeconds: start }]);
      this._videoCommand(this._video.soundHere ? "unMute" : "mute");
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
      const params = new URLSearchParams({
        enablejsapi: "1",
        autoplay: "1",
        rel: "0",
        playsinline: "1",
        origin: location.origin,
      });
      if (!this._video.soundHere) params.set("mute", "1");
      if (start) params.set("start", String(start));
      const src = `https://www.youtube-nocookie.com/embed/${id}?${params}`;
      iframe.setAttribute("src", src);
    }
    this._video.open = true;
    this._video.state = -1;
    this._soundHintShown = false;
    clearTimeout(this._soundCheckTimer);
    if (this._video.soundHere) this._soundCheckTimer = setTimeout(() => this._checkVideoSound(), 1500);
    window.addEventListener("message", this._onVideoMessage);
    if (!this._videoTimer) this._videoTimer = setInterval(() => this._syncVideo(), 2000);
    this._syncNowPlaying();
    this._updateTransportState();
    const player = this.shadowRoot.querySelector(".player");
    if (!player.classList.contains("expanded")) player.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }

  _toggleSoundHere() {
    const video = this._video;
    const pictureSound = video.open && video.withSpeakers && video.soundHere;
    if (deviceAudio.along || pictureSound) {
      if (deviceAudio.along) deviceAudio.stopAlong();
      if (pictureSound) {
        video.soundHere = false;
        this._videoCommand("mute");
      }
    } else if (video.open && video.withSpeakers && !video.picture && !listenScreenOff()) {
      // With speakers the picture starts muted (the speakers carry the sound); this
      // lets the device showing the card play the sound too.
      video.soundHere = true;
      this._videoCommand("unMute");
      clearTimeout(this._soundCheckTimer);
      this._soundCheckTimer = setTimeout(() => this._checkVideoSound(), 1500);
    } else if (this._focusedSession()?.title) {
      // No picture, or screen-off listening: an audio element plays the speakers'
      // song in step with them (it goes on with the screen off when that is on).
      deviceAudio.entryId = this._entryId();
      deviceAudio.startAlong();
      this._syncAlong();
    }
    this._syncSoundHint();
    this._syncNowPlaying();
  }

  _toggleScreenOff() {
    const on = !listenScreenOff();
    setListenScreenOff(on);
    const video = this._video;
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
      video.soundHere = false;
      this._videoCommand("mute");
      deviceAudio.entryId = this._entryId();
      deviceAudio.startAlong();
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
    deviceAudio.loadAlong({
      source: session.source,
      id: session.id,
      url: session.url,
      title: session.title,
      channel: session.artist,
      duration: session.duration,
      thumbnail: session.thumbnail,
    });
    const audio = deviceAudio.real();
    if (!audio || (document.visibilityState === "hidden" && !listenScreenOff())) return;
    const lead = session.output_entity_ids.find((entityId) =>
      ["playing", "paused", "buffering"].includes(this._hass.states[entityId]?.state));
    const speaker = lead && this._hass.states[lead];
    if (!speaker || !this._speakerPlaysItem(speaker, session)) return;
    if (speaker.state === "paused" && !audio.paused) audio.pause();
    if (speaker.state === "playing" && audio.paused) audio.play().catch(() => {});
    const speakerTime = this._speakerPosition(lead, session);
    if (speaker.state !== "playing" || speakerTime === null || Date.now() < this._alongSeekHold) return;
    if (Math.abs(speakerTime - audio.currentTime) > 2) {
      audio.currentTime = speakerTime;
      this._alongSeekHold = Date.now() + 4000;
    }
  }

  _deviceAudioChanged(message, isError) {
    if (!this.shadowRoot || !this._hass) return;
    const video = this._video;
    // The picture follows the device's sound: a new song there (the next one when a
    // song ends) changes the picture too.
    if (video.open && video.followsDevice && isError && !video.picture) {
      // The device's sound couldn't start (no stream from the player server, or the
      // browser refused to play it): the picture keeps its own sound, and a tap inside
      // the video starts it. Following a silent sound paused the video each time it was
      // tapped (owner 15/09/2026: "Kích vào play trên khung video thì giật rồi dừng").
      video.followsDevice = false;
      video.soundHere = true;
      if (deviceAudio.item) deviceAudio.stop();
      // Stopped and unmuted, so the tap inside the video starts it with its sound.
      this._videoCommand("pauseVideo");
      this._videoCommand("unMute");
      this._soundHintShown = true;
      this._syncSoundHint();
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
    const player = this.shadowRoot?.querySelector(".player");
    const memory = {
      // Big (expanded or fullscreen) and turned: HA re-renders the view when the phone
      // turns, which drops fullscreen; the new card comes back expanded instead.
      big: !!player && (player.classList.contains("expanded") || this.shadowRoot.fullscreenElement === player || !!this._ownFullscreen),
      rotated: !!player?.classList.contains("rotated"),
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
    if (memory && !this._results.length && Array.isArray(memory.results) && memory.results.length) {
      this._source = ["youtube", "zing", "http"].includes(memory.source) ? memory.source : "youtube";
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
          this._openVideo(deviceAudio.item, {
            withSpeakers: false,
            followsDevice: true,
            startSeconds: deviceAudio.position()?.time || 0,
          });
        }
      } else {
        // Back at once: the video goes on where it was.
        const startSeconds = saved.playing ? saved.time + (Date.now() - saved.at) / 1000 : saved.time;
        this._openVideo(saved.item, { withSpeakers: false, startSeconds });
      }
      const player = this.shadowRoot.querySelector(".player");
      if (memory.big && this._video.open && !player.classList.contains("expanded")) {
        // Fullscreen can't come back without a tap; the page-covering view can.
        player.classList.add("expanded");
        player.classList.toggle("rotated", !!memory.rotated);
        if (player.getBoundingClientRect().width < window.innerWidth * 0.9) player.classList.remove("expanded", "rotated");
        this._syncVideoExpandButton();
      }
    }
    if (!this._video.open && this._results.some((item) => this._isVideoItem(item, item.source || this._source))) this._warmFrame();
    this._syncNowPlaying();
    this._updateTransportState();
    this._updateProgress();
  }

  /**
   * Load the YouTube player ahead (hidden, no video) once results are on the card: a
   * first "watch" then only switches the video in it instead of loading the player
   * (owner 15/09/2026: "Khi chọn xem video thì mất 1 2 s video mới chạy").
   */
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
    window.addEventListener("message", this._onVideoMessage);
    const params = new URLSearchParams({ enablejsapi: "1", rel: "0", playsinline: "1", origin: location.origin });
    iframe.setAttribute("src", `https://www.youtube-nocookie.com/embed/?${params}`);
  }

  /**
   * The frame loaded a new page (a video opened before the player loaded ahead was
   * ready, or Home Assistant moved the card and the frame reloaded). That page hasn't
   * heard from the card yet. Words from the page it replaced had already marked the
   * frame ready and stopped the handshake, so the new player ignored every command —
   * play, pause, mute (reproduced on the owner's Home Assistant 15/09/2026: the video
   * stayed cued while this device's sound played).
   */
  _frameLoaded() {
    this._frameReady = false;
    this._video.ready = false;
    this._videoHandshake();
  }

  _videoHandshake() {
    // The embed reports its state only after the page says it is listening.
    clearInterval(this._videoHandshakeTimer);
    let tries = 0;
    this._videoHandshakeTimer = setInterval(() => {
      if (this._video.ready || (!this._video.open && this._frameReady) || ++tries > 40) {
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
    if (!this._frameReady) {
      // First word from the player: commands sent before it could take them were
      // dropped, so ask for its events now (a refused video reports onError only then).
      this._frameReady = true;
      this._videoPost({ event: "command", func: "addEventListener", args: ["onStateChange"] });
      this._videoPost({ event: "command", func: "addEventListener", args: ["onError"] });
    }
    // A player loaded ahead talks before any video is open: nothing else to follow yet.
    if (!this._video.open) return;
    this._video.ready = true;
    if (data.event === "onError") {
      this._embedRefused();
      return;
    }
    const info = data.info;
    if (["infoDelivery", "initialDelivery"].includes(data.event) && info && typeof info === "object") {
      if (Number.isFinite(info.currentTime)) {
        this._video.time = info.currentTime;
        this._video.timeAt = Date.now();
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
  _checkVideoSound() {
    const video = this._video;
    if (!video.open || video.picture || !video.soundHere || !this._soundBlocked()) return;
    if (!video.withSpeakers) {
      this._soundFromDevice();
      return;
    }
    this._videoCommand("unMute");
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
    // Shown until the frame plays with its sound: stopped for a tap (state 2 after the
    // device's sound failed) still needs the tap.
    if (this._soundHintShown && (!this._video.soundHere || (this._video.state === 1 && this._video.muted !== true))) this._soundHintShown = false;
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
    if (this._awayPictureOk) {
      await openAway();
      return;
    }
    this._pictureNote(`Đang nghe tiếng · ở ngoài mạng nhà, hình ~${perMinute} MB/phút`, "Xem hình", () => {
      const agreed = window.confirm(
        `Xem hình khi ở ngoài mạng nhà: hình ${info.height || ""}p đi từ mạng nhà qua Internet tới máy này, `
        + `khoảng ${perMinute} MB mỗi phút — tốn dữ liệu di động của máy và băng thông tải lên của nhà. Xem hình?`,
      );
      if (!agreed || this._video.picture !== pending) return;
      // Agreed once: the next refused videos of this viewing open their picture too.
      this._awayPictureOk = true;
      this._pictureNote("Đang nghe tiếng · đang mở hình…");
      openAway();
    });
    this._setStatus(`${why} Đang nghe tiếng; ở ngoài mạng nhà nên chưa mở hình.`);
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
    // That player refused a video: load a fresh one for the next.
    this._frameReady = false;
  }

  _setVideoState(state) {
    if (!Number.isFinite(state) || state === this._video.state) return;
    const previous = this._video.state;
    this._video.state = state;
    if (state === 1 && previous === 3 && this._pictureSeekStarted) {
      // How long that seek took to show: the lead for the next one (smoothed, ≤ 1.5 s).
      const took = (Date.now() - this._pictureSeekStarted) / 1000;
      if (took < 4) this._pictureSeekLag = Math.min(1.5, ((this._pictureSeekLag ?? 0.3) + took) / 2);
      this._pictureSeekStarted = 0;
    }
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
      // Sound still loading (no data yet, position 0): leave the picture alone. Following
      // it sent the picture back to 0 s every few seconds (owner 15/09/2026: "cứ quay về
      // 0s liên tục không chạy tiếp").
      const soundReady = audio.readyState >= 3 && !audio.seeking;
      if (audio.paused && [1, 3].includes(video.state)) this._videoCommand("pauseVideo");
      if (!audio.paused && [-1, 2, 5].includes(video.state)) this._videoCommand("playVideo");
      // This device's sound has an exact clock: keep the picture within 0.35 s of it.
      if (soundReady && !audio.paused && video.state === 1 && Date.now() >= this._lastVideoSeekAt + 3000 && Math.abs(audio.currentTime - this._videoTimeNow()) > 0.35) {
        this._seekPicture(audio.currentTime);
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
    const speakerTime = this._speakerPosition(primary);
    if (speaker.state !== "playing" || speakerTime === null || Date.now() < this._lastVideoSeekAt + 5000) return;
    // The speaker plays its own audio stream, a few seconds after the picture starts
    // (the stream is prepared server-side), so the muted picture follows the speaker's
    // reported position. Past 0.8 s the lag shows on lips and beats (owner 15/09/2026:
    // "khi xem hình ko đc khớp với audio"); the 5 s pause after a seek stops it hunting.
    // Home Assistant reports the speaker's position a few hundred ms late, so 0.5 s is
    // as tight as it holds without the picture seeking over and over.
    if (video.state === 1 && Math.abs(speakerTime - this._videoTimeNow()) > 0.5) {
      this._seekPicture(speakerTime);
    }
  }

  /**
   * Seek the picture to where the sound is. A seek takes a moment to show (YouTube
   * buffers), so the picture landed late; aim ahead by the time the last seeks took.
   */
  _seekPicture(soundTime) {
    const lead = this._pictureSeekLag ?? 0.3;
    this._videoCommand("seekTo", [soundTime + lead, true]);
    this._lastVideoSeekAt = Date.now();
    this._pictureSeekStarted = Date.now();
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
    clearTimeout(this._soundCheckTimer);
    this._soundHintShown = false;
    clearInterval(this._videoTimer);
    this._videoTimer = null;
    this._pendingSpeakerSeek = null;
    const keepFrame = !!this._frameReady && this.isConnected;
    if (keepFrame) {
      // Keep the loaded player (stopped, hidden) so the next video starts at once.
      this._videoPost({ event: "command", func: "stopVideo", args: [] });
    } else {
      clearInterval(this._videoHandshakeTimer);
      window.removeEventListener("message", this._onVideoMessage);
      this._frameReady = false;
    }
    this._video = this._idleVideo();
    const player = this.shadowRoot?.querySelector(".player");
    if (!player) return;
    const frame = this.shadowRoot.querySelector(".video-frame");
    if (keepFrame) {
      for (const child of [...frame.children]) {
        if (child.tagName !== "IFRAME" && !child.classList.contains("sound-hint")) child.remove();
      }
      frame.querySelector(".sound-hint")?.setAttribute("hidden", "");
    } else {
      frame.replaceChildren();
    }
    player.classList.remove("expanded", "rotated");
    this._syncVideoExpandButton();
    this._syncNowPlaying();
    this._updateTransportState();
  }

  async _playResult(item, button, index = -1, watch = true, playlist = null) {
    const source = item.source || this._source;
    const requestedCount = this._selectedPlayers.size;
    const isVideo = this._isVideoItem(item, source);
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
      if (watch && isVideo) {
        this._queue = queue;
        this._queueIndex = position;
        if (listenScreenOff()) {
          // The sound comes from the audio element (it goes on with the screen off),
          // the picture follows it muted.
          deviceAudio.listen(queue[position], queue, position);
          this._openVideo(item, { withSpeakers: false, followsDevice: true });
          this._setStatus(`Đang xem “${name}”, tiếng phát trên máy này cả khi tắt màn hình.`);
          return;
        }
        if (deviceAudio.item || deviceAudio.along) deviceAudio.stop();
        // Unlocked inside this tap, with the song's link fetched meanwhile: if the frame
        // can't play its sound (the HA app), the card's sound starts without waiting.
        deviceAudio.unlock();
        deviceAudio.prefetch(queue[position]);
        this._openVideo(item, { withSpeakers: false });
        this._setStatus(`Đang xem “${name}” trên thẻ. Chọn loa để phát tiếng ra loa.`);
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
      if ((watch && isVideo) || this._video.open) {
        // The picture follows the speakers: the next video synced, or closed
        // when the speakers now play an audio-only source.
        if (isVideo) this._openVideo(item, { withSpeakers: true });
        else this._closeVideo();
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
      this._openVideo(this._queue[target], { withSpeakers: false });
      return;
    }
    const session = this._focusedSession();
    if (!session) return;
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
    }
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
    if (!this._supportsFeature(entityId, 512) || !this._supportsSource(entityId, "youtube")) {
      this._setStatus(`${name} không nhận tiếng YouTube.`, true);
      return;
    }
    const videoTime = this._videoTimeNow();
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source: "youtube",
        target: item.url,
        entity_id: [entityId],
      });
      this._pendingSpeakerSeek = { entityId, from: videoTime, at: Date.now() };
      this._video.withSpeakers = true;
      this._video.followsDevice = false;
      this._video.soundHere = false;
      this._videoCommand("mute");
      if (deviceAudio.item) deviceAudio.stop();
      this._syncNowPlaying();
      this._updateTransportState();
      this._setStatus(`${name} phát tiếng; video trên thẻ tắt tiếng và chạy theo loa.`);
    } catch (error) {
      this._setStatus(error?.message || `Không phát được ra ${name}.`, true);
    }
  }

  async _onSpeakerRemoved(_entityId) {
    if (this._video.open && this._video.withSpeakers && !this._selectedPlayers.size) {
      // No speaker ticked any more: the card's video plays on its own with sound.
      this._video.withSpeakers = false;
      this._video.soundHere = true;
      this._pendingSpeakerSeek = null;
      this._videoCommand("unMute");
      this._syncNowPlaying();
    }
  }

  async _togglePlay() {
    if (deviceAudio.item) {
      deviceAudio.toggle();
      return;
    }
    if (this._video.open && !this._video.withSpeakers) {
      if (!this._video.followsDevice && !this._video.picture && (this._soundHintShown || [-1, 5].includes(this._video.state))) {
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
    this._view = view === "playlists" ? "playlists" : "search";
    const playlists = this._view === "playlists";
    this.shadowRoot.querySelectorAll(".view-tab").forEach((tab) => {
      tab.setAttribute("aria-pressed", String(tab.dataset.view === this._view));
    });
    for (const selector of [".source-switch", "form", ".results"]) {
      this.shadowRoot.querySelector(selector).hidden = playlists;
    }
    this.shadowRoot.querySelector(".playlist-panel").hidden = !playlists;
    this._syncSavePlaylist();
    if (playlists) this._loadPlaylists();
  }

  _syncSavePlaylist() {
    const value = this.shadowRoot.querySelector('input[type="search"]').value.trim();
    this.shadowRoot.querySelector(".save-playlist").hidden =
      this._view !== "search" || this._source === "http" || !PLAYLIST_LINK.test(value);
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

if (!customElements.get("tritue-youtube-player-card")) {
  customElements.define("tritue-youtube-player-card", TriTueYouTubePlayerCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === "tritue-youtube-player-card")) {
  window.customCards.push({
    type: "tritue-youtube-player-card",
    name: "TriTue Music Player",
    description: "Search YouTube/Zing or play direct HTTP audio on Home Assistant media players.",
    preview: true,
  });
}
