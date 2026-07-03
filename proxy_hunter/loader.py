"""Load working proxies from source_tests results."""

from __future__ import annotations

import json
from pathlib import Path

from .pool import ProxyEntry, ProxyPool

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent.parent / "source_tests" / "results"


def load_ranking_source_ids(
    results_dir: Path,
    *,
    top_n: int = 8,
    min_success_rate: float = 10.0,
) -> list[str]:
    ranking = results_dir / "00_RANKING.json"
    if not ranking.exists():
        return []

    data = json.loads(ranking.read_text(encoding="utf-8"))
    summaries = data.get("summaries", [])
    ok = [
        s for s in summaries
        if s.get("fetch_ok") and s.get("working", 0) > 0 and s.get("success_rate", 0) >= min_success_rate
    ]
    ok.sort(key=lambda x: (-x.get("success_rate", 0), -(x.get("working", 0))))
    return [s["id"] for s in ok[:top_n]]


def load_pool_from_results(
    results_dir: Path | str | None = None,
    *,
    source_ids: list[str] | None = None,
    top_n_sources: int = 8,
    prefer_https: bool = True,
    max_proxies: int = 200,
) -> ProxyPool:
    """Build a ProxyPool from per-platform JSON reports."""
    root = Path(results_dir) if results_dir else DEFAULT_RESULTS_DIR
    if not root.exists():
        raise FileNotFoundError(f"Proxy results not found: {root}. Run: cd source_tests && python run_all.py")

    ids = source_ids or load_ranking_source_ids(root, top_n=top_n_sources)
    if not ids:
        raise FileNotFoundError(f"No ranked sources in {root}. Run source_tests/run_all.py first.")

    entries: list[ProxyEntry] = []
    seen: set[str] = set()

    for sid in ids:
        path = root / f"{sid}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for item in data.get("working_proxies", []):
            url = item.get("proxy")
            if not url or url in seen:
                continue
            if prefer_https and not item.get("https_ok") and url.startswith("http://"):
                # still keep HTTP proxies; crawlers can use them for HTTPS targets often
                pass
            seen.add(url)
            entries.append(
                ProxyEntry(
                    url=url,
                    source_id=sid,
                    latency_ms=item.get("latency_ms"),
                    https_ok=bool(item.get("https_ok")),
                )
            )
            if len(entries) >= max_proxies:
                break
        if len(entries) >= max_proxies:
            break

    if not entries:
        raise RuntimeError(f"No working proxies loaded from {root} (sources={ids})")

    entries.sort(key=lambda e: (e.latency_ms is None, e.latency_ms or 9999))
    return ProxyPool(entries)