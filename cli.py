#!/usr/bin/env python3
"""agentdom CLI: render a web page as an AI-first representation.

    agentdom render <url> [--format tree|json] [--interactive-only] [--max-depth N]
    agentdom render --from-file page.html [options]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

from agentdom.pipeline import represent


def fetch_html(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (agentdom/0.1)"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentdom",
        description="Render a web page as a compact, actionable representation for AI agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    render = sub.add_parser("render", help="Render a page to stdout.")
    render.add_argument("url", nargs="?",
                        help="URL to render (or omit with --from-file).")
    render.add_argument("--from-file", metavar="PATH",
                        help="Render a saved HTML file instead of fetching a URL.")
    render.add_argument("--format", choices=["tree", "json"], default="tree")
    render.add_argument("--interactive-only", action="store_true",
                        help="Show only interactive elements and their containers.")
    render.add_argument("--max-depth", type=int, default=None)

    args = parser.parse_args(argv)

    if args.command == "render":
        if args.from_file:
            with open(args.from_file, encoding="utf-8", errors="replace") as f:
                html = f.read()
        elif args.url:
            try:
                html = fetch_html(args.url)
            except Exception as exc:  # noqa: BLE001 — CLI surface, report cleanly
                print(f"error: could not fetch {args.url}: {exc}", file=sys.stderr)
                return 1
        else:
            print("error: provide a URL or --from-file", file=sys.stderr)
            return 1

        _, text, as_json, elapsed_ms = represent(
            html, interactive_only=args.interactive_only, max_depth=args.max_depth
        )
        if args.format == "json":
            print(json.dumps(as_json, indent=1))
        else:
            print(text)
        print(f"\n# extracted in {elapsed_ms:.0f} ms", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
