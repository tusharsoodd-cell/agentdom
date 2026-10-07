"""Extraction: DOM/HTML -> semantic Node tree.

Two entry points:
  extract_html(html)   parse static HTML (no browser needed; no bounding boxes)
  extract_live(page)   snapshot a Playwright page (rendered DOM, with bboxes)

Both produce the same Node tree shape; downstream stages (prune, order,
render) are shared.
"""

from __future__ import annotations

from html.parser import HTMLParser

from agentdom.model import BBox, Node

# Tags whose content is never meaningful to an agent.
_DEAD_TAGS = {
    "script", "style", "noscript", "template", "head", "meta", "link",
    "title", "base", "source",
}

# Void elements: never have children, don't wait for a close tag.
_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}

_ROLE_BY_TAG = {
    "a": "link",
    "button": "button",
    "input": "textbox",   # refined by type below
    "select": "combobox",
    "textarea": "textbox",
    "img": "img",
    "h1": "heading", "h2": "heading", "h3": "heading",
    "h4": "heading", "h5": "heading", "h6": "heading",
    "p": "paragraph",
    "ul": "list", "ol": "list",
    "li": "listitem",
    "nav": "navigation",
    "main": "main",
    "header": "banner",
    "footer": "contentinfo",
    "form": "form",
    "table": "table",
    "tr": "row",
    "td": "cell", "th": "cell",
    "label": "label",
    "svg": "img",
}

_INPUT_ROLE = {
    "text": "textbox", "password": "textbox", "email": "textbox",
    "search": "searchbox", "tel": "textbox", "url": "textbox",
    "number": "spinbutton",
    "checkbox": "checkbox", "radio": "radio",
    "submit": "button", "button": "button", "reset": "button",
    "file": "button", "hidden": None,
}

_CONTAINER_TAGS = {
    "div", "span", "section", "article", "aside", "body", "html",
    "figure", "figcaption", "blockquote", "details", "summary",
}


