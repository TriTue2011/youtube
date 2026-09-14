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

  /** Call inside the tap, before any await. */
  unlock() {
    const audio = this.audio();
    audio.src = SILENCE;
    audio.play().catch(() => {});
    return audio;
  },

  async streamUrl(item) {
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
      this.stop();
      this.notify("Không lấy được tiếng bài này.", true);
      return;
    }
    audio.src = url;
    if (startAt >= 1) audio.addEventListener("loadedmetadata", () => { audio.currentTime = startAt; }, { once: true });
    audio.play().catch(() => this.notify("Trình duyệt chặn tự phát có tiếng — bấm ▶ để nghe.", true));
    this.notify();
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
    this._onDeviceAudio = (message, isError) => this._deviceAudioChanged(message, isError);
  }

  _idleVideo() {
    return { open: false, ready: false, item: null, state: -1, time: 0, timeAt: 0, withSpeakers: false, followsDevice: false, soundHere: true, muted: null };
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
        if (document.fullscreenElement) return;
        try {
          screen.orientation?.unlock?.();
        } catch (_error) {
          // Nothing was locked.
        }
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
        .result-actions { display: flex; gap: 6px; }
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
          padding: max(12px, env(safe-area-inset-top)) 12px 12px;
          color: #fff;
          background: #000;
        }
        .player.expanded > *,
        .player:fullscreen > * { width: min(100%, calc((100vh - 150px) * 16 / 9)); margin-left: auto; margin-right: auto; }
        /* Browser fullscreen on a phone turned sideways: the picture takes the whole
           height (16:9, never cropped) and only the control bar stays under it. */
        @media (orientation: landscape) {
          .player:fullscreen { padding: 4px 8px; }
          .player:fullscreen .now,
          .player:fullscreen .speaker-volumes,
          .player:fullscreen .device-row,
          .player:fullscreen .others { display: none; }
          .player:fullscreen .video-frame { width: min(100%, calc((100dvh - 64px) * 16 / 9)); margin-bottom: 2px; border-radius: 0; }
          .player:fullscreen .progress,
          .player:fullscreen .control-bar { width: min(100%, calc((100dvh - 64px) * 16 / 9)); }
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
          .section-title h3 { font-size: .82rem; }
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
          </section>

          <div class="source-switch" role="group" aria-label="Nguồn nhạc">
            <button class="source-button" type="button" data-source="youtube">YouTube</button>
            <button class="source-button" type="button" data-source="zing">Zing MP3</button>
            <button class="source-button" type="button" data-source="http">Link audio</button>
          </div>

          <form>
            <input type="search" maxlength="2048" autocomplete="off" aria-label="Tìm tên bài hát hoặc ca sĩ" placeholder="Tìm tên bài hát, ca sĩ hoặc dán link YouTube…" required />
            <button class="primary search-button" type="submit" aria-label="Tìm kiếm" title="Tìm kiếm"><ha-icon icon="mdi:magnify"></ha-icon><span class="search-label">Tìm kiếm</span></button>
          </form>
          <p class="status" role="status" aria-live="polite"></p>

          <section class="section">
            <div class="section-title">
              <h3>Loa / màn hình</h3>
              <span class="hint selected-count">0 đã chọn</span>
            </div>
            <div class="players"></div>
            <div class="hidden-players"></div>
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
        this._setStatus("");
      });
    });
    this.shadowRoot.querySelector("form").addEventListener("submit", (event) => {
      event.preventDefault();
      this._search();
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
    this.shadowRoot.querySelector(".selected-count").textContent = `${this._selectedPlayers.size} đã chọn`;
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

  _playTargets() {
    return [...this._selectedPlayers].filter((entityId) => {
      const state = this._hass?.states?.[entityId];
      if (!state || state.state === "unavailable" || !this._supportsFeature(entityId, 512)) return false;
      return this._supportsSource(entityId, this._source);
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

  _updateTransportState() {
    if (!this.shadowRoot || !this._hass) return;
    const listening = !!deviceAudio.item;
    const videoAlone = this._video.open && !this._video.withSpeakers;
    const session = this._focusedSession();
    const outputs = session?.output_entity_ids || [...this._selectedPlayers];
    const playing = listening
      ? deviceAudio.playing()
      : videoAlone
      ? [1, 3].includes(this._video.state)
      : outputs.some((entityId) => this._hass.states[entityId]?.state === "playing");
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
    for (const selector of [".video-expand", ".video-fullscreen", ".video-close"]) {
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
          : video.followsDevice ? "Tiếng từ máy này, cả khi tắt màn hình" : "Xem trên thẻ",
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
      this._nowWatchItem = null;
      this.shadowRoot.querySelector(".watch").hidden = true;
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
      if (this._isVideoItem(item, item.source || this._source)) action("mdi:television-play", "Xem video", true);
      action("mdi:headphones", "Nghe (chỉ tiếng)", false);
      row.append(image, track, actions);
      container.append(row);
    });
  }

  _watchCurrent() {
    if (!this._nowWatchItem) return;
    // Already playing on the speakers: keep their sound, show the picture here muted.
    this._openVideo(this._nowWatchItem, { withSpeakers: this._activeSpeakers().length > 0 });
  }

  _openVideo(item, { withSpeakers, followsDevice = false, startSeconds = 0 }) {
    const id = String(item?.id || "");
    if (!VIDEO_ID.test(id)) {
      this._setStatus("Chỉ xem được video YouTube trên thẻ.", true);
      return;
    }
    const frame = this.shadowRoot.querySelector(".video-frame");
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
    if (iframe && this._video.ready) {
      // Same player: switch video without reloading, so fullscreen and mute stay put.
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
        iframe.addEventListener("load", () => this._videoHandshake());
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
    if (this._video.soundHere) this._soundCheckTimer = setTimeout(() => this._checkVideoSound(), 3500);
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
    } else if (video.open && video.withSpeakers && !listenScreenOff()) {
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
    if (video.open && video.followsDevice && deviceAudio.item?.id !== video.item?.id) {
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
    this._videoPost({ event: "command", func, args });
  }

  _videoTimeNow() {
    const video = this._video;
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
    if (!data || typeof data !== "object") return;
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
   * inside the video itself: the embed then stays stopped or plays muted. Ask
   * once more, then tell the viewer to tap the video.
   */
  _checkVideoSound() {
    const video = this._video;
    if (!video.open || !video.soundHere || !this._soundBlocked()) return;
    this._videoCommand("unMute");
    this._videoCommand("playVideo");
    clearTimeout(this._soundCheckTimer);
    this._soundCheckTimer = setTimeout(() => {
      this._soundHintShown = this._video.open && this._video.soundHere && this._soundBlocked();
      this._syncSoundHint();
    }, 1500);
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
   * Home Assistant is opened by IP address, while the same video plays when it is
   * opened by name. Rather than leave a dead frame, the sound goes on without it.
   */
  _embedRefused() {
    const video = this._video;
    if (!video.open || !video.item) return;
    const item = { source: "youtube", ...video.item };
    const host = location.hostname;
    const why = /^[\d.]+$/.test(host) || host.includes(":")
      ? `YouTube không cho xem hình “${item.title}” khi mở Home Assistant bằng địa chỉ IP (mở bằng tên, ví dụ homeassistant.local, thì xem được).`
      : `YouTube không cho xem hình “${item.title}” trên thẻ.`;
    if (video.withSpeakers) {
      this._closeVideo();
      this._setStatus(`${why} Loa vẫn phát tiếng.`);
      return;
    }
    const followsDevice = video.followsDevice;
    const queue = this._queue.length ? this._queue : [item];
    const index = Math.max(0, this._queueIndex);
    this._closeVideo();
    if (!followsDevice) {
      deviceAudio.entryId = this._entryId();
      deviceAudio.listen(item, queue, index);
    }
    this._setStatus(`${why} Đang nghe tiếng trên máy này.`);
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
      if (!audio.paused && Date.now() >= this._lastVideoSeekAt + 4000 && Math.abs(audio.currentTime - this._videoTimeNow()) > 2) {
        this._videoCommand("seekTo", [audio.currentTime, true]);
        this._lastVideoSeekAt = Date.now();
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
    // The speaker starts a few seconds after the picture (its stream is prepared
    // server-side), so the muted picture follows the speaker's reported position.
    if (Math.abs(speakerTime - this._videoTimeNow()) > 2) {
      this._videoCommand("seekTo", [speakerTime, true]);
      this._lastVideoSeekAt = Date.now();
    }
  }

  _toggleVideoExpanded() {
    const player = this.shadowRoot.querySelector(".player");
    const expand = !player.classList.contains("expanded");
    player.classList.toggle("expanded", expand);
    // Some dashboard layouts contain their cards, which traps a fixed overlay
    // inside the card; fall back to the browser's fullscreen mode there.
    if (expand && player.getBoundingClientRect().width < window.innerWidth * 0.9) {
      player.classList.remove("expanded");
      this._videoFullscreen();
      return;
    }
    this._syncVideoExpandButton();
  }

  _syncVideoExpandButton() {
    const button = this.shadowRoot.querySelector(".video-expand");
    const expanded = this.shadowRoot.querySelector(".player").classList.contains("expanded");
    button.querySelector("ha-icon").setAttribute("icon", expanded ? "mdi:arrow-collapse" : "mdi:arrow-expand");
    button.setAttribute("aria-label", expanded ? "Thu nhỏ video" : "Phóng to video");
    button.title = expanded ? "Thu nhỏ" : "Phóng to";
  }

  _videoFullscreen() {
    if (document.fullscreenElement) {
      document.exitFullscreen?.();
      return;
    }
    // The whole player goes fullscreen so the card's buttons stay usable there.
    const player = this.shadowRoot.querySelector(".player");
    const request = player.requestFullscreen || player.webkitRequestFullscreen;
    if (!request) {
      this._setStatus("Trình duyệt này không hỗ trợ toàn màn hình — dùng nút toàn màn hình trong khung video.", true);
      return;
    }
    Promise.resolve(request.call(player, { navigationUI: "hide" }))
      .then(() => screen.orientation?.lock?.("landscape"))
      // Phones: turn sideways for the 16:9 picture. Only browsers that can lock the
      // orientation while fullscreen (Chrome on Android) rotate; elsewhere the video
      // still fits the screen without cropping.
      .catch(() => {
        if (!document.fullscreenElement) {
          this._setStatus("Không mở được toàn màn hình — dùng nút toàn màn hình trong khung video.", true);
        }
      });
  }

  _closeVideo() {
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
    player.classList.remove("expanded");
    this._syncVideoExpandButton();
    this._syncNowPlaying();
    this._updateTransportState();
  }

  async _playResult(item, button, index = -1, watch = true) {
    const source = item.source || this._source;
    const requestedCount = this._selectedPlayers.size;
    const isVideo = this._isVideoItem(item, source);
    if (!requestedCount) {
      // No speaker ticked: listen or watch right here, with the results as the queue.
      const queue = (this._results.includes(item) ? this._results : [item])
        .map((entry) => ({ ...entry, source: entry.source || source }));
      const position = Math.max(0, index >= 0
        ? index
        : queue.findIndex((entry) => (entry.url || entry.id) === (item.url || item.id)));
      deviceAudio.entryId = this._entryId();
      const name = item.title || item.id;
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
        // Unlocked inside this tap: if YouTube refuses the video here, its sound plays instead.
        deviceAudio.unlock();
        this._openVideo(item, { withSpeakers: false });
        this._setStatus(`Đang xem “${name}” trên thẻ. Chọn loa để phát tiếng ra loa.`);
        return;
      }
      if (this._video.open) this._closeVideo();
      deviceAudio.listen(queue[position], queue, position);
      this._setStatus(`Đang nghe “${name}” trên máy này.`);
      return;
    }
    const entityIds = this._playTargets();
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
