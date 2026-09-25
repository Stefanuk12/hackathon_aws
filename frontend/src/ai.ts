import { $, pick, sleep, typewrite } from "./ui";

export const LOBBY_LINES = [
  "Waiting for victims. I mean... players.",
  "Scan the code. I promise to judge fairly. Mostly.",
  "I have analysed every drawing ever made. Impress me.",
  "Join now. Resistance is futile.",
];

export const JUDGING_LINES = [
  "ANALYSING SCRIBBLES...",
  "Calculating how disappointed to be...",
  "Consulting 175 billion parameters of taste...",
  "Detecting crimes against art...",
  "Deciding who survives...",
  "Hmm. Hmm. HMMMM.",
];

export const WAITING_LINES = [
  "Submitted. No take-backs.",
  "I've already seen yours. Interesting choice.",
  "Waiting for the slow humans...",
  "Your drawing is safe with me. For now.",
];

const robotSvg = (cls = "") => `
<svg class="robot ${cls}" viewBox="0 0 120 120" aria-hidden="true">
  <line class="robot-antenna" x1="60" y1="10" x2="60" y2="26" />
  <circle class="robot-bulb" cx="60" cy="9" r="7" />
  <rect class="robot-head" x="12" y="26" width="96" height="80" rx="20" />
  <circle class="robot-socket" cx="60" cy="58" r="21" />
  <circle class="robot-eye" cx="60" cy="58" r="10" />
  <g class="robot-mouth">
    <rect x="34" y="86" width="8" height="10" rx="2" />
    <rect x="46" y="86" width="8" height="10" rx="2" />
    <rect x="58" y="86" width="8" height="10" rx="2" />
    <rect x="70" y="86" width="8" height="10" rx="2" />
    <rect x="82" y="86" width="8" height="10" rx="2" />
  </g>
</svg>`;

/** The robot narrator with an empty speech bubble. Fill it with aiSay(). */
export function aiHtml(cls = "", robotCls = "") {
  return `
  <div class="ai ${cls}">
    ${robotSvg(robotCls)}
    <div class="ai-bubble">
      <div class="ai-label">THE AI</div>
      <p class="ai-text" aria-live="polite"></p>
    </div>
  </div>`;
}

/** Make the AI type a line, with its mouth moving while it talks. */
export async function aiSay(root: ParentNode, text: string, charsPerSecond?: number) {
  const ai = root instanceof HTMLElement && root.classList.contains("ai") ? root : $(root, ".ai");
  ai.classList.add("speaking");
  await typewrite($(ai, ".ai-text"), text, charsPerSecond);
  ai.classList.remove("speaking");
}

/** Cycle through lines until the AI leaves the page. */
export async function aiLoop(root: ParentNode, lines: readonly string[], pauseMs = 2200) {
  const ai = $(root, ".ai");
  let last = "";
  while (ai.isConnected) {
    let line = pick(lines);
    if (line === last && lines.length > 1) line = pick(lines);
    last = line;
    await aiSay(ai, line);
    await sleep(pauseMs);
  }
}
