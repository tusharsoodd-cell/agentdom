"""Pruning: collapse boilerplate so the tree stays small and meaningful.

Stages:
  1. Drop dead subtrees (already mostly handled at extraction; belt & braces).
  2. Collapse SVG internals to a single node.
  3. Splice transparent inline nodes (folded <b>/<i>/etc.) into their parents.
  4. Remove empty wrapper divs (no name, no affordances, single child).
  5. Dedupe adjacent identical siblings (desktop/mobile nav rendered twice).
  6. Truncate long text.
"""

from __future__ import annotations

from agentdom.model import Node

MAX_NAME_LEN = 160

# Landmarks are kept even when they look empty — they orient the agent.
_LANDMARKS = {
    "navigation", "main", "banner", "contentinfo", "form", "search",
    "dialog", "alertdialog",
}


def _signature(node: Node) -> tuple:
    return (
        node.role,
        node.name,
        tuple(_signature(c) for c in node.children),
    )


def prune(root: Node) -> Node:
    _prune_children(root)
    return root


def _prune_children(node: Node) -> None:
    pruned: list[Node] = []
    for child in node.children:
        _prune_children(child)

        if child.tag == "svg" or child.role == "img" and child.tag == "svg":
            child.children = []
            child.collapsed = True
            if not child.name:
                child.name = "graphic"
            pruned.append(child)
            continue

        # Empty wrapper: generic container, no name, no affordances, one child.
        if (
            child.role == "generic"
            and not child.name
            and not child.affordances
            and len(child.children) == 1
            and child.role not in _LANDMARKS
        ):
            pruned.append(child.children[0])
            continue

        pruned.append(child)

    # Dedupe adjacent identical siblings.
    deduped: list[Node] = []
    for child in pruned:
        if deduped and _signature(deduped[-1]) == _signature(child):
            continue
        deduped.append(child)

    # Truncate long names.
    for child in deduped:
        if len(child.name) > MAX_NAME_LEN:
            child.name = child.name[:MAX_NAME_LEN].rstrip() + "…"

    node.children = deduped
