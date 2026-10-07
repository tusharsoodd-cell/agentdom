import json

from agentdom.pipeline import represent
from tests.fixture import FIXTURE_HTML


def tree():
    root, text, as_json, _ = represent(FIXTURE_HTML)
    return root, text, as_json


def test_extracts_interactive_elements():
    root, text, _ = tree()
    nodes = list(root.walk())
    by_role = {}
    for n in nodes:
        by_role.setdefault(n.role, []).append(n)
    assert len(by_role["link"]) >= 4          # nav + product links
    assert len(by_role["button"]) >= 3        # Go + 2x Add to cart
    assert any(n.role == "searchbox" for n in nodes)
    assert any(n.role == "combobox" for n in nodes)
    assert any(n.role == "checkbox" for n in nodes)


def test_pruning_removes_boilerplate():
    root, text, _ = tree()
    assert "var x = 1" not in text
    assert "Hidden link" not in text          # display:none dropped
    assert "<path" not in text                # svg internals collapsed
    names = [n.name for n in root.walk()]
    assert sum(1 for x in names if x == "Pricing") == 1  # duplicate link deduped


def test_empty_wrappers_spliced():
    root, text, _ = tree()
    assert "Deeply" in text and "wrapped" in text
    # the triple-nested divs should not each appear as a node
    generics = [n for n in root.walk() if n.role == "generic"]
    assert len(generics) <= 3


def test_refs_stable_across_runs():
    _, text1, _ = tree()
    _, text2, _ = tree()
    assert text1 == text2


def test_json_validates():
    _, _, as_json = tree()
    blob = json.dumps(as_json)
    back = json.loads(blob)
    ids = []

    def collect(n):
        ids.append(n["id"])
        assert "role" in n and "name" in n
        for c in n.get("children", []):
            collect(c)

    collect(back)
    assert ids == sorted(ids)                # DFS pre-order
    assert len(set(ids)) == len(ids)         # unique


def test_interactive_only_mode():
    root, text, _, _ = represent(FIXTURE_HTML, interactive_only=True)
    assert "Add to cart" in text
    assert "© 2026" not in text              # footer paragraph has no affordance


def test_link_hrefs_survive():
    root, _, _ = tree()
    links = {n.name: n.href for n in root.walk() if n.role == "link"}
    assert links.get("Widget One") == "/w/1"
