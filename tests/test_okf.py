"""OKF format helpers: frontmatter, reserved-name dodging, validate, zip."""

from __future__ import annotations

import zipfile
from pathlib import PurePosixPath

from okf_kit.okf import dodge_reserved, frontmatter, validate_bundle, zip_bundle


def test_frontmatter_drops_empty():
    fm = frontmatter({"type": "Web Page", "title": "T", "description": "", "tags": []})
    assert "type: Web Page" in fm and "title: T" in fm
    assert "description" not in fm and "tags" not in fm
    assert fm.startswith("---\n") and fm.rstrip().endswith("---")


def test_dodge_reserved():
    assert dodge_reserved(PurePosixPath("pages/index.md")).name == "home.md"
    assert dodge_reserved(PurePosixPath("pages/log.md")).name == "history.md"
    assert dodge_reserved(PurePosixPath("pages/intro.md")).name == "intro.md"


def _make_bundle(tmp_path):
    b = tmp_path / "bundle"
    (b / "pages").mkdir(parents=True)
    (b / "index.md").write_text("# root\n")
    (b / "pages" / "index.md").write_text("# listing\n")
    (b / "pages" / "a.md").write_text(frontmatter({"type": "Web Page", "title": "A"}) + "\nbody\n")
    return b


def test_validate_conformant(tmp_path):
    assert validate_bundle(_make_bundle(tmp_path), quiet=True) is True


def test_validate_rejects_missing_type(tmp_path):
    b = _make_bundle(tmp_path)
    (b / "pages" / "bad.md").write_text("no frontmatter here\n")
    assert validate_bundle(b, quiet=True) is False


def test_zip_single_root_includes_state(tmp_path):
    b = _make_bundle(tmp_path)
    (b / ".okf-kit").mkdir()
    (b / ".okf-kit" / "state.json").write_text("{}")
    out = zip_bundle(b, output=str(tmp_path / "out.zip"))
    names = zipfile.ZipFile(out).namelist()
    assert any(n.endswith("pages/a.md") for n in names)
    # state is included so recipients can list/sync the downloaded bundle
    assert any(n.endswith(".okf-kit/state.json") for n in names)
    assert all(n.startswith("bundle/") for n in names)
