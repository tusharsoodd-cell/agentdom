"""Benchmark pages and agent-task definitions.

Tasks are small, deterministic proxies for what a browser agent needs:
- "info" tasks: is the answer present in the representation?
- "act" tasks: is there an unambiguous actionable reference (a numbered ref
  the agent could click/type into)? Raw HTML has no refs, so it can never
  pass an "act" task — which is exactly the point.

Each task carries two probes:
- html_probe: a regex searched in the raw HTML (the fair baseline for the
  "can an agent read this out of the HTML firehose?" question).
- check: a semantic predicate over the agentdom tree (used for both the
  text-tree and JSON formats).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable


def _nodes(root):
    return list(root.walk())


def has_link(root, pattern: str) -> bool:
    rx = re.compile(pattern, re.I)
    return any(n.role == "link" and n.interactive and rx.search(n.name or "")
               for n in _nodes(root))


def has_role(root, role: str, name_pattern: str = "") -> bool:
    rx = re.compile(name_pattern or ".*", re.I)
    return any(n.role == role and rx.search(n.name or "") for n in _nodes(root))


def has_text(root, pattern: str) -> bool:
    rx = re.compile(pattern, re.I)
    return any(rx.search(n.name or "") for n in _nodes(root))


@dataclass
class Task:
    desc: str
    kind: str  # "info" or "act"
    html_probe: str = ""          # regex for the raw-HTML baseline
    check: Callable = field(default=lambda r: False, repr=False)  # root -> bool


@dataclass
class Page:
    name: str
    url: str
    fixture: str
    tasks: list[Task]


PAGES = [
    Page(
        name="Wikipedia article",
        url="https://en.wikipedia.org/wiki/Web_scraping",
        fixture="wikipedia.html",
        tasks=[
            Task("find the search box", "act",
                 html_probe=r"<input[^>]*search",
                 check=lambda r: has_role(r, "searchbox")),
            Task("find the article title", "info",
                 html_probe=r"<h1[^>]*>.*?Web scraping",
                 check=lambda r: has_text(r, r"^web scraping$")),
            Task("find a TOC link to the 'Techniques' section", "act",
                 html_probe=r'href="#Techniques"',
                 check=lambda r: has_link(r, r"techniques")),
            Task("find the 'View history' tab", "act",
                 html_probe=r"View history",
                 check=lambda r: has_link(r, r"view history")),
        ],
    ),
    Page(
        name="Hacker News front page",
        url="https://news.ycombinator.com",
        fixture="hackernews.html",
        tasks=[
            Task("find a link to a story's comment thread", "act",
                 html_probe=r"item\?id=\d+",
                 check=lambda r: any(
                     n.role == "link" and "item?id=" in n.href
                     for n in _nodes(r))),
            Task("find the 'new comments' link", "act",
                 html_probe=r"newcomments",
                 check=lambda r: any(
                     n.role == "link" and "newcomments" in n.href
                     for n in _nodes(r))),
            Task("find the login link", "act",
                 html_probe=r"login",
                 check=lambda r: has_link(r, r"^login$")),
            Task("find the link to submit a new story", "act",
                 html_probe=r"submit",
                 check=lambda r: has_link(r, r"submit")),
        ],
    ),
    Page(
        name="Wikipedia portal",
        url="https://www.wikipedia.org/",
        fixture="wikipedia-portal.html",
        tasks=[
            Task("find the search box", "act",
                 html_probe=r'<input[^>]*name="search"',
                 check=lambda r: has_role(r, "searchbox")),
            Task("find the English language edition link", "act",
                 html_probe=r"English",
                 check=lambda r: has_link(r, r"^english$")),
            Task("find the site tagline", "info",
                 html_probe=r"free encyclopedia",
                 check=lambda r: has_text(r, r"free encyclopedia")),
        ],
    ),
]
