"""Registry client: list and fetch published OKF bundles.

The registry is an index (registry.yaml) of bundles published as release zips.
`okf get` downloads a zip, extracts it into the local bundle store
(~/.okf/bundles/), and validates it.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import httpx
import yaml

from .config import bundles_dir
from .okf import validate_bundle

DEFAULT_REGISTRY = (
    "https://raw.githubusercontent.com/vinodborole/awesome-okf-kit/main/registry.yaml"
)


def load_registry(source: str) -> list[dict]:
    """Load registry.yaml from a URL or local path."""
    if source.startswith(("http://", "https://")):
        text = httpx.get(source, follow_redirects=True, timeout=30).raise_for_status().text
    else:
        text = Path(source).read_text(encoding="utf8")
    data = yaml.safe_load(text) or []
    if not isinstance(data, list):
        raise SystemExit("registry.yaml must be a list of bundle entries")
    return data


def local_bundles() -> list[dict]:
    """Bundles already downloaded into ~/.okf/bundles/."""
    out = []
    for state in sorted(bundles_dir().glob("*/.okf-kit/state.json")):
        s = json.loads(state.read_text(encoding="utf8"))
        out.append(
            {
                "name": state.parent.parent.name,
                "root_url": s.get("root_url"),
                "pages": s.get("page_count"),
                "updated": (s.get("last_sync") or {}).get("synced_at", s.get("updated_at", ""))[:10],
            }
        )
    return out


def cmd_list(*, remote: bool, registry: str) -> int:
    if remote:
        entries = load_registry(registry or DEFAULT_REGISTRY)
        if not entries:
            print("Registry is empty.")
            return 0
        for e in entries:
            print(f"{e.get('name',''):28} {str(e.get('pages','?')):>6} pages  "
                  f"{e.get('license','?'):12} {e.get('description','')[:50]}")
    else:
        local = local_bundles()
        if not local:
            print("No local bundles. Try `okf list --remote` or `okf get <name>`.")
            return 0
        for e in local:
            print(f"{e['name']:28} {str(e['pages']):>6} pages  updated {e['updated']}  {e['root_url']}")
    return 0


def cmd_get(name: str, *, registry: str, yes: bool) -> int:
    entries = load_registry(registry or DEFAULT_REGISTRY)
    entry = next((e for e in entries if e.get("name") == name), None)
    if not entry:
        print(f"'{name}' is not in the registry. Try `okf list --remote`.")
        return 1
    download = entry.get("download")
    if not download:
        print(f"'{name}' has no download URL in the registry.")
        return 1

    size = entry.get("size_mb")
    if not yes:
        size_str = f" (~{size} MB)" if size else ""
        resp = input(f"Download '{name}'{size_str} from {download}? [y/N] ").strip().lower()
        if resp not in ("y", "yes"):
            print("Cancelled.")
            return 1

    print(f"Downloading {name}…")
    data = httpx.get(download, follow_redirects=True, timeout=120).raise_for_status().content

    dest = bundles_dir() / name
    _extract_zip(io.BytesIO(data), dest)
    if not validate_bundle(dest, quiet=True):
        print(f"Warning: '{name}' failed OKF validation after download.")
        return 3
    print(f"Installed '{name}' -> {dest}\nChat with it:  okf chat {name}")
    return 0


def _extract_zip(buf, dest: Path) -> None:
    """Extract a bundle zip into dest, flattening a single top-level folder."""
    import shutil

    if dest.exists():
        shutil.rmtree(dest)
    with zipfile.ZipFile(buf) as zf:
        names = zf.namelist()
        # Bundles ship under one top folder (<name>-okf/…); strip it.
        tops = {n.split("/", 1)[0] for n in names if "/" in n}
        strip = tops.pop() + "/" if len(tops) == 1 else ""
        for member in names:
            if member.endswith("/"):
                continue
            rel = member[len(strip):] if strip and member.startswith(strip) else member
            if not rel or ".." in Path(rel).parts:
                continue
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(zf.read(member))


def resolve_bundle(name_or_dir: str) -> Path:
    """A bundle argument may be a local directory or a downloaded bundle name."""
    p = Path(name_or_dir)
    if (p / "index.md").exists():
        return p
    stored = bundles_dir() / name_or_dir
    if (stored / "index.md").exists():
        return stored
    raise SystemExit(
        f"'{name_or_dir}' is neither an OKF bundle directory nor a downloaded bundle. "
        f"Use `okf get {name_or_dir}` or pass a path."
    )
