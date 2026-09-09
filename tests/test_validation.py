"""Shell validation must distinguish a usable shell from a Windows WSL shim."""
import importlib.util
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location("repository_validate", Path(__file__).parents[1] / "scripts/validate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_unusable_bash_is_reported_not_used(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(module.shutil, "which", lambda _: "bash")
    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "WSL is not installed", "")
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.validate_shell_scripts([Path("unused.sh")]) == []
    assert calls == [["bash", "--version"]]
    assert "unverified" in capsys.readouterr().out


def test_syntax_uses_stdin_and_preserves_failure(monkeypatch, tmp_path):
    script = tmp_path / "Chinese path 空格.sh"
    script.write_text("if broken", encoding="utf-8")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module.shutil, "which", lambda _: "bash")
    def run(args, **kwargs):
        if args[-1] == "--version":
            return subprocess.CompletedProcess(args, 0, "GNU bash", "")
        assert args == ["bash", "-n"]
        assert kwargs["input"] == "if broken"
        return subprocess.CompletedProcess(args, 2, "unexpected end of file", "")
    monkeypatch.setattr(module.subprocess, "run", run)
    assert module.validate_shell_scripts([script]) == ["bash syntax: Chinese path 空格.sh: unexpected end of file"]
