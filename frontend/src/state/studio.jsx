import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  USE_MOCK,
  APP_NAME,
  APP_TITLE,
  PROCESS_STEPS,
  IMPORT_PROCESS_STEPS,
  MATERIAL_PAGE_IDS
} from '../lib/constants.js';
import { deepClone, hookStats as calcHookStats, trackTitle } from '../lib/format.js';
import { INITIAL_MOCK_STORE, createMockApi } from '../lib/mock.js';

/**
 * Seluruh state & aksi aplikasi (dipindah dari App.jsx versi lama).
 * Halaman membaca lewat useStudio(); tidak ada prop drilling.
 */
const StudioContext = createContext(null);
export const useStudio = () => useContext(StudioContext);

const EMPTY_PROGRESS = {
  job_id: '',
  percent: 0,
  step: 'ingest',
  step_label: '',
  step_index: 1,
  steps_total: 6,
  detail: '',
  elapsed_sec: 0,
  state: 'berjalan',
  error: null,
  log: []
};

/** Simpan job yang sedang dibuka di URL (?job=) agar bisa di-refresh/dibagikan. */
function setJobInUrl(jobId) {
  const url = new URL(window.location.href);
  if (jobId) url.searchParams.set('job', jobId);
  else url.searchParams.delete('job');
  window.history.replaceState(null, '', url);
}

const PAGE_IDS = ['create', 'animasi', 'import', 'history', 'materials', ...MATERIAL_PAGE_IDS];

/** Halaman aktif di URL (?page=) agar refresh tetap di halaman yang sama. */
function setPageInUrl(pageId) {
  const url = new URL(window.location.href);
  if (pageId && pageId !== 'create') url.searchParams.set('page', pageId);
  else url.searchParams.delete('page');
  if (pageId !== 'create') url.searchParams.delete('job');
  if (pageId !== 'animasi') url.searchParams.delete('video');
  window.history.replaceState(null, '', url);
}

function initialPage() {
  const p = new URLSearchParams(window.location.search).get('page');
  return PAGE_IDS.includes(p) ? p : 'create';
}

