const COLOURS = [
  "#0d0a1a", "#ffffff", "#8b5a2b", "#ff3b3b", "#ff8a3d", "#ffd23f",
  "#9dff5c", "#2ecc71", "#3ee0cf", "#5ab0ff", "#7b5cff", "#ff4f8b",
];
// Canvas is 1024px internally, shown at ~350px on a phone, so widths are ~3x what they look like.
const SIZES = [
  { width: 10, dot: 6 },
  { width: 26, dot: 12 },
  { width: 64, dot: 22 },
];
const UNDO_LIMIT = 25;

/** Drawing pad: canvas + colour palette + brush sizes, eraser, undo, clear. */
export function createPad(root: HTMLElement) {
  root.innerHTML = `
    <canvas width="1024" height="1024" aria-label="Drawing canvas"></canvas>
    <div class="palette" role="group" aria-label="Colours">
      ${COLOURS.map((c, i) => `<button type="button" class="swatch${i === 0 ? " active" : ""}" style="--c:${c}" data-colour="${c}" aria-label="Colour ${c}"></button>`).join("")}
    </div>
    <div class="tools" role="group" aria-label="Tools">
      ${SIZES.map((s, i) => `<button type="button" class="tool${i === 1 ? " active" : ""}" data-size="${s.width}" aria-label="Brush size ${i + 1}"><span class="dot" style="width:${s.dot}px;height:${s.dot}px"></span></button>`).join("")}
      <button type="button" class="tool" data-eraser aria-label="Eraser">🧽</button>
      <button type="button" class="tool" data-undo aria-label="Undo">↩️</button>
      <button type="button" class="tool" data-clear aria-label="Clear">🗑️</button>
    </div>`;

  const canvas = root.querySelector("canvas")!;
  const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
  let colour = COLOURS[0];
  let width = SIZES[1].width;
  let erasing = false;
  let last: { x: number; y: number } | null = null;
  const history: ImageData[] = [];

  const fillWhite = () => {
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  };
  const snapshot = () => {
    history.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    if (history.length > UNDO_LIMIT) history.shift();
  };
  const pos = (e: PointerEvent) => {
    const r = canvas.getBoundingClientRect();
    return { x: ((e.clientX - r.left) * canvas.width) / r.width, y: ((e.clientY - r.top) * canvas.height) / r.height };
  };
  const line = (from: { x: number; y: number }, to: { x: number; y: number }) => {
    ctx.strokeStyle = erasing ? "#fff" : colour;
    ctx.lineWidth = erasing ? width * 2 : width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.beginPath();
    ctx.moveTo(from.x, from.y);
    ctx.lineTo(to.x, to.y);
    ctx.stroke();
  };

  fillWhite();

  canvas.addEventListener("pointerdown", (e) => {
    if (!e.isPrimary || e.button !== 0) return;
    canvas.setPointerCapture(e.pointerId);
    snapshot();
    last = pos(e);
    line(last, last); // a tap draws a dot
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!last || !e.isPrimary) return;
    const events = e.getCoalescedEvents?.() ?? [];
    for (const ev of events.length ? events : [e]) {
      const p = pos(ev);
      line(last, p);
      last = p;
    }
  });
  const stop = () => (last = null);
  canvas.addEventListener("pointerup", stop);
  canvas.addEventListener("pointercancel", stop);

  const select = (btn: HTMLElement, group: string) => {
    root.querySelectorAll(group).forEach((b) => b.classList.toggle("active", b === btn));
  };

  root.addEventListener("click", (e) => {
    const btn = (e.target as HTMLElement).closest<HTMLElement>("button");
    if (!btn) return;
    if (btn.dataset.colour) {
      colour = btn.dataset.colour;
      erasing = false;
      root.querySelector("[data-eraser]")!.classList.remove("active");
      select(btn, ".swatch");
    } else if (btn.dataset.size) {
      width = Number(btn.dataset.size);
      select(btn, "[data-size]");
    } else if (btn.hasAttribute("data-eraser")) {
      erasing = !erasing;
      btn.classList.toggle("active", erasing);
    } else if (btn.hasAttribute("data-undo")) {
      const prev = history.pop();
      if (prev) ctx.putImageData(prev, 0, 0);
    } else if (btn.hasAttribute("data-clear")) {
      snapshot();
      fillWhite();
    }
  });

  return { canvas };
}
