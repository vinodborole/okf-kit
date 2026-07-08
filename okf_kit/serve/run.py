"""`okf serve` entry point: bind loopback, mint a token, print a machine-readable
`ready` line for the desktop shell, then run uvicorn. Exits when the parent PID
dies (shell closed) if --parent-pid is given.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import sys
import threading
import time


def serve(*, host: str = "127.0.0.1", port: int = 0, token: str = "auto",
          ui: str | None = None, parent_pid: int | None = None) -> int:
    try:
        import uvicorn
    except ImportError:
        print("`okf serve` needs the serve extra:  pip install 'okf-kit[serve]'", file=sys.stderr)
        return 2

    from .app import create_app

    tok = secrets.token_hex(16) if token in (None, "auto", "") else token
    if port == 0:
        port = _free_port(host)

    app = create_app(tok, ui_dir=ui)
    print(json.dumps({"event": "ready", "url": f"http://{host}:{port}", "token": tok, "pid": os.getpid()}),
          flush=True)

    if parent_pid:
        _watch_parent(parent_pid)

    uvicorn.run(app, host=host, port=port, log_level="warning")
    return 0


def _free_port(host: str) -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _watch_parent(pid: int) -> None:
    def watch():
        while True:
            time.sleep(2)
            try:
                os.kill(pid, 0)
            except OSError:
                os._exit(0)

    threading.Thread(target=watch, daemon=True).start()
