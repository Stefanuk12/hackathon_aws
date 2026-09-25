import { api, MOCK } from "./api";
import type { GameEvent, Room } from "./types";

/**
 * Subscribe to /rooms/<code>. See contracts/events.md.
 *
 * TODO person 1/2: AppSync Events WebSocket (wss://<VITE_EVENTS_REALTIME_DOMAIN>/event/realtime,
 * subprotocols ["aws-appsync-event-ws", header-<base64url auth>]). Until then this polls
 * GET /rooms/{code} every second, which is also the fallback if the socket gives trouble.
 */
export function subscribe(
  code: string,
  onRoom: (room: Room) => void,
  _onEvent?: (event: GameEvent) => void,
): () => void {
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try {
      onRoom(await api.getRoom(code));
    } catch (err) {
      console.warn("poll failed", err);
    }
    if (!MOCK) setTimeout(tick, 1000);
  };
  tick();
  return () => {
    stopped = true;
  };
}
