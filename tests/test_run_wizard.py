import runpy
from pathlib import Path


def test_wizard_derives_repo_root_from_script_when_cwd_changes(tmp_path, monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)

    wizard = runpy.run_path(str(repo_root / "scripts" / "run-wizard.py"))

    assert wizard["REPO_ROOT"] == repo_root
    assert wizard["DEFAULT_PROJECTS_DIR"] == repo_root / "projects"


def test_wizard_local_mode_uses_placeholder_channel(monkeypatch):
    repo_root = Path(__file__).resolve().parents[1]
    answers = iter(["", "", "1", "n", "n", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    wizard = runpy.run_path(str(repo_root / "scripts" / "run-wizard.py"))

    command = wizard["build_command"]()

    assert command[command.index("--channel") + 1] == "example-channel"
    assert command[command.index("--projects-dir") + 1] == str(repo_root / "projects")
    assert "--use-existing-videos" in command
    assert "--links-file" not in command
