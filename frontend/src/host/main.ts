import "../styles.css";
import { api } from "../api";
import { subscribe } from "../realtime";
import { renderLobby } from "./lobby";
import { renderReveal } from "./reveal";

// TODO person 2: drawing countdown (call api.endRound when it hits 0) and judging screens.
const app = document.querySelector<HTMLDivElement>("#app")!;

api.createRoom().then(({ code }) =>
  subscribe(code, (room) => {
    if (room.state === "results") renderReveal(app, room);
    else renderLobby(app, room);
  }),
);
