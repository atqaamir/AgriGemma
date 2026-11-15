"""
Web search utility for the chatbot's GENERAL intent pipeline.

Uses DuckDuckGo (no API key required). Results are injected as context
snippets so Gemma can synthesise an answer grounded in recent information.
"""

import logging

logger = logging.getLogger(__name__)

_MAX_SNIPPET = 300   # chars per result snippet — keeps token cost low
TIMEOUT_S = 3.0      # the answer never waits longer than this for the web


def search(query: str, max_results: int = 5) -> list[dict]:
    """search() with a hard time limit (TIMEOUT_S): [] if the web is slower."""
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as _Timeout
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_search, query, max_results)
    try:
        return future.result(timeout=TIMEOUT_S)
    except _Timeout:
        logger.warning("[WEB-SEARCH] '%s' → no results within %.0f s, answering without", query, TIMEOUT_S)
        return []
    finally:
        pool.shutdown(wait=False)


def _search(query: str, max_results: int = 5) -> list[dict]:
    """
    Search DuckDuckGo and return up to max_results snippets.
    Each item: {"title": str, "snippet": str, "url": str}
    Returns [] on any failure — caller must handle gracefully.
    """
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            raw = list(ddgs.text(query, max_results=max_results))
        results = []
        for r in raw:
            snippet = (r.get("body") or "").strip()
            if len(snippet) > _MAX_SNIPPET:
                snippet = snippet[:_MAX_SNIPPET].rsplit(" ", 1)[0] + "…"
            results.append({
                "title":   (r.get("title") or "").strip(),
                "snippet": snippet,
                "url":     (r.get("href")  or "").strip(),
            })
        logger.info("[WEB-SEARCH] '%s' → %d results", query, len(results))
        return results
    except ImportError:
        logger.warning("[WEB-SEARCH] ddgs not installed — run: pip install ddgs")
        return []
    except Exception as exc:
        logger.warning("[WEB-SEARCH] search failed: %s", exc)
        return []
