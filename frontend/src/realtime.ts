import { api, MOCK } from "./api";
import type { Room } from "./types";

/**
 * Keep a room in sync. Polls GET /rooms/{code} every second, which is also
 * the documented fallback in contracts/events.md.
 *
 * TODO person 1/2: switch to AppSync Events (wss://<VITE_EVENTS_REALTIME_DOMAIN>/event/realtime)
 * and keep this poll as the fallback. The screens only need onRoom(), so nothing else changes.
 */
export function subscribe(code: string, onRoom: (room: Room) => void, onError?: (err: unknown) => void) {
  let stopped = false;
  let timer: ReturnType<typeof setTimeout> | undefined;

  const refresh = async () => {
    clearTimeout(timer);
    if (stopped) return;
    try {
      onRoom(await api.getRoom(code));
    } catch (err) {
      onError?.(err);
    }
    if (!stopped) timer = setTimeout(refresh, 1000);
  };

  // Mock mode: other tabs write localStorage, so refresh the moment they do.
  const onStorage = (e: StorageEvent) => {
    if (MOCK && e.key === `mock:room:${code}`) refresh();
  };
  addEventListener("storage", onStorage);
  refresh();

  return () => {
    stopped = true;
    clearTimeout(timer);
    removeEventListener("storage", onStorage);
  };
}
