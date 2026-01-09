#!/usr/bin/env python3
"""Simple internal link crawler for the Flask panel.

- Crawls same-origin GET pages
- Extracts href/src from HTML
- Reports non-2xx/3xx responses

Usage:
  python tools/link_crawl.py http://127.0.0.1:5000/ --max-pages 200
"""

from __future__ import annotations

import argparse
import collections
import re
import sys
import urllib.parse
import urllib.request
from html.parser import HTMLParser


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {k: v for k, v in attrs}
        if tag == "a" and attr_map.get("href"):
            self.urls.append(attr_map["href"] or "")
        elif tag in {"img", "script"} and attr_map.get("src"):
            self.urls.append(attr_map["src"] or "")
        elif tag == "link" and attr_map.get("href"):
            self.urls.append(attr_map["href"] or "")


def fetch(url: str, timeout: float = 10.0) -> tuple[int, str, bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "panel-link-crawl"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", 200)
            ctype = resp.headers.get("content-type", "")
            data = resp.read()
            final_url = resp.geturl()
            return status, final_url, data, ctype
    except Exception as e:
        return 0, url, (str(e)).encode("utf-8", errors="ignore"), ""


def is_same_origin(base: urllib.parse.ParseResult, url: str) -> bool:
    p = urllib.parse.urlparse(url)
    if not p.scheme and not p.netloc:
        return True
    return (p.scheme, p.netloc) == (base.scheme, base.netloc)


def normalize(base_url: str, raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    if raw.startswith("mailto:") or raw.startswith("tel:"):
        return None
    if raw.startswith("javascript:"):
        return None
    # strip fragments
    raw = raw.split("#", 1)[0]
    if not raw:
        return None
    return urllib.parse.urljoin(base_url, raw)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("start_url")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--timeout", type=float, default=10.0)
    args = ap.parse_args()

    start = args.start_url
    base = urllib.parse.urlparse(start)

    q: collections.deque[str] = collections.deque([start])
    seen: set[str] = set()
    failures: list[tuple[int, str]] = []

    while q and len(seen) < args.max_pages:
        url = q.popleft()
        if url in seen:
            continue
        if not is_same_origin(base, url):
            continue
        seen.add(url)

        status, final_url, data, ctype = fetch(url, timeout=args.timeout)
        if status == 0 or status >= 400:
            failures.append((status, url))
            continue

        if "text/html" in ctype:
            parser = LinkParser()
            try:
                parser.feed(data.decode("utf-8", errors="ignore"))
            except Exception:
                pass

            for raw in parser.urls:
                nxt = normalize(final_url, raw)
                if not nxt:
                    continue
                if not is_same_origin(base, nxt):
                    continue
                # Avoid crawling logout endpoints or destructive actions
                if re.search(r"/logout$", nxt):
                    continue
                q.append(nxt)

    if failures:
        print("FAILURES:")
        for st, u in sorted(failures, key=lambda x: (x[0], x[1])):
            print(f"  {st:>3}  {u}")
        print(f"\nVisited {len(seen)} pages, failures {len(failures)}")
        return 2

    print(f"OK: visited {len(seen)} pages, no 4xx/5xx")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
