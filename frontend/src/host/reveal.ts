import type { Room } from "../types";

/** TODO person 2: reveal drawings one by one (last place → winner), play room.audioUrl. */
export function renderReveal(el: HTMLElement, room: Room) {
  const results = [...(room.results ?? [])].sort((a, b) => b.rank - a.rank);
  el.innerHTML = results
    .map(
      (r) => `
      <figure>
        <img src="${r.imageUrl}" width="256" height="256" alt="Drawing by ${r.name}" />
        <figcaption>#${r.rank} ${r.name} — ${r.score}/10<br /><em>${r.roast}</em></figcaption>
      </figure>`,
    )
    .join("");
}
