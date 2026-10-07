"""Shared fixture: a small but gnarly page exercising the pipeline."""

FIXTURE_HTML = """<!DOCTYPE html>
<html>
<head>
<title>Fixture</title>
<script>var x = 1;</script>
<style>.a { color: red; }</style>
<meta name="desc" content="nope">
</head>
<body>
<header>
  <nav aria-label="Main">
    <a href="/">Home</a>
    <a href="/pricing">Pricing</a>
    <a href="/pricing">Pricing</a>
  </nav>
</header>
<main>
  <h1>Search results for "widget"</h1>
  <form role="search" action="/search">
    <input type="search" name="q" placeholder="Search widgets" aria-label="Search">
    <button type="submit">Go</button>
  </form>
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
  <div><div><div>
    <p>Deeply <b>wrapped</b> paragraph.</p>
  </div></div></div>
  <div style="display:none"><a href="/hidden">Hidden link</a></div>
  <svg viewBox="0 0 10 10"><path d="M0 0L10 10"/><circle cx="5" cy="5" r="2"/></svg>
  <select name="sort"><option>Price</option><option>Rating</option></select>
  <label><input type="checkbox" checked> In stock only</label>
</main>
<footer><p>© 2026 Fixture Inc.</p></footer>
</body>
</html>
"""
