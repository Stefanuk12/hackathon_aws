import { aiHtml, aiLoop, aiSay, JUDGING_LINES, WAITING_LINES } from "../ai";
import type { ScreenFactory } from "../router";
import { isGameOver, type Room } from "../types";
import { $, avatarHtml, confetti, countdown, esc, logoHtml, pick, syncChips, toast } from "../ui";
import { createPad } from "./canvas";
import { submitDrawing } from "./upload";

export interface PlayerCtx {
  code: string;
  playerId: string;
  /** Rounds this phone has submitted, so we can move on before the next poll. */
  submitted: Set<number>;
  rerender(): void;
}

const me = (ctx: PlayerCtx, room: Room) => room.players.find((p) => p.playerId === ctx.playerId);

export const lobbyScreen =
  (ctx: PlayerCtx): ScreenFactory =>
  (el, room) => {
    el.innerHTML = `
    <main class="screen">
      ${logoHtml("logo-sm")}
      <section class="card stack center-text">
        ${avatarHtml(ctx.playerId, "lg")}
        <h2>You're in, ${esc(me(ctx, room)?.name ?? "")}!</h2>
        <p>Look at the big screen. The game starts soon.</p>
      </section>
      ${aiHtml()}
      <section class="stack">
        <h3 data-count></h3>
        <div class="chips" data-players></div>
      </section>
    </main>`;
    aiSay(el, pick(["I'm watching you.", "Stretch your drawing hand.", "I've heard you're terrible at drawing. Prove me wrong."]));
    const update = (room: Room) => {
      $(el, "[data-count]").textContent = `Players (${room.players.length})`;
      syncChips($(el, "[data-players]"), room.players);
    };
    update(room);
    return { update };
  };

export const drawingScreen =
  (ctx: PlayerCtx): ScreenFactory =>
  (el, room) => {
    el.innerHTML = `
    <main class="screen draw-screen">
      <header class="draw-head">
        <div class="prompt-card">
          <span class="prompt-label">Round ${room.round}/${room.totalRounds} · Draw this</span>
          <strong>${esc(room.prompt ?? "")}</strong>
        </div>
        <div class="timer" aria-label="Seconds left"></div>
      </header>
      <div class="pad"></div>
      <button class="btn btn-big btn-block btn-go">Done! Send it ✏️</button>
    </main>`;

    const { canvas } = createPad($(el, ".pad"));
    const button = $<HTMLButtonElement>(el, ".btn-go");
    let sending = false;

    const send = async () => {
      if (sending || ctx.submitted.has(room.round)) return;
      sending = true;
      button.disabled = true;
      button.textContent = "Sending…";
      try {
        await submitDrawing(canvas, ctx.code, ctx.playerId);
        ctx.submitted.add(room.round);
        ctx.rerender();
      } catch (err) {
        sending = false;
        button.disabled = false;
        button.textContent = "Try again";
        toast(err instanceof Error ? err.message : "Couldn't send your drawing");
      }
    };

    button.addEventListener("click", send);
    // Time's up: send whatever is on the canvas. The AI roasts blank canvases too.
    const stop = countdown($(el, ".timer"), room.endsAt ?? Date.now() + 60_000, send);
    return { unmount: stop };
  };

export const sentScreen =
  (ctx: PlayerCtx): ScreenFactory =>
  (el, room) => {
    el.innerHTML = `
    <main class="screen center">
      <section class="card stack center-text">
        <div class="big-emoji">📨</div>
        <h2>Sent!</h2>
        <p data-progress></p>
      </section>
      ${aiHtml()}
      <div class="chips" data-players></div>
    </main>`;
    aiLoop(el, WAITING_LINES, 3000);
    const update = (room: Room) => {
      const done = room.players.filter((p) => p.submitted || p.playerId === ctx.playerId).length;
      $(el, "[data-progress]").textContent = `${done} of ${room.players.length} drawings in`;
      syncChips($(el, "[data-players]"), room.players, (p) =>
        p.submitted || p.playerId === ctx.playerId ? "done" : "waiting",
      );
    };
    update(room);
    return { update };
  };

export const judgingScreen = (): ScreenFactory => (el) => {
  el.innerHTML = `
    <main class="screen center">
      ${aiHtml("ai-lg", "scanning")}
      <p class="tagline" style="text-align:center">👀 Look at the big screen!</p>
    </main>`;
  aiLoop(el, JUDGING_LINES);
  return {};
};

export const resultsScreen =
  (ctx: PlayerCtx): ScreenFactory =>
  (el, room) => {
    const results = room.results ?? [];
    const mine = results.find((r) => r.playerId === ctx.playerId);
    const total = me(ctx, room)?.score ?? 0;
    const final = isGameOver(room);
    const overall = [...room.players].sort((a, b) => b.score - a.score).findIndex((p) => p.playerId === ctx.playerId) + 1;
    const footer = final
      ? `<section class="card stack center-text final-card">
           <div class="prompt-label">Game over</div>
           <div class="result-rank">${overall === 1 ? "🏆 Champion!" : `#${overall} overall`}</div>
           <p>${total} pts across ${room.totalRounds} round${room.totalRounds === 1 ? "" : "s"}</p>
         </section>`
      : `<p class="muted" style="text-align:center">Round ${room.round} of ${room.totalRounds}. Waiting for the host…</p>`;

    el.innerHTML = mine
      ? `
    <main class="screen center player-result">
      <section class="card stack center-text">
        <div class="result-rank">#${mine.rank} <small>of ${results.length}</small></div>
        <figure class="frame">
          ${mine.imageUrl ? `<img src="${esc(mine.imageUrl)}" alt="Your drawing" />` : `<div class="blank">?</div>`}
        </figure>
        <span class="stamp ${mine.score >= 7 ? "good" : ""}">${mine.score}/10</span>
        <p>Total: <strong>${total} pts</strong></p>
      </section>
      ${aiHtml()}
      ${footer}
    </main>`
      : `
    <main class="screen center">
      <section class="card stack center-text">
        <div class="big-emoji">🙈</div>
        <h2>No drawing, no score</h2>
        <p>Total: <strong>${total} pts</strong></p>
      </section>
      ${aiHtml()}
      ${footer}
    </main>`;

    aiSay(el, mine?.roast ?? "You didn't submit anything. I noticed. I always notice.");
    if (mine?.rank === 1 || (final && overall === 1)) confetti();
    return {};
  };

export const goneScreen =
  (onRejoin: () => void): ScreenFactory =>
  (el) => {
    el.innerHTML = `
    <main class="screen center">
      <section class="card stack center-text">
        <div class="big-emoji">🤖</div>
        <h2>You're not in this game</h2>
        <button class="btn btn-big">Join again</button>
      </section>
    </main>`;
    $(el, "button").addEventListener("click", onRejoin);
    return {};
  };
