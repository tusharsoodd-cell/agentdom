"""agentdom — AI-first web page representation.

Turns a rendered (or static) web page into a compact, semantic, actionable
projection that an AI agent can reason over and click through, at a fraction
of the token cost of raw HTML.
"""

from agentdom.pipeline import represent, represent_live

__all__ = ["represent", "represent_live"]
__version__ = "0.1.0"
