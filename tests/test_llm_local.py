"""Mesin AI lokal (Ollama): pemilihan model, konversi pesan, batas gambar."""

from autoreels.config import get_settings
from autoreels.llm import is_local_model, max_images_per_request, ollama_messages


def test_models_for_engine():
    s = get_settings()
    assert s.models_for("api") == (s.llm_model, s.vision_model)
    llm, vision = s.models_for("local")
    assert is_local_model(llm) and is_local_model(vision)


def test_is_local_model():
    assert is_local_model("ollama/qwen3:8b")
    assert is_local_model("ollama_chat/qwen3-vl:4b")
    assert not is_local_model("gemini/gemini-3.1-flash-lite")
    assert not is_local_model(None)


def test_ollama_messages_marks_image_order():
    msgs = [
        {"role": "system", "content": "sistem"},
        {"role": "user", "content": [
            {"type": "text", "text": "ADEGAN K1-1:"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAA"}},
            {"type": "text", "text": "ADEGAN K1-2:"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,BBB"}},
        ]},
    ]
    out = ollama_messages(msgs)
    assert out[0] == {"role": "system", "content": "sistem"}
    assert out[1]["images"] == ["AAA", "BBB"]
    assert out[1]["content"] == "ADEGAN K1-1:\n[gambar #1]\nADEGAN K1-2:\n[gambar #2]"


def test_local_image_limit_is_small():
    assert max_images_per_request("ollama/qwen3-vl:4b") <= 4
    assert max_images_per_request("gemini/gemini-3.1-flash-lite") == 24


def test_fallback_chain_tries_models_in_order(monkeypatch):
    from autoreels import llm as llm_mod
    from autoreels.llm import CostTracker, LLMClient

    import dataclasses

    client = LLMClient(CostTracker(), log=lambda *_: None)
    client.settings = dataclasses.replace(client.settings, llm_model="groq/utama",
                                          llm_fallback="gemini/a, runcrate/openai/b ,groq/utama, cohere_chat/c")
    assert client.fallback_chain("groq/utama") == ["gemini/a", "runcrate/openai/b", "cohere_chat/c"]
    assert client.fallback_chain("ollama/qwen3:4b") == []  # mesin lokal tidak pernah pindah diam-diam ke API
    tried, patience_list = [], []

    def fake_one(messages, *, model, patience=0.0, **_):
        tried.append(model)
        patience_list.append(patience)
        if model != "runcrate/openai/b":
            raise RuntimeError("429 quota exceeded per day")
        return "ok"

    monkeypatch.setattr(client, "_complete_one", fake_one)
    assert client.complete([{"role": "user", "content": "x"}]) == "ok"
    assert tried == ["groq/utama", "gemini/a", "runcrate/openai/b"]
    assert patience_list[0] == llm_mod.FALLBACK_PATIENCE_SEC  # masih ada cadangan → tunggu sebentar saja


def test_strip_code_fence_takes_first_json_object():
    from autoreels.llm import strip_code_fence

    assert strip_code_fence('```json\n{"a": 1}\n```\nPenjelasan: ini {bukan} json') == '{"a": 1}'
    assert strip_code_fence('Berikut hasilnya: {"a": {"b": 2}} semoga membantu') == '{"a": {"b": 2}}'


def test_openai_compatible_gateways_are_routed():
    from autoreels.llm import _KEY_ENV, OPENAI_COMPAT_BASES

    assert OPENAI_COMPAT_BASES["runcrate"].startswith("https://api.runcrate.ai")
    assert _KEY_ENV["runcrate"] == "RUN_CRATE_API_KEY" and _KEY_ENV["cohere_chat"] == "COHERE_API_KEY"
    assert _KEY_ENV["aionlabs"] == "AIONLABS_API_KEY"


def test_fallback_chain_continues_from_a_fallback_model():
    import dataclasses

    from autoreels.llm import CostTracker, LLMClient

    client = LLMClient(CostTracker(), log=lambda *_: None)
    client.settings = dataclasses.replace(client.settings, llm_model="groq/utama",
                                          llm_fallback="gemini/a,runcrate/openai/b,cohere_chat/c")
    assert client.fallback_chain("gemini/a") == ["runcrate/openai/b", "cohere_chat/c"]
    assert client.fallback_chain("cohere_chat/c") == []
    assert client.fallback_chain("lain/x") == []
    client.fallback_enabled = False
    calls = []
    client._complete_one = lambda messages, *, model, **_: calls.append(model) or (_ for _ in ()).throw(RuntimeError("x"))
    import pytest

    with pytest.raises(RuntimeError):
        client.complete([{"role": "user", "content": "x"}], model="gemini/a")
    assert calls == ["gemini/a"]  # mode evaluasi: tanpa cadangan
