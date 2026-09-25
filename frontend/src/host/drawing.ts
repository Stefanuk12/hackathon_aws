import { aiHtml, aiSay } from "../ai";
import { api } from "../api";
import type { ScreenFactory } from "../router";
import type { Room } from "../types";
import { $, countdown, esc, logoHtml, pick, syncChips } from "../ui";

// Phones auto-submit at 0; give their uploads a moment to land before ending the round.
const END_GRACE_MS = 2500;

export const drawingScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    el.innerHTML = `
    <main class="host-screen host-drawing">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <span class="pill">Round ${room.round} of ${room.totalRounds}</span>
      </header>
      ${aiHtml("ai-lg")}
      <div class="card prompt-huge">${esc(room.prompt ?? "")}</div>
      <div class="timer timer-huge" aria-label="Seconds left"></div>
      <section class="stack">
        <p class="progress" data-progress></p>
        <div class="chips" data-players></div>
      </section>
      <footer class="row spread">
        <span class="muted">Draw on your phone!</span>
        <button class="btn btn-ghost" data-end>End round now</button>
      </footer>
    </main>`;

    aiSay(el, pick(["Your prompt. Draw it. I'll be watching.", "Here is your task, humans.", "Draw this. Try not to embarrass yourselves."]));

    let endTimer: ReturnType<typeof setTimeout> | undefined;
    const end = () => api.endRound(code).catch(() => undefined);
    const stop = countdown($(el, ".timer"), room.endsAt ?? Date.now() + 60_000, () => {
      endTimer = setTimeout(end, END_GRACE_MS);
    });
    $(el, "[data-end]").addEventListener("click", end);

    const update = (room: Room) => {
      const done = room.players.filter((p) => p.submitted).length;
      $(el, "[data-progress]").textContent = `${done} / ${room.players.length} drawings in`;
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
