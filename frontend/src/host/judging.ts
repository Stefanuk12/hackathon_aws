import { aiHtml, aiLoop, JUDGING_LINES } from "../ai";
import type { ScreenFactory } from "../router";
import { logoHtml } from "../ui";

export const judgingScreen = (): ScreenFactory => (el, room) => {
  const count = room.players.filter((p) => p.submitted).length;
  el.innerHTML = `
    <main class="host-screen host-judging">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <span class="pill">Judging ${count} drawing${count === 1 ? "" : "s"}</span>
      </header>
      <section class="judging-stage">
        ${aiHtml("ai-lg", "scanning")}
      </section>
    </main>`;
  aiLoop(el, JUDGING_LINES);
  return {};
};
