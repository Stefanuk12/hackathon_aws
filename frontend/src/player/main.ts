import "../styles.css";
import { createCanvas } from "./canvas";
import { submitDrawing } from "./upload";

// TODO person 1: screens for join (code from ?room= in QR link, name) → wait → draw → submitted → results.
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <canvas id="c" width="1024" height="1024" style="width:100vw;max-width:512px;aspect-ratio:1"></canvas>
  <button id="send">Submit</button>
`;
const canvas = app.querySelector<HTMLCanvasElement>("#c")!;
createCanvas(canvas);
app.querySelector("#send")!.addEventListener("click", () => submitDrawing(canvas, "WXYZ", "p_1a2b3c"));
