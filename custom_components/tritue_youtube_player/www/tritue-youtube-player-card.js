class TriTueYouTubePlayerCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._source = "youtube";
    this._selectedPlayers = new Set();
    this._results = [];
    this._currentItem = null;
    this._rendered = false;
    this._defaultsApplied = false;
    this._capabilities = new Map();
    this._capabilityEntryId = "";
    this._capabilitiesLoading = false;
    this._sharedSessionMarker = "";
    this._queue = [];
    this._queueIndex = -1;
    this._volumeRowsSig = "";
    this._activeVolumeEntity = null;
    this._autoAdvance = false;
    this._trackPlaying = false;
    this._manualSelection = false;
    // Players hidden from this card. Stored by the integration in HA storage so
    // the list survives restarts and card reloads; restorable from the card.
    this._hiddenPlayers = new Set();
    this._hiddenLoading = false;
    this._hiddenLoaded = false;
    this._showHidden = false;
    this._nowWatchItem = null;
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string") {
      throw new Error("TriTue card requires a media_player entity");
    }
    this._config = { title: "TriTue Music", ...config };
    this._restoreNowPlaying();
  }

  set hass(hass) {
    this._hass = hass;
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
    this._checkAutoAdvance();
  }

  getCardSize() {
    return 10;
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
        .wrap { padding: 20px; }
        header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
        h2 { margin: 0; font-size: 1.35rem; line-height: 1.2; }
        .subtitle, .hint { color: var(--secondary-text-color); font-size: .86rem; }
        .subtitle { margin: 5px 0 0; }
        .source-switch {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          padding: 4px;
          margin: 18px 0 14px;
          border-radius: 12px;
          background: var(--secondary-background-color);
        }
        button, input { font: inherit; }
        button { cursor: pointer; }
        .source-button {
          border: 0;
          border-radius: 9px;
          padding: 9px 12px;
          color: var(--secondary-text-color);
          background: transparent;
          font-weight: 600;
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
          padding: 11px 13px;
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
        button:disabled { cursor: not-allowed; opacity: .45; }
        .status { min-height: 21px; margin: 8px 1px 0; color: var(--secondary-text-color); font-size: .84rem; }
        .status.error { color: var(--error-color); }
        .section { margin-top: 18px; }
        .section-title { display: flex; align-items: center; justify-content: space-between; margin-bottom: 9px; }
        .section-title h3 { margin: 0; font-size: .95rem; }
        .players { display: flex; flex-wrap: wrap; gap: 8px; max-height: 132px; overflow: auto; }
        .player-chip {
          display: flex;
          align-items: center;
          gap: 7px;
          max-width: 100%;
          padding: 7px 10px;
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
        .hidden-players { margin-top: 8px; }
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
        .now-playing {
          display: grid;
          grid-template-columns: 70px minmax(0, 1fr);
          gap: 13px;
          align-items: center;
          padding: 12px;
          border: 1px solid var(--divider-color);
          border-radius: 14px;
          background: color-mix(in srgb, var(--secondary-background-color) 78%, transparent);
        }
        .now-cover {
          display: grid;
          place-items: center;
          width: 70px;
          height: 70px;
          overflow: hidden;
          border-radius: 11px;
          color: var(--secondary-text-color);
          background: var(--divider-color);
        }
        .now-cover img { width: 100%; height: 100%; object-fit: cover; }
        .now-copy { min-width: 0; }
        .now-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 700; }
        .now-meta, .now-targets { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .82rem; }
        .now-meta { margin-top: 5px; }
        .now-targets { margin-top: 7px; }
        .controls { display: grid; gap: 14px; }
        .transport-row { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; }
        .transport {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 7px;
          min-height: 44px;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 11px;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
          font-weight: 600;
        }
        .transport:hover:not(:disabled) { border-color: var(--primary-color); color: var(--primary-color); }
        .transport.stop { color: var(--error-color); }
        .volume-row { display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: 9px; }
        input[type="range"] { width: 100%; accent-color: var(--primary-color); }
        .speaker-volumes { display: grid; gap: 10px; }
        .svol-row { display: grid; grid-template-columns: minmax(80px, 34%) 1fr auto; align-items: center; gap: 10px; }
        .svol-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: .86rem; }
        .svol-pct { min-width: 38px; text-align: right; color: var(--secondary-text-color); font-size: .82rem; font-variant-numeric: tabular-nums; }
        .results { display: grid; gap: 8px; max-height: 370px; overflow: auto; padding-right: 2px; }
        .result {
          display: grid;
          grid-template-columns: 54px minmax(0, 1fr) auto;
          gap: 11px;
          align-items: center;
          padding: 8px;
          border: 1px solid var(--divider-color);
          border-radius: 12px;
          background: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
        }
        .cover { width: 54px; height: 54px; border-radius: 8px; object-fit: cover; background: var(--divider-color); }
        .track { min-width: 0; }
        .track-title { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }
        .track-meta { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--secondary-text-color); font-size: .8rem; margin-top: 4px; }
        .play-result {
          display: grid;
          place-items: center;
          width: 38px;
          height: 38px;
          border: 0;
          border-radius: 50%;
          color: var(--text-primary-color, #fff);
          background: var(--primary-color);
        }
        .empty { padding: 22px 8px; text-align: center; color: var(--secondary-text-color); }
        .video-panel { margin: 16px 0 4px; }
        .video-frame {
          position: relative;
          width: 100%;
          aspect-ratio: 16 / 9;
          overflow: hidden;
          border-radius: 12px;
          background: #000;
        }
        .video-frame iframe { position: absolute; inset: 0; width: 100%; height: 100%; border: 0; }
        .video-bar { display: flex; align-items: center; gap: 6px; margin-top: 8px; }
        .video-title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; font-size: .9rem; }
        .video-button {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 6px 9px;
          border: 1px solid var(--divider-color);
          border-radius: 9px;
          color: var(--primary-text-color);
          background: var(--secondary-background-color);
          font-size: .8rem;
          --mdc-icon-size: 16px;
        }
        .video-button:hover { border-color: var(--primary-color); color: var(--primary-color); }
        .video-panel .hint { margin: 6px 1px 0; font-size: .78rem; }
        /* Phóng to: phủ kín màn hình trên bảng điều khiển. */
        .video-panel.expanded {
          position: fixed;
          inset: 0;
          z-index: 10;
          margin: 0;
          padding: max(12px, env(safe-area-inset-top)) 12px 12px;
          display: flex;
          flex-direction: column;
          justify-content: center;
          background: #000;
          color: #fff;
        }
        .video-panel.expanded .video-frame,
        .video-panel.expanded .video-bar { width: min(100%, calc((100vh - 96px) * 16 / 9)); margin-left: auto; margin-right: auto; }
        .video-panel.expanded .video-title { color: #fff; }
        .watch-result {
          display: grid;
          place-items: center;
          width: 34px;
          height: 34px;
          border: 1px solid var(--divider-color);
          border-radius: 50%;
          color: var(--primary-text-color);
          background: transparent;
          --mdc-icon-size: 18px;
        }
        .watch-result:hover { border-color: var(--primary-color); color: var(--primary-color); }
        .result { grid-template-columns: 54px minmax(0, 1fr) auto auto; }
        .now-watch { margin-top: 8px; }
        @media (max-width: 520px) {
          .wrap { padding: 16px; }
          form { grid-template-columns: 1fr; }
          .transport-row { grid-template-columns: 1fr 1fr; }
          .transport { min-height: 48px; }
        }
      </style>
      <ha-card>
        <div class="wrap">
          <header>
            <div>
              <h2></h2>
              <p class="subtitle">Nguồn nhạc độc lập · loa là thiết bị phát</p>
            </div>
            <ha-icon icon="mdi:music-circle"></ha-icon>
          </header>

          <section class="video-panel" hidden>
            <div class="video-frame"></div>
            <div class="video-bar">
              <span class="video-title"></span>
              <button class="video-button video-expand" type="button" aria-label="Phóng to video">
                <ha-icon icon="mdi:arrow-expand"></ha-icon><span>Phóng to</span>
              </button>
              <button class="video-button video-fullscreen" type="button" aria-label="Xem toàn màn hình">
                <ha-icon icon="mdi:fullscreen"></ha-icon>
              </button>
              <button class="video-button video-close" type="button" aria-label="Đóng video">
                <ha-icon icon="mdi:close"></ha-icon>
              </button>
            </div>
            <p class="hint">Chất lượng: bấm biểu tượng bánh răng trong khung video.</p>
          </section>

          <div class="source-switch" role="group" aria-label="Nguồn nhạc">
            <button class="source-button" type="button" data-source="youtube">YouTube</button>
            <button class="source-button" type="button" data-source="zing">Zing MP3</button>
            <button class="source-button" type="button" data-source="http">HTTP Audio</button>
          </div>

          <form>
            <input type="search" maxlength="2048" autocomplete="off" aria-label="Tìm tên bài hát hoặc ca sĩ" placeholder="Tìm tên bài hát, ca sĩ hoặc dán link YouTube…" required />
            <button class="primary search-button" type="submit">Tìm kiếm</button>
          </form>
          <p class="status" role="status" aria-live="polite"></p>

          <section class="section">
            <div class="section-title">
              <h3>Chọn loa / màn hình</h3>
              <span class="hint selected-count">0 đã chọn</span>
            </div>
            <div class="players"></div>
            <div class="hidden-players"></div>
          </section>

          <section class="section">
            <div class="section-title">
              <h3>Đang phát</h3>
              <span class="hint now-state">Chưa phát</span>
            </div>
            <div class="now-playing">
              <div class="now-cover">
                <ha-icon icon="mdi:music-note"></ha-icon>
                <img alt="" hidden />
              </div>
              <div class="now-copy">
                <div class="now-title">Chưa phát bài nào</div>
                <div class="now-meta">Chọn một bài trong kết quả để bắt đầu.</div>
                <div class="now-targets">Chưa chọn thiết bị phát</div>
                <button class="video-button now-watch" type="button" hidden>
                  <ha-icon icon="mdi:television-play"></ha-icon><span>Xem trên thẻ</span>
                </button>
              </div>
            </div>
          </section>

          <section class="section controls">
            <div class="section-title">
              <h3>Điều khiển các thiết bị đã chọn</h3>
              <span class="hint transport-state">Chưa chọn thiết bị</span>
            </div>
            <div class="transport-row" role="group" aria-label="Điều khiển phát nhạc">
              <button class="transport previous" type="button" data-service="media_previous_track" aria-label="Bài trước">
                <ha-icon icon="mdi:skip-previous"></ha-icon><span>Bài trước</span>
              </button>
              <button class="transport play-pause" type="button" data-service="media_play_pause" aria-label="Phát hoặc tạm dừng">
                <ha-icon icon="mdi:play"></ha-icon><span>Phát / Tạm dừng</span>
              </button>
              <button class="transport next" type="button" data-service="media_next_track" aria-label="Bài tiếp theo">
                <ha-icon icon="mdi:skip-next"></ha-icon><span>Bài tiếp</span>
              </button>
              <button class="transport stop" type="button" data-service="media_stop" aria-label="Dừng phát nhạc">
                <ha-icon icon="mdi:stop"></ha-icon><span>Dừng</span>
              </button>
            </div>
            <div>
              <div class="section-title"><h3>Âm lượng từng loa</h3></div>
              <div class="speaker-volumes"></div>
            </div>
          </section>

          <section class="section">
            <div class="section-title">
              <h3>Kết quả</h3>
              <span class="hint source-hint"></span>
            </div>
            <div class="results"><div class="empty">Nhập từ khóa để tìm nhạc.</div></div>
          </section>
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
    this.shadowRoot.querySelector(".play-pause").addEventListener("click", () => this._transport("media_play_pause"));
    this.shadowRoot.querySelector(".next").addEventListener("click", () => this._skip(1));
    this.shadowRoot.querySelector(".stop").addEventListener("click", () => this._stop());
    this.shadowRoot.querySelector(".video-expand").addEventListener("click", () => this._toggleVideoExpanded());
    this.shadowRoot.querySelector(".video-fullscreen").addEventListener("click", () => this._videoFullscreen());
    this.shadowRoot.querySelector(".video-close").addEventListener("click", () => this._closeVideo());
    this.shadowRoot.querySelector(".now-watch").addEventListener("click", () => {
      if (this._nowWatchItem) this._watchVideo(this._nowWatchItem);
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
      .filter(([entityId]) => entityId.startsWith("media_player.") && entityId !== virtualEntity)
      .sort((left, right) => this._friendlyName(left).localeCompare(this._friendlyName(right), "vi"));
    const players = allPlayers.filter(([entityId]) => !this._hiddenPlayers.has(entityId));

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
      empty.textContent = this._hiddenPlayers.size
        ? "Mọi thiết bị đang ẩn — mở mục Đã ẩn để khôi phục."
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
    this._renderHiddenPlayers(allPlayers.filter(([entityId]) => this._hiddenPlayers.has(entityId)));
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
    return [...this._selectedPlayers].filter((entityId) => {
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

  _updateTransportState() {
    if (!this.shadowRoot || !this._hass) return;
    const selectedStates = [...this._selectedPlayers]
      .map((entityId) => this._hass.states[entityId]?.state)
      .filter(Boolean);
    const anyPlaying = selectedStates.includes("playing");
    const anyPaused = selectedStates.includes("paused");
    const stateLabel = this.shadowRoot.querySelector(".transport-state");
    stateLabel.textContent = !selectedStates.length
      ? "Chưa chọn thiết bị"
      : anyPlaying
        ? "Đang phát"
        : anyPaused
          ? "Đang tạm dừng"
          : "Sẵn sàng";
    this.shadowRoot.querySelector(".play-pause ha-icon")
      .setAttribute("icon", anyPlaying ? "mdi:pause" : "mdi:play");
    const hasNext = this._queueIndex >= 0 && this._queueIndex < this._queue.length - 1;
    const hasPrev = this._queueIndex > 0;
    const canNavigate = this._playTargets().length > 0;
    this.shadowRoot.querySelectorAll(".transport").forEach((button) => {
      const service = button.dataset.service;
      if (service === "media_stop") {
        button.disabled = !selectedStates.length && !this._currentItem;
      } else if (service === "media_next_track") {
        button.disabled = !(hasNext && canNavigate);
      } else if (service === "media_previous_track") {
        button.disabled = !(hasPrev && canNavigate);
      } else {
        button.disabled = !this._targetsForService(service).length;
      }
    });
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
      if (!speakers.length) {
        const empty = document.createElement("div");
        empty.className = "hint";
        empty.textContent = this._selectedPlayers.size
          ? "Loa đã chọn không chỉnh được âm lượng tuyệt đối."
          : "Chọn loa để chỉnh âm lượng riêng.";
        container.append(empty);
        return;
      }
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

  _storageKey() {
    return `tritue-player:${this._config?.entity || "default"}:now-playing`;
  }

  _restoreNowPlaying() {
    try {
      const saved = globalThis.localStorage?.getItem(this._storageKey());
      this._currentItem = saved ? JSON.parse(saved) : null;
    } catch (_error) {
      this._currentItem = null;
    }
  }

  _rememberNowPlaying(item, entityIds) {
    this._currentItem = {
      source: this._source,
      id: String(item.id || ""),
      target: String(item.url || item.id || ""),
      media_content_type: item.media_content_type,
      title: String(item.title || item.id || "Không rõ tên"),
      channel: String(item.channel || ""),
      thumbnail: /^https?:\/\//.test(item.thumbnail || "") ? item.thumbnail : "",
      duration: Number(item.duration || 0),
      entity_ids: entityIds,
      started_at: Date.now(),
    };
    try {
      globalThis.localStorage?.setItem(this._storageKey(), JSON.stringify(this._currentItem));
    } catch (_error) {
      // The card still works when browser storage is disabled.
    }
  }

  _clearRememberedNowPlaying() {
    this._currentItem = null;
    try {
      globalThis.localStorage?.removeItem(this._storageKey());
    } catch (_error) {
      // Ignore unavailable browser storage.
    }
  }

  _syncNowPlaying() {
    if (!this.shadowRoot || !this._hass) return;
    const selected = [...this._selectedPlayers]
      .map((entityId) => [entityId, this._hass.states[entityId]])
      .filter(([, state]) => state);
    const active = selected.find(([, state]) => state.state === "playing")
      || selected.find(([, state]) => state.state === "paused")
      || selected.find(([, state]) => state.state === "buffering");
    const serverState = this._hass.states[this._config.entity];
    const serverAttributes = serverState?.attributes || {};
    const state = active?.[1] || serverState;
    const attributes = active?.[1]?.attributes || serverAttributes;
    const sharedSession = serverAttributes.media_title ? {
      source: serverAttributes.session_source,
      id: serverAttributes.media_content_id,
      title: serverAttributes.media_title,
      channel: serverAttributes.media_artist,
      thumbnail: serverAttributes.entity_picture || serverAttributes.media_image_url,
      duration: serverAttributes.media_duration,
      entity_ids: serverAttributes.output_entity_ids,
      queue_index: Number(serverAttributes.queue_index ?? -1),
      queue_size: Number(serverAttributes.queue_size || 0),
    } : null;
    const fallback = sharedSession || this._currentItem || {};
    const title = attributes.media_title || fallback.title || "";
    const artist = attributes.media_artist || fallback.channel || "";
    const duration = this._formatDuration(attributes.media_duration || fallback.duration);
    const queuePosition = fallback.queue_size > 1 && fallback.queue_index >= 0
      ? `Hàng đợi ${fallback.queue_index + 1}/${fallback.queue_size}`
      : "";
    const imageUrl = attributes.entity_picture || attributes.media_image_url || fallback.thumbnail || "";
    const targetIds = this._manualSelection
      ? [...this._selectedPlayers]
      : (fallback.entity_ids?.length ? fallback.entity_ids : [...this._selectedPlayers]);
    const targetNames = targetIds
      .map((entityId) => this._hass.states[entityId]?.attributes?.friendly_name || entityId)
      .filter(Boolean);

    this.shadowRoot.querySelector(".now-title").textContent = title || "Chưa phát bài nào";
    this.shadowRoot.querySelector(".now-meta").textContent = title
      ? [artist, duration, queuePosition, fallback.source === "zing" ? "Zing MP3" : fallback.source === "youtube" ? "YouTube" : fallback.source === "http" ? "HTTP Audio" : ""]
        .filter(Boolean).join(" · ")
      : "Chọn một bài trong kết quả để bắt đầu.";
    this.shadowRoot.querySelector(".now-targets").textContent = targetNames.length
      ? `Thiết bị: ${targetNames.join(", ")}`
      : "Chưa chọn thiết bị phát";
    this.shadowRoot.querySelector(".now-state").textContent = state?.state === "playing"
      ? "Đang phát"
      : state?.state === "paused"
        ? "Tạm dừng"
        : title
          ? "Đã gửi"
          : "Chưa phát";

    const watchId = String(fallback.id || "");
    this._nowWatchItem = title && fallback.source === "youtube" && /^[A-Za-z0-9_-]{11}$/.test(watchId)
      ? { id: watchId, title }
      : null;
    this.shadowRoot.querySelector(".now-watch").hidden = !this._nowWatchItem;

    const image = this.shadowRoot.querySelector(".now-cover img");
    const icon = this.shadowRoot.querySelector(".now-cover ha-icon");
    image.hidden = !/^https?:\/\//.test(imageUrl);
    icon.hidden = !image.hidden;
    if (!image.hidden && image.src !== imageUrl) image.src = imageUrl;
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
    submit.textContent = isHttp ? "Thêm URL" : "Tìm kiếm";
    const hints = {
      youtube: "TV phát video · loa phát nhạc",
      zing: "Bài công khai, không VIP",
      http: "MP3/AAC/FLAC/HLS trực tiếp",
    };
    this.shadowRoot.querySelector(".source-hint").textContent = hints[this._source] || "";
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
    if (!this._results.length) {
      const empty = document.createElement("div");
      empty.className = "empty";
      empty.textContent = "Chưa có kết quả.";
      container.append(empty);
      return;
    }
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
      const play = document.createElement("button");
      play.className = "play-result";
      play.type = "button";
      play.title = `Phát ${title.textContent}`;
      play.setAttribute("aria-label", play.title);
      play.textContent = "▶";
      play.addEventListener("click", () => this._playResult(item, play, index));
      const watch = document.createElement("button");
      watch.className = "watch-result";
      watch.type = "button";
      watch.title = `Xem video ${title.textContent} trên thẻ`;
      watch.setAttribute("aria-label", watch.title);
      const watchIcon = document.createElement("ha-icon");
      watchIcon.setAttribute("icon", "mdi:television-play");
      watch.append(watchIcon);
      watch.addEventListener("click", () => this._watchVideo(item));
      watch.hidden = (item.source || this._source) !== "youtube" || !/^[A-Za-z0-9_-]{11}$/.test(String(item.id || ""));
      row.append(image, track, watch, play);
      container.append(row);
    });
  }

  _watchVideo(item) {
    const id = String(item?.id || "");
    if (!/^[A-Za-z0-9_-]{11}$/.test(id)) {
      this._setStatus("Chỉ xem được video YouTube trên thẻ.", true);
      return;
    }
    const panel = this.shadowRoot.querySelector(".video-panel");
    const frame = panel.querySelector(".video-frame");
    let iframe = frame.querySelector("iframe");
    if (!iframe) {
      iframe = document.createElement("iframe");
      // Home Assistant sends "Referrer-Policy: no-referrer", and YouTube refuses
      // embeds without a Referer ("Error 153 — Video player configuration error").
      // The iframe's own policy overrides the page's; it must be set before src.
      iframe.setAttribute("referrerpolicy", "strict-origin-when-cross-origin");
      iframe.setAttribute("allow", "autoplay; encrypted-media; picture-in-picture; fullscreen");
      iframe.setAttribute("allowfullscreen", "");
      iframe.title = "Video YouTube";
      frame.append(iframe);
    }
    const src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&playsinline=1`;
    if (iframe.getAttribute("src") !== src) iframe.setAttribute("src", src);
    panel.querySelector(".video-title").textContent = item.title || id;
    panel.hidden = false;
    if (!panel.classList.contains("expanded")) panel.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }

  _toggleVideoExpanded() {
    const panel = this.shadowRoot.querySelector(".video-panel");
    const expand = !panel.classList.contains("expanded");
    panel.classList.toggle("expanded", expand);
    // Some dashboard layouts contain their cards, which traps a fixed overlay
    // inside the card; fall back to the browser's fullscreen mode there.
    if (expand && panel.getBoundingClientRect().width < window.innerWidth * 0.9) {
      panel.classList.remove("expanded");
      this._videoFullscreen();
      return;
    }
    this._syncVideoExpandButton();
  }

  _syncVideoExpandButton() {
    const panel = this.shadowRoot.querySelector(".video-panel");
    const button = panel.querySelector(".video-expand");
    const expanded = panel.classList.contains("expanded");
    button.querySelector("ha-icon").setAttribute("icon", expanded ? "mdi:arrow-collapse" : "mdi:arrow-expand");
    button.querySelector("span").textContent = expanded ? "Thu nhỏ" : "Phóng to";
    button.setAttribute("aria-label", expanded ? "Thu nhỏ video" : "Phóng to video");
  }

  _videoFullscreen() {
    const frame = this.shadowRoot.querySelector(".video-frame");
    const request = frame.requestFullscreen || frame.webkitRequestFullscreen;
    if (!request) {
      this._setStatus("Trình duyệt này không hỗ trợ toàn màn hình — dùng nút toàn màn hình trong khung video.", true);
      return;
    }
    Promise.resolve(request.call(frame)).catch(() =>
      this._setStatus("Không mở được toàn màn hình — dùng nút toàn màn hình trong khung video.", true));
  }

  _closeVideo() {
    const panel = this.shadowRoot.querySelector(".video-panel");
    panel.querySelector(".video-frame").replaceChildren();
    panel.classList.remove("expanded");
    panel.hidden = true;
    this._syncVideoExpandButton();
  }

  async _playResult(item, button, index = -1) {
    const requestedCount = this._selectedPlayers.size;
    const entityIds = this._playTargets();
    if (!entityIds.length) {
      this._setStatus(
        requestedCount
          ? "Thiết bị đã chọn không hỗ trợ nguồn này. Với loa, hãy dùng Zing hoặc URL audio trực tiếp."
          : "Hãy chọn ít nhất một loa hoặc màn hình.",
        true,
      );
      return;
    }
    const entryId = this._entryId();
    if (!entryId) {
      this._setStatus("Không tìm thấy config entry của integration.", true);
      return;
    }
    // Snapshot the current results as the play queue so Bài trước/Bài tiếp work.
    if (this._results.length) this._queue = this._results.slice();
    this._queueIndex = index >= 0
      ? index
      : this._queue.findIndex((entry) => (entry.url || entry.id) === (item.url || item.id));
    button.disabled = true;
    this._setStatus(`Đang phát “${item.title || item.id}”…`);
    try {
      // No volume_level: each speaker keeps its own level (set per-speaker below).
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source: this._source,
        target: item.url || item.id,
        entity_id: entityIds,
        media_content_type: item.media_content_type,
      });
      this._rememberNowPlaying(item, entityIds);
      // Arm auto-advance: play the next queue item when this track finishes.
      this._autoAdvance = true;
      this._trackPlaying = false;
      this._syncNowPlaying();
      this._updateTransportState();
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
    const target = this._queueIndex + step;
    if (this._queueIndex < 0 || target < 0 || target >= this._queue.length) {
      this._setStatus(step > 0 ? "Đã ở cuối hàng đợi." : "Đã ở đầu hàng đợi.");
      return;
    }
    const button = this.shadowRoot.querySelector(
      step > 0 ? ".transport.next" : ".transport.previous",
    );
    await this._playResult(this._queue[target], button, target);
  }

  _checkAutoAdvance() {
    if (!this._autoAdvance || this._queueIndex < 0) return;
    const targets = this._currentItem?.entity_ids?.length
      ? this._currentItem.entity_ids
      : [...this._selectedPlayers];
    const primary = targets.find((entityId) => this._hass?.states?.[entityId]);
    if (!primary) return;
    const state = this._hass.states[primary].state;
    if (state === "playing" || state === "buffering") {
      this._trackPlaying = true;
      return;
    }
    // The track reached a terminal state after actually playing -> it finished.
    // "paused" is excluded so a manual pause never skips the song.
    const finished =
      this._trackPlaying && ["idle", "off", "standby", "stopped"].includes(state);
    if (!finished) return;
    this._trackPlaying = false;
    if (this._queueIndex < this._queue.length - 1) {
      this._skip(1);
    } else {
      this._autoAdvance = false;
      this._setStatus("Đã phát hết hàng đợi.");
    }
  }

  _isPlaying() {
    return this._autoAdvance && !!this._currentItem?.target;
  }

  async _onSpeakerAdded(entityId) {
    // Ticking a speaker while something is playing makes it join the song now.
    if (!this._isPlaying()) return;
    const source = this._currentItem.source || this._source;
    const state = this._hass?.states?.[entityId];
    if (!state || state.state === "unavailable") return;
    if (!this._supportsFeature(entityId, 512) || !this._supportsSource(entityId, source)) {
      this._setStatus(
        `${state.attributes?.friendly_name || entityId} không nhận nguồn đang phát.`,
        true,
      );
      return;
    }
    const entryId = this._entryId();
    if (!entryId) return;
    try {
      await this._hass.callService("tritue_youtube_player", "play_on_players", {
        entry_id: entryId,
        source,
        target: this._currentItem.target,
        entity_id: [entityId],
        media_content_type: this._currentItem.media_content_type,
      });
      this._setStatus(`Đã thêm ${state.attributes?.friendly_name || entityId} vào bài đang phát.`);
    } catch (error) {
      this._setStatus(error?.message || "Không thêm được loa vào bài đang phát.", true);
    }
  }

  async _onSpeakerRemoved(entityId) {
    // Un-ticking a playing speaker stops just that one; the rest keep going.
    const state = this._hass?.states?.[entityId];
    if (!state || !["playing", "paused", "buffering"].includes(state.state)) return;
    try {
      await this._hass.callService("media_player", "media_stop", { entity_id: entityId });
      this._setStatus(`Đã tắt ${state.attributes?.friendly_name || entityId}.`);
    } catch (error) {
      this._setStatus(error?.message || "Không tắt được loa.", true);
    }
  }

  async _transport(service) {
    const entityIds = this._targetsForService(service);
    if (!entityIds.length) {
      this._setStatus("Không có thiết bị đã chọn hỗ trợ lệnh này.", true);
      return;
    }
    const labels = {
      media_previous_track: "bài trước",
      media_play_pause: "phát/tạm dừng",
      media_next_track: "bài tiếp theo",
    };
    const button = this.shadowRoot.querySelector(`[data-service="${service}"]`);
    button.disabled = true;
    try {
      await this._hass.callService("media_player", service, { entity_id: entityIds });
      this._setStatus(`Đã gửi lệnh ${labels[service]} tới ${entityIds.length} thiết bị.`);
    } catch (error) {
      this._setStatus(error?.message || "Không thể điều khiển thiết bị.", true);
    } finally {
      this._updateTransportState();
    }
  }

  async _stop() {
    const entityIds = this._targetsForService("media_stop");
    if (!this._selectedPlayers.size && !this._currentItem) {
      this._setStatus("Hãy chọn ít nhất một thiết bị để dừng.", true);
      return;
    }
    try {
      this._autoAdvance = false;
      const stopTargets = [...entityIds, this._config.entity];
      await this._hass.callService("media_player", "media_stop", { entity_id: stopTargets });
      this._clearRememberedNowPlaying();
      this._syncNowPlaying();
      this._setStatus(`Đã gửi lệnh dừng tới ${entityIds.length} thiết bị.`);
    } catch (error) {
      this._setStatus(error?.message || "Không thể dừng thiết bị.", true);
    }
  }

  _formatDuration(seconds) {
    const value = Number(seconds);
    if (!Number.isFinite(value) || value <= 0) return "";
    const minutes = Math.floor(value / 60);
    return `${minutes}:${String(Math.floor(value % 60)).padStart(2, "0")}`;
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
