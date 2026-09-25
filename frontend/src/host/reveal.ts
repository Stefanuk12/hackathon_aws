import { aiHtml, aiSay } from "../ai";
import { api } from "../api";
import type { ScreenFactory } from "../router";
import type { Result, Room } from "../types";
import { $, avatarHtml, confetti, esc, logoHtml, sleep, toast } from "../ui";

const PAUSE_AFTER_ROAST_MS = 2200;

/** Reveal drawings from last place to the winner, then show the leaderboard. */
export const revealScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    el.innerHTML = `
    <main class="host-screen">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <div class="row">
          <span class="pill" data-step></span>
          <button class="btn btn-ghost" data-skip>Skip to scores ⏭</button>
        </div>
      </header>
      <section data-stage></section>
    </main>`;

    const stage = $(el, "[data-stage]");
    const step = $(el, "[data-step]");
    const skipButton = $<HTMLButtonElement>(el, "[data-skip]");
    let skipped = false;
    let latest = room;
    skipButton.addEventListener("click", () => {
      skipped = true;
      showBoard(latest);
    });

    const results = [...(room.results ?? [])].sort((a, b) => b.rank - a.rank);
    const audio = room.audioUrl ? new Audio(room.audioUrl) : undefined;
    audio?.play().catch(() => undefined);

    const showOne = async (r: Result, index: number) => {
      const winner = r.rank === 1;
      step.textContent = `Drawing ${index + 1} of ${results.length}`;
      stage.innerHTML = `
        <div class="reveal-grid">
          <figure class="frame">
            ${r.imageUrl ? `<img src="${esc(r.imageUrl)}" alt="Drawing by ${esc(r.name)}" />` : `<div class="blank">?</div>`}
            <figcaption>${avatarHtml(r.playerId, "sm")} ${esc(r.name)}</figcaption>
          </figure>
          <div class="stack">
            <div class="rank-row">
              <div class="rank-label">${winner ? "🏆 WINNER" : `#${r.rank}`}</div>
              <div data-stamp></div>
            </div>
            ${aiHtml("ai-lg")}
          </div>
        </div>`;
      await aiSay(stage, r.roast, 32);
      if (skipped) return;
      $(stage, "[data-stamp]").innerHTML = `<span class="stamp ${r.score >= 7 ? "good" : ""}">${r.score}/10</span>`;
      if (winner) confetti();
      await sleep(winner ? PAUSE_AFTER_ROAST_MS * 1.5 : PAUSE_AFTER_ROAST_MS);
    };

    const showBoard = (room: Room) => {
      skipButton.hidden = true;
      step.textContent = `After round ${room.round}`;
      const roundScore = new Map((room.results ?? []).map((r) => [r.playerId, r.score]));
      const players = [...room.players].sort((a, b) => b.score - a.score);
      const medal = ["🥇", "🥈", "🥉"];
      stage.innerHTML = `
        <div class="board-wrap">
          <h2 class="rank-label">Leaderboard</h2>
          <ol class="board">
            ${players
              .map(
                (p, i) => `
              <li style="animation-delay:${i * 80}ms">
                <span class="pos">${medal[i] ?? i + 1}</span>
                ${avatarHtml(p.playerId, "sm")}
                <span>${esc(p.name)}</span>
                <span class="delta">${roundScore.has(p.playerId) ? `+${roundScore.get(p.playerId)}` : "—"}</span>
                <span class="total">${p.score}</span>
              </li>`,
              )
              .join("")}
          </ol>
          <div class="row" style="justify-content:flex-end">
            <button class="btn btn-big" data-next>Next round ▶</button>
          </div>
        </div>`;
      const next = $<HTMLButtonElement>(stage, "[data-next]");
      next.addEventListener("click", async () => {
        next.disabled = true;
        try {
          await api.startRound(code);
        } catch (err) {
          toast(err instanceof Error ? err.message : "Couldn't start the round");
          next.disabled = false;
        }
      });
    };

    (async () => {
      if (!results.length) {
        stage.innerHTML = `<div class="judging-stage">${aiHtml("ai-lg")}</div>`;
        await aiSay(stage, "Nobody drew anything. Cowards. All of you.");
        await sleep(PAUSE_AFTER_ROAST_MS);
      }
      for (const [i, r] of results.entries()) {
        if (skipped || !el.isConnected) return;
        await showOne(r, i);
      }
      if (!skipped && el.isConnected) showBoard(latest);
    })();

    return {
      update(room) {
        latest = room;
      },
      unmount() {
        skipped = true;
        audio?.pause();
      },
    };
  };
