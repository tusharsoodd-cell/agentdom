"""The semantic node model: one node per meaningful page element."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BBox:
    """Viewport-relative bounding box in CSS pixels (None when unknown,
    e.g. when parsing static HTML without a browser)."""

    x: float
    y: float
    width: float
    height: float

    @property
    def cx(self) -> float:
        return self.x + self.width / 2

    @property
    def cy(self) -> float:
        return self.y + self.height / 2

    def contains(self, other: "BBox") -> bool:
        return (
            self.x <= other.x
            and self.y <= other.y
            and self.x + self.width >= other.x + other.width
            and self.y + self.height >= other.y + other.height
        )


@dataclass
class Node:
    """A semantic element in the agent-facing projection of a page."""

    role: str                       # e.g. "button", "link", "heading", "textbox"
    name: str = ""                  # accessible name / visible text
    tag: str = ""                   # original HTML tag, for debugging
    affordances: set[str] = field(default_factory=set)  # click, type, select, check
    bbox: Optional[BBox] = None
    href: str = ""                  # for links
    collapsed: bool = False         # True if children were pruned away (e.g. SVG)
    ref: int = -1                   # stable reference id, assigned at render time
    children: list["Node"] = field(default_factory=list)

    @property
    def interactive(self) -> bool:
        return bool(self.affordances)

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()
