#!/usr/bin/env python3
"""Benchmark: raw HTML vs agentdom tree vs agentdom JSON.

For each page, measures:
  - size: characters and estimated tokens (chars / 4)
  - structure: node/element counts
  - extraction latency (ms)
  - answerability: fraction of agent tasks whose target is present AND
    (for "act" tasks) actionable via a stable ref.

Usage:
    python bench/run.py [--live] [--out bench/results.md]

Default runs against saved fixtures (fast, deterministic). --live refetches
each page first.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agentdom.pipeline import represent
from bench.pages import PAGES

HERE = Path(__file__).resolve().parent


def fetch(url: str) -> str:
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (agentdom/0.1)"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def count_elements(html: str) -> int:
    return len(re.findall(r"<[a-zA-Z][^>]*>", html))


def bench_page(page, html: str) -> dict:
    raw_chars = len(html)
    results: dict = {"page": page.name, "formats": {}}

    # raw HTML baseline
    t0 = time.perf_counter()
    n_elements = count_elements(html)
    parse_ms = (time.perf_counter() - t0) * 1000
    raw_scores = []
    for task in page.tasks:
        if task.kind == "act":
            raw_scores.append(False)  # no refs in raw HTML — can't act
        else:
            raw_scores.append(bool(re.search(task.html_probe, html, re.S | re.I)))
    results["formats"]["raw html"] = {
        "chars": raw_chars,
        "tokens": raw_chars // 4,
        "nodes": n_elements,
        "extract_ms": round(parse_ms, 1),
        "answerability": f"{sum(raw_scores)}/{len(raw_scores)}",
        "score": round(sum(raw_scores) / len(raw_scores), 2),
    }

    # agentdom tree + json share one extraction
    root, tree_text, as_json, extract_ms = represent(html)
    n_nodes = sum(1 for _ in root.walk())
    tree_chars = len(tree_text)
    json_chars = len(json.dumps(as_json))

    # interactive-only tree: the acting-optimized view
    _, itree_text, _, _ = represent(html, interactive_only=True)
    itree_chars = len(itree_text)
    itree_nodes = sum(1 for line in itree_text.splitlines() if line.strip())

    for fmt, chars, nodes in (("tree", tree_chars, n_nodes),
                              ("json", json_chars, n_nodes),
                              ("tree (interactive)", itree_chars, itree_nodes)):
        scores = [bool(task.check(root)) for task in page.tasks]
        results["formats"][fmt] = {
            "chars": chars,
            "tokens": chars // 4,
            "nodes": nodes,
            "extract_ms": round(extract_ms, 1),
            "answerability": f"{sum(scores)}/{len(scores)}",
            "score": round(sum(scores) / len(scores), 2),
        }
    results["reduction_tree"] = round(raw_chars / max(tree_chars, 1), 1)
    results["reduction_json"] = round(raw_chars / max(json_chars, 1), 1)
    results["reduction_itree"] = round(raw_chars / max(itree_chars, 1), 1)
    return results


def markdown_table(all_results: list[dict]) -> str:
    lines = [
        "# agentdom benchmark",
        "",
        "Estimated tokens = characters / 4. Answerability = tasks whose target",
        "is present and (for action tasks) clickable via a stable ref.",
        "",
        "| page | format | tokens | nodes | extract ms | answerability |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for r in all_results:
        for fmt in ("raw html", "tree", "tree (interactive)", "json"):
            f = r["formats"][fmt]
            lines.append(
                f"| {r['page']} | {fmt} | {f['tokens']:,} | {f['nodes']:,} "
                f"| {f['extract_ms']} | {f['answerability']} |"
            )
    lines += [
        "",
        "## Size reduction (raw HTML -> representation)",
        "",
        "| page | -> tree | -> tree (interactive) | -> json |",
        "| --- | ---: | ---: | ---: |",
    ]
    for r in all_results:
        lines.append(
            f"| {r['page']} | {r['reduction_tree']}x | {r['reduction_itree']}x "
            f"| {r['reduction_json']}x |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="refetch pages instead of using fixtures")
    parser.add_argument("--out", default=str(HERE / "results.md"))
    args = parser.parse_args()

    all_results = []
    for page in PAGES:
        fixture = HERE / "fixtures" / page.fixture
        if args.live:
            print(f"fetching {page.url} ...", flush=True)
            html = fetch(page.url)
            fixture.write_text(html, encoding="utf-8")
        else:
            html = fixture.read_text(encoding="utf-8")
        print(f"benching {page.name} ({len(html):,} chars) ...", flush=True)
        all_results.append(bench_page(page, html))

    report = markdown_table(all_results)
    print(report)
    Path(args.out).write_text(report, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
