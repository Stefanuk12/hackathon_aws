/**
 * Animated background scenes for the host screen (inline SVG + CSS animations in styles.css).
 * Same visual language as the narrator robot in ai.ts: purple head, one red eye, cyan mouth, ink outlines.
 */

const INK = "#0d0a1a";

/** Lobby: the AI lounging on its throne, crowned, sceptre in hand. */
export const throneScene = () => `
<div class="scene scene-throne" aria-hidden="true">
  <svg viewBox="0 0 400 520">
    <ellipse cx="200" cy="506" rx="175" ry="12" fill="rgba(0,0,0,0.35)" />

    <!-- throne -->
    <path class="throne-back" d="M80 470 V170 L110 120 L140 170 L170 95 L200 40 L230 95 L260 170 L290 120 L320 170 V470 Z"
          fill="#5a1446" stroke="#ffd23f" stroke-width="10" stroke-linejoin="round" />
    <path d="M80 470 V170 L110 120 L140 170 L170 95 L200 40 L230 95 L260 170 L290 120 L320 170 V470 Z"
          fill="none" stroke="${INK}" stroke-width="4" stroke-linejoin="round" />
    <rect x="120" y="180" width="160" height="250" rx="30" fill="#7a1d5c" stroke="${INK}" stroke-width="4" />
    <g fill="#ffd23f" stroke="${INK}" stroke-width="2">
      <circle cx="150" cy="215" r="4" /><circle cx="200" cy="215" r="4" /><circle cx="250" cy="215" r="4" />
      <circle cx="175" cy="245" r="4" /><circle cx="225" cy="245" r="4" />
    </g>
    <g class="gem"><circle cx="110" cy="124" r="10" fill="#3ee0cf" stroke="${INK}" stroke-width="3" /></g>
    <g class="gem" style="animation-delay:.6s"><circle cx="200" cy="46" r="12" fill="#ff3864" stroke="${INK}" stroke-width="3" /></g>
    <g class="gem" style="animation-delay:1.2s"><circle cx="290" cy="124" r="10" fill="#3ee0cf" stroke="${INK}" stroke-width="3" /></g>
    <rect x="48" y="350" width="44" height="90" fill="#5a1446" stroke="${INK}" stroke-width="4" />
    <rect x="308" y="350" width="44" height="90" fill="#5a1446" stroke="${INK}" stroke-width="4" />
    <rect x="60" y="380" width="280" height="50" rx="14" fill="#7a1d5c" stroke="${INK}" stroke-width="4" />
    <rect x="70" y="425" width="260" height="45" rx="6" fill="#ffd23f" stroke="${INK}" stroke-width="4" />
    <rect x="80" y="466" width="26" height="36" rx="4" fill="#ffd23f" stroke="${INK}" stroke-width="4" />
    <rect x="294" y="466" width="26" height="36" rx="4" fill="#ffd23f" stroke="${INK}" stroke-width="4" />

    <!-- the AI, seated -->
    <g class="sit-robot">
      <path class="cape" d="M142 252 Q120 340 104 420 L296 420 Q280 340 258 252 Z" fill="#c21d4a" stroke="${INK}" stroke-width="4" stroke-linejoin="round" />
      <rect x="150" y="388" width="36" height="84" rx="10" fill="#2c2150" stroke="${INK}" stroke-width="4" />
      <rect x="214" y="388" width="36" height="84" rx="10" fill="#2c2150" stroke="${INK}" stroke-width="4" />
      <rect x="138" y="466" width="54" height="22" rx="10" fill="#3a2a6b" stroke="${INK}" stroke-width="4" />
      <rect x="208" y="466" width="54" height="22" rx="10" fill="#3a2a6b" stroke="${INK}" stroke-width="4" />
      <rect x="135" y="250" width="130" height="145" rx="28" fill="#3a2a6b" stroke="${INK}" stroke-width="5" />
      <rect x="165" y="285" width="70" height="46" rx="10" fill="#0b0718" stroke="${INK}" stroke-width="3" />
      <circle class="chest-light" cx="182" cy="308" r="6" fill="#3ee0cf" />
      <circle class="chest-light" cx="200" cy="308" r="6" fill="#ffd23f" style="animation-delay:.4s" />
      <circle class="chest-light" cx="218" cy="308" r="6" fill="#ff3864" style="animation-delay:.8s" />
      <!-- resting arm -->
      <rect x="100" y="262" width="36" height="84" rx="17" fill="#3a2a6b" stroke="${INK}" stroke-width="4" transform="rotate(22 118 262)" />
      <circle cx="90" cy="340" r="17" fill="#3a2a6b" stroke="${INK}" stroke-width="4" />
      <!-- sceptre arm -->
      <line x1="322" y1="238" x2="300" y2="446" stroke="#ffd23f" stroke-width="11" stroke-linecap="round" />
      <line x1="322" y1="238" x2="300" y2="446" stroke="${INK}" stroke-width="3" stroke-linecap="round" opacity=".5" />
      <circle class="orb" cx="323" cy="224" r="19" fill="#3ee0cf" stroke="${INK}" stroke-width="4" />
      <rect x="264" y="262" width="36" height="84" rx="17" fill="#3a2a6b" stroke="${INK}" stroke-width="4" transform="rotate(-22 282 262)" />
      <circle cx="310" cy="338" r="17" fill="#3a2a6b" stroke="${INK}" stroke-width="4" />
      <!-- head -->
      <rect x="182" y="236" width="36" height="20" fill="#2c2150" stroke="${INK}" stroke-width="4" />
      <rect x="130" y="128" width="140" height="115" rx="30" fill="#2c2150" stroke="${INK}" stroke-width="5" />
      <circle cx="200" cy="178" r="30" fill="${INK}" />
      <circle class="robot-eye" cx="200" cy="178" r="14" />
      <g fill="#3ee0cf">
        <rect x="163" y="214" width="10" height="12" rx="2" /><rect x="179" y="214" width="10" height="12" rx="2" />
        <rect x="195" y="214" width="10" height="12" rx="2" /><rect x="211" y="214" width="10" height="12" rx="2" />
        <rect x="227" y="214" width="10" height="12" rx="2" />
      </g>
      <g class="crown">
        <path d="M148 132 L148 92 L172 114 L200 78 L228 114 L252 92 L252 132 Z" fill="#ffd23f" stroke="${INK}" stroke-width="4" stroke-linejoin="round" />
        <circle cx="200" cy="112" r="6" fill="#ff3864" stroke="${INK}" stroke-width="2" />
        <circle cx="170" cy="122" r="4" fill="#3ee0cf" /><circle cx="230" cy="122" r="4" fill="#3ee0cf" />
      </g>
    </g>

    <g class="sparkles" fill="#ffd23f">
      <path class="sparkle" d="M40 200 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4Z" />
      <path class="sparkle" style="animation-delay:1.1s" d="M360 90 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3Z" />
      <path class="sparkle" style="animation-delay:2.2s" d="M60 60 l3 8 8 3 -8 3 -3 8 -3 -8 -8 -3 8 -3Z" />
      <path class="sparkle" style="animation-delay:.5s" d="M370 300 l4 10 10 4 -10 4 -4 10 -4 -10 -10 -4 10 -4Z" />
    </g>
  </svg>
</div>`;

