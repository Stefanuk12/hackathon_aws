import QRCode from "qrcode";
import { aiHtml, aiLoop, LOBBY_LINES } from "../ai";
import { api, MOCK } from "../api";
import {
  DEFAULT_MODE,
  DEFAULT_ROUNDS,
  DEFAULT_THEME_EVERY,
  ELIMINATION,
  joinUrl,
  MAX_ROUNDS,
  MODE_SETTINGS,
  settingInfo,
  TAGLINE,
  THEME_OPTIONS,
} from "../config";
import { mockAddBot } from "../mock";
import { startNewRoom } from "./session";
import type { ScreenFactory } from "../router";
import { throneScene } from "../scenes";
import type { ModeSetting, Room } from "../types";
import { $, bindStepper, chipState, esc, logoHtml, stepperHtml, syncChips, toast } from "../ui";

// Remember the host's choices across games in this tab.
const ROUNDS_KEY = "host:rounds";
const MODE_KEY = "host:mode";
const ELIM_KEY = "host:elimination";
const REVIVE_KEY = "host:reviveAfter";
const THEME_KEY = "host:themeEvery";

export const lobbyScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    const url = joinUrl(code);
    el.innerHTML = `
    <main class="host-screen host-lobby">
      ${throneScene()}
      <header class="host-head">
        ${logoHtml()}
        <p class="tagline">${esc(TAGLINE)}</p>
      </header>
      <section class="card join-card">
        <img alt="QR code to join the game" width="300" height="300" />
        <p class="join-url">${esc(url.replace(/^https?:\/\//, ""))}</p>
        <p class="lbl">Room code</p>
        <div class="room-code">${esc(code)}</div>
      </section>
      <section class="players-panel">
        <h2 data-count></h2>
        <p class="empty-hint">Scan the QR code with your phone to join.</p>
        <div class="chips" data-players></div>
      </section>
      <section class="card settings">
        <div class="settings-row">
          <span class="lbl">Game mode</span>
          <div class="mode-picker" role="radiogroup" aria-label="Game mode">
            ${MODE_SETTINGS.map((m) => {
              const info = settingInfo(m);
              return `<button type="button" class="mode-btn" role="radio" data-mode="${m}">
                <span class="mode-emoji" aria-hidden="true">${info.emoji}</span>${esc(info.name)}
              </button>`;
            }).join("")}
          </div>
        </div>
        <p class="mode-blurb" aria-live="polite"></p>
        <div class="settings-row">
          <span class="lbl">☁️ AWS themes</span>
          <div class="theme-picker mode-picker" role="radiogroup" aria-label="Themed rounds">
            ${THEME_OPTIONS.map((o) => `<button type="button" class="mode-btn" role="radio" data-theme-every="${o.every}">${esc(o.label)}</button>`).join("")}
          </div>
        </div>
        <div class="settings-row">
          <span class="lbl">Rounds</span>
          ${stepperHtml("rounds", "Number of rounds")}
          <span class="lbl elim-lbl">💀 Elimination</span>
          <button type="button" class="switch" role="switch" data-elim aria-label="Elimination"><span></span></button>
          <div class="revive-setting">
            <span class="muted-ink">Revive after</span>
            ${stepperHtml("revive", "Good rounds in a row to revive")}
            <span class="muted-ink" data-revive-unit></span>
          </div>
        </div>
        <p class="elim-rules" hidden>
          Lowest score each round dies. Ghosts keep playing for half points, and come back after
          scoring ${ELIMINATION.reviveScore}+ in enough rounds in a row.
        </p>
      </section>
      <footer class="host-foot">
        ${aiHtml("ai-lg")}
        <div class="row">
          ${MOCK ? `<button class="btn btn-ghost" data-bot>+ Add bot</button>` : ""}
          <button class="btn btn-ghost" data-new-room>New room ↻</button>
          <button class="btn btn-big" data-start>Start game ▶</button>
        </div>
      </footer>
    </main>`;

    QRCode.toDataURL(url, { margin: 1, width: 600, color: { dark: "#0d0a1a", light: "#fffdf6" } })
      .then((src) => ($<HTMLImageElement>(el, "img").src = src))
      .catch(() => toast("Couldn't draw the QR code"));
    aiLoop(el, LOBBY_LINES, 4000);

    // ---- Game mode ----
    const savedMode = sessionStorage.getItem(MODE_KEY) as ModeSetting | null;
    let mode: ModeSetting = savedMode && MODE_SETTINGS.includes(savedMode) ? savedMode : room.mode || DEFAULT_MODE;
    const setMode = (m: ModeSetting) => {
      mode = m;
      el.querySelectorAll<HTMLElement>("[data-mode]").forEach((b) => {
        const on = b.dataset.mode === m;
        b.classList.toggle("active", on);
        b.setAttribute("aria-checked", String(on));
      });
      $(el, ".mode-blurb").textContent = settingInfo(m).blurb;
      sessionStorage.setItem(MODE_KEY, m);
    };
    setMode(mode);
    $(el, ".mode-picker").addEventListener("click", (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-mode]");
      if (btn) setMode(btn.dataset.mode as ModeSetting);
    });

    // ---- AWS themes ----
    const savedTheme = sessionStorage.getItem(THEME_KEY);
    let themeEvery = savedTheme === null ? room.themeEvery ?? DEFAULT_THEME_EVERY : Number(savedTheme);
    const setThemeEvery = (n: number) => {
      themeEvery = n;
      el.querySelectorAll<HTMLElement>("[data-theme-every]").forEach((b) => {
        const on = Number(b.dataset.themeEvery) === n;
        b.classList.toggle("active", on);
        b.setAttribute("aria-checked", String(on));
      });
      sessionStorage.setItem(THEME_KEY, String(n));
    };
    setThemeEvery(themeEvery);
    $(el, ".theme-picker").addEventListener("click", (e) => {
      const btn = (e.target as HTMLElement).closest<HTMLElement>("[data-theme-every]");
      if (btn) setThemeEvery(Number(btn.dataset.themeEvery));
    });

    // ---- Rounds ----
    const rounds = bindStepper(el, "rounds", 1, MAX_ROUNDS,
      Number(sessionStorage.getItem(ROUNDS_KEY)) || room.totalRounds || DEFAULT_ROUNDS,
      (n) => sessionStorage.setItem(ROUNDS_KEY, String(n)));

    // ---- Elimination ----
    const savedElim = sessionStorage.getItem(ELIM_KEY);
    let elimination = savedElim === null ? room.elimination ?? ELIMINATION.defaultOn : savedElim === "true";
    const toggle = $<HTMLButtonElement>(el, "[data-elim]");
    const setElimination = (on: boolean) => {
      elimination = on;
      toggle.setAttribute("aria-checked", String(on));
      $(el, ".revive-setting").classList.toggle("off", !on);
      el.querySelectorAll<HTMLButtonElement>('[data-stepper="revive"] button').forEach((b) => (b.dataset.off = String(!on)));
      $(el, ".elim-rules").hidden = !on;
      sessionStorage.setItem(ELIM_KEY, String(on));
    };
    toggle.addEventListener("click", () => setElimination(!elimination));
    const reviveAfter = bindStepper(el, "revive", 1, ELIMINATION.maxReviveAfter,
      Number(sessionStorage.getItem(REVIVE_KEY)) || room.reviveAfter || ELIMINATION.defaultReviveAfter,
      (n) => {
        sessionStorage.setItem(REVIVE_KEY, String(n));
        $(el, "[data-revive-unit]").textContent = n === 1 ? "good round" : "good rounds in a row";
      });
    setElimination(elimination);

    const start = $<HTMLButtonElement>(el, "[data-start]");
    start.addEventListener("click", async () => {
      start.disabled = true;
      try {
        await api.startRound(code, { totalRounds: rounds(), mode, elimination, reviveAfter: reviveAfter(), themeEvery });
      } catch (err) {
        toast(err instanceof Error ? err.message : "Couldn't start the round");
        start.disabled = false;
      }
    });
    el.querySelector("[data-bot]")?.addEventListener("click", () => mockAddBot(code));

    // New room: a fresh code, so everyone has to rejoin. Anyone already in the lobby would be
    // stranded on a dead code, so that case asks twice rather than popping a browser dialog
    // up on the projector.
    const newRoom = $<HTMLButtonElement>(el, "[data-new-room]");
    let armed = false;
    let disarm: ReturnType<typeof setTimeout> | undefined;
    newRoom.addEventListener("click", async () => {
      const joined = latest.players.length;
      if (joined > 0 && !armed) {
        armed = true;
        newRoom.textContent = `Kick ${joined} player${joined === 1 ? "" : "s"}? Tap again`;
        newRoom.classList.add("btn-danger");
        disarm = setTimeout(() => {
          armed = false;
          newRoom.textContent = "New room ↻";
          newRoom.classList.remove("btn-danger");
        }, 5000);
        return;
      }
      clearTimeout(disarm);
      newRoom.disabled = true;
      newRoom.textContent = "Starting…";
      try {
        await startNewRoom();
      } catch (err) {
        toast(err instanceof Error ? err.message : "Couldn't start a new room");
        newRoom.disabled = false;
        newRoom.textContent = "New room ↻";
      }
    });

    let latest = room;
    const update = (room: Room) => {
      latest = room;
      $(el, "[data-count]").textContent = `Players (${room.players.length})`;
      $(el, ".empty-hint").hidden = room.players.length > 0;
      syncChips($(el, "[data-players]"), room.players, (p) => chipState(p, false));
      start.disabled = room.players.length === 0;
    };
    update(room);
    return { update };
  };
