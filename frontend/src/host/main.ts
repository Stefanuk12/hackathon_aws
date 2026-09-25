import "../theme";
import { api } from "../api";
import { subscribe } from "../realtime";
import { createRouter, type ScreenFactory } from "../router";
import { toast } from "../ui";
import { roundScreen } from "./round";
import { themeScreen } from "./theme";
import { judgingScreen } from "./judging";
import { lobbyScreen } from "./lobby";
import { revealScreen } from "./reveal";

const app = document.querySelector<HTMLDivElement>("#app")!;
const CODE_KEY = "host:code";

/** Reuse this tab's room across reloads; ?new forces a fresh room. */
async function getOrCreateRoom() {
  const saved = new URLSearchParams(location.search).has("new") ? null : sessionStorage.getItem(CODE_KEY);
  if (saved) {
    try {
      await api.getRoom(saved);
      return saved;
    } catch {
      /* room is gone: make a new one */
    }
  }
  const { code } = await api.createRoom();
  sessionStorage.setItem(CODE_KEY, code);
  return code;
}

async function main() {
  const code = await getOrCreateRoom();
  const route = createRouter(app, (room): [string, ScreenFactory] => {
    switch (room.state) {
      case "lobby":
        return ["lobby", lobbyScreen(code)];
      case "theme":
        return [`theme:${room.round}`, themeScreen(code)];
      case "drawing":
        return [`round:${room.round}`, roundScreen(code)];
      case "judging":
        return [`judging:${room.round}`, judgingScreen()];
      case "results":
        return [`results:${room.round}`, revealScreen(code)];
    }
  });
  let failures = 0;
  subscribe(
    code,
    (room) => {
      failures = 0;
      route(room);
    },
    () => {
      if (++failures === 3) toast("Lost connection to the game. Retrying…");
    },
  );
}

main().catch((err) => {
  app.innerHTML = `<main class="screen center"><p class="error">Couldn't create a room. Is the API up?</p></main>`;
  console.error(err);
});
