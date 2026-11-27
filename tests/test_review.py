"""Cek visual video jadi: rencana frame, panggilan vision (palsu), butir checklist."""

from __future__ import annotations

import pytest

from autoreels import review
from autoreels.checklist import Checklist
from autoreels.media import run_ffmpeg
from tests.test_validate import _edl


@pytest.fixture(scope="module")
def reel(tmp_path_factory):
    p = tmp_path_factory.mktemp("rv") / "reel.mp4"
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=108x192:r=30:d=18", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(p)])
    return p


def test_frame_plan_covers_hook_middle_and_cta():
    plan = review.frame_plan(_edl(), 18.0)
    assert 3 <= len(plan) <= review.MAX_FRAMES
    assert plan[0][0] < 1 and "Keliling Garut pakai motor" in plan[0][1]       # hook di detik awal
    assert "CTA" in plan[-1][1] and plan[-1][0] == pytest.approx(16.0)         # CTA at_sec 15 + 1
    times = [t for t, _ in plan]
    assert len(set(times)) == len(times) and all(0 <= t < 18 for t in times)


class FakeVision:
    def __init__(self, result=None, error=None):
        self.result, self.error, self.messages = result, error, None

    def complete_structured(self, messages, schema, **_):
        self.messages = messages
        if self.error:
            raise self.error
        return schema.model_validate(self.result)


def test_review_sends_labelled_frames_and_maps_issues(reel, tmp_path):
    llm = FakeVision({"score": 3, "summary": "x", "issues": [
        {"frame": 1, "severity": "berat", "problem": "teks hook tidak terbaca"},
        {"frame": 4, "severity": "ringan", "problem": "agak gelap", "fix": "pakai adegan lain"}]})
    data = review.review_video(reel, _edl(), llm, "gemini/x", tmp_path, log=lambda *_: None)
    content = llm.messages[1]["content"]
    images = [c for c in content if c["type"] == "image_url"]
    labels = [c["text"] for c in content if c["type"] == "text" and c["text"].startswith("Frame ")]
    assert len(images) == len(labels) == len(data["frames"]) >= 3
    c = Checklist()
    review.add_visual_checks(c, data)
    assert c.status == "perlu_tinjau"                                           # masalah berat wajib diperbaiki
    assert any(i.name == "Catatan frame 4" and not i.required for i in c.items)


def test_minor_issues_and_ai_errors_do_not_block(reel, tmp_path):
    ok = review.review_video(reel, _edl(), FakeVision({"score": 4, "issues": [
        {"frame": 2, "severity": "ringan", "problem": "kontras kurang"}]}), "m", tmp_path, log=lambda *_: None)
    failed = review.review_video(reel, _edl(), FakeVision(error=RuntimeError("kuota habis")), "m", tmp_path,
                                 log=lambda *_: None)
    assert "kuota habis" in failed["error"]
    for data in (ok, failed):
        c = Checklist()
        review.add_visual_checks(c, data)
        assert c.status == "siap_unggah"
