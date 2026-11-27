import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, FileCode2, Terminal, Eye, MessageCircle, Check, Circle, Loader2, MonitorPlay } from 'lucide-react';
import { useStudio } from '../state/studio.jsx';
import { Button, cx } from './ui.jsx';

/**
 * Ruang Kerja: lihat Claude Code mengedit secara langsung (event nyata dari `claude -p` stream-json, bukan simulasi).
 * Live lewat SSE /api/animasi/{nama}/events/stream; replay = event tersimpan (jalan terakhir) diputar ulang lebih cepat.
 */
const SPEEDS = [1, 4, 16];
const TYPE_MS = 1400; // kode baru "diketik" selama ini (tampilan saja; isinya edit nyata)

function useTyped(text, active) {
  const [n, setN] = useState(active ? 0 : text.length);
  useEffect(() => {
    if (!active) {
      setN(text.length);
      return undefined;
    }
    setN(0);
    const step = Math.max(2, Math.ceil(text.length / (TYPE_MS / 30)));
    const id = setInterval(() => setN((c) => (c + step >= text.length ? (clearInterval(id), text.length) : c + step)), 30);
    return () => clearInterval(id);
  }, [text, active]);
  return text.slice(0, n);
}

function CodePanel({ ev, fresh, agentShort }) {
  const isEdit = ev?.k === 'edit';
  const newText = ev ? (isEdit ? ev.new : ev.content) : '';
  const typed = useTyped(newText || '', fresh);
  if (!ev) {
    return <p className="grid h-full place-items-center p-6 text-center text-[13px] text-muted">{`Belum ada kode yang diubah. Panel ini terisi saat ${agentShort} mulai menulis.`}</p>;
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-line px-3 py-2 text-[12px]">
        <FileCode2 className="h-3.5 w-3.5 text-muted" aria-hidden="true" />
        <span className="font-semibold text-ink" translate="no">{ev.file}</span>
        <span className="text-muted">{isEdit ? 'diubah' : 'ditulis'}{ev.scene != null && `, adegan ${ev.scene}`}</span>
        <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-brand-soft px-2 py-0.5 font-semibold text-brand">
          <span className="h-1.5 w-1.5 rounded-full bg-brand" aria-hidden="true" />
          {agentShort}
        </span>
      </div>
      <pre className="min-h-0 flex-1 overflow-auto whitespace-pre-wrap break-words p-3 font-mono text-[12px] leading-relaxed scroll-thin" translate="no">
        {isEdit && ev.old && <span className="block bg-stop/10 text-stop-text line-through decoration-stop/60">{ev.old}</span>}
        <span className={cx('block', isEdit ? 'bg-go/10 text-ink' : 'text-ink')}>
          {typed}
          {fresh && typed.length < newText.length && <span className="ml-0.5 inline-block h-3.5 w-1.5 translate-y-0.5 animate-pulse bg-brand" aria-hidden="true" />}
        </span>
      </pre>
    </div>
  );
}

function SceneStrip({ scenes, active, refs }) {
  if (!scenes?.length) return null;
  return (
    <ol className="flex gap-1.5 overflow-x-auto pb-1 scroll-thin" aria-label="Adegan">
      {scenes.map((sc) => (
        <li
          key={sc.n}
          ref={(el) => {
            refs.current[sc.n] = el;
          }}
          className={cx('shrink-0 rounded-md border px-2.5 py-1.5 text-[12px] transition-colors', active === sc.n ? 'border-brand bg-brand-soft font-semibold text-brand' : 'border-line text-muted')}
          aria-current={active === sc.n ? 'true' : undefined}
        >
          <span className="tabular-nums">{sc.n}</span> <span translate="no">{sc.judul}</span>
        </li>
      ))}
    </ol>
  );
}

