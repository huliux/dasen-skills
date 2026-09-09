"""Count factual origins, keeping research summaries and structural references distinct."""
from urllib.parse import urldefrag


def factual_origins(sources: list[dict], pattern_url: str = "") -> list[dict]:
    origins: dict[str, dict] = {}
    for source in sources:
        purpose = source.get("purpose", "fact")
        if purpose not in ("fact", "structure"):
            raise ValueError("source.purpose must be fact or structure")
        if purpose == "structure" or (pattern_url and source.get("url") == pattern_url):
            continue
        if source.get("wiki_path"):
            if not source.get("origin") or not source.get("origin_type"):
                raise ValueError("Wiki evidence requires origin and origin_type")
            if source.get("type") != source.get("origin_type"):
                raise ValueError("Wiki evidence must inherit its origin_type; a summary is not independent evidence")
        locator = str(source.get("origin") or source.get("url") or source.get("path") or "").strip()
        if not locator:
            raise ValueError("fact source requires an original URL or local locator")
        origin = urldefrag(locator)[0]
        if origin in origins and origins[origin].get("type") != source.get("type"):
            raise ValueError("one factual origin has conflicting source types")
        origins.setdefault(origin, source)
    return list(origins.values())
