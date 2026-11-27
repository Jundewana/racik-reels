"""Pembuatan file teks .ass (libass) untuk hook, teks info per segmen, dan CTA.

Zona aman Reels: hindari ±15% atas dan ±20% bawah layar. Maks 2 baris, ±5 kata per baris.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from autoreels.render.reframe import OUT_H, OUT_W

SAFE_TOP = int(OUT_H * 0.15)
SAFE_BOTTOM = int(OUT_H * 0.80)
SIDE_MARGIN = 90
HOOK_SIZE = 118  # teks hook besar agar menghentikan scroll


# --- font --------------------------------------------------------------------------
def font_full_name(path: Path) -> str:
    """Baca nama font dari tabel 'name' TTF/OTF (nameID 4 = full name), tanpa dependensi tambahan."""
    data = path.read_bytes()
    num_tables = struct.unpack(">H", data[4:6])[0]
    for i in range(num_tables):
        tag, _, offset, _ = struct.unpack(">4sIII", data[12 + 16 * i: 28 + 16 * i])
        if tag != b"name":
            continue
        _, count, str_off = struct.unpack(">HHH", data[offset: offset + 6])
        names: dict[int, str] = {}
        for j in range(count):
            rec = offset + 6 + 12 * j
            pid, eid, lid, nid, length, noff = struct.unpack(">HHHHHH", data[rec: rec + 12])
            raw = data[offset + str_off + noff: offset + str_off + noff + length]
            if pid == 3 and nid in (1, 4) and nid not in names:
                names[nid] = raw.decode("utf-16-be", errors="ignore")
            elif pid == 1 and nid in (1, 4) and nid not in names:
                names[nid] = raw.decode("latin-1", errors="ignore")
        return names.get(4) or names.get(1) or path.stem
    return path.stem


# --- warna ---------------------------------------------------------------------------
def ass_color(hex_color: str, alpha: int | None = None) -> str:
    """'#RRGGBB' atau '#RRGGBBAA' → '&HAABBGGRR' (alpha ASS: 00 = solid, FF = transparan)."""
    h = hex_color.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    if alpha is None:
        a = 255 - int(h[6:8], 16) if len(h) == 8 else 0
    else:
        a = alpha
    return f"&H{a:02X}{b}{g}{r}".upper()


# --- teks ------------------------------------------------------------------------------
def wrap_text(text: str, max_chars: int, max_words: int = 5) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        candidate = " ".join(cur + [w])
        if cur and (len(candidate) > max_chars or len(cur) >= max_words):
            lines.append(" ".join(cur))
            cur = [w]
        else:
            cur.append(w)
    if cur:
        lines.append(" ".join(cur))
    return lines


def fit_text(text: str, base_size: int, chars_at_base: int) -> tuple[list[str], int]:
    """Bungkus maks 2 baris; bila tidak muat, kecilkan font."""
    size, chars = base_size, chars_at_base
    for _ in range(6):
        lines = wrap_text(text, chars)
        if len(lines) <= 2:
            return lines, size
        size = int(size * 0.88)
        chars = int(chars / 0.88)
    return wrap_text(text, chars, max_words=99)[:2], size


def _esc(text: str) -> str:
    return text.replace("\\", "/").replace("{", "(").replace("}", ")").replace("\n", " ")


def _ts(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int(t % 3600 // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


@dataclass
class TextEvent:
    start: float
    end: float
    kind: str      # hook | cover | info | cta | cta_sub | sub | karaoke | badge
    text: str
    avoid: list[tuple[int, int]] | None = None  # hook: rentang y kepala pembicara yang tidak boleh tertutup
    reveal: float = 0.0  # karaoke: detik setelah start saat teks mulai tampil (disembunyikan selama teks hook)
    place: tuple[int, int] | None = None  # hook/cover di belakang orang: (pusat y, ukuran font) dari render/behind.py


HOOK_Y = int(OUT_H * 0.36)
LINE_H = 1.12       # tinggi baris ≈ 1,12 × ukuran font (+ outline)
FACE_GAP = 30       # jarak teks dari kepala
KARAOKE_TOP = SAFE_BOTTOM - 40 - 2 * 100   # subtitle karaoke (2 baris) di atas SAFE_BOTTOM


def hook_position(n_lines: int, size: int, avoid: list[tuple[int, int]] | None) -> tuple[int, int]:
    """(pusat y, ukuran font) teks hook. Tanpa wajah: posisi bawaan. Dengan wajah: di bawah kepala (dada, di atas
    subtitle) bila muat, kalau tidak di atasnya; bila keduanya sempit, font dikecilkan agar muat di ruang terbesar."""
    if not avoid:
        return HOOK_Y, size
    top, bottom = min(a for a, _ in avoid), max(b for _, b in avoid)
    zones = [(max(bottom + FACE_GAP, SAFE_TOP), KARAOKE_TOP, "bawah"), (SAFE_TOP, top - FACE_GAP, "atas")]
    need = n_lines * size * LINE_H
    for a, b, where in zones:
        if b - a >= need:
            return int(a + need / 2) if where == "bawah" else int(b - need / 2), size
    a, b, _ = max(zones, key=lambda z: z[1] - z[0])
    room = b - a
    if room < n_lines * 60 * LINE_H:  # tidak ada ruang layak (wajah sangat besar) → posisi bawaan
        return HOOK_Y, size
    return int((a + b) / 2), int(room / (n_lines * LINE_H))


def build_ass(events: list[TextEvent], style: dict, font_name: str) -> str:
    colors = style.get("colors", {})
    text_c = ass_color(colors.get("text", "#FFFFFF"))
    outline_c = ass_color(colors.get("outline", "#000000"))
    hl = ass_color(colors.get("highlight", "#FFC400"))
    box_c = ass_color(colors.get("box", "#000000B3"))
    text_style = style.get("text_style", "bold_putih_outline")

    if text_style == "rapi_box":
        border_style, outline, shadow, back = 3, 18, 0, box_c
        outline_col = box_c
    elif text_style == "elegan_tipis":
        border_style, outline, shadow, back = 1, 2, 3, ass_color("#000000", 120)
        outline_col = outline_c
    else:  # bold_putih_outline
        border_style, outline, shadow, back = 1, 7, 3, ass_color("#000000", 110)
        outline_col = outline_c

    def style_line(name: str, size: int, primary: str, *, box: str | None = None,
                   secondary: str | None = None) -> str:
        if box:  # teks di dalam kotak warna (gaya "tombol")
            return (f"Style: {name},{font_name},{size},{primary},{primary},{box},{box},"
                    f"0,0,0,0,100,100,0,0,3,22,0,5,{SIDE_MARGIN},{SIDE_MARGIN},0,1")
        # karaoke (\k): kata belum diucapkan = secondary, sudah/sedang diucapkan = primary
        return (f"Style: {name},{font_name},{size},{primary},{secondary or primary},{outline_col},{back},"
                f"0,0,0,0,100,100,0,0,{border_style},{outline},{shadow},5,{SIDE_MARGIN},{SIDE_MARGIN},0,1")

    emphasis_on = style.get("subtitle_emphasis", True)
    emph_c = _inline(ass_color(colors.get("emphasis", colors.get("highlight", "#FFC400"))))

    def render_emphasis(text: str) -> str:
        """Penanda karaoke_events → warna penekanan tetap + pop (membesar lalu menetap) saat kata diucapkan."""
        if not emphasis_on:
            return re.sub(r"\\EMPH\d+", "", text).replace("{\\EMPHEND}", "")

        def pop(m: re.Match) -> str:
            t = int(m.group(1))
            return (f"\\1c{emph_c}\\2c{emph_c}\\t({t},{t + 120},\\fscx128\\fscy128)"
                    f"\\t({t + 120},{t + 280},\\fscx112\\fscy112)")

        text = re.sub(r"\\EMPH(\d+)", pop, text)
        return text.replace("{\\EMPHEND}", f"{{\\1c{_inline(hl)}\\2c{_inline(text_c)}\\fscx100\\fscy100}}")

    def color_line(line: str, sentence_start: bool) -> str:
        """Subtitle voice over (tanpa karaoke): kata penting diberi warna penekanan."""
        out, n = [], 0
        for w in line.split(" "):
            if emphasis_on and w and n < EMPHASIS_MAX and is_emphasis(w, sentence_start):
                out.append(f"{{\\c{emph_c}}}{_esc(w)}{{\\c{_inline(text_c)}}}")
                n += 1
            else:
                out.append(_esc(w))
            if w:
                sentence_start = _ends_sentence(w)
        return " ".join(out)

    cta_text_c = ass_color(colors.get("cta_text", "#111111"))
    cta_box_c = ass_color(colors.get("cta_box", colors.get("highlight", "#FFC400")))

    header = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {OUT_W}",
        f"PlayResY: {OUT_H}",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        style_line("Hook", HOOK_SIZE, text_c),
        # teks di belakang orang: selalu huruf ber-outline tebal tanpa kotak (kotak terlihat janggal terpotong badan)
        (f"Style: HookBehind,{font_name},{HOOK_SIZE},{text_c},{text_c},&H00000000,&H64000000,"
         f"0,0,0,0,100,100,0,0,1,6,4,5,{SIDE_MARGIN},{SIDE_MARGIN},0,1"),
        style_line("Info", 70, text_c),
        style_line("CTA", 76, cta_text_c, box=cta_box_c),
        style_line("CTASub", 54, text_c),
        style_line("Badge", 46, cta_text_c, box=cta_box_c),
        style_line("Karaoke", KARAOKE_SIZE, hl, secondary=text_c),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ])

    lines_out = []
    for ev in events:
        if ev.kind in ("hook", "cover"):
            behind = ev.place is not None
            lines, size = fit_text(ev.text, *((ev.place[1], 11) if behind else (HOOK_SIZE, 14)))
            hl_tag = f"&H{hl[4:]}&"  # \c memakai format &HBBGGRR& (tanpa alpha)
            body = lines[0] if len(lines) == 1 else f"{lines[0]}\\N{{\\c{hl_tag}}}{lines[1]}"
            y, size = (ev.place[0], size) if behind else hook_position(len(lines), size, ev.avoid)
            if ev.kind == "cover":  # gambar diam: tanpa animasi masuk (frame 0 kosong bila ada \fad)
                tag = f"{{\\an5\\pos({OUT_W // 2},{y})\\fs{size}}}"
            else:
                tag = (f"{{\\an5\\pos({OUT_W // 2},{y})\\fs{size}\\fad(80,200)"
                       f"\\fscx118\\fscy118\\t(0,200,\\fscx100\\fscy100)}}")
            lines_out.append(("HookBehind" if behind else "Hook", ev, tag + _esc_keep(body)))
        elif ev.kind == "info":
            lines, size = fit_text(ev.text, 68, 22)
            y = SAFE_BOTTOM - 40
            tag = (f"{{\\an2\\fs{size}\\fad(150,150)"
                   f"\\move({OUT_W // 2},{y + 30},{OUT_W // 2},{y},0,220)}}")
            lines_out.append(("Info", ev, tag + "\\N".join(_esc(x) for x in lines)))
        elif ev.kind == "sub":  # subtitle voice over: bawah, di atas zona UI Instagram
            lines, size = fit_text(ev.text, 62, 24)
            tag = f"{{\\an2\\fs{size}\\fad(60,60)\\pos({OUT_W // 2},{SAFE_BOTTOM - 40})}}"
            lines_out.append(("Info", ev, tag + "\\N".join(
                color_line(x, k == 0) for k, x in enumerate(lines))))
        elif ev.kind == "cta":
            lines, size = fit_text(ev.text, 76, 20)
            tag = (f"{{\\an5\\pos({OUT_W // 2},{int(OUT_H * 0.47)})\\fs{size}\\fad(150,0)"
                   f"\\fscx110\\fscy110\\t(0,200,\\fscx100\\fscy100)}}")
            lines_out.append(("CTA", ev, tag + "\\N".join(_esc(x) for x in lines)))
        elif ev.kind == "karaoke":  # teks sudah berisi tag \k per kata (lihat karaoke_events)
            reveal = ""
            if ev.reveal > 0:  # muncul setelah teks hook hilang; waktu \k tetap dihitung dari awal potongan
                ms = round(ev.reveal * 1000)
                reveal = f"\\alpha&HFF&\\t({ms},{ms + 80},\\alpha&H00&)"
            tag = f"{{\\an2\\pos({OUT_W // 2},{SAFE_BOTTOM - 40})\\fad(60,60){reveal}}}"
            lines_out.append(("Karaoke", ev, tag + render_emphasis(ev.text)))
        elif ev.kind == "badge":  # label before–after: kiri atas, di bawah zona UI atas Instagram
            tag = f"{{\\an7\\pos({SIDE_MARGIN + 10},{int(OUT_H * 0.17)})\\fad(80,80)}}"
            lines_out.append(("Badge", ev, tag + _esc(ev.text)))
        elif ev.kind == "cta_sub":
            tag = f"{{\\an5\\pos({OUT_W // 2},{int(OUT_H * 0.47) + 230})\\fad(250,0)}}"
            lines_out.append(("CTASub", ev, tag + _esc(ev.text)))

    # pengaman: event dengan durasi ≤ 0 tidak boleh ditulis (libass bisa ikut menyembunyikan event lain)
    events_txt = "\n".join(
        f"Dialogue: 0,{_ts(ev.start)},{_ts(ev.end)},{name},,0,0,0,,{text}" for name, ev, text in lines_out
        if round(ev.end, 2) > round(ev.start, 2)
    )
    return header + "\n" + events_txt + "\n"


# --- penekanan subtitle: angka, harga, promo, nama tempat ----------------------------
NUMBER_WORDS = {"dua", "tiga", "empat", "lima", "enam", "tujuh", "delapan", "sembilan", "sepuluh", "sebelas",
                "seratus", "seribu", "sejuta", "puluh", "belas", "ratus", "ribu", "juta", "miliar", "rupiah",
                "rp", "persen", "setengah"}
PROMO_WORDS = {"gratis", "diskon", "promo", "free", "murah", "hemat"}
# kata berhuruf kapital di tengah kalimat yang bukan nama tempat (sapaan, kata ganti hormat)
CAPITAL_STOPWORDS = {"anda", "bapak", "ibu", "kakak", "kak", "pak", "bu", "mas", "mbak", "teh", "akang", "aa",
                     "tuhan", "allah", "insya", "insyaallah", "alhamdulillah", "saya", "kami", "kita", "ok", "oke"}
EMPHASIS_MAX = 3  # maks kata ditekankan per potongan subtitle agar tidak ramai


def _norm_word(word: str) -> str:
    return re.sub(r"[^\w%]", "", word.lower())


@lru_cache(maxsize=1)
def emphasis_vocab() -> frozenset[str]:
    """Nama tempat/merek satu kata dari brand.yaml (transcribe_vocab) + daftar tambahan `emphasis_words`."""
    try:
        from autoreels.config import load_brand

        brand = load_brand()
    except Exception:  # noqa: BLE001 — config rusak tidak boleh menggagalkan render subtitle
        return frozenset()
    out = {_norm_word(str(t)) for t in (brand.get("transcribe_vocab") or []) if len(str(t).split()) == 1}
    for term in brand.get("emphasis_words") or []:
        out.update(_norm_word(t) for t in str(term).split())
    return frozenset(x for x in out if x)


def is_emphasis(word: str, sentence_start: bool, vocab=None) -> bool:
    """Kata layak ditekankan: mengandung angka, kata bilangan/harga, promo, nama tempat (kosakata brand),
    atau berhuruf kapital di tengah kalimat (nama diri versi Whisper)."""
    w = _norm_word(word)
    if not w:
        return False
    if any(c.isdigit() for c in w) or w in NUMBER_WORDS or w in PROMO_WORDS:
        return True
    if w in (emphasis_vocab() if vocab is None else vocab):
        return True
    core = word.strip().lstrip("\"'“‘(")
    return (not sentence_start and len(w) > 2 and core[:1].isupper() and not core.isupper()
            and w not in CAPITAL_STOPWORDS)


def _ends_sentence(word: str) -> bool:
    return word.rstrip().rstrip("\"'”’)").endswith((".", "?", "!"))


def _inline(color: str) -> str:
    return f"&H{color[4:]}&"  # \c memakai format &HBBGGRR& (tanpa alpha)


KARAOKE_SIZE = 72
KARAOKE_WORDS = 6        # kata per potongan subtitle
KARAOKE_LINE_CHARS = 18  # pindah baris setelah ±18 huruf (maks 2 baris)
KARAOKE_GAP = 0.35       # jeda lebih dari ini → potongan baru


def karaoke_events(words, total: float | None = None, vocab=None) -> list[TextEvent]:
    """Kata (start, end, text) → potongan subtitle karaoke: tiap kata menyala tepat saat diucapkan (\\k).
    Potongan baru setelah KARAOKE_WORDS kata, akhir kalimat, atau jeda > KARAOKE_GAP.
    Kata penting (is_emphasis) diberi penanda \\EMPH<ms> … {\\EMPHEND}; build_ass mengubahnya menjadi warna
    penekanan + efek "pop" saat diucapkan, atau membuangnya bila style `subtitle_emphasis: false`."""
    def fits_two_lines(ws) -> bool:
        """Simulasi pindah baris yang sama dengan di bawah: muat dalam 2 baris × KARAOKE_LINE_CHARS?"""
        lines, length = 1, 0
        for w in ws:
            n = len(w.text.strip())
            if length and length + n > KARAOKE_LINE_CHARS:
                lines, length = lines + 1, 0
            length += n + 1
        return lines <= 2 and length <= KARAOKE_LINE_CHARS + 6

    # waktu kata dari Whisper kadang tidak urut (mis. "Oh," 32,07 lalu "baru" 31,06) → potongan dengan
    # akhir < awal membuat libass ikut menyembunyikan teks lain (hook hilang). Urutkan dulu.
    words = sorted(words, key=lambda w: (w.start, w.end))
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= KARAOKE_WORDS or w.start - cur[-1].end > KARAOKE_GAP
                    or cur[-1].text.rstrip().endswith((".", "?", "!")) or not fits_two_lines(cur + [w])):
            chunks.append(cur)
            cur = []
        cur.append(w)
    if cur:
        chunks.append(cur)
    events = []
    prev_end_sentence = True
    for i, ch in enumerate(chunks):
        start = ch[0].start
        emph = set()
        for j, w in enumerate(ch):
            sentence_start = prev_end_sentence if j == 0 else _ends_sentence(ch[j - 1].text)
            if len(emph) < EMPHASIS_MAX and is_emphasis(w.text, sentence_start, vocab):
                emph.add(j)
        prev_end_sentence = _ends_sentence(ch[-1].text)
        nxt = chunks[i + 1][0].start if i + 1 < len(chunks) else (total or ch[-1].end + 0.6)
        end = min(nxt, ch[-1].end + 0.6)
        parts, line_len, lines = [], 0, 1
        for j, w in enumerate(ch):
            until = ch[j + 1].start if j + 1 < len(ch) else end
            cs = max(1, round((until - w.start) * 100))  # \k dalam centidetik (termasuk jeda setelah kata)
            text = _esc(w.text.strip())
            sep = ""
            if parts:
                if line_len + len(text) > KARAOKE_LINE_CHARS and lines < 2:
                    sep, line_len, lines = "\\N", 0, lines + 1
                else:
                    sep = " "
            if j in emph:
                ms = max(0, round((w.start - start) * 1000))
                parts.append(f"{sep}{{\\k{cs}\\EMPH{ms}}}{text}{{\\EMPHEND}}")
            else:
                parts.append(f"{sep}{{\\k{cs}}}{text}")
            line_len += len(text) + 1
        events.append(TextEvent(round(start, 3), round(end, 3), "karaoke", "".join(parts)))
    return events


def _esc_keep(body: str) -> str:
    """Escape teks tetapi pertahankan override tag warna yang kita sisipkan sendiri."""
    parts = body.split("\\N")
    out = []
    for p in parts:
        if p.startswith("{\\c"):
            close = p.index("}") + 1
            out.append(p[:close] + _esc(p[close:]))
        else:
            out.append(_esc(p))
    return "\\N".join(out)
