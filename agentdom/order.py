"""Visual ordering and occlusion filtering.

DOM order is not visual order — CSS can place anything anywhere. When we
have bounding boxes (live browser snapshots), children are re-sorted into
reading order (top-to-bottom rows, left-to-right within a row) so that
"the first result" means the visually-first one.

Occlusion: elements hidden underneath a modal/dialog are dropped, since an
agent that tries to click them will hit the overlay instead.
"""

from __future__ import annotations

from agentdom.model import Node

_ROW_BUCKET_PX = 24


def apply_visual_order(root: Node) -> Node:
    """Sort children recursively by visual position where bboxes exist."""
    _sort_children(root)
    return root


def _sort_children(node: Node) -> None:
    for child in node.children:
        _sort_children(child)
    if all(c.bbox is not None for c in node.children) and len(node.children) > 1:
        node.children.sort(
            key=lambda c: (int(c.bbox.y // _ROW_BUCKET_PX), c.bbox.x)
        )


def remove_occluded(root: Node) -> Node:
    """Drop nodes fully covered by a modal/dialog overlay."""
    overlay_nodes = [n for n in root.walk()
                     if n.bbox is not None
                     and (n.role in ("dialog", "alertdialog")
                          or "modal" in (n.tag + " " + n.name).lower())]
    if not overlay_nodes:
        return root
    overlay_ids = {id(n) for n in overlay_nodes}
    bboxes = [n.bbox for n in overlay_nodes]
    _drop_covered(root, bboxes, overlay_ids, False)
    return root


def _drop_covered(node: Node, overlays: list, overlay_ids: set[int],
                 inside_overlay: bool = False) -> None:
    kept = []
    for child in node.children:
        child_is_overlay = id(child) in overlay_ids
        child_inside = inside_overlay or child_is_overlay
        if child_is_overlay:
            _drop_covered(child, overlays, overlay_ids, True)
            kept.append(child)
            continue
        covered = (
            not child_inside
            and child.bbox is not None
            and any(ov.contains(child.bbox) for ov in overlays)
        )
        if covered:
            continue  # covered by the modal — not clickable in practice
        _drop_covered(child, overlays, overlay_ids, child_inside)
        kept.append(child)
    node.children = kept
