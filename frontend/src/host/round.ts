import { aiHtml, aiSay, ROUND_INTRO_LINES } from "../ai";
import { api } from "../api";
import { MODES } from "../config";
import type { ScreenFactory } from "../router";
import type { Room } from "../types";
import { $, countdown, esc, logoHtml, pick, syncChips } from "../ui";

// Phones auto-submit at 0; give their uploads a moment to land before ending the round.
const END_GRACE_MS = 2500;

/** A round in progress on the big screen: prompt, countdown, who has submitted. */
export const roundScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    const mode = MODES[room.roundMode ?? "draw"];
    el.innerHTML = `
    <main class="host-screen host-round">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <div class="row">
          <span class="pill mode-pill">${mode.emoji} ${esc(mode.name)}</span>
          <span class="pill">Round ${room.round} of ${room.totalRounds}</span>
        </div>
      </header>
      ${aiHtml("ai-lg")}
      <div class="card prompt-huge">
        <span class="prompt-label">${esc(mode.instruction)}</span>
        ${esc(room.prompt ?? "")}
      </div>
      <div class="timer timer-huge" aria-label="Seconds left"></div>
      <section class="stack">
        <p class="progress" data-progress></p>
        <div class="chips" data-players></div>
      </section>
      <footer class="row spread">
        <span class="muted">${room.roundMode === "draw" ? "Draw" : "Type your answer"} on your phone!</span>
        <button class="btn btn-ghost" data-end>End round now</button>
      </footer>
    </main>`;

    aiSay(el, pick(ROUND_INTRO_LINES[room.roundMode ?? "draw"]));

    let endTimer: ReturnType<typeof setTimeout> | undefined;
    const end = () => api.endRound(code).catch(() => undefined);
    const stop = countdown($(el, ".timer"), room.endsAt ?? Date.now() + 60_000, () => {
      endTimer = setTimeout(end, END_GRACE_MS);
    });
    $(el, "[data-end]").addEventListener("click", end);

    const update = (room: Room) => {
      const done = room.players.filter((p) => p.submitted).length;
      $(el, "[data-progress]").textContent = `${done} / ${room.players.length} ${mode.noun} in`;
      syncChips($(el, "[data-players]"), room.players, (p) => (p.submitted ? "done" : "waiting"));
    };
    update(room);
    return {
      update,
      unmount() {
        stop();
        clearTimeout(endTimer);
      },
    };
  };
