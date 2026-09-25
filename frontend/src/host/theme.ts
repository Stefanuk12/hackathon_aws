import { aiHtml, aiSay } from "../ai";
import { api } from "../api";
import { MODES } from "../config";
import type { ScreenFactory } from "../router";
import { $, countdown, esc, logoHtml, pick } from "../ui";

const INTROS = [
  "This round is brought to you by {service}. Pay attention. There may be a test.",
  "Before you play, a word from our sponsor: {service}.",
  "Today's theme is {service}. I run on this stuff, you know.",
];

/** Themed round intro: what the AWS service is, fun facts, and how Amacide uses it. Host can skip. */
export const themeScreen =
  (code: string): ScreenFactory =>
  (el, room) => {
    const theme = room.theme!;
    const mode = MODES[room.roundMode ?? "draw"];
    el.innerHTML = `
    <main class="host-screen host-theme">
      <header class="row spread">
        ${logoHtml("logo-sm")}
        <div class="row">
          <span class="pill mode-pill">Up next: ${mode.emoji} ${esc(mode.name)}</span>
          <span class="pill">Round ${room.round} of ${room.totalRounds}</span>
        </div>
      </header>
      ${aiHtml("ai-lg")}
      <section class="theme-card card">
        <div class="theme-title">
          <span class="theme-emoji" aria-hidden="true">${esc(theme.emoji)}</span>
          <div>
            <span class="prompt-label">Themed round</span>
            <h2>${esc(theme.service)}</h2>
            <p class="theme-tagline">${esc(theme.tagline)}</p>
          </div>
        </div>
        <p class="theme-what">${esc(theme.what)}</p>
        <div class="theme-facts">
          ${theme.facts.map((f) => `<div class="theme-fact"><span class="prompt-label">Did you know?</span>${esc(f)}</div>`).join("")}
        </div>
        <div class="theme-used"><span class="prompt-label">In Amacide</span>${esc(theme.inAmacide)}</div>
      </section>
      <footer class="row spread">
        <p class="theme-countdown">Round starts in <span class="timer" aria-label="Seconds until the round starts"></span></p>
        <button class="btn btn-big" data-skip>Skip ⏭</button>
      </footer>
    </main>`;

    aiSay(el, pick(INTROS).replace("{service}", theme.service));
    const begin = () => api.beginRound(code).catch(() => undefined);
    const skip = $<HTMLButtonElement>(el, "[data-skip]");
    skip.addEventListener("click", () => {
      skip.disabled = true;
      begin();
    });
    const stop = countdown($(el, ".timer"), room.themeEndsAt ?? Date.now() + 20_000, begin);
    return { unmount: stop };
  };
