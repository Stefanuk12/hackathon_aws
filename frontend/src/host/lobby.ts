import type { Room } from "../types";

/** TODO person 2: big QR code for `${location.origin}/?room=${room.code}`, room code, joined players, Start button. */
export function renderLobby(el: HTMLElement, room: Room) {
  el.innerHTML = `
    <h1>Join: ${room.code}</h1>
    <ul>${room.players.map((p) => `<li>${p.name}</li>`).join("")}</ul>
  `;
}
