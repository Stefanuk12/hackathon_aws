import { GAME_NAME, GAME_NAME_ACCENT } from "./config";
import type { Player, Result } from "./types";

export const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export const pick = <T>(items: readonly T[]): T => items[Math.floor(Math.random() * items.length)];

const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escape user-provided text (names, prompts, roasts) before putting it in innerHTML. */
export const esc = (text: string) => text.replace(/[&<>"']/g, (c) => ESCAPES[c]);

export function $<T extends Element = HTMLElement>(root: ParentNode, selector: string): T {
  const found = root.querySelector<T>(selector);
  if (!found) throw new Error(`Missing element: ${selector}`);
  return found;
}

export function logoHtml(cls = "") {
  const accent = GAME_NAME.endsWith(GAME_NAME_ACCENT) ? GAME_NAME_ACCENT : "";
  const base = GAME_NAME.slice(0, GAME_NAME.length - accent.length);
  return `<h1 class="logo ${cls}" aria-label="${esc(GAME_NAME)}">${esc(base)}<span class="logo-ai">${esc(accent)}</span></h1>`;
}

/** Type text into an element. Stops early if the element leaves the page or is re-typed. */
export async function typewrite(target: HTMLElement, text: string, charsPerSecond = 40) {
  const token = String(Math.random());
  target.dataset.typing = token;
  target.classList.add("typing");
  for (let i = 1; i <= text.length; i++) {
    if (!target.isConnected || target.dataset.typing !== token) return;
    target.textContent = text.slice(0, i);
    await sleep(1000 / charsPerSecond);
  }
  target.classList.remove("typing");
}

/** Live countdown to `endsAt` (ms). Calls onEnd once at zero. Returns a stop function. */
export function countdown(target: HTMLElement, endsAt: number, onEnd?: () => void) {
  let fired = false;
  const tick = () => {
    const left = Math.max(0, Math.ceil((endsAt - Date.now()) / 1000));
    target.textContent = String(left);
    target.classList.toggle("danger", left <= 10);
    if (left === 0 && !fired) {
      fired = true;
      onEnd?.();
    }
  };
  tick();
  const id = setInterval(tick, 250);
  return () => clearInterval(id);
}

export function toast(message: string) {
  document.querySelector(".toast")?.remove();
  const el = document.createElement("div");
  el.className = "toast";
  el.setAttribute("role", "alert");
  el.textContent = message;
  document.body.append(el);
  setTimeout(() => el.remove(), 3500);
}

export function confetti(count = 50) {
  const bits = ["🎉", "⭐", "✨", "🖍️", "🏆", "💥"];
  for (let i = 0; i < count; i++) {
    const el = document.createElement("span");
    el.className = "confetti";
    el.textContent = pick(bits);
    el.style.left = `${Math.random() * 100}vw`;
    el.style.animationDuration = `${2 + Math.random() * 2.5}s`;
    el.style.animationDelay = `${Math.random() * 0.8}s`;
    document.body.append(el);
    setTimeout(() => el.remove(), 5500);
  }
}

// ---------- Avatars ----------

const EMOJI = ["🐸", "🦊", "🐙", "🦄", "🐼", "🐔", "🐢", "🦖", "👻", "🤡", "🐝", "🦀", "🍄", "🌵", "🐧", "🦉", "🐷", "👽"];
const COLOURS = ["#ff4f8b", "#ffd23f", "#3ee0cf", "#9dff5c", "#b388ff", "#ff8a3d", "#5ab0ff", "#ff6b6b"];

function hash(text: string) {
  let h = 7;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) | 0;
  return Math.abs(h);
}

/** Avatars are derived from playerId, so they need no backend support. */
export function avatarHtml(playerId: string, size: "sm" | "md" | "lg" = "md") {
  const h = hash(playerId);
  const cls = size === "md" ? "" : ` avatar-${size}`;
  return `<span class="avatar${cls}" style="--c:${COLOURS[(h >> 3) % COLOURS.length]}" aria-hidden="true">${EMOJI[h % EMOJI.length]}</span>`;
}

/**
 * Keep a grid of player chips in sync without re-creating existing ones
 * (so the pop-in animation only plays for new players).
 */
export function syncChips(container: HTMLElement, players: Player[], stateOf?: (p: Player) => string) {
  const ids = new Set(players.map((p) => p.playerId));
  for (const chip of [...container.children] as HTMLElement[]) {
    if (!ids.has(chip.dataset.id ?? "")) chip.remove();
  }
  for (const p of players) {
    let chip = container.querySelector<HTMLElement>(`[data-id="${CSS.escape(p.playerId)}"]`);
    if (!chip) {
      chip = document.createElement("div");
      chip.dataset.id = p.playerId;
      chip.innerHTML = `${avatarHtml(p.playerId)}<span class="chip-name">${esc(p.name)}</span>`;
      container.append(chip);
    }
    chip.className = `chip ${stateOf?.(p) ?? ""}`;
  }
}

// ---------- Submissions ----------

/** A player's entry: framed drawing (Draw) or quote card (Survive / Quick Wit). */
export function entryHtml(r: Result, caption = "") {
  const cap = caption ? `<figcaption>${caption}</figcaption>` : "";
  if (r.text !== undefined) {
    return `<figure class="frame answer-card">
      <blockquote>${r.text ? esc(r.text) : `<span class="muted-ink">…silence…</span>`}</blockquote>${cap}
    </figure>`;
  }
  const img = r.imageUrl
    ? `<img src="${esc(r.imageUrl)}" alt="Drawing by ${esc(r.name)}" />`
    : `<div class="blank">?</div>`;
  return `<figure class="frame">${img}${cap}</figure>`;
}

/** The stamp: the score out of 10, plus the halved points for ghosts. */
export function stampHtml(r: Result) {
  const ghost = r.ghost ? ` <small>→ +${r.points ?? 0} 👻</small>` : "";
  return `<span class="stamp ${r.score >= 7 ? "good" : ""}">${r.score}/10${ghost}</span>`;
}

// ---------- Stepper (− n +) ----------

export const stepperHtml = (name: string, label: string) => `
  <div class="stepper" role="group" aria-label="${esc(label)}" data-stepper="${name}">
    <button type="button" class="stepper-btn" data-dec aria-label="Less">−</button>
    <output class="stepper-value" aria-live="polite"></output>
    <button type="button" class="stepper-btn" data-inc aria-label="More">+</button>
  </div>`;

/** Wire up a stepperHtml() block. Returns a getter for the current value. */
export function bindStepper(root: ParentNode, name: string, min: number, max: number, initial: number, onChange: (n: number) => void) {
  const el = $(root, `[data-stepper="${name}"]`);
  const value = $(el, ".stepper-value");
  const dec = $<HTMLButtonElement>(el, "[data-dec]");
  const inc = $<HTMLButtonElement>(el, "[data-inc]");
  let current = initial;
  const set = (n: number) => {
    current = Math.min(max, Math.max(min, n));
    value.textContent = String(current);
    dec.disabled = current <= min;
    inc.disabled = current >= max;
    onChange(current);
  };
  set(initial);
  dec.addEventListener("click", () => set(current - 1));
  inc.addEventListener("click", () => set(current + 1));
  return () => current;
}

/** Chip classes for a player: submitted state + ghost when eliminated. */
export const chipState = (p: Player, submittedClass = true) =>
  [submittedClass ? (p.submitted ? "done" : "waiting") : "", p.alive === false ? "dead" : ""].join(" ");
