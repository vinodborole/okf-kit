"""Write crawled pages into an OKF bundle directory.

The output directory *is* the bundle:

    <bundle>/
        index.md                 root directory listing (reserved)
        log.md                   generation/sync history (reserved)
        pages/                   one concept per page (frontmatter + body)
            index.md
            home.md
            docs/...
        .okf-kit/state.json      crawl config + per-page content hashes (sync)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath

from .config import STATE_DIRNAME, STATE_FILENAME
from .mapper import url_to_relpath
from .model import Page, PageRecord, utcnow_iso
from .okf import (
    dodge_reserved,
    frontmatter,
    write_directory_indexes,
    write_root_index,
)


class BundleWriter:
    def __init__(self, bundle_dir):
        self.bundle_dir = Path(bundle_dir)
        self.pages_dir = self.bundle_dir / "pages"
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.records: list[PageRecord] = []
        self._seen: set[str] = set()

    def write_page(self, page: Page, timestamp: str) -> PageRecord | None:
        body = page.markdown.strip()
        if not body:
            return None

        rel = dodge_reserved(url_to_relpath(page.url).with_suffix(".md"))
        bundle_rel = PurePosixPath("pages") / rel
        key = str(bundle_rel)
        if key in self._seen:  # e.g. / and /index.html both map to pages/home.md
            return None
        self._seen.add(key)

        fm = frontmatter(
            {
                "type": "Web Page",
                "title": page.title,
                "description": page.description,
                "resource": page.url,
                "timestamp": timestamp,
            }
        )
        content = f"{fm}\n{body}\n\n# Citations\n\n1. Source page: {page.url}\n"

        dest = self.bundle_dir / bundle_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf8")

        record = PageRecord(
            path=key,
            url=page.url,
            title=page.title,
            content_hash=hashlib.sha256(page.markdown.encode("utf8")).hexdigest(),
        )
        self.records.append(record)
        return record

    def finalize(self, *, root_url: str, config: dict) -> None:
        entries = {
            PurePosixPath(r.path): (r.title or PurePosixPath(r.path).stem)
            for r in self.records
        }
        write_directory_indexes(self.bundle_dir, entries)
        write_root_index(self.bundle_dir, root_url, len(self.records))

        (self.bundle_dir / "log.md").write_text(
            f"# Log\n\n## {utcnow_iso()[:10]}\n\n"
            f"- Built by okf-kit from {root_url}: {len(self.records)} pages.\n",
            encoding="utf8",
        )

        state_dir = self.bundle_dir / STATE_DIRNAME
        state_dir.mkdir(exist_ok=True)
        (state_dir / STATE_FILENAME).write_text(
            json.dumps(
                {
                    "generator": "okf-kit",
                    "okf_version": "0.1",
                    "root_url": root_url,
                    "built_at": utcnow_iso(),
                    "config": config,
                    "page_count": len(self.records),
                    "pages": [
                        {"path": r.path, "url": r.url, "title": r.title, "hash": r.content_hash}
                        for r in sorted(self.records, key=lambda r: r.path)
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf8",
        )
