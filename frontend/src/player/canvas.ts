/** Drawing canvas. TODO person 1: brush sizes, colour palette, undo stack, clear. */
export function createCanvas(el: HTMLCanvasElement) {
  const ctx = el.getContext("2d")!;
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, el.width, el.height);
  ctx.lineCap = "round";
  ctx.lineWidth = 6;

  let drawing = false;
  const pos = (e: PointerEvent) => {
    const r = el.getBoundingClientRect();
    return [((e.clientX - r.left) * el.width) / r.width, ((e.clientY - r.top) * el.height) / r.height] as const;
  };
  el.style.touchAction = "none";
  el.addEventListener("pointerdown", (e) => {
    drawing = true;
    ctx.beginPath();
    ctx.moveTo(...pos(e));
  });
  el.addEventListener("pointermove", (e) => {
    if (!drawing) return;
    ctx.lineTo(...pos(e));
    ctx.stroke();
  });
  addEventListener("pointerup", () => (drawing = false));

  return { ctx };
}
