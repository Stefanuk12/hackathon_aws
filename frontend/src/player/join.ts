import { aiHtml, aiSay } from "../ai";
import { api } from "../api";
import { TAGLINE } from "../config";
import { $, esc, logoHtml } from "../ui";

const NAME_KEY = "player:name";

export function showJoin(el: HTMLElement, code: string, onJoined: (code: string, playerId: string) => void) {
  let savedName = "";
  try {
    savedName = localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    /* storage blocked: fine */
  }

  el.innerHTML = `
  <main class="screen center">
    <div>
      ${logoHtml()}
      <p class="tagline">${esc(TAGLINE)}</p>
    </div>
    <form class="card stack" novalidate>
      <div>
        <label class="lbl" for="code">Room code</label>
        <input id="code" class="field field-code" maxlength="4" autocomplete="off" autocapitalize="characters"
               spellcheck="false" value="${esc(code)}" required />
      </div>
      <div>
        <label class="lbl" for="name">Your name</label>
        <input id="name" class="field" maxlength="16" autocomplete="nickname" value="${esc(savedName)}" required />
      </div>
      <p class="error" hidden></p>
      <button class="btn btn-big btn-block">Join game</button>
    </form>
    ${aiHtml()}
  </main>`;

  const form = $<HTMLFormElement>(el, "form");
  const codeInput = $<HTMLInputElement>(el, "#code");
  const nameInput = $<HTMLInputElement>(el, "#name");
  const error = $(el, ".error");
  const button = $<HTMLButtonElement>(el, "button");

  (code ? nameInput : codeInput).focus();
  aiSay(el, "Tell me your name. I'll need it for the judging.");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const roomCode = codeInput.value.trim().toUpperCase();
    const name = nameInput.value.trim();
    error.hidden = true;
    if (roomCode.length !== 4 || !name) {
      error.textContent = roomCode.length !== 4 ? "Room codes are 4 letters." : "You need a name.";
      error.hidden = false;
      return;
    }
    button.disabled = true;
    button.textContent = "Joining…";
    try {
      const { playerId } = await api.joinRoom(roomCode, name);
      try {
        localStorage.setItem(NAME_KEY, name);
      } catch {
        /* ignore */
      }
      onJoined(roomCode, playerId);
    } catch (err) {
      error.textContent = err instanceof Error ? err.message : "Couldn't join that room.";
      error.hidden = false;
      button.disabled = false;
      button.textContent = "Join game";
    }
  });
}
