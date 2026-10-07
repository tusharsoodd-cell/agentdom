"""One-call pipeline: HTML -> pruned, ordered, ref-assigned tree."""

from __future__ import annotations

import time

from agentdom import render as _render
from agentdom.extract import extract_html, extract_live
from agentdom.model import Node
from agentdom.order import apply_visual_order, remove_occluded
from agentdom.prune import prune


def process(root: Node) -> Node:
    prune(root)
    remove_occluded(root)
    apply_visual_order(root)
    _render.assign_refs(root)
    return root


def represent(html: str, interactive_only: bool = False,
              max_depth: int | None = None) -> tuple[Node, str, dict, float]:
    """Parse static HTML. Returns (tree, text, json, elapsed_ms)."""
    start = time.perf_counter()
    root = process(extract_html(html))
    elapsed_ms = (time.perf_counter() - start) * 1000
    text = _render.render_tree(root, interactive_only, max_depth)
    return root, text, _render.render_json(root), elapsed_ms


def represent_live(page, interactive_only: bool = False,
                   max_depth: int | None = None) -> tuple[Node, str, dict, float]:
    """Snapshot a Playwright page. `page` is a playwright Page object."""
    start = time.perf_counter()
    root = process(extract_live(page))
    elapsed_ms = (time.perf_counter() - start) * 1000
    text = _render.render_tree(root, interactive_only, max_depth)
    return root, text, _render.render_json(root), elapsed_ms
