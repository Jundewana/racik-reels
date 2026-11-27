"""True peak audio setelah encoding AAC harus ≤ −1 dBTP (checklist), tanpa menurunkan loudness berlebihan."""

import pytest

from autoreels.media import ffmpeg_bin, run_ffmpeg
from autoreels.render.audio_mix import PEAK_CEILING, fix_true_peak, measure_audio, peak_guard_wav


def _has_ffmpeg() -> bool:
    try:
        return bool(ffmpeg_bin())
    except Exception:  # noqa: BLE001
        return False


pytestmark = pytest.mark.skipif(not _has_ffmpeg(), reason="ffmpeg tidak tersedia")


def _hot_wav(path):
    # nada keras ±−0,4 dBFS (sine lavfi ffmpeg 9 berpuncak ±−21,1 dBFS, jadi +20,7 dB): tanpa pembatas, AAC > −1 dBTP
    run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=997:sample_rate=48000:duration=4", "-af",
                "volume=20.7dB,aformat=channel_layouts=stereo", "-c:a", "pcm_s16le", str(path)])
    return path


def _mux_aac(wav, out):
    run_ffmpeg(["-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=4", "-i", str(wav), "-map", "0:v", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)])
    return out


def test_peak_guard_keeps_aac_under_ceiling(tmp_path):
    guarded = peak_guard_wav(_hot_wav(tmp_path / "hot.wav"), tmp_path / "guarded.wav")
    video = _mux_aac(guarded, tmp_path / "out.mp4")
    peak = fix_true_peak(video, pcm=guarded, log=lambda *_: None)
    assert peak is not None and peak <= PEAK_CEILING


def test_measure_audio_reads_loudness_and_peak(tmp_path):
    lufs, peak = measure_audio(_hot_wav(tmp_path / "hot.wav"))
    assert lufs is not None and peak is not None and peak > -1.0
