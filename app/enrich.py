"""
העשרת מחברים — מושך מ-Semantic Scholar את ה-h-index של המחברים לפי DOI,
שומר את המקסימום (החוקר המשפיע ביותר), ומעדכן את ציון החשיבות.
Best-effort: אם אין נתון, המאמר פשוט מקבל ציון מחבר ניטרלי.
"""
import json
import time
from urllib.request import urlopen, Request

from . import db
from .scoring import compute_importance

SS_BATCH = "https://api.semanticscholar.org/graph/v1/paper/batch"
USER_AGENT = "LitRadar/0.1 (research tool)"


def _batch_hindex(dois: list[str]) -> dict:
    """dois -> {doi: (max_hindex, top_author_name)}. עמיד לשגיאות."""
    dois = [d for d in dois if d]
    if not dois:
        return {}
    body = json.dumps({"ids": ["DOI:" + d for d in dois]}).encode()
    url = SS_BATCH + "?fields=authors.name,authors.hIndex"
    data = None
    for attempt in range(4):
        try:
            req = Request(url, data=body,
                          headers={"User-Agent": USER_AGENT, "Content-Type": "application/json"})
            with urlopen(req, timeout=30) as r:
                data = json.load(r)
            break
        except Exception as e:
            code = getattr(e, "code", None)
            if attempt == 3 or code not in (429, 500, 502, 503):
                return {}
            time.sleep(2.0 * (attempt + 1))
    out = {}
    for doi, rec in zip(dois, data or []):
        if not rec:
            continue
        best_h, best_n = -1, None
        for a in (rec.get("authors") or []):
            h = a.get("hIndex")
            if h is not None and h > best_h:
                best_h, best_n = h, a.get("name")
        if best_h >= 0:
            out[doi] = (best_h, best_n)
    return out


def enrich_missing(progress=None, force: bool = False) -> int:
    """מעשיר מאמרים ללא h-index (או הכל אם force). מחזיר כמה עודכנו."""
    db.init_db()
    arts = db.query_articles(limit=3000)
    todo = [a for a in arts if a.get("doi") and (force or a.get("author_hindex") is None)]
    updated = 0
    for i in range(0, len(todo), 100):          # batch של עד 100 DOI
        chunk = todo[i:i + 100]
        res = _batch_hindex([a["doi"] for a in chunk])
        for a in chunk:
            hit = res.get(a["doi"])
            if hit:
                a["author_hindex"], a["author_top"] = hit[0], hit[1]
                a["importance"] = compute_importance(a)   # רענון ציון עם המחבר
                db.upsert_article(a)
                updated += 1
        if progress:
            progress(f"  העשרת מחברים: {updated}/{len(todo)}")
        time.sleep(1.0)
    return updated


if __name__ == "__main__":
    print("עודכנו:", enrich_missing(progress=print, force=True))
