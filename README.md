# agentdom

**An AI-first representation of web pages — built for agents that act, not just read.**

Raw HTML is a terrible observation format for an AI agent: it's 10–100x more tokens than needed, it buries the three things an acting agent actually needs (which elements are interactive, what actions they afford, and what order they appear in visually), and it has no stable way to say "click *that* one."

## Why not the existing tools?

The current ecosystem solves the **reading** case:

- **llms.txt / markdown converters / Jina Reader** turn pages into clean markdown for *content extraction*. Great for RAG, useless when the agent needs to click "Add to cart" — markdown has no element identities.
- **Screenshots** show the agent what the page looks like, but a model can't reliably map pixels back to something clickable without extra grounding machinery.
- **Accessibility trees** (Playwright's `ariaSnapshot`, Chrome's AXTree) are the closest prior art, and agentdom builds on their ideas — but they're verbose, unpruned, DOM-ordered rather than visually ordered, and they don't distinguish the acting-optimized view from the reading view.

agentdom targets the **acting** case: a compact, semantic, actionable projection of a page. Every element gets a stable numbered ref (`[13]`), interactive elements declare their affordances (`click`, `type`, `select`, `check`), boilerplate is pruned, and nodes are ordered the way they appear on screen — so "click the first result" means the *visually* first one.

## Example

Raw HTML in:

```html
<ul>
  <li>
    <a href="/w/1">Widget One</a>
    <span class="price">$19.99</span>
    <button onclick="add(1)">Add to cart</button>
  </li>
  <li>
    <a href="/w/2">Widget Two</a>
    <span class="price">$29.99</span>
    <button onclick="add(2)">Add to cart</button>
  </li>
</ul>
```

agentdom out (`--interactive-only`):

```
[11] list
  [12] listitem
    [13] link "Widget One" -> /w/1
    [15] button "Add to cart"
  [16] listitem
    [17] link "Widget Two" -> /w/2
    [19] button "Add to cart"
```

An agent can now answer "add the second widget to the cart" with `click [19]` — no CSS selectors, no pixel coordinates, no parsing 40KB of divs.

## Architecture

```
agentdom/
  extract.py   DOM/HTML -> semantic Node tree (roles, accessible names, affordances)
               two entry points: extract_html() for static HTML,
               extract_live() for a Playwright page (rendered DOM + bounding boxes)
  prune.py     collapse boilerplate: scripts/styles/hidden nodes, SVG internals,
               empty wrapper divs, duplicate subtrees; truncate long text
  order.py     visual ordering from bounding boxes (row-bucketed reading order);
               drop elements occluded by modal/dialog overlays
  render.py    assign stable DFS refs; render indented text tree or structured JSON
  pipeline.py  one-call represent() / represent_live()
cli.py         agentdom render <url> [--format tree|json] [--interactive-only] [--max-depth N]
               agentdom render --from-file page.html   # offline, no browser needed
bench/         benchmark harness: pages, tasks, fixtures, results
```

Key design decisions:

- **Accessible-name computation** follows the ARIA precedence (aria-label → content → title as last resort), including "name from content" for links/buttons that wrap markup (`<a><span>Techniques</span></a>` → `"2 Techniques"`).
- **Transparent inline elements** (`<b>`, `<i>`, …) are spliced at build time so their text lands in document order — `<p>Deeply <b>wrapped</b> text</p>` keeps "Deeply wrapped text", not "Deeply text".
- **Refs are stable**: same page in → same refs out, assigned in DFS pre-order.

## Benchmarks

`bench/run.py` compares three representations of the same pages — raw HTML, the agentdom tree, and agentdom JSON — on size and on **answerability**: 11 small agent tasks ("find the search box", "find the link to submit a story", …). An "act" task only passes if the target is present *and* clickable via a stable ref, which raw HTML can never do.

Measured 2026-10-07 on static HTML snapshots (Wikipedia article, Hacker News front page, wikipedia.org portal). Tokens estimated as chars/4.

| page | format | tokens | answerability |
| --- | --- | --- | --- |
| Wikipedia article | raw HTML | 58,869 | 1/4 |
| Wikipedia article | agentdom tree | 24,582 | 4/4 |
| Wikipedia article | tree (interactive-only) | 17,242 | 4/4 |
| Hacker News front page | raw HTML | 8,664 | 0/4 |
| Hacker News front page | agentdom tree | 7,874 | 4/4 |
| Hacker News front page | tree (interactive-only) | 5,886 | 4/4 |
| Wikipedia portal | raw HTML | 22,961 | 1/3 |
| Wikipedia portal | agentdom tree | 8,894 | 3/3 |
| Wikipedia portal | tree (interactive-only) | 8,065 | 3/3 |

**11/11 tasks answerable with refs vs 2/11 for raw HTML.** Extraction runs in 35–110 ms per page on static HTML.

Two honest notes on the numbers. First, the size reductions here (1.1–3.4x) are modest compared to the 17–105x reported by the browser-agent observation benchmark — because those compare against *rendered* page DOMs (hydrated app state, injected scripts, far heavier than static HTML), which is exactly what agentdom's live Playwright path targets; I couldn't run a browser in this environment, so these numbers are the static-HTML floor. Second, JSON is larger than the tree — it's the machine-parseable mode, not the token-saving mode.

Run it yourself: `python bench/run.py` (uses saved fixtures) or `python bench/run.py --live` to refetch.

## Tradeoffs

- **Text tree vs JSON**: the tree is for LLM prompts (token-cheap, human-scannable); JSON is for code that needs to walk the structure programmatically.
- **Full tree vs interactive-only**: the full tree keeps content text (needed for "find the price" style questions); interactive-only is the acting-optimized view (smaller, but content questions fail).
- **Static HTML vs live browser**: static parsing is fast and dependency-light but sees no JS-rendered content and no bounding boxes (visual ordering falls back to DOM order). The live path costs a browser but gets real geometry, occlusion filtering, and rendered content.

## Setup

```bash
pip install -r requirements.txt
python -m playwright install chromium   # only needed for the live path

# render a live URL (static fetch; use extract_live() with Playwright for rendered pages)
python cli.py render https://news.ycombinator.com --interactive-only

# render a saved page offline
python cli.py render --from-file page.html --format json | head -50

# tests and bench
python -m pytest tests/ -q
python bench/run.py
```

As a library:

```python
from agentdom.pipeline import represent

root, text, as_json, ms = represent(html)
print(text)  # the indented tree with [refs]
```

## Limitations

- **Canvas-heavy pages**: anything drawn on `<canvas>` (games, maps, charts) is invisible — there's no DOM to project. Screenshots + grounding remain the answer there.
- **Shadow DOM**: web components' shadow roots aren't traversed by the static parser; the live path sees them only if the snapshot script pierces them (not yet implemented).
- **JS-gated content**: the static path sees what the server sent. SPAs that render client-side need the live Playwright path.
- **Visual ordering needs a browser**: without bounding boxes, order falls back to DOM order, which CSS can contradict.
- **Occlusion heuristic is simple**: bounding-box containment against dialog/modal overlays; it won't catch every stacking-context trick.

## What I'd do next

Pierce shadow DOM in the live snapshot script, add a `--screenshots` comparison mode that pairs the tree with annotated screenshots, and grow the bench task set toward full MiniWoB-style task completion with a real agent loop.