/** Question screen: the AI scheming, hand on chin, one suspicious half-lidded eye and a smirk. */
export const thinkerScene = () => `
<div class="scene scene-thinker" aria-hidden="true">
  <svg viewBox="0 0 420 520">
    <defs>
      <clipPath id="socket-clip"><circle cx="210" cy="205" r="42" /></clipPath>
    </defs>

    <!-- thought bubbles -->
    <g class="thought">
      <circle class="bubble b1" cx="318" cy="132" r="8" fill="#fffdf6" stroke="${INK}" stroke-width="3" />
      <circle class="bubble b2" cx="342" cy="100" r="13" fill="#fffdf6" stroke="${INK}" stroke-width="3" />
      <g class="bubble b3">
        <ellipse cx="362" cy="48" rx="50" ry="34" fill="#fffdf6" stroke="${INK}" stroke-width="4" />
        <text x="362" y="62" text-anchor="middle" class="thought-text">?!</text>
      </g>
    </g>

    <!-- body -->
    <rect x="110" y="372" width="200" height="170" rx="40" fill="#3a2a6b" stroke="${INK}" stroke-width="5" />
    <rect x="160" y="410" width="80" height="50" rx="10" fill="#0b0718" stroke="${INK}" stroke-width="3" />
    <circle class="chest-light" cx="180" cy="435" r="6" fill="#3ee0cf" />
    <circle class="chest-light" cx="200" cy="435" r="6" fill="#ffd23f" style="animation-delay:.4s" />
    <circle class="chest-light" cx="220" cy="435" r="6" fill="#ff3864" style="animation-delay:.8s" />

    <!-- head, slowly tilting -->
    <g class="think-head">
      <line x1="200" y1="130" x2="184" y2="92" stroke="${INK}" stroke-width="5" />
      <circle class="robot-bulb" cx="182" cy="86" r="10" />
      <rect x="100" y="128" width="220" height="182" rx="44" fill="#2c2150" stroke="${INK}" stroke-width="6" />
      <circle cx="210" cy="205" r="42" fill="${INK}" />
      <circle class="shifty-eye" cx="210" cy="205" r="18" fill="#ff3864" />
      <g clip-path="url(#socket-clip)">
        <path class="eyelid" d="M160 150 H262 V214 L160 180 Z" fill="#2c2150" />
      </g>
      <path class="brow" d="M150 138 L266 180" stroke="${INK}" stroke-width="13" stroke-linecap="round" />
      <g class="smirk">
        <path d="M158 262 Q210 268 246 254 Q262 246 270 228 Q258 272 206 280 Q176 282 158 262 Z" fill="${INK}" stroke="#3ee0cf" stroke-width="5" stroke-linejoin="round" />
        <path d="M184 268 v9 M204 270 v10 M224 266 v10 M244 257 v10" stroke="#3ee0cf" stroke-width="4" stroke-linecap="round" />
      </g>
    </g>

    <!-- arm up to the chin -->
    <path d="M300 420 Q362 372 306 344 L262 336" fill="none" stroke="${INK}" stroke-width="46" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M300 420 Q362 372 306 344 L262 336" fill="none" stroke="#3a2a6b" stroke-width="36" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="252" cy="334" r="24" fill="#3a2a6b" stroke="${INK}" stroke-width="5" />
    <rect class="finger" x="240" y="296" width="15" height="36" rx="7.5" fill="#3a2a6b" stroke="${INK}" stroke-width="4" />
  </svg>
</div>`;
