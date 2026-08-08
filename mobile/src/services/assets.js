import { NativeModules } from 'react-native';

// Mirror of the base-URL derivation in api.js: in dev, use the Metro host so a
// phone on the same Wi-Fi reaches the dev machine; in prod, use the live API.
let devHost = 'localhost';
try {
  const host = NativeModules.SourceCode?.scriptURL?.match(/^https?:\/\/([^/:]+)/)?.[1];
  if (host) devHost = host;
} catch (e) { /* fall back to localhost */ }

const API_BASE_URL = __DEV__
  ? `http://${devHost}:8000`
  : 'https://api.valtheriononline.com';

/**
 * Build an absolute URL for a bundled game asset served by the backend's
 * static /assets route. Paths are relative to mobile/assets/, e.g.
 * `assetUrl('combat/rogue_pick0_0_0.png')`.
 */
export function assetUrl(relPath) {
  return `${API_BASE_URL}/assets/${relPath}`;
}

/** Deterministic pseudo-random hash of a string -> 0..1, for stable asset pick. */
function hash01(str) {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return (h >>> 0) / 4294967295;
}

const COMBAT_SPRITES = [
  'combat/rogue_pick0_0_0.png',
  'combat/rogue_pick1_1_10.png',
  'combat/rogue_pick2_2_19.png',
  'combat/rogue_pick3_3_33.png',
  'combat/rogue_pick4_4_44.png',
  'combat/rogue_pick5_6_6.png',
  'combat/rogue_pick6_7_16.png',
  'combat/rogue_pick7_8_33.png',
];

/**
 * Pick a combat sprite for a monster. Stable per monster id so a species keeps
 * its sprite across encounters, but different species get different sprites.
 */
export function monsterSprite(monsterId) {
  const idx = Math.floor(hash01(String(monsterId)) * COMBAT_SPRITES.length) % COMBAT_SPRITES.length;
  return assetUrl(COMBAT_SPRITES[idx]);
}

/** Weapon/armor icons by equipment slot, falling back to a generic icon. */
const SLOT_ICONS = {
  weapon: 'icons/sword_gold.png',
  shield: 'icons/gauntlet_bronze.png',
  helmet: 'icons/star.png',
  chest: 'icons/star.png',
  legs: 'icons/star.png',
  boots: 'icons/star.png',
  gloves: 'icons/gauntlet_bronze.png',
  ring: 'icons/star.png',
  amulet: 'icons/star.png',
  trinket: 'icons/star.png',
};

export function slotIcon(slot) {
  return assetUrl(SLOT_ICONS[slot] || 'icons/sword_silver.png');
}

/* ---------------------------------------------------------------------------
 * SFX (sound effects)
 *
 * click1.ogg / click2.ogg are short CC0 UI clicks (see mobile/assets/LICENSE.md)
 * served by the backend's static /assets route. They're fire-and-forget: we
 * stream them with react-native-sound and never let an audio hiccup block or
 * crash gameplay. Two clips alternate for light variety on repeated taps.
 * ------------------------------------------------------------------------- */
import Sound from 'react-native-sound';

const SFX_CLIPS = ['sfx/click1.ogg', 'sfx/click2.ogg'];

// iOS requires audio sessions before playback. Android plays immediately.
try {
  Sound.setCategory('Ambient', true);
} catch (e) { /* ignore on Android */ }

let sfxCursor = 0;
const sfxCache = new Map(); // url -> { sound, ready }

/** Ensure a clip is loaded (once), then loop-ready. Returns the loaded Sound. */
function loadSfx(url) {
  let entry = sfxCache.get(url);
  if (!entry) {
    entry = { sound: null, ready: false };
    try {
      const s = new Sound(url, undefined, (err) => {
        if (!err) {
          entry.sound = s;
          entry.ready = true;
        }
      });
      entry.loader = s;
      entry.sound = s;
    } catch (e) {
      entry.ready = false;
    }
    sfxCache.set(url, entry);
  }
  return entry;
}

/**
 * Fire-and-forget UI click. Alternates between the two bundled clips.
 * Silent no-op if the clip isn't loaded/playable yet, so taps are never
 * blocked waiting on audio.
 */
export function playSfx() {
  const url = assetUrl(SFX_CLIPS[sfxCursor % SFX_CLIPS.length]);
  sfxCursor += 1;
  const entry = sfxCache.get(url) || loadSfx(url);
  if (!entry.ready || !entry.sound) return;
  try {
    entry.sound.stop();
    entry.sound.play();
  } catch (e) { /* audio glitch — never block gameplay */ }
}

export { API_BASE_URL };
