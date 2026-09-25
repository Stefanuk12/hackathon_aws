import { aiHtml, aiSay } from "../ai";
import { api } from "../api";
import { MODES } from "../config";
import type { ScreenFactory } from "../router";
import { isGameOver, type Result, type Room } from "../types";
import { $, avatarHtml, confetti, entryHtml, esc, logoHtml, sleep, stampHtml, toast } from "../ui";

const PAUSE_AFTER_ROAST_MS = 2200;

/** Reveal entries (drawings or answers) from last place to the winner, then show the leaderboard. */
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
    const mode = MODES[room.roundMode ?? "draw"];
    const noun = mode.noun.replace(/s$/, "");
    const audio = room.audioUrl ? new Audio(room.audioUrl) : undefined;
    audio?.play().catch(() => undefined);

    const showOne = async (r: Result, index: number) => {
      const winner = r.rank === 1;
      step.textContent = `${noun[0].toUpperCase()}${noun.slice(1)} ${index + 1} of ${results.length}`;
      stage.innerHTML = `
        <div class="reveal-grid">
          ${entryHtml(r, `${avatarHtml(r.playerId, "sm")} ${esc(r.name)}${r.ghost ? ` <span class="ghost-tag">👻 ghost · half points</span>` : ""}`)}
          <div class="stack">
            <div class="card prompt-recap"><span class="prompt-label">${esc(mode.instruction)}</span>${esc(room.prompt ?? "")}</div>
            <div class="rank-row">
              <div class="rank-label">${winner ? "🏆 WINNER" : `#${r.rank}`}</div>
              <div data-stamp></div>
            </div>
            ${aiHtml("ai-lg")}
          </div>
        </div>`;
      await aiSay(stage, r.roast, 32);
      if (skipped) return;
      $(stage, "[data-stamp]").innerHTML = stampHtml(r);
      if (winner) confetti();
      await sleep(winner ? PAUSE_AFTER_ROAST_MS * 1.5 : PAUSE_AFTER_ROAST_MS);
    };

    /** Elimination: announce who died and who came back before the leaderboard. */
    const showOutcome = async (room: Room) => {
      const out = room.outcome;
      if (!out || (!out.eliminated.length && !out.revived.length)) return;
      const nameOf = (id: string) => room.players.find((p) => p.playerId === id)?.name ?? "?";
      const card = (id: string, dead: boolean) => `
        <div class="outcome-card ${dead ? "outcome-dead" : "outcome-revived"}">
          ${avatarHtml(id, "lg")}
          <strong>${esc(nameOf(id))}</strong>
          <span>${dead ? "💀 ELIMINATED" : "🧟 BACK FROM THE DEAD"}</span>
        </div>`;
      step.textContent = "Elimination";
      stage.innerHTML = `
        <div class="outcome-stage">
          <div class="outcome-cards">
            ${out.eliminated.map((id) => card(id, true)).join("")}
            ${out.revived.map((id) => card(id, false)).join("")}
          </div>
          ${aiHtml("ai-lg")}
        </div>`;
      const died = out.eliminated.map(nameOf);
      const back = out.revived.map(nameOf);
      const lines = [
        died.length ? `${died.join(" and ")} scored lowest. ${died.length > 1 ? "They are" : "They're"} dead now. Half points from here on.` : "",
        back.length ? `${back.join(" and ")} clawed their way back. Welcome back to the living.` : "",
      ];
      await aiSay(stage, lines.filter(Boolean).join(" "), 34);
      await sleep(PAUSE_AFTER_ROAST_MS * 1.5);
    };

    const showBoard = (room: Room) => {
      const final = isGameOver(room);
      skipButton.hidden = true;
      step.textContent = final ? "Game over" : `After round ${room.round} of ${room.totalRounds}`;
      const roundPoints = new Map((room.results ?? []).map((r) => [r.playerId, r.points ?? r.score]));
      const eliminated = new Set(room.outcome?.eliminated);
      const revived = new Set(room.outcome?.revived);
      const status = (p: Room["players"][number]) => {
        if (eliminated.has(p.playerId)) return `<span class="status-tag dead-tag">💀 eliminated</span>`;
        if (revived.has(p.playerId)) return `<span class="status-tag revived-tag">🧟 revived</span>`;
        if (p.alive === false) return `<span class="status-tag dead-tag">👻 revive ${p.streak ?? 0}/${room.reviveAfter}</span>`;
        return "";
      };
      const players = [...room.players].sort((a, b) => b.score - a.score);
      const medal = ["🥇", "🥈", "🥉"];
      stage.innerHTML = `
        <div class="board-wrap">
          <h2 class="rank-label">${final ? "🏆 Final scores" : "Leaderboard"}</h2>
          ${final ? aiHtml("ai-lg") : ""}
          <ol class="board">
            ${players
              .map(
                (p, i) => `
              <li style="animation-delay:${i * 80}ms" class="${p.alive === false ? "dead" : ""}">
                <span class="pos">${medal[i] ?? i + 1}</span>
                ${avatarHtml(p.playerId, "sm")}
                <span>${esc(p.name)} ${status(p)}</span>
                <span class="delta">${roundPoints.has(p.playerId) ? `+${roundPoints.get(p.playerId)}` : "—"}</span>
                <span class="total">${p.score}</span>
              </li>`,
              )
              .join("")}
          </ol>
          <div class="row" style="justify-content:flex-end">
            ${
              final
                ? `<button class="btn btn-big" data-next>Play again ↺</button>`
                : `<button class="btn btn-big" data-next>Next round (${room.round + 1} of ${room.totalRounds}) ▶</button>`
            }
          </div>
        </div>`;
      if (final && players.length) {
        confetti(80);
        aiSay(stage, `${players[0].name} is the champion. The rest of you... I have notes.`);
      }
      const next = $<HTMLButtonElement>(stage, "[data-next]");
      next.addEventListener("click", async () => {
        next.disabled = true;
        try {
          await (final ? api.resetRoom(code) : api.startRound(code));
        } catch (err) {
          toast(err instanceof Error ? err.message : "Something went wrong");
          next.disabled = false;
        }
      });
    };

    (async () => {
      if (!results.length) {
        stage.innerHTML = `<div class="judging-stage">${aiHtml("ai-lg")}</div>`;
        await aiSay(stage, `No ${mode.noun}. Nothing. Cowards, all of you.`);
        await sleep(PAUSE_AFTER_ROAST_MS);
      }
      for (const [i, r] of results.entries()) {
        if (skipped || !el.isConnected) return;
        await showOne(r, i);
      }
      if (!skipped && el.isConnected) await showOutcome(latest);
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