function useStudioState() {
  const mockStoreRef = useRef(deepClone(INITIAL_MOCK_STORE));
  const mockApiRef = useRef(createMockApi(mockStoreRef));
  const [processSteps, setProcessSteps] = useState(PROCESS_STEPS);
  const [lastSubmitKind, setLastSubmitKind] = useState('create');
  const [remotionRuns, setRemotionRuns] = useState([]); // nama video Claude + Remotion yang dipantau di langkah Proses

  /* ---------------- Tema & navigasi ---------------- */
  const [darkMode, setDarkMode] = useState(() => document.documentElement.classList.contains('dark'));
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [wizardStep, setWizardStep] = useState(1);
  const pageRef = useRef(currentPage);
  const stepRef = useRef(wizardStep);
  pageRef.current = currentPage;
  stepRef.current = wizardStep;

  /* ---------------- Toast ---------------- */
  const [toasts, setToasts] = useState([]);
  /** action (opsional): { label, onClick } — tombol di dalam toast, mis. "Lihat hasil". */
  const showToast = (message, type = 'success', action = null) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, message, type, action }]);
    const ms = action ? 12000 : type === 'error' ? 6000 : 3000;
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), ms);
  };
  const dismissToast = (id) => setToasts((prev) => prev.filter((t) => t.id !== id));

  /* ---------------- Opsi & form wizard ---------------- */
  const [options, setOptions] = useState(INITIAL_MOCK_STORE.options);
  const [form, setForm] = useState({
    pillar: 'rental',
    input_path: 'footage/rental',
    brief: 'Promo sewa motor untuk wisatawan yang mau keliling Garut',
    style: 'rental_energik',
    duration: 20,
    hook_text: '',
    cta_text: '',
    music_file: null,
    no_music: false, // tanpa musik latar
    voiceover: 'none',
    voice: 'Puck',
    engine: 'api', // api | local (Ollama, uji coba)
    musik_claude: false, // Claude + Remotion: musik & efek suara orisinal gubahan Claude
    remotion: false, // true = Claude Code / Antigravity + Remotion menyusun video dari footage (alur montase)
    agen: 'claude', // penyusun Remotion: 'claude' | 'antigravity'
    blur_faces: false, // privasi: pilihan pengguna, default mati
    blur_plates: false,
    logo: true, // watermark di pojok video
    talk_full: false, // video bicara: true = utuh (ikut panjang video, maks 3 mnt)
    flow: 'video', // video = ikut ketukan musik | narasi = ikut suara narasi
    narration_path: null,
    narration_draft: null, // ID transkrip yang sudah diperiksa manusia (wajib untuk alur narasi)
    talk_clip: null, // alur "bicara": nama file video pembicara di folder footage
    purpose: '' // '' = dipilih AI | promosi | informasi
  });

  /* ---------------- Footage & unggah ---------------- */
  const [clips, setClips] = useState([]);
  const [narrations, setNarrations] = useState([]);
  const [uploadingNarration, setUploadingNarration] = useState(false);
  const [narrationDraft, setNarrationDraft] = useState(null);
  const [highlight, setHighlight] = useState(null); // tugas cari cuplikan: state, percent, candidates
  const highlightTimer = useRef(null);
  const [creatingClips, setCreatingClips] = useState(false);
  const [highlightRanks, setHighlightRanks] = useState([]); // cuplikan yang dicentang (diproses lewat tombol utama)
  const [batch, setBatch] = useState(null); // { ids: [...], titles: [...], index } — Reel dari cuplikan
  const batchRef = useRef(null);
  useEffect(() => {
    batchRef.current = batch;
  }, [batch]);
  const [transcribing, setTranscribing] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  // Klip yang TIDAK dipakai (nama file). Disimpan sebagai pengecualian agar video yang baru diunggah
  // otomatis ikut terpilih. Dikosongkan saat folder berganti.
  const [excludedClips, setExcludedClips] = useState([]);
  const [loadingClips, setLoadingClips] = useState(false);
  const [uploadQueue, setUploadQueue] = useState([]);

  /* ---------------- Cuplikan musik ---------------- */
  const [playingTrackPath, setPlayingTrackPath] = useState(null);
  const audioPlayerRef = useRef(null);
  const audioTimerRef = useRef(null);

  /* ---------------- Progress & polling ---------------- */
  const [submittingJob, setSubmittingJob] = useState(false);
  const [jobState, setJobState] = useState('idle');
  const [progress, setProgress] = useState(EMPTY_PROGRESS);
  const pollTimerRef = useRef(null);

  /* ---------------- Hasil ---------------- */
  const [currentJob, setCurrentJob] = useState(null);
  const [showReportModal, setShowReportModal] = useState(false);

  /* ---------------- Riwayat ---------------- */
  const [jobs, setJobs] = useState([]);
  const [historyFilter, setHistoryFilter] = useState({ pillar: 'all', status: 'all' });

  /* ---------------- Konfigurasi ---------------- */
  const [hasUnsavedConfig, setHasUnsavedConfig] = useState(false);
  const [savingConfig, setSavingConfig] = useState(false);
  const [unsavedModal, setUnsavedModal] = useState({ open: false, targetPage: null });

  const [activeConfigPillar, setActiveConfigPillar] = useState('rental');
  const [hooksConfig, setHooksConfig] = useState(INITIAL_MOCK_STORE.configHooks);
  const [activeSeoPillar, setActiveSeoPillar] = useState('rental');
  const [pillarSeoConfig, setPillarSeoConfig] = useState(INITIAL_MOCK_STORE.configPillars);
  const [trendsConfig, setTrendsConfig] = useState(INITIAL_MOCK_STORE.configTrends);
  const [brandConfig, setBrandConfig] = useState(INITIAL_MOCK_STORE.configBrand);
  const [captionGuideConfig, setCaptionGuideConfig] = useState(INITIAL_MOCK_STORE.configCaptionGuide);

  /* ======================================================================
   * API
   * ====================================================================== */
  const api = async (method, path, body = null) => {
    if (USE_MOCK) return mockApiRef.current(method, path, body);

    try {
      const fetchOptions = { method, headers: {} };
      if (body instanceof FormData) {
        fetchOptions.body = body;
      } else if (body !== null) {
        fetchOptions.headers['Content-Type'] = 'application/json';
        fetchOptions.body = JSON.stringify(body);
      }
      const res = await fetch(path, fetchOptions);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errMsg = data.error || `Permintaan gagal (${res.status})`;
        showToast(errMsg, 'error');
        throw new Error(errMsg);
      }
      return data;
    } catch (err) {
      // fetch() gagal total (server mati) melempar TypeError tanpa respons
      if (err instanceof TypeError || !err.message) {
        showToast('Server lokal tidak menjawab. Jalankan: python main.py --web', 'error');
      }
      throw err;
    }
  };

  const uploadWithProgress = (url, formData, onProgress) =>
    new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
      xhr.onload = () => {
        let json = {};
        try {
          json = JSON.parse(xhr.responseText || '{}');
        } catch (_) {}
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(json);
        } else {
          const msg = json.error || `Unggahan gagal (${xhr.status})`;
          showToast(msg, 'error');
          reject(new Error(msg));
        }
      };
      xhr.onerror = () => {
        showToast('Koneksi terputus saat mengunggah. Pastikan laptop masih menyala, lalu coba lagi.', 'error');
        reject(new Error('Network error'));
      };
      xhr.send(formData);
    });

  /* ======================================================================
   * EFEK: TEMA, BEFOREUNLOAD, MUAT AWAL
   * ====================================================================== */
  useEffect(() => {
    try {
      localStorage.setItem('autoreels_dark_mode', String(darkMode));
    } catch (_) {}
    document.documentElement.classList.toggle('dark', darkMode);
  }, [darkMode]);

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      if (hasUnsavedConfig) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [hasUnsavedConfig]);

  useEffect(() => {
    const bootstrap = async () => {
      const [optData, hooksData, jobsData, seoData, trendsData, brandData, guideData] = await Promise.all([
        api('GET', '/api/options'),
        api('GET', '/api/config/hooks'),
        api('GET', '/api/jobs'),
        api('GET', '/api/config/pillars/rental'),
        api('GET', '/api/config/trends'),
        api('GET', '/api/config/brand'),
        api('GET', '/api/config/caption-guide')
      ]);

      setOptions(optData);
      // mesin lokal dipilih tapi tidak tersedia (Ollama mati) → kembali ke API
      setForm((prev) => {
        const eng = (optData.engines || []).find((e) => e.id === prev.engine);
        return eng && !eng.available ? { ...prev, engine: 'api' } : prev;
      });
      setHooksConfig({
        rental: hooksData.rental || [],
        konstruksi: hooksData.konstruksi || [],
        profil: hooksData.profil || [],
        lowongan: hooksData.lowongan || [],
        umum: hooksData.umum || []
      });
      setJobs(jobsData.jobs || []);
      setPillarSeoConfig((prev) => ({
        ...prev,
        rental: { hashtags: seoData.hashtags || [], keywords: seoData.keywords || [] }
      }));
      setTrendsConfig(trendsData);
      setBrandConfig(brandData);
      setCaptionGuideConfig(guideData);

      await loadFootage('footage/rental');
      loadNarrations().catch(() => {});

      // Tautan langsung ke hasil: /?job=<job_id>
      const deepJob = new URLSearchParams(window.location.search).get('job');
      if (deepJob) openJobDetail(deepJob).catch(() => setJobInUrl(null));

      // Ada job yang masih berjalan di server (mis. halaman di-refresh)? Pantau lagi.
      const active = await api('GET', '/api/jobs/active').catch(() => ({ jobs: [] }));
      const running = (active.jobs || []).filter((j) => j.state === 'berjalan');
      const resume = running[running.length - 1] || (active.jobs || [])[0];
      if (resume) {
        setLastSubmitKind(resume.kind || 'create');
        startPollingProgress(resume.job_id, resume.kind || 'create', {
          focus: !deepJob && pageRef.current === 'create'
        });
      }
    };

    bootstrap().catch(() => {});
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
      if (audioTimerRef.current) clearTimeout(audioTimerRef.current);
      if (audioPlayerRef.current) audioPlayerRef.current.pause();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ======================================================================
   * HELPER
   * ====================================================================== */
  const hookStats = (text) => calcHookStats(text, options.hook_limits);
  const getPillarLabel = (pillarId) => options.pillars.find((x) => x.id === pillarId)?.label || pillarId;
  const getMusicName = (path) => trackTitle(options.music.find((m) => m.path === path)?.name || path);

  /* ======================================================================
   * NAVIGASI & KONFIRMASI PERUBAHAN BELUM DISIMPAN
   * ====================================================================== */
  const goTo = async (pageId) => {
    setCurrentPage(pageId);
    setPageInUrl(pageId);
    window.scrollTo({ top: 0 });
    if (pageId === 'history') {
      const data = await api('GET', '/api/jobs');
      setJobs(data.jobs || []);
    }
  };

  const navigateTo = (pageId) => {
    if (currentPage === pageId) return;
    if (hasUnsavedConfig) {
      setUnsavedModal({ open: true, targetPage: pageId });
      return;
    }
    goTo(pageId).catch(() => {});
  };

  const confirmDiscardChanges = () => {
    const target = unsavedModal.targetPage;
    setHasUnsavedConfig(false);
    setUnsavedModal({ open: false, targetPage: null });
    if (target) goTo(target).catch(() => {});
  };

  /* ======================================================================
   * LANGKAH 1 & 2: FOOTAGE, MUSIK, PENGATURAN
   * ====================================================================== */
  const loadFootage = async (folder) => {
    setLoadingClips(true);
    try {
      const data = await api('GET', `/api/footage?folder=${encodeURIComponent(folder)}`);
      setClips(data.clips || []);
    } finally {
      setLoadingClips(false);
    }
  };

  const selectPillar = (pillarId) => {
    const pObj = options.pillars.find((p) => p.id === pillarId);
    const matchingFolder = options.footage_folders.find((f) => f.path === `footage/${pillarId}`);
    const nextFolder = matchingFolder ? matchingFolder.path : form.input_path;
    setForm((prev) => ({
      ...prev,
      pillar: pillarId,
      style: pObj ? pObj.default_style : prev.style,
      brief: pObj ? pObj.default_brief : prev.brief,
      input_path: nextFolder
    }));
    if (nextFolder !== form.input_path) setExcludedClips([]);
    loadFootage(nextFolder).catch(() => {});
  };

  /* ---------------- Narasi (alur "narasi dulu") ---------------- */
  const loadNarrations = async () => {
    const data = await api('GET', '/api/narration');
    setNarrations(data.files || []);
    return data.files || [];
  };

  const uploadNarration = async (file) => {
    if (!file) return;
    setUploadingNarration(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = USE_MOCK
        ? await mockApiRef.current('POST', '/api/narration/upload', fd)
        : await uploadWithProgress('/api/narration/upload', fd, () => {});
      await loadNarrations();
      selectNarration(res.path);
      setForm((prev) => ({ ...prev, flow: 'narasi' }));
      showToast('Narasi diunggah');
    } finally {
      setUploadingNarration(false);
    }
  };

  const selectNarration = (path) => {
    setForm((prev) => ({ ...prev, narration_path: path, narration_draft: null }));
    setNarrationDraft(null);
  };

  /** Transkrip + koreksi AI di server (±30–90 dtk), hasilnya diperiksa manusia sebelum video dibuat. */
  const transcribeNarration = async () => {
    if (!form.narration_path) return;
    setTranscribing(true);
    try {
      const res = await api('POST', '/api/narration/transcribe', {
        narration_path: form.narration_path,
        engine: form.engine || 'api',
        brief: form.brief || ''
      });
      setNarrationDraft(res);
      setForm((prev) => ({ ...prev, narration_draft: null }));
    } catch {
      // pesan galat sudah ditampilkan api()
    } finally {
      setTranscribing(false);
    }
  };

  /** Video bicara: transkrip + pilih kalimat (ringkas/utuh) + koreksi AI → draf diperiksa sebelum render. */
  const transcribeTalk = async () => {
    if (!form.talk_clip) return;
    setTranscribing(true);
    try {
      const res = await api('POST', '/api/talk/transcribe', {
        input_path: form.input_path,
        talk_clip: form.talk_clip,
        brief: form.brief || '',
        engine: form.engine || 'api',
        talk_full: Boolean(form.talk_full),
        duration: 40
      });
      setNarrationDraft(res);
      setForm((prev) => ({ ...prev, narration_draft: null }));
    } catch {
      // pesan galat sudah ditampilkan api()
    } finally {
      setTranscribing(false);
    }
  };

  const resetNarrationDraft = () => {
    setNarrationDraft(null);
    setForm((prev) => ({ ...prev, narration_draft: null }));
  };

  const saveNarrationDraft = async (texts) => {
    if (!narrationDraft) return;
    setSavingDraft(true);
    try {
      const res = await api('PUT', `/api/narration/drafts/${narrationDraft.id}`, { texts });
      setNarrationDraft(res);
      setForm((prev) => ({ ...prev, narration_draft: res.id }));
      showToast('Transkrip disimpan');
    } catch {
      // pesan galat sudah ditampilkan api()
    } finally {
      setSavingDraft(false);
    }
  };

  /* ---------------- Cari cuplikan (video panjang → beberapa Reel) ---------------- */
  const pollHighlight = (taskId) => {
    clearInterval(highlightTimer.current);
    highlightTimer.current = setInterval(async () => {
      try {
        const st = await api('GET', `/api/highlights/${taskId}`);
        setHighlight(st);
        if (st.state !== 'berjalan') clearInterval(highlightTimer.current);
      } catch {
        clearInterval(highlightTimer.current);
      }
    }, USE_MOCK ? 600 : 2000);
  };

  // "Cari ulang": semua cuplikan yang pernah ditampilkan untuk video + brief ini dikirim agar AI mencari bagian lain
  const seenHighlights = useRef({ key: '', items: [] });
  const startHighlights = async ({ again = false } = {}) => {
    if (!form.talk_clip) return;
    const videoPath = `${form.input_path}/${form.talk_clip}`;
    const key = `${videoPath}|${form.brief || ''}`;
    if (seenHighlights.current.key !== key) seenHighlights.current = { key, items: [] };
    if (again && highlight?.candidates?.length) {
      seenHighlights.current.items = [
        ...seenHighlights.current.items,
        ...highlight.candidates.map(({ start, end, title }) => ({ start, end, title }))
      ].slice(-40);
    }
    const res = await api('POST', '/api/highlights', {
      video_path: videoPath,
      count: 0, // semua bagian yang layak (maks 20)
      brief: form.brief || '',
      engine: form.engine || 'api',
      exclude: again ? seenHighlights.current.items : []
    });
    setHighlight({ task_id: res.task_id, state: 'berjalan', percent: 0, detail: 'memulai…', candidates: [] });
    setHighlightRanks([]);
    pollHighlight(res.task_id);
  };

  const resetHighlight = () => {
    clearInterval(highlightTimer.current);
    setHighlight(null);
    setHighlightRanks([]);
  };

  const createFromHighlights = async (ranks = highlightRanks) => {
    if (!highlight?.task_id || !ranks.length) return;
    setCreatingClips(true);
    try {
      if (form.remotion) {
        const res = await api('POST', `/api/highlights/${highlight.task_id}/animasi`, {
          ...buildJobPayload(),
          ranks,
          musik_claude: Boolean(form.musik_claude) && !form.no_music,
          agen: form.agen || 'claude'
        });
        setRemotionRuns(res.names);
        setLastSubmitKind('remotion');
        setWizardStep(3);
        window.scrollTo({ top: 0 });
        return;
      }
      const res = await api('POST', `/api/highlights/${highlight.task_id}/jobs`, { ...buildJobPayload(), ranks });
      showToast(`${res.job_ids.length} Reel masuk antrean, dibuat satu per satu`);
      const titles = ranks.map((r) => highlight.candidates.find((c) => c.rank === r)?.title || `Cuplikan ${r}`);
      const b = res.job_ids.length > 1 ? { ids: res.job_ids, titles, index: 0, states: {} } : null;
      setBatch(b);
      batchRef.current = b;
      startPollingProgress(res.job_ids[0]);
    } finally {
      setCreatingClips(false);
    }
  };

  /** Varian dari job jadi (durasi lain / tanpa CTA / ringkas-utuh): antre seperti beberapa Reel cuplikan. */
  const createVariants = async (jobId, variants, titles) => {
    const res = await api('POST', `/api/jobs/${encodeURIComponent(jobId)}/variants`, { variants });
    showToast(`${res.job_ids.length} varian masuk antrean, dibuat satu per satu`);
    const b = res.job_ids.length > 1 ? { ids: res.job_ids, titles: titles.map((t) => `Varian: ${t}`), index: 0, states: {} } : null;
    setBatch(b);
    batchRef.current = b;
    startPollingProgress(res.job_ids[0]);
  };

  const selectFolder = (folder) => {
    setExcludedClips([]);
    setForm((prev) => ({ ...prev, input_path: folder }));
    loadFootage(folder).catch(() => {});
  };

  const uploadFiles = async (fileList) => {
    const validFiles = Array.from(fileList).filter((f) => /\.(mp4|mov)$/i.test(f.name) || f.type.startsWith('video/'));
    if (validFiles.length === 0) {
      showToast('File ini bukan video. Pilih file .mp4 atau .mov.', 'error');
      return;
    }

    let latestFolder = form.input_path;
    let okCount = 0;
    for (const file of validFiles) {
      const itemId = `${Date.now()}-${Math.random()}`;
      setUploadQueue((prev) => [...prev, { id: itemId, name: file.name, progress: 0, status: 'uploading' }]);
      const fd = new FormData();
      fd.append('pillar', form.pillar);
      fd.append('files[]', file);
      try {
        if (USE_MOCK) {
          for (let p = 20; p <= 100; p += 20) {
            await new Promise((r) => setTimeout(r, 80));
            setUploadQueue((prev) => prev.map((q) => (q.id === itemId ? { ...q, progress: p } : q)));
          }
          const res = await mockApiRef.current('POST', '/api/footage/upload', fd);
          latestFolder = res.folder;
        } else {
          const res = await uploadWithProgress('/api/footage/upload', fd, (pct) => {
            setUploadQueue((prev) => prev.map((q) => (q.id === itemId ? { ...q, progress: pct } : q)));
          });
          if (res.folder) latestFolder = res.folder;
        }
        okCount += 1;
        setUploadQueue((prev) => prev.map((q) => (q.id === itemId ? { ...q, status: 'done', progress: 100 } : q)));
      } catch (_) {
        setUploadQueue((prev) => prev.map((q) => (q.id === itemId ? { ...q, status: 'error' } : q)));
      }
    }

    const optData = await api('GET', '/api/options');
    setOptions(optData);
    setForm((prev) => ({ ...prev, input_path: latestFolder }));
    await loadFootage(latestFolder);
    if (okCount) showToast(okCount === 1 ? '1 video diunggah' : `${okCount} video diunggah`);
    setTimeout(() => setUploadQueue((prev) => prev.filter((q) => q.status !== 'done')), 2500);
  };

  const stopMusicPreview = () => {
    if (audioTimerRef.current) {
      clearTimeout(audioTimerRef.current);
      audioTimerRef.current = null;
    }
    if (audioPlayerRef.current) {
      audioPlayerRef.current.pause();
      audioPlayerRef.current = null;
    }
    setPlayingTrackPath(null);
  };

  const playMockSynthPreview = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(330, ctx.currentTime);
      gain.gain.setValueAtTime(0.04, ctx.currentTime);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      setTimeout(() => {
        osc.stop();
        ctx.close();
      }, 600);
    } catch (_) {}
  };

  const toggleMusicPreview = (track) => {
    if (playingTrackPath === track.path) {
      stopMusicPreview();
      return;
    }
    stopMusicPreview();
    setPlayingTrackPath(track.path);
    const audio = new Audio(track.url);
    audioPlayerRef.current = audio;
    audio.play().catch(() => playMockSynthPreview());
    audioTimerRef.current = setTimeout(stopMusicPreview, 10000);
  };

  /* ======================================================================
   * LANGKAH 3 & 4: KIRIM JOB, POLLING, HASIL
   * ====================================================================== */
  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
    document.title = APP_TITLE;
  };

  const openJobDetail = async (jobId) => {
    const data = await api('GET', `/api/jobs/${encodeURIComponent(jobId)}`);
    setCurrentJob(data);
    setPageInUrl('create');
    setJobInUrl(data.job_id || jobId);
    setCurrentPage('create');
    setWizardStep(4);
    window.scrollTo({ top: 0 });
  };

  /** focus=true: tampilkan layar Proses sekarang. false: pantau diam-diam (indikator di navigasi). */
  const startPollingProgress = (jobId, kind = 'create', { focus = true } = {}) => {
    stopPolling();
    setProcessSteps(kind === 'import' ? IMPORT_PROCESS_STEPS : PROCESS_STEPS);
    if (focus) setWizardStep(3);
    setJobState('berjalan');
    setProgress({ ...EMPTY_PROGRESS, job_id: jobId, detail: 'Memulai antrean…' });

    const watchingProcess = () => pageRef.current === 'create' && stepRef.current === 3;

    const pollOnce = async () => {
      try {
        const data = await api('GET', `/api/jobs/${encodeURIComponent(jobId)}/progress`);
        setProgress(data);
        setJobState(data.state);
        document.title = data.state === 'berjalan' ? `(${Math.round(data.percent)}%) ${APP_NAME}` : APP_TITLE;

        const b = batchRef.current;
        const bi = b ? b.ids.indexOf(jobId) : -1;
        if ((data.state === 'selesai' || data.state === 'gagal') && bi >= 0 && bi < b.ids.length - 1) {
          stopPolling();
          api('GET', '/api/jobs').then((d) => setJobs(d.jobs || [])).catch(() => {});
          showToast(`Reel ${bi + 1} dari ${b.ids.length} ${data.state === 'selesai' ? 'selesai' : 'gagal'}, lanjut Reel ${bi + 2}`,
                    data.state === 'selesai' ? 'success' : 'error',
                    data.state === 'selesai' ? { label: 'Lihat', onClick: () => openJobDetail(jobId).catch(() => {}) } : null);
          const next = { ...b, index: bi + 1, states: { ...(b.states || {}), [jobId]: data.state } };
          setBatch(next);
          batchRef.current = next;
          startPollingProgress(b.ids[bi + 1], kind, { focus: watchingProcess() });
          return;
        }
        if (data.state === 'selesai') {
          stopPolling();
          if (bi >= 0) {
            setBatch(null);
            batchRef.current = null;
          }
          api('GET', '/api/jobs').then((d) => setJobs(d.jobs || [])).catch(() => {});
          if (watchingProcess()) {
            showToast('Video selesai dibuat');
            await openJobDetail(jobId);
          } else {
            // pengguna sedang di halaman lain: beri tahu, jangan pindahkan paksa
            showToast('Video selesai dibuat', 'success', {
              label: 'Lihat hasil',
              onClick: () => openJobDetail(jobId).catch(() => {})
            });
          }
        } else if (data.state === 'gagal') {
          stopPolling();
          if (bi >= 0) {
            const fin = { ...b, states: { ...(b.states || {}), [jobId]: 'gagal' } };
            setBatch(fin);
            batchRef.current = fin;
          }
          if (!watchingProcess()) {
            showToast('Pembuatan video gagal', 'error', { label: 'Lihat detail', onClick: () => goToProcess() });
          }
        }
      } catch (err) {
        stopPolling();
        setJobState('gagal');
        setProgress((prev) => ({ ...prev, state: 'gagal', error: err.message || 'Progres tidak bisa dipantau.' }));
      }
    };

    pollOnce();
    pollTimerRef.current = setInterval(pollOnce, 1000);
  };

  const buildJobPayload = () => ({
    input_path: form.input_path,
    clips: excludedClips.length ? selectedClipNames : null, // null = semua klip di folder
    pillar: form.pillar,
    brief: form.brief.trim(),
    style: form.style,
    duration: Number(form.duration) || 20,
    hook_text: form.hook_text.trim() || null,
    cta_text: form.cta_text.trim() || null,
    music_file: form.no_music ? null : form.music_file || null,
    no_music: Boolean(form.no_music),
    voiceover: form.flow === 'video' ? form.voiceover || 'none' : 'none',
    talk_clip: form.flow === 'bicara' ? form.talk_clip : null,
    purpose: form.purpose || null,
    narration_path: form.flow === 'narasi' ? form.narration_path : null,
    // draf hanya berlaku untuk alur pembuatnya (pindah narasi ↔ bicara tidak membawa draf yang salah)
    narration_draft:
      (form.flow === 'narasi' && narrationDraft?.kind !== 'bicara') ||
      (form.flow === 'bicara' && narrationDraft?.kind === 'bicara' && narrationDraft?.speaker_clip === form.talk_clip)
        ? form.narration_draft
        : null,
    voice: form.voice || 'Puck',
    engine: form.engine || 'api',
    blur_faces: form.flow !== 'bicara' && Boolean(form.blur_faces),
    blur_plates: Boolean(form.blur_plates),
    logo: form.logo !== false,
    talk_full: form.flow === 'bicara' ? Boolean(form.talk_full) : false
  });

  const submitCreateJob = async () => {
    if (submittingJob) return;
    stopMusicPreview();
    setSubmittingJob(true);
    setLastSubmitKind('create');
    try {
      if (form.remotion) {
        const p = buildJobPayload();
        const d = new Date();
        const pad = (n) => String(n).padStart(2, '0');
        const nama = `${form.pillar}-${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`;
        const res = await api('POST', '/api/animasi/footage', {
          nama,
          input_path: p.input_path,
          pilar: p.pillar,
          brief: p.brief,
          style: p.style,
          duration: p.duration,
          clips: p.clips,
          hook_text: p.hook_text,
          cta_text: p.cta_text,
          music_file: p.music_file,
          no_music: p.no_music,
          musik_claude: Boolean(form.musik_claude) && !p.no_music,
          narration_draft: p.narration_draft,
          talk_clip: p.talk_clip,
          auto_claude: true,
          agen: form.agen || 'claude'
        });
        setRemotionRuns([res.nama]);
        setLastSubmitKind('remotion');
        setWizardStep(3);
        window.scrollTo({ top: 0 });
        return;
      }
      const res = await api('POST', '/api/jobs', buildJobPayload());
      startPollingProgress(res.job_id);
    } finally {
      setSubmittingJob(false);
    }
  };

  const resetWizardToNew = () => {
    if (jobState !== 'berjalan') {
      stopPolling();
      setJobState('idle');
    }
    setCurrentJob(null);
    setRemotionRuns([]);
    setPageInUrl('create');
    setJobInUrl(null);
    setForm((prev) => ({ ...prev, hook_text: '', cta_text: '' }));
    setWizardStep(1);
    setCurrentPage('create');
    window.scrollTo({ top: 0 });
  };

  /** Kembali ke layar Proses dari halaman mana pun (indikator navigasi, kartu di Riwayat, toast). */
  const goToProcess = () => {
    if (hasUnsavedConfig) {
      setUnsavedModal({ open: true, targetPage: 'create' });
      return;
    }
    setCurrentPage('create');
    setPageInUrl('create');
    setWizardStep(3);
    window.scrollTo({ top: 0 });
  };

  const wasBusyRef = useRef(false);
  const [remotionBusy, setRemotionBusy] = useState(null); // {n, label}: Claude + Remotion yang sedang berjalan (tampil di navigasi)

  // pulihkan setelah muat ulang halaman: video Claude + Remotion yang masih berjalan di server
  useEffect(() => {
    if (USE_MOCK) return;
    api('GET', '/api/animasi?mode=footage')
      .then((d) => {
        const run = (d.videos || []).filter((x) => x.mode === 'footage' && x.state === 'berjalan').map((x) => x.nama);
        if (run.length) {
          setRemotionRuns((cur) => (cur.length ? cur : run));
          setLastSubmitKind((k) => (k === 'create' ? 'remotion' : k));
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // pantau terus walau pengguna pindah halaman, agar penanda "sedang berjalan" tetap ada
  useEffect(() => {
    if (!remotionRuns.length) {
      setRemotionBusy(null);
      return undefined;
    }
    let stop = false;
    const tick = async () => {
      try {
        const d = await api('GET', '/api/animasi?mode=footage');
        const mine = (d.videos || []).filter((x) => remotionRuns.includes(x.nama));
        const busy = mine.filter((x) => x.state === 'berjalan');
        if (!stop) setRemotionBusy(busy.length ? { n: busy.length, label: busy[0].detail || 'Claude Code bekerja' } : null);
        if (!stop && wasBusyRef.current && !busy.length) {
          const done = mine.find((x) => x.hasil?.job_id);
          const watching = pageRef.current === 'create' && stepRef.current === 3;
          if (done && !watching) {
            showToast('Video Claude + Remotion selesai', 'success', {
              label: 'Lihat hasil',
              onClick: () => openJobDetail(done.hasil.job_id).catch(() => {})
            });
          }
        }
        wasBusyRef.current = busy.length > 0;
      } catch {
        /* dicoba lagi */
      }
    };
    tick();
    const id = setInterval(tick, 3000);
    return () => {
      stop = true;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [remotionRuns.join('|')]);

  const activeJob =
    jobState === 'berjalan' && progress.job_id
      ? {
          job_id: progress.job_id,
          percent: Math.round(Math.min(100, Math.max(0, progress.percent || 0))),
          label: processSteps[(progress.step_index || 1) - 1]?.label || progress.step_label || 'Memproses'
        }
      : remotionBusy
        ? { job_id: 'remotion', percent: 0, indeterminate: true, label: `${form.agen === 'antigravity' ? 'Antigravity' : 'Claude'} + Remotion: ${remotionBusy.label}` }
        : null;
  const viewingProcess = currentPage === 'create' && wizardStep === 3;

  const canJumpToStep = (stepNum) => {
    if (stepNum === wizardStep) return true;
    if (stepNum === 3) return Boolean(progress.job_id) || remotionRuns.length > 0; // job terakhir (berjalan/selesai/gagal) tetap bisa dibuka lagi
    if (stepNum === 1) return true;
    if (stepNum === 2) return selectedClipNames.length > 0;
    if (stepNum === 4) return Boolean(currentJob);
    return false;
  };

  const selectedClipNames = clips.map((c) => c.name).filter((n) => !excludedClips.includes(n));
  const isClipSelected = (name) => !excludedClips.includes(name);
  const toggleClip = (name) =>
    setExcludedClips((prev) => (prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name]));
  const selectAllClips = () => setExcludedClips([]);
  const clearClipSelection = () => setExcludedClips(clips.map((c) => c.name));

  const filteredJobs = useMemo(
    () =>
      jobs.filter((j) => {
        const matchPillar = historyFilter.pillar === 'all' || j.pillar === historyFilter.pillar;
        const matchStatus = historyFilter.status === 'all' || j.status === historyFilter.status;
        return matchPillar && matchStatus;
      }),
    [jobs, historyFilter]
  );

  /* ======================================================================
   * HALAMAN BAHAN AI (HOOK, HASHTAG, TREN, BRAND, CAPTION)
   * ====================================================================== */
  const markDirty = () => setHasUnsavedConfig(true);

  const saveWith = async (fn, message) => {
    setSavingConfig(true);
    try {
      await fn();
      setHasUnsavedConfig(false);
      showToast(message);
    } finally {
      setSavingConfig(false);
    }
  };

  const addHookItem = (hook) => {
    setHooksConfig((prev) => ({
      ...prev,
      [activeConfigPillar]: [...(prev[activeConfigPillar] || []), hook]
    }));
    markDirty();
  };
  const updateHookItem = (idx, hook) => {
    setHooksConfig((prev) => {
      const updated = [...(prev[activeConfigPillar] || [])];
      updated[idx] = hook;
      return { ...prev, [activeConfigPillar]: updated };
    });
    markDirty();
  };
  const deleteHookItem = (idx) => {
    setHooksConfig((prev) => {
      const updated = [...(prev[activeConfigPillar] || [])];
      updated.splice(idx, 1);
      return { ...prev, [activeConfigPillar]: updated };
    });
    markDirty();
  };
  const saveHooksConfig = () => saveWith(() => api('PUT', '/api/config/hooks', hooksConfig), 'Pustaka hook disimpan');

  const switchSeoPillar = async (pillarId) => {
    setActiveSeoPillar(pillarId);
    const data = await api('GET', `/api/config/pillars/${encodeURIComponent(pillarId)}`);
    setPillarSeoConfig((prev) => ({
      ...prev,
      [pillarId]: { hashtags: data.hashtags || [], keywords: data.keywords || [] }
    }));
  };

  /** kind: 'hashtags' | 'keywords' */
  const addSeoChip = (kind, raw) => {
    let value = (raw || '').trim().toLowerCase();
    if (kind === 'hashtags') {
      value = value.replace(/\s+/g, '').replace(/^#+/, '');
      if (value) value = `#${value}`;
    }
    if (!value) return false;
    const current = pillarSeoConfig[activeSeoPillar]?.[kind] || [];
    if (current.includes(value)) return false;
    setPillarSeoConfig((prev) => ({
      ...prev,
      [activeSeoPillar]: { ...prev[activeSeoPillar], [kind]: [...current, value] }
    }));
    markDirty();
    return true;
  };
  const removeSeoChip = (kind, idx) => {
    setPillarSeoConfig((prev) => {
      const updated = [...(prev[activeSeoPillar]?.[kind] || [])];
      updated.splice(idx, 1);
      return { ...prev, [activeSeoPillar]: { ...prev[activeSeoPillar], [kind]: updated } };
    });
    markDirty();
  };
  const savePillarSeoConfig = () =>
    saveWith(
      () => api('PUT', `/api/config/pillars/${encodeURIComponent(activeSeoPillar)}`, pillarSeoConfig[activeSeoPillar]),
      'Hashtag & keyword disimpan'
    );

  const addTrendItem = (key, value) => {
    const val = (value || '').trim();
    if (!val) return false;
    setTrendsConfig((prev) => ({ ...prev, [key]: [...(prev[key] || []), val] }));
    markDirty();
    return true;
  };
  const removeTrendItem = (key, idx) => {
    setTrendsConfig((prev) => {
      const updated = [...(prev[key] || [])];
      updated.splice(idx, 1);
      return { ...prev, [key]: updated };
    });
    markDirty();
  };
  const clearAllTrends = () => {
    setTrendsConfig((prev) => ({ ...prev, formats: [], hooks: [], audio: [], moments: [], notes: [] }));
    markDirty();
  };
  const saveTrendsConfig = () =>
    saveWith(async () => {
      await api('PUT', '/api/config/trends', trendsConfig);
      setTrendsConfig((prev) => ({ ...prev, updated: new Date().toISOString().slice(0, 10) }));
    }, 'Brief tren disimpan');

  const saveBrandConfig = () =>
    saveWith(async () => {
      await api('PUT', '/api/config/brand', {
        price_per_day: brandConfig.price_per_day,
        default_cta: brandConfig.default_cta
      });
      setOptions((prev) => ({ ...prev, default_cta: { ...brandConfig.default_cta } }));
    }, 'Pengaturan brand disimpan');

  const saveCaptionGuideConfig = () =>
    saveWith(async () => {
      const cleanedExamples = (captionGuideConfig.examples || []).map((e) => e.trim()).filter(Boolean);
      await api('PUT', '/api/config/caption-guide', { fields: captionGuideConfig.fields, examples: cleanedExamples });
      setCaptionGuideConfig((prev) => ({ ...prev, examples: cleanedExamples }));
    }, 'Panduan caption disimpan');

  return {
    useMock: USE_MOCK,
    api,
    uploadWithProgress,
    // tema & navigasi
    darkMode,
    setDarkMode,
    currentPage,
    navigateTo,
    isMaterialPage: MATERIAL_PAGE_IDS.includes(currentPage),
    wizardStep,
    setWizardStep,
    canJumpToStep,
    unsavedModal,
    setUnsavedModal,
    confirmDiscardChanges,
    // toast
    toasts,
    showToast,
    dismissToast,
    // opsi & form
    options,
    form,
    setForm,
    hookStats,
    getPillarLabel,
    getMusicName,
    // footage
    clips,
    loadingClips,
    selectedClipNames,
    isClipSelected,
    toggleClip,
    selectAllClips,
    clearClipSelection,
    uploadQueue,
    selectPillar,
    selectFolder,
    narrations,
    narrationDraft,
    highlight,
    batch,
    highlightRanks,
    setHighlightRanks,
    startHighlights,
    resetHighlight,
    createFromHighlights,
    createVariants,
    creatingClips,
    transcribing,
    savingDraft,
    selectNarration,
    transcribeNarration,
    transcribeTalk,
    resetNarrationDraft,
    saveNarrationDraft,
    loadNarrations,
    uploadNarration,
    uploadingNarration,
    uploadFiles,
    // musik
    playingTrackPath,
    toggleMusicPreview,
    stopMusicPreview,
    // proses
    submittingJob,
    submitCreateJob,
    jobState,
    progress,
    processSteps,
    lastSubmitKind,
    remotionRuns,
    setLastSubmitKind,
    startPollingProgress,
    activeJob,
    viewingProcess,
    goToProcess,
    // hasil
    currentJob,
    openJobDetail,
    resetWizardToNew,
    showReportModal,
    setShowReportModal,
    // riwayat
    jobs,
    filteredJobs,
    historyFilter,
    setHistoryFilter,
    // bahan AI
    hasUnsavedConfig,
    markDirty,
    savingConfig,
    activeConfigPillar,
    setActiveConfigPillar,
    hooksConfig,
    addHookItem,
    updateHookItem,
    deleteHookItem,
    saveHooksConfig,
    activeSeoPillar,
    switchSeoPillar,
    pillarSeoConfig,
    addSeoChip,
    removeSeoChip,
    savePillarSeoConfig,
    trendsConfig,
    addTrendItem,
    removeTrendItem,
    clearAllTrends,
    saveTrendsConfig,
    brandConfig,
    setBrandConfig,
    saveBrandConfig,
    captionGuideConfig,
    setCaptionGuideConfig,
    saveCaptionGuideConfig
  };
}

export function StudioProvider({ children }) {
  const studio = useStudioState();
  return <StudioContext.Provider value={studio}>{children}</StudioContext.Provider>;
}
