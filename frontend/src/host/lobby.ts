import QRCode from "qrcode";
import { aiHtml, aiLoop, LOBBY_LINES } from "../ai";
import { api, MOCK } from "../api";
import { DEFAULT_ROUNDS, joinUrl, MAX_ROUNDS, TAGLINE } from "../config";
import { mockAddBot } from "../mock";
import type { ScreenFactory } from "../router";
import type { Room } from "../types";
import { $, esc, logoHtml, syncChips, toast } from "../ui";

const ROUNDS_KEY = "host:rounds";

export const lobbyScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    const url = joinUrl(code);
    el.innerHTML = `
    <main class="host-screen host-lobby">
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
      <footer class="host-foot">
        ${aiHtml("ai-lg")}
        <div class="row">
          ${MOCK ? `<button class="btn btn-ghost" data-bot>+ Add bot</button>` : ""}
          <div class="stepper" role="group" aria-label="Number of rounds">
            <span class="stepper-label">Rounds</span>
            <button type="button" class="stepper-btn" data-dec aria-label="Fewer rounds">−</button>
            <output class="stepper-value" aria-live="polite"></output>
            <button type="button" class="stepper-btn" data-inc aria-label="More rounds">+</button>
          </div>
          <button class="btn btn-big" data-start>Start game ▶</button>
        </div>
      </footer>
    </main>`;

    QRCode.toDataURL(url, { margin: 1, width: 600, color: { dark: "#0d0a1a", light: "#fffdf6" } })
      .then((src) => ($<HTMLImageElement>(el, "img").src = src))
      .catch(() => toast("Couldn't draw the QR code"));
    aiLoop(el, LOBBY_LINES, 4000);

    // Remember the host's choice across games in this tab.
    let rounds = Number(sessionStorage.getItem(ROUNDS_KEY)) || room.totalRounds || DEFAULT_ROUNDS;
    const value = $(el, ".stepper-value");
    const dec = $<HTMLButtonElement>(el, "[data-dec]");
    const inc = $<HTMLButtonElement>(el, "[data-inc]");
    const setRounds = (n: number) => {
      rounds = Math.min(MAX_ROUNDS, Math.max(1, n));
      value.textContent = String(rounds);
      dec.disabled = rounds <= 1;
      inc.disabled = rounds >= MAX_ROUNDS;
      sessionStorage.setItem(ROUNDS_KEY, String(rounds));
    };
    setRounds(rounds);
    dec.addEventListener("click", () => setRounds(rounds - 1));
    inc.addEventListener("click", () => setRounds(rounds + 1));

    const start = $<HTMLButtonElement>(el, "[data-start]");
    start.addEventListener("click", async () => {
      start.disabled = true;
      try {
        await api.startRound(code, rounds);
      } catch (err) {
        toast(err instanceof Error ? err.message : "Couldn't start the round");
        start.disabled = false;
      }
    });
    el.querySelector("[data-bot]")?.addEventListener("click", () => mockAddBot(code));

    const update = (room: Room) => {
      $(el, "[data-count]").textContent = `Players (${room.players.length})`;
      $(el, ".empty-hint").hidden = room.players.length > 0;
      syncChips($(el, "[data-players]"), room.players);
      start.disabled = room.players.length === 0;
    };
    update(room);
    return { update };
  };
