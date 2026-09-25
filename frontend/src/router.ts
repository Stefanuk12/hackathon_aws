import type { Room } from "./types";

export interface Screen {
  update?(room: Room): void;
  unmount?(): void;
}

export type ScreenFactory = (el: HTMLElement, room: Room) => Screen;

/**
 * Re-mounts a screen only when its key changes (e.g. "draw:2" -> "sent:2").
 * Otherwise the current screen just gets update(room), so the canvas and animations survive polling.
 */
export function createRouter(el: HTMLElement, choose: (room: Room) => [key: string, factory: ScreenFactory]) {
  let key: string | undefined;
  let screen: Screen | undefined;
  return (room: Room) => {
    const [nextKey, factory] = choose(room);
    if (nextKey === key) {
      screen?.update?.(room);
      return;
    }
    screen?.unmount?.();
    key = nextKey;
    el.innerHTML = "";
    window.scrollTo(0, 0);
    screen = factory(el, room);
  };
}
