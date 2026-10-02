from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_no_google_api_key_is_committed_in_python_sources() -> None:
    marker = "AI" + "za"
    for path in ROOT.rglob("*.py"):
        if ".venv" in path.parts:
            continue
        assert marker not in path.read_text(encoding="utf-8"), path


def test_no_unsafe_default_jwt_secret() -> None:
    auth_source = (ROOT / "backend" / "routers" / "auth.py").read_text(encoding="utf-8")
    unsafe_default = "mediflow" + "_secret"
    assert unsafe_default not in auth_source


def test_environment_file_is_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in ignore