/** Pratinjau video langsung: Remotion Studio di iframe, hot reload tiap Claude menyimpan kode. Dinyalakan sesuai permintaan. */
function LivePreview({ nama, agentShort }) {
  const { api } = useStudio();
  const [state, setState] = useState('off'); // off | starting | ready
  const [error, setError] = useState('');

  useEffect(() => {
    if (state !== 'starting') return undefined;
    const id = setInterval(() => {
      api('GET', '/api/studio-remotion')
        .then((d) => d.ready && setState('ready'))
        .catch(() => {});
    }, 1000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state]);

  const start = async () => {
    setError('');
    setState('starting');
    try {
      const d = await api('POST', '/api/studio-remotion');
      if (d.ready) setState('ready');
    } catch (e) {
      setError(e.message || 'Remotion Studio tidak bisa dinyalakan.');
      setState('off');
    }
  };

  if (state === 'ready') {
    return (
      <iframe
        title="Pratinjau video langsung (Remotion Studio)"
        src={`http://${window.location.hostname}:3010/${nama}`}
        className="h-[34rem] w-full rounded-lg border border-line bg-paper"
      />
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-line p-3">
      <Button variant="secondary" size="sm" icon={MonitorPlay} onClick={start} loading={state === 'starting'}>
        {state === 'starting' ? 'Menyalakan pratinjau…' : 'Pratinjau video langsung'}
      </Button>
      <span className="text-[13px] text-muted">{`Video berubah di sini setiap ${agentShort} menyimpan kode. Dinyalakan sekali, mati bersama server.`}</span>
      {error && <span className="w-full text-[13px] font-semibold text-stop-text">{error}</span>}
    </div>
  );
}

function Plan({ items, agentShort }) {
  if (!items?.length) return <p className="text-[13px] text-muted">{`Rencana langkah muncul di sini bila ${agentShort} membuatnya.`}</p>;
  return (
    <ul className="space-y-1.5">
      {items.map((it, i) => (
        <li key={i} className="flex items-start gap-2 text-[13px]">
          {it.status === 'completed' ? (
            <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-go" aria-label="selesai" />
          ) : it.status === 'in_progress' ? (
            <Loader2 className="mt-0.5 h-3.5 w-3.5 shrink-0 animate-spin text-brand" aria-label="berjalan" />
          ) : (
            <Circle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted" aria-label="menunggu" />
          )}
          <span className={cx(it.status === 'completed' && 'text-muted line-through')} translate="no">{it.text}</span>
        </li>
      ))}
    </ul>
  );
}

const feedLine = (e) =>
  e.k === 'read' ? `membaca ${e.file}` : e.k === 'bash' ? e.cmd : e.k === 'edit' ? `mengubah ${e.file}` : e.k === 'write' ? `menulis ${e.file}` : e.k === 'frame' ? 'frame diam selesai dirender' : e.k === 'tool' ? e.name : null;

export default function RuangKerja({ nama, agen = 'claude', running, lembarUrl, punyaKode = false }) {
  const { api } = useStudio();
  const agentShort = agen === 'antigravity' ? 'Antigravity' : 'Claude';
  const agentFull = agen === 'antigravity' ? 'Antigravity' : 'Claude Code';
  const [events, setEvents] = useState([]);
  const [replay, setReplay] = useState(null); // null = live; {view, speed, playing}
  const feedRef = useRef(null);
  const wrapRef = useRef(null);
  const targets = { code: useRef(null), plan: useRef(null), frame: useRef(null), thought: useRef(null), feed: feedRef };
  const sceneRefs = useRef({});
  const [cursor, setCursor] = useState(null); // {x, y} relatif ke wrapRef

  // muat jalan terakhir, lalu ikuti live lewat SSE selama Claude berjalan
  useEffect(() => {
    let es;
    let cancelled = false;
    setEvents([]);
    setReplay(null);
    api('GET', `/api/animasi/${nama}/events`)
      .then((d) => {
        if (cancelled) return;
        setEvents(d.events);
        if (!d.running) return;
        es = new EventSource(`/api/animasi/${nama}/events/stream?since=${d.events.length}`);
        es.onmessage = (m) => {
          const e = JSON.parse(m.data);
          if (e.k === 'selesai') es.close();
          else setEvents((cur) => (cur.some((x) => x.i === e.i) ? cur : [...cur, e]));
        };
        es.onerror = () => es.close();
      })
      .catch(() => {});
    return () => {
      cancelled = true;
      if (es) es.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nama, running]);

  // putar ulang: majukan indeks sesuai selisih waktu event asli ÷ kecepatan
  useEffect(() => {
    if (!replay?.playing) return undefined;
    if (replay.view >= events.length) {
      setReplay((r) => ({ ...r, playing: false }));
      return undefined;
    }
    const prev = replay.view > 0 ? events[replay.view - 1].t : 0;
    const wait = Math.min(2500, Math.max(120, ((events[replay.view].t - prev) * 1000) / replay.speed));
    const id = setTimeout(() => setReplay((r) => ({ ...r, view: r.view + 1 })), wait);
    return () => clearTimeout(id);
  }, [replay, events]);

  const view = replay ? replay.view : events.length;
  const shown = useMemo(() => events.slice(0, view), [events, view]);
  const lastCode = useMemo(() => [...shown].reverse().find((e) => e.k === 'edit' || e.k === 'write'), [shown]);
  const plan = useMemo(() => [...shown].reverse().find((e) => e.k === 'plan')?.items, [shown]);
  const thoughts = useMemo(() => shown.filter((e) => e.k === 'text').slice(-3), [shown]);
  const feed = useMemo(() => shown.filter((e) => feedLine(e)).slice(-40), [shown]);
  const frames = shown.filter((e) => e.k === 'frame');
  const scenes = useMemo(() => [...shown].reverse().find((e) => e.scenes?.length)?.scenes, [shown]);
  const activeScene = useMemo(() => [...shown].reverse().find((e) => e.scene != null)?.scene ?? null, [shown]);
  const live = !replay && running;
  const fresh = lastCode && lastCode === shown[shown.length - 1] && (live || replay?.playing);

  useEffect(() => {
    if (feedRef.current) feedRef.current.scrollTop = feedRef.current.scrollHeight;
  }, [feed.length]);

  // kursor melayang: pindah ke panel yang sedang dikerjakan Claude (dari event terakhir yang tampil)
  const lastEv = shown[shown.length - 1];
  const targetKey = !lastEv ? null : lastEv.k === 'edit' || lastEv.k === 'write' ? 'code' : lastEv.k === 'plan' ? 'plan' : lastEv.k === 'frame' ? 'frame' : lastEv.k === 'text' ? 'thought' : feedLine(lastEv) ? 'feed' : null;
  const placeCursor = () => {
    const sceneEl = (targetKey === 'code' && lastEv?.scene != null && sceneRefs.current[lastEv.scene]) || null;
    const el = sceneEl || (targetKey && (targets[targetKey].current || targets.plan.current));
    const wrap = wrapRef.current;
    if (!el || !wrap) return;
    const a = el.getBoundingClientRect();
    const w = wrap.getBoundingClientRect();
    const typing = targetKey === 'code' && !sceneEl;
    setCursor({ x: a.left - w.left + Math.min(a.width * (typing ? 0.45 : 0.3), 220), y: a.top - w.top + Math.min(a.height * (typing ? 0.45 : 0.5), 120) });
  };
  useLayoutEffect(() => {
    placeCursor();
    // tata letak bisa bergeser setelah gambar/ukuran berubah → hitung ulang agar kursor tetap menempel di panelnya
    const wrap = wrapRef.current;
    if (!wrap || typeof ResizeObserver === 'undefined') return undefined;
    const ro = new ResizeObserver(() => placeCursor());
    ro.observe(wrap);
    return () => ro.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [targetKey, view, thoughts.length, frames.length]);
  const showCursor = cursor && (live || replay?.playing);

  if (!events.length && !running) {
    return <p className="text-sm text-muted max-w-prose">{`Belum ada rekaman kerja. Jalankan ${agentFull} sekali, lalu pekerjaannya bisa dilihat langsung dan diputar ulang di sini.`}</p>;
  }

  const startReplay = (speed) => setReplay({ view: 0, speed, playing: true });

  return (
    <div ref={wrapRef} className="relative space-y-3">
      {showCursor && (
        <div className="pointer-events-none absolute left-0 top-0 z-20 transition-transform duration-500 ease-out" style={{ transform: `translate(${cursor.x}px, ${cursor.y}px)` }} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 18 18" className="drop-shadow">
            <path d="M2 1.5 16 8l-6 1.8L8 16z" className="fill-brand stroke-white" strokeWidth="1.2" strokeLinejoin="round" />
          </svg>
          <span className="ml-3.5 -mt-0.5 inline-block rounded-full bg-brand px-2 py-0.5 text-[11px] font-semibold text-white shadow">{`${agentShort} 1`}</span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-2">
        <span className={cx('inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12px] font-semibold', live ? 'bg-brand-soft text-brand' : 'bg-sunken text-muted')}>
          <span className={cx('h-2 w-2 rounded-full', live ? 'animate-pulse bg-brand' : 'bg-muted')} aria-hidden="true" />
          {replay ? 'Putar ulang' : live ? `${agentShort} sedang bekerja` : 'Rekaman terakhir'}
        </span>
        <span className="text-[12px] text-muted">{shown.length} / {events.length} langkah</span>
        <div className="ml-auto flex items-center gap-1">
          {SPEEDS.map((s) => (
            <Button key={s} variant={replay?.speed === s ? 'secondary' : 'ghost'} size="sm" onClick={() => startReplay(s)} disabled={running || !events.length}>
              {replay?.speed === s && replay.playing ? <Pause className="h-3.5 w-3.5" aria-hidden="true" /> : <Play className="h-3.5 w-3.5" aria-hidden="true" />}
              <span className="ml-1">{s}×</span>
            </Button>
          ))}
          {replay && (
            <Button variant="ghost" size="sm" onClick={() => setReplay(null)}>
              Ke akhir
            </Button>
          )}
        </div>
      </div>

      <SceneStrip scenes={scenes} active={activeScene} refs={sceneRefs} />
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_14rem]">
        <div ref={targets.code} className="h-80 overflow-hidden rounded-lg border border-line bg-paper">
          <CodePanel ev={lastCode} fresh={fresh} agentShort={agentShort} />
        </div>
        <div className="space-y-3">
          <div ref={targets.plan} className="rounded-lg border border-line p-3">
            <p className="mb-2 text-[12px] font-semibold uppercase tracking-wide text-muted">Rencana</p>
            <Plan items={plan} agentShort={agentShort} />
          </div>
          {frames.length > 0 && lembarUrl && (
            <div ref={targets.frame} className="h-52 overflow-y-auto rounded-lg border border-line scroll-thin">
              <img src={`${lembarUrl}${lembarUrl.includes('?') ? '&' : '?'}n=${frames[frames.length - 1].n}`} alt={`Frame diam terbaru dari ${agentShort}`} width={1080} height={2400} className="h-auto w-full" loading="lazy" />
            </div>
          )}
        </div>
      </div>

      {(punyaKode || lastCode) && <LivePreview nama={nama} agentShort={agentShort} />}

      {thoughts.length > 0 && (
        <ul ref={targets.thought} className="space-y-1.5">
          {thoughts.map((e) => (
            <li key={e.i} className="flex items-start gap-2 rounded-lg bg-sunken px-3 py-2 text-[13px] text-ink">
              <MessageCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" aria-hidden="true" />
              <span className="line-clamp-3 break-words" translate="no">{e.text}</span>
            </li>
          ))}
        </ul>
      )}

      <ul ref={feedRef} className="h-32 space-y-0.5 overflow-y-auto rounded-lg border border-line p-2 text-[12px] scroll-thin" aria-label="Aktivitas Claude">
        {feed.map((e) => (
          <li key={e.i} className="flex items-center gap-2 text-muted">
            {e.k === 'bash' ? <Terminal className="h-3 w-3 shrink-0" aria-hidden="true" /> : e.k === 'read' ? <Eye className="h-3 w-3 shrink-0" aria-hidden="true" /> : <FileCode2 className="h-3 w-3 shrink-0" aria-hidden="true" />}
            <span className="w-10 shrink-0 tabular-nums">{Math.round(e.t)}s</span>
            <span className="truncate" translate="no">{feedLine(e)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
