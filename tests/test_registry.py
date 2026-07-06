"""Registry: load index, resolve bundles, and end-to-end `get` over http."""

from __future__ import annotations

import yaml

from okf_kit import registry
from okf_kit.okf import zip_bundle
from okf_kit.registry import load_registry, resolve_bundle


def test_load_registry_local(tmp_path):
    reg = tmp_path / "registry.yaml"
    reg.write_text(yaml.safe_dump([{"name": "x", "pages": 3, "license": "CC-BY-4.0"}]))
    entries = load_registry(str(reg))
    assert entries[0]["name"] == "x"


def test_resolve_bundle_local_dir(built_bundle):
    assert resolve_bundle(str(built_bundle)) == built_bundle


def test_get_end_to_end(built_bundle, tmp_path, okf_home):
    # Publish: zip the bundle into a served directory + a local registry.yaml
    from serve_util import serve as _serve

    pub = tmp_path / "pub"
    pub.mkdir()
    zip_bundle(built_bundle, output=str(pub / "acme.zip"))
    server, base = _serve(pub)
    try:
        reg = tmp_path / "registry.yaml"
        reg.write_text(yaml.safe_dump([{
            "name": "acme-docs", "pages": 5, "license": "CC-BY-4.0",
            "download": f"{base}/acme.zip",
        }]))
        rc = registry.cmd_get("acme-docs", registry=str(reg), yes=True)
        assert rc == 0
        # Installed into ~/.okf/bundles and resolvable
        installed = resolve_bundle("acme-docs")
        assert (installed / "index.md").exists()
        assert (installed / "pages" / "home.md").exists()
    finally:
        server.shutdown()
        server.server_close()


def test_local_bundles_listing(built_bundle, tmp_path, okf_home):
    from serve_util import serve as _serve

    pub = tmp_path / "pub"
    pub.mkdir()
    zip_bundle(built_bundle, output=str(pub / "acme.zip"))
    server, base = _serve(pub)
    try:
        reg = tmp_path / "registry.yaml"
        reg.write_text(yaml.safe_dump([{"name": "acme-docs", "download": f"{base}/acme.zip"}]))
        registry.cmd_get("acme-docs", registry=str(reg), yes=True)
    finally:
        server.shutdown()
        server.server_close()
    names = [b["name"] for b in registry.local_bundles()]
    assert "acme-docs" in names
