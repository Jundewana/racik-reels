export function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

export const formatStyleName = (styleId) =>
  (styleId || '')
    .split('_')
    .map((w, i) => (i === 0 ? w.charAt(0).toUpperCase() + w.slice(1) : w))
    .join(' ');

export const formatElapsed = (sec) => {
  const total = Math.max(0, Math.floor(sec || 0));
  const m = String(Math.floor(total / 60)).padStart(2, '0');
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
};

const numberFmt = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
/** 20.33 → "20,3" (format angka Indonesia) */
export const formatSec = (n) => numberFmt.format(Number(n) || 0);

/** "2026-11-18 15:54:44" → "18 Nov 2026, 15.54" */
export const formatDateTime = (raw) => {
  if (!raw) return '';
  const d = new Date(String(raw).replace(' ', 'T'));
  if (Number.isNaN(d.getTime())) return raw;
  return new Intl.DateTimeFormat('id-ID', { dateStyle: 'medium', timeStyle: 'short' }).format(d);
};

/** Hitung kata & huruf teks hook terhadap batas dari backend (options.hook_limits). */
export const hookStats = (text, limits) => {
  const maxWords = limits?.max_words || 5;
  const maxChars = limits?.max_chars || 28;
  const t = (text || '').trim();
  const words = t ? t.split(/\s+/).length : 0;
  return { words, chars: t.length, maxWords, maxChars, over: words > maxWords || t.length > maxChars };
};

export function renderSimpleMarkdown(md) {
  const escaped = (md || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  return escaped
    .split('\n')
    .map((line) => {
      if (line.startsWith('### ')) return `<h3>${line.slice(4)}</h3>`;
      if (line.startsWith('## ')) return `<h2>${line.slice(3)}</h2>`;
      if (line.startsWith('# ')) return `<h1>${line.slice(2)}</h1>`;
      if (line.trim() === '---') return '<hr />';
      if (line.startsWith('- ')) return `<ul><li>${line.slice(2)}</li></ul>`;
      return line ? `<p>${line}</p>` : '';
    })
    .join('')
    .replace(/<\/ul><ul>/g, '')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>');
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (_) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
  }
}

/** Segmen EDL → blok timeline berurutan (detik keluaran). Kecepatan segmen tidak dikirim API, jadi dianggap 1×. */
export function segmentBlocks(segments) {
  let t = 0;
  return (segments || []).map((s) => {
    const dur = Math.max(0.1, (Number(s.end) || 0) - (Number(s.start) || 0));
    const block = { ...s, from: t, to: t + dur, dur };
    t += dur;
    return block;
  });
}

/**
 * Judul lagu yang rapi dari nama file unduhan: buang ID video [..], frasa "no copyright"/"royalty free"/
 * "background music", kredit "by …", awalan "mixkit-" & nomor katalog; maks 4 kata.
 * "Epic+Cinematic+Dramatic+Background+Music+NO+COPYRIGHT+…[kVQbz5MG2Ms]" → "Epic Cinematic Dramatic EMW".
 */
const TRACK_NOISE = /\b(no copyright music|no copyright|copyright free|royalty free music|royalty free|background music|music for videos?|vlog music)\b/gi;

export function trackTitle(name) {
  const raw = String(name || '');
  let t = raw
    .replace(/\[[^\]]*\]/g, ' ')
    .replace(/^mixkit-/i, '')
    .replace(/[+_•|]/g, ' ')
    .replace(/-\d+\b/g, ' ')
    .replace(/\s-\s|-/g, ' ')
    .replace(TRACK_NOISE, ' ')
    .replace(/\bby\s+\S+/gi, ' ');
  const seen = new Set();
  const words = t
    .split(/\s+/)
    .filter((w) => w && !/^music$/i.test(w))
    .filter((w) => (seen.has(w.toLowerCase()) ? false : seen.add(w.toLowerCase())));
  if (!words.length) return raw;
  return words
    .slice(0, 4)
    .map((w) => (w === w.toUpperCase() && w.length > 1 ? w : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(' ');
}

/** Lama video yang enak dibaca: "14 dtk", "1 mnt 56 dtk", "59 mnt 17 dtk", "2 jam 19 mnt". */
export function formatLength(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  if (s < 60) return `${s} dtk`;
  if (s < 3600) return `${Math.floor(s / 60)} mnt ${s % 60} dtk`;
  return `${Math.floor(s / 3600)} jam ${Math.floor((s % 3600) / 60)} mnt`;
}
