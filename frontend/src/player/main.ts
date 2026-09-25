import "../theme";
import { subscribe } from "../realtime";
import { createRouter, type ScreenFactory } from "../router";
import type { Room } from "../types";
import { toast } from "../ui";
import { showJoin } from "./join";
import {
  drawingScreen,
  goneScreen,
  judgingScreen,
  lobbyScreen,
  type PlayerCtx,
  resultsScreen,
  sentScreen,
} from "./screens";

const app = document.querySelector<HTMLDivElement>("#app")!;
const sessionKey = (code: string) => `player:${code}`;

function join(code: string) {
  showJoin(app, code, (roomCode, playerId) => {
    sessionStorage.setItem(sessionKey(roomCode), playerId);
    history.replaceState(null, "", `?room=${roomCode}`);
    play(roomCode, playerId);
  });
}

function play(code: string, playerId: string) {
  let last: Room | undefined;
  const ctx: PlayerCtx = { code, playerId, submitted: new Set(), rerender: () => last && route(last) };

  const rejoin = () => {
    stop();
    sessionStorage.removeItem(sessionKey(code));
    join(code);
  };

  const route = createRouter(app, (room): [string, ScreenFactory] => {
    const player = room.players.find((p) => p.playerId === playerId);
    if (!player) return ["gone", goneScreen(rejoin)];
    switch (room.state) {
      case "lobby":
        ctx.submitted.clear(); // "Play again" restarts round numbers at 1
        return ["lobby", lobbyScreen(ctx)];
      case "drawing":
        return player.submitted || ctx.submitted.has(room.round)
          ? [`sent:${room.round}`, sentScreen(ctx)]
          : [`draw:${room.round}`, drawingScreen(ctx)];
      case "judging":
        return [`judging:${room.round}`, judgingScreen()];
      case "results":
        return [`results:${room.round}`, resultsScreen(ctx)];
    }
  });

  let failures = 0;
  const stop = subscribe(
    code,
    (room) => {
      failures = 0;
      last = room;
      route(room);
    },
    () => {
      if (++failures === 3) toast("Can't reach the game. Retrying…");
    },
  );
}

const code = (new URLSearchParams(location.search).get("room") ?? "").toUpperCase();
const playerId = code ? sessionStorage.getItem(sessionKey(code)) : null;
if (code && playerId) play(code, playerId);
else join(code);
