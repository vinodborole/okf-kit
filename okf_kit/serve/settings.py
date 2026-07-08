"""User settings for `okf serve`: provider/model/base_url in ~/.okf/settings.json,
the API key in the OS keychain (via `keyring`). The key is never returned by the
API and never written into a bundle.

If no OS keychain backend is available (e.g. a headless Linux box), the key falls
back to a 0600 file in ~/.okf — still outside any bundle.
"""

from __future__ import annotations

import json
import os
import stat

from ..config import home_dir

SERVICE = "okf-kit"
_DEFAULTS = {"provider": "none", "model": None, "base_url": None}


def _settings_path():
    return home_dir() / "settings.json"


def _secrets_path():
    return home_dir() / ".secrets.json"


def load_settings() -> dict:
    p = _settings_path()
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf8"))
            return {**_DEFAULTS, **{k: data.get(k) for k in _DEFAULTS}}
        except Exception:  # noqa: BLE001 — corrupt file → defaults
            pass
    return dict(_DEFAULTS)


def save_settings(provider: str, model: str | None, base_url: str | None,
                  api_key: str | None = None) -> dict:
    _settings_path().write_text(
        json.dumps({"provider": provider, "model": model, "base_url": base_url}, indent=2),
        encoding="utf8",
    )
    if api_key:
        _store_key(provider, api_key)
    return public_settings()


def get_key(provider: str) -> str | None:
    try:
        import keyring

        val = keyring.get_password(SERVICE, provider)
        if val:
            return val
    except Exception:  # noqa: BLE001 — no backend → fall back to file
        pass
    if _secrets_path().exists():
        try:
            return json.loads(_secrets_path().read_text(encoding="utf8")).get(provider)
        except Exception:  # noqa: BLE001
            return None
    return None


def _store_key(provider: str, api_key: str) -> None:
    try:
        import keyring

        keyring.set_password(SERVICE, provider, api_key)
        return
    except Exception:  # noqa: BLE001 — no backend → 0600 file fallback
        pass
    path = _secrets_path()
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf8"))
        except Exception:  # noqa: BLE001
            data = {}
    data[provider] = api_key
    path.write_text(json.dumps(data), encoding="utf8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass


def public_settings() -> dict:
    s = load_settings()
    return {
        "provider": s["provider"],
        "model": s["model"],
        "base_url": s["base_url"],
        "has_key": bool(get_key(s["provider"])) if s["provider"] not in (None, "none") else False,
    }