class _DOMBuilder(HTMLParser):
    """Builds a nested dict tree from HTML, skipping dead tags entirely.

    Each node: {"tag", "attrs", "parts"} where parts preserves document
    order and holds either text strings or child node dicts.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = {"tag": "root", "attrs": {}, "parts": []}
        self._stack = [self.root]
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in _DEAD_TAGS:
            # Void dead tags (<meta>, <link>) have no end tag; don't let them
            # swallow the rest of the document.
            if tag not in _VOID_TAGS:
                self._skip_depth += 1
            return
        if self._skip_depth:
            return
        node = {"tag": tag, "attrs": dict(attrs), "parts": []}
        self._stack[-1]["parts"].append(node)
        if tag not in _VOID_TAGS:
            self._stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in _DEAD_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        # Pop until we find the matching open tag (tolerates sloppy HTML).
        for i in range(len(self._stack) - 1, 0, -1):
            if self._stack[i]["tag"] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            parts = self._stack[-1]["parts"]
            if parts and isinstance(parts[-1], str):
                parts[-1] = parts[-1] + " " + text
            else:
                parts.append(text)


def _accessible_name(tag: str, attrs: dict, text: str,
                    has_element_children: bool = False) -> str:
    # Precedence follows the accessible-name computation: explicit labels
    # first, then content, with title as a last resort. When the element
    # wraps other elements, the name comes from their content instead.
    if attrs.get("aria-label"):
        return attrs["aria-label"].strip()
    if tag == "img" and attrs.get("alt"):
        return attrs["alt"].strip()
    if tag == "input":
        if attrs.get("placeholder"):
            return attrs["placeholder"].strip()
        if attrs.get("value") and attrs.get("type") not in ("submit", "button"):
            return attrs["value"].strip()
    if text:
        return text.strip()
    if attrs.get("title") and not has_element_children:
        return attrs["title"].strip()
    return ""


def _role_and_affordances(tag: str, attrs: dict) -> tuple[str | None, set[str]]:
    """Returns (role, affordances). Role None means 'not a semantic node'."""
    if attrs.get("role"):
        role = attrs["role"].strip().lower()
    elif tag == "input":
        role = _INPUT_ROLE.get(attrs.get("type", "text").lower(), "textbox")
        if role is None:
            return None, set()
    else:
        role = _ROLE_BY_TAG.get(tag)

    if role is None:
        # Plain containers stay in the tree as structure; anything else is
        # dropped (e.g. stray <b>, <i> with no text are folded into parents).
        if tag in _CONTAINER_TAGS:
            return "generic", set()
        return None, set()

    affordances: set[str] = set()
    if role in ("button", "link"):
        affordances.add("click")
    elif role in ("textbox", "searchbox", "spinbutton"):
        affordances.add("type")
    elif role == "combobox":
        affordances.add("select")
    elif role in ("checkbox", "radio"):
        affordances.add("check")
    # clickable divs/spans are common in the wild
    if attrs.get("onclick") or attrs.get("tabindex") == "0":
        affordances.add("click")
        if role == "generic":
            role = "button"
    return role, affordances


def _subtree_text(node: Node) -> str:
    """Concatenated text of a node and its descendants, in order."""
    bits = [node.name] if node.name else []
    for child in node.children:
        text = _subtree_text(child)
        if text:
            bits.append(text)
    return " ".join(bits)


def _build_node(dom: dict) -> Node | None:
    tag = dom["tag"]
    attrs = dom["attrs"]
    if attrs.get("aria-hidden") == "true" or "hidden" in attrs:
        return None
    style = attrs.get("style", "").replace(" ", "").lower()
    if "display:none" in style or "visibility:hidden" in style:
        return None

    role, affordances = _role_and_affordances(tag, attrs)

    # Build children in document order; transparent inline nodes are spliced
    # here so their text lands in the right position.
    children: list[Node] = []
    text_segs: list[str] = []
    for part in dom["parts"]:
        if isinstance(part, str):
            text_segs.append(part)
        else:
            child = _build_node(part)
            if child is None:
                continue
            if child.role == "transparent":
                if child.name:
                    text_segs.append(child.name)
                children.extend(child.children)
            else:
                children.append(child)
    inner_text = " ".join(text_segs)

    if role is None:
        # Non-semantic inline tag: bubble its text and children up.
        if not children and not inner_text:
            return None
        return Node(role="transparent", name=inner_text, tag=tag,
                    children=children)

    name = _accessible_name(tag, attrs, inner_text,
                            has_element_children=bool(children))
    href = attrs.get("href", "") if tag == "a" else ""
    node = Node(role=role, name=name, tag=tag, affordances=affordances,
                href=href, children=children)
    if not name and role in ("link", "button", "heading"):
        # ARIA "name from content": a link/button wrapping markup (e.g.
        # <a><span>Techniques</span></a>) takes its name from descendants.
        node.name = _subtree_text(node)
    raw_bbox = dom.get("bbox")
    if raw_bbox:
        x, y, w, h = raw_bbox
        node.bbox = BBox(x, y, w, h) if w > 0 and h > 0 else None
    return node


def extract_html(html: str) -> Node:
    """Parse static HTML into a semantic tree (no bounding boxes)."""
    builder = _DOMBuilder()
    builder.feed(html)
    builder.close()
    root = Node(role="root", tag="root")
    for part in builder.root["parts"]:
        if isinstance(part, str):
            continue
        node = _build_node(part)
        if node is not None:
            root.children.append(node)
    return root


_LIVE_SNAPSHOT_JS = """() => {
  function snap(el, depth) {
    if (depth > 60) return null;
    const tag = el.tagName.toLowerCase();
    if (['script','style','noscript','template','head','meta','link','title'].includes(tag)) return null;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') return null;
    const r = el.getBoundingClientRect();
    // parts preserve document order: text segments and child snapshots
    const parts = [];
    for (const n of el.childNodes) {
      if (n.nodeType === 3) {
        const t = n.textContent.trim().replace(/\\s+/g, ' ');
        if (t) parts.push(t);
      } else if (n.nodeType === 1) {
        const s = snap(n, depth + 1);
        if (s) parts.push(s);
      }
    }
    const attrs = {};
    for (const a of el.attributes) {
      if (['role','aria-label','href','type','placeholder','value','alt','title','id','class','tabindex','onclick'].includes(a.name))
        attrs[a.name] = a.value;
    }
    return {tag, attrs, parts, bbox: [r.x, r.y, r.width, r.height]};
  }
  return snap(document.body || document.documentElement, 0);
}"""


def extract_live(page) -> Node:
    """Snapshot a Playwright page into a semantic tree (with bounding boxes).

    `page` is a playwright.sync_api.Page (or async — call from async code).
    """
    snap = page.evaluate(_LIVE_SNAPSHOT_JS)
    root = Node(role="root", tag="root")
    node = _live_to_node(snap)
    if node is not None:
        root.children.append(node)
    return root


def _live_to_node(snap: dict) -> Node | None:
    if snap is None:
        return None
    return _build_node(snap)
