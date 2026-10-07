"""Rendering: semantic tree -> text tree or structured JSON.

Refs are assigned in DFS pre-order and are stable for a given tree:
the same page produces the same refs on every run.
"""

from __future__ import annotations

from agentdom.model import Node


def assign_refs(root: Node) -> None:
    counter = [0]

    def visit(node: Node) -> None:
        node.ref = counter[0]
        counter[0] += 1
        for child in node.children:
            visit(child)

    visit(root)


def _node_label(node: Node) -> str:
    label = f"[{node.ref}] {node.role}"
    if node.name:
        label += f' "{node.name}"'
    if node.role == "link" and node.href:
        label += f" -> {node.href}"
    if node.collapsed:
        label += " (collapsed)"
    return label


def render_tree(root: Node, interactive_only: bool = False,
                max_depth: int | None = None) -> str:
    lines: list[str] = []

    def visit(node: Node, depth: int) -> None:
        if max_depth is not None and depth > max_depth:
            return
        show = node.role != "root" and (
            not interactive_only or node.interactive
            or any(c.interactive or _has_interactive(c) for c in node.children)
        )
        if show:
            lines.append("  " * depth + _node_label(node))
        for child in node.children:
            visit(child, depth + (1 if show else 0))

    visit(root, 0)
    return "\n".join(lines)


def _has_interactive(node: Node) -> bool:
    return any(c.interactive or _has_interactive(c) for c in node.children)


def render_json(root: Node) -> dict:
    def convert(node: Node) -> dict:
        out = {
            "id": node.ref,
            "role": node.role,
            "name": node.name,
        }
        if node.affordances:
            out["affordances"] = sorted(node.affordances)
        if node.href:
            out["href"] = node.href
        if node.bbox is not None:
            out["bbox"] = [round(node.bbox.x), round(node.bbox.y),
                           round(node.bbox.width), round(node.bbox.height)]
        if node.children:
            out["children"] = [convert(c) for c in node.children]
        return out

    return convert(root)
