"""
Team Logo Resolver – TheSportsDB lookup with persistent JSON cache.

Usage:
    from team_logo_resolver import get_logo_url, enrich_matches_with_logos

Single lookup:
    url = get_logo_url("Arsenal")           # -> "https://…/Arsenal.png" or None

Batch (in-place, adds home_logo_url / away_logo_url):
    enrich_matches_with_logos(matches)
"""

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
_API_KEY = os.environ.get("THESPORTSDB_API_KEY", "3")  # free tier key
_CACHE_FILE = Path(__file__).with_name("team_logos_cache.json")
_CACHE_TTL = 7 * 24 * 3600  # 7 days
_REQUEST_TIMEOUT = 6  # seconds
_NEGATIVE_TTL = 24 * 3600  # cache misses for 1 day


# ---------------------------------------------------------------------------
# In-memory + file cache
# ---------------------------------------------------------------------------
_mem_cache: Dict[str, Dict[str, Any]] = {}


def _load_file_cache() -> Dict[str, Dict[str, Any]]:
    """Load cache from disk once, merging into memory."""
    global _mem_cache
    if _mem_cache:
        return _mem_cache
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as fh:
                _mem_cache = json.load(fh)
        except (json.JSONDecodeError, OSError):
            _mem_cache = {}
    return _mem_cache


def _save_file_cache() -> None:
    """Persist cache to disk (best-effort)."""
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as fh:
            json.dump(_mem_cache, fh, ensure_ascii=False)
    except OSError:
        pass


def _normalize_name(name: str) -> str:
    return name.strip().lower()


# ---------------------------------------------------------------------------
# Core lookup
# ---------------------------------------------------------------------------

def get_logo_url(team_name: str) -> Optional[str]:
    """
    Return a badge/logo URL for *team_name* or ``None``.

    Results (including misses) are cached on disk for fast subsequent calls.
    """
    if not team_name or not team_name.strip():
        return None

    key = _normalize_name(team_name)
    cache = _load_file_cache()
    now = time.time()

    cached = cache.get(key)
    if cached:
        ttl = _CACHE_TTL if cached.get("url") else _NEGATIVE_TTL
        if now - cached.get("ts", 0) < ttl:
            return cached.get("url")

    # Fetch from TheSportsDB
    encoded = urllib.parse.quote(team_name.strip(), safe="")
    api_url = f"{_SPORTSDB_BASE}/{_API_KEY}/searchteams.php?t={encoded}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "PicklySportsApp/1.0"})

    url: Optional[str] = None
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
            data: Dict[str, Any] = json.loads(resp.read().decode())
        teams: List[Any] = data.get("teams") or []
        if teams:
            t: Dict[str, Any] = teams[0]
            url = t.get("strBadge") or t.get("strLogo") or None
    except Exception:
        # On network error keep stale cache entry if exists, else store None
        if cached and cached.get("url"):
            return cached["url"]

    cache[key] = {"url": url, "ts": now}
    _mem_cache[key] = cache[key]
    _save_file_cache()
    return url


def get_logo_url_cached_only(team_name: str) -> Optional[str]:
    """Return logo URL only from cache – no network call."""
    if not team_name:
        return None
    cache = _load_file_cache()
    entry = cache.get(_normalize_name(team_name))
    if entry:
        return entry.get("url")
    return None


# ---------------------------------------------------------------------------
# Batch enrichment
# ---------------------------------------------------------------------------

def enrich_matches_with_logos(matches: List[Dict[str, Any]]) -> None:
    """
    Add ``home_logo_url`` and ``away_logo_url`` to each match dict (in-place).

    Uses batched lookups so each unique team name hits the network at most once.
    """
    # Collect unique team names first to avoid duplicate network calls
    team_names: set[str] = set()
    for m in matches:
        home = m.get("home_team", "")
        away = m.get("away_team", "")
        if home:
            team_names.add(home)
        if away:
            team_names.add(away)

    # Resolve all unique names
    resolved: Dict[str, Optional[str]] = {}
    for name in team_names:
        resolved[name] = get_logo_url(name)

    # Inject into match dicts
    for m in matches:
        home = m.get("home_team", "")
        away = m.get("away_team", "")
        m["home_logo_url"] = resolved.get(home)
        m["away_logo_url"] = resolved.get(away)
