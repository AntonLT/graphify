"""Tests for the `codex-cli` backend.

Mocks subprocess.run + shutil.which so CI never needs a live Codex session.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from graphify import llm


_RESULT = {
    "nodes": [
        {"id": "foo_module", "label": "Foo", "file_type": "document", "source_file": "foo.md"},
    ],
    "edges": [],
    "hyperedges": [],
    "input_tokens": 0,
    "output_tokens": 0,
}


def _clear_backend_env(monkeypatch):
    for key in (
        "GEMINI_API_KEY", "GOOGLE_API_KEY", "MOONSHOT_API_KEY",
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
        "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT",
        "AWS_PROFILE", "AWS_REGION", "AWS_DEFAULT_REGION", "AWS_ACCESS_KEY_ID",
        "OLLAMA_BASE_URL", "OLLAMA_API_KEY",
        "GRAPHIFY_CODEX_CLI_MODEL", "GRAPHIFY_CODEX_CLI_REASONING",
    ):
        monkeypatch.delenv(key, raising=False)


def _fake_codex_run(argv, **kwargs):
    out_path = Path(argv[argv.index("--output-last-message") + 1])
    out_path.write_text(json.dumps(_RESULT), encoding="utf-8")
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = ""
    proc.stderr = ""
    return proc


def test_codex_cli_backend_registered_with_defaults():
    assert "codex-cli" in llm.BACKENDS
    cfg = llm.BACKENDS["codex-cli"]
    assert cfg["default_model"] == "gpt-5.3-codex-spark"
    assert cfg["reasoning_effort"] == "xhigh"
    assert llm.estimate_cost("codex-cli", 1_000_000, 1_000_000) == 0.0


def test_detect_backend_uses_codex_cli_when_no_api_backend(monkeypatch):
    _clear_backend_env(monkeypatch)

    with patch("shutil.which", return_value="/fake/bin/codex"):
        assert llm.detect_backend() == "codex-cli"


def test_detect_backend_prefers_api_key_over_codex_cli(monkeypatch):
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")

    with patch("shutil.which", return_value="/fake/bin/codex"):
        assert llm.detect_backend() == "gemini"


def test_call_codex_cli_passes_default_model_and_reasoning(monkeypatch):
    _clear_backend_env(monkeypatch)
    monkeypatch.setattr(llm, "_response_is_hollow", lambda raw, parsed: False)

    with patch("shutil.which", return_value="/fake/bin/codex"), \
         patch("subprocess.run", side_effect=_fake_codex_run) as run:
        result = llm._call_codex_cli("UNIQUE_SOURCE_MARKER", max_tokens=8192)

    argv = run.call_args.args[0]
    assert argv[:2] == ["codex", "exec"]
    assert "--ephemeral" in argv
    assert "--skip-git-repo-check" in argv
    assert "--ignore-rules" in argv
    assert argv[argv.index("--sandbox") + 1] == "read-only"
    assert argv[argv.index("--cd") + 1]
    assert argv[argv.index("--model") + 1] == "gpt-5.3-codex-spark"
    assert "model_reasoning_effort=\"xhigh\"" in argv
    assert "--output-last-message" in argv
    assert argv[-1] == "-"
    sent = run.call_args.kwargs["input"]
    assert "graphify semantic extraction agent" in sent
    assert "output ONLY the JSON object" in sent
    assert "UNIQUE_SOURCE_MARKER" in sent
    assert result["nodes"] == _RESULT["nodes"]
    assert result["model"] == "gpt-5.3-codex-spark"


def test_call_codex_cli_env_overrides_model_and_reasoning(monkeypatch):
    _clear_backend_env(monkeypatch)
    monkeypatch.setenv("GRAPHIFY_CODEX_CLI_MODEL", "gpt-5.5-codex")
    monkeypatch.setenv("GRAPHIFY_CODEX_CLI_REASONING", "high")
    monkeypatch.setattr(llm, "_response_is_hollow", lambda raw, parsed: False)

    with patch("shutil.which", return_value="/fake/bin/codex"), \
         patch("subprocess.run", side_effect=_fake_codex_run) as run:
        llm._call_codex_cli("payload", max_tokens=8192)

    argv = run.call_args.args[0]
    assert argv[argv.index("--model") + 1] == "gpt-5.5-codex"
    assert "model_reasoning_effort=\"high\"" in argv


def test_extract_corpus_parallel_codex_cli_progress_and_serial(monkeypatch, tmp_path, capsys):
    _clear_backend_env(monkeypatch)
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("# A\n")
    b.write_text("# B\n")

    def fake_extract(chunk, **kwargs):
        return {
            "nodes": [{"id": unit_path.name, "label": unit_path.name} for unit_path in chunk],
            "edges": [],
            "hyperedges": [],
            "input_tokens": 1,
            "output_tokens": 1,
        }

    monkeypatch.setattr(llm, "_extract_with_adaptive_retry", fake_extract)

    result = llm.extract_corpus_parallel(
        [a, b],
        backend="codex-cli",
        root=tmp_path,
        token_budget=1,
        max_concurrency=4,
    )

    out = capsys.readouterr().out
    assert "[graphify codex-cli] model: gpt-5.3-codex-spark" in out
    assert "[graphify codex-cli] reasoning: xhigh" in out
    assert "[graphify codex-cli] chunks: 2, concurrency: 1" in out
    assert "[graphify codex-cli] chunk 1/2: 1 files," in out
    assert "[graphify codex-cli] chunk 1/2 done: 1 nodes, 0 edges," in out
    assert len(result["nodes"]) == 2
