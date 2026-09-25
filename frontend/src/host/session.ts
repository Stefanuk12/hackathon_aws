import { api } from "../api";

/**
 * Which room this host tab is running. Kept in sessionStorage so a refresh resumes the
 * game (the state itself lives in DynamoDB), while a brand-new tab starts fresh.
 */
const CODE_KEY = "host:code";

/** Reuse this tab's room across reloads; ?new forces a fresh one. */
export async function getOrCreateRoom() {
  const url = new URL(location.href);
  const forced = url.searchParams.has("new");
  const saved = forced ? null : sessionStorage.getItem(CODE_KEY);

  if (forced) {
    // Drop ?new from the address bar, or every later refresh would silently abandon
    // the game and strand everyone's phone on a dead room code.
    url.searchParams.delete("new");
    history.replaceState(null, "", url);
  }

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

/** Abandon this room and start a fresh one. Reloading re-reads the saved code. */
export async function startNewRoom() {
  const { code } = await api.createRoom();
  sessionStorage.setItem(CODE_KEY, code);
  location.reload();
}
