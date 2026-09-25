import { aiHtml, aiLoop, JUDGING_LINES } from "../ai";
import { MODES } from "../config";
import type { ScreenFactory } from "../router";
import { logoHtml } from "../ui";

export const judgingScreen = (): ScreenFactory => (el, room) => {
  const mode = room.roundMode ?? "draw";
  const count = room.players.filter((p) => p.submitted).length;
  const noun = count === 1 ? MODES[mode].noun.replace(/s$/, "") : MODES[mode].noun;
  el.innerHTML = `
    <main class="host-screen host-judging">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <span class="pill">Judging ${count} ${noun}</span>
      </header>
      <section class="judging-stage">
        ${aiHtml("ai-lg", "scanning")}
      </section>
    </main>`;
  aiLoop(el, JUDGING_LINES[mode]);
  return {};
};
