/*
 * Bahasa antarmuka (Indonesia bawaan, Inggris opsional).
 *
 * Komponen tetap ditulis dalam bahasa Indonesia. Saat bahasa Inggris aktif, pengamat DOM menerjemahkan
 * teks & atribut (placeholder, aria-label, title, alt) memakai kamus lib/en.js (kunci = teks Indonesia),
 * sebelum layar digambar. Teks asli disimpan agar bisa kembali ke Indonesia tanpa memuat ulang.
 * Yang tidak ada di kamus tetap tampil Indonesia. Isi buatan pengguna (caption, subtitle, log) dilewati:
 * tandai wadahnya dengan translate="no". Daftar teks yang belum diterjemahkan: window.__i18nMissing.
 */
import { EN, EN_PATTERNS } from './en.js';

const STORE_KEY = 'racik-lang';
const ATTRS = ['placeholder', 'aria-label', 'title', 'alt'];
const SKIP = 'script,style,textarea,pre,code,[translate="no"],[contenteditable="true"]';

const textRec = new WeakMap(); // Text node → { src, out }
const attrRec = new WeakMap(); // Element → { [attr]: { src, out } }
const missing = new Set();
const listeners = new Set();
let lang = 'id';
let observer = null;

try {
  lang = localStorage.getItem(STORE_KEY) === 'en' ? 'en' : 'id';
} catch {
  /* penyimpanan browser diblokir: pakai bawaan */
}

/** Terjemahkan satu teks Indonesia (spasi di tepi dipertahankan). null bila tidak ada di kamus. */
export function translate(text) {
  const core = text.trim();
  if (!core || !/[A-Za-z]/.test(core)) return null;
  let en = EN[core];
  if (en === undefined) {
    for (const [re, rep] of EN_PATTERNS) {
      const m = core.match(re);
      if (m) {
        // rep: string ($1…) atau fungsi (match, sub) — sub menerjemahkan potongan di dalamnya
        en = typeof rep === 'function' ? rep(m, sub) : core.replace(re, rep);
        break;
      }
    }
  }
  if (en === undefined) {
    missing.add(core);
    return null;
  }
  return text.replace(core, en);
}

const sub = (part) => translate(part) ?? part;

/** Untuk teks di luar DOM (mis. confirm()). */
export const t = (text) => (lang === 'en' ? translate(text) ?? text : text);

const skipped = (el) => !el || !!el.closest?.(SKIP);

function doText(node) {
  const rec = textRec.get(node);
  if (rec && node.nodeValue === rec.out) return; // tulisan kita sendiri
  const src = node.nodeValue;
  if (skipped(node.parentElement)) return;
  const out = translate(src);
  if (out === null || out === src) return;
  textRec.set(node, { src, out });
  node.nodeValue = out;
}

function doAttrs(el) {
  if (skipped(el)) return;
  let recs = attrRec.get(el);
  for (const a of ATTRS) {
    const val = el.getAttribute(a);
    if (!val || recs?.[a]?.out === val) continue;
    const out = translate(val);
    if (out === null || out === val) continue;
    recs = recs || {};
    recs[a] = { src: val, out };
    attrRec.set(el, recs);
    el.setAttribute(a, out);
  }
}

function walk(root) {
  if (root.nodeType === Node.TEXT_NODE) return doText(root);
  if (root.nodeType !== Node.ELEMENT_NODE) return;
  doAttrs(root);
  const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = it.nextNode(); n; n = it.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) doText(n);
    else doAttrs(n);
  }
}

function restore(root) {
  const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  for (let n = it.nextNode(); n; n = it.nextNode()) {
    if (n.nodeType === Node.TEXT_NODE) {
      const rec = textRec.get(n);
      if (rec && n.nodeValue === rec.out) n.nodeValue = rec.src;
      textRec.delete(n);
    } else {
      const recs = attrRec.get(n);
      if (recs) for (const [a, r] of Object.entries(recs)) if (n.getAttribute(a) === r.out) n.setAttribute(a, r.src);
      attrRec.delete(n);
    }
  }
}

function start() {
  if (observer) return;
  walk(document.documentElement);
  observer = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === 'characterData') doText(m.target);
      else if (m.type === 'attributes') doAttrs(m.target);
      else m.addedNodes.forEach(walk);
    }
  });
  observer.observe(document.documentElement, {
    subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS
  });
}

function stop() {
  observer?.disconnect();
  observer = null;
  restore(document.documentElement);
}

export function getLang() {
  return lang;
}

export function setLang(next) {
  lang = next === 'en' ? 'en' : 'id';
  try {
    localStorage.setItem(STORE_KEY, lang);
  } catch {
    /* abaikan */
  }
  document.documentElement.lang = lang;
  if (lang === 'en') start();
  else stop();
  listeners.forEach((fn) => fn(lang));
}

export function onLangChange(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

/** Panggil sekali sebelum React dirender. */
export function initI18n() {
  window.__i18nMissing = missing;
  if (lang === 'en') setLang('en');
}
