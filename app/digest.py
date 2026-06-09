"""בחירת הדייג'סט השבועי — 2-3 המאמרים החשובים ביותר מכל עיתון ליבה."""
from . import db
from .config import JOURNALS, DIGEST_PER_JOURNAL, DIGEST_WINDOW_DAYS

_PRIMARY_LIST = [j for j in JOURNALS if j.get("primary")]
# מפתח לפי כל ה-ISSN-ים הידועים (print + electronic) → עיתון הליבה.
PRIMARY = {}
for _j in _PRIMARY_LIST:
    for _is in (_j.get("issn"), _j.get("issn_e")):
        if _is:
            PRIMARY[_is] = _j
PRIMARY_ORDER = [j.get("issn_e") or j.get("issn") for j in _PRIMARY_LIST]
_BY_KEY = {(j.get("issn_e") or j.get("issn")): j for j in _PRIMARY_LIST}


def weekly_digest(per_journal: int = DIGEST_PER_JOURNAL,
                  window_days: int = DIGEST_WINDOW_DAYS) -> list[dict]:
    """מחזיר רשימת מאמרים נבחרים: עד per_journal מכל עיתון ליבה, בחלון window_days."""
    arts = db.query_articles(days=window_days or None, limit=3000)
    groups: dict[str, list] = {}
    for a in arts:
        j = PRIMARY.get(a.get("journal_issn"))
        if j:
            key = j.get("issn_e") or j.get("issn")
            groups.setdefault(key, []).append(a)

    digest = []
    for issn in PRIMARY_ORDER:
        j = _BY_KEY[issn]
        items = sorted(groups.get(issn, []),
                       key=lambda x: x.get("importance", 0), reverse=True)[:per_journal]
        for it in items:
            it = dict(it)
            it["journal_nick"] = j.get("nick") or j["name"]
            it["journal_label"] = j["name"]
            digest.append(it)
    digest.sort(key=lambda x: x.get("importance", 0), reverse=True)
    return digest


def digest_with_analyses(per_journal: int = DIGEST_PER_JOURNAL,
                         window_days: int = DIGEST_WINDOW_DAYS) -> list[dict]:
    """כמו weekly_digest אך מצרף ניתוח שמור (אם קיים) לכל מאמר."""
    out = weekly_digest(per_journal, window_days)
    for a in out:
        an = db.get_analysis(a["pmid"])
        a["analysis"] = an["payload"] if an else None
        a["analysis_scope"] = an["source_scope"] if an else None
    return out
