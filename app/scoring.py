"""חישוב ציון חשיבות (0..100) — אובייקטיבי: רמת ראיות + עיתון + מעמד החוקרים."""
import math

from .config import (SCORE_WEIGHTS, DESIGN_RANK, DESIGN_RANK_DEFAULT, JOURNALS,
                     AUTHOR_HINDEX_TOP, IMPACT_FWCI_TOP, IMPACT_FLOOR)

# מפתח לפי print + electronic ISSN (מאמרים מאוחסנים עם ה-electronic)
_JOURNAL_WEIGHT = {}
for _j in JOURNALS:
    for _k in (_j.get("issn"), _j.get("issn_e")):
        if _k:
            _JOURNAL_WEIGHT[_k] = _j["weight"]
_MAX_JOURNAL_WEIGHT = max((j["weight"] for j in JOURNALS), default=10)


def _journal_component(issn: str | None) -> float:
    w = _JOURNAL_WEIGHT.get(issn or "", 4)  # ברירת מחדל בינונית-נמוכה
    return w / _MAX_JOURNAL_WEIGHT


def _design_component(pub_types: list[str], title: str = "") -> float:
    # מאמרים טריים לרוב מתויגים רק כ-"Journal Article"; הכותרת חושפת את התכנון האמיתי.
    blob = (" ".join(pub_types) + " " + (title or "")).lower()
    for keywords, rank in DESIGN_RANK:
        if any(k.lower() in blob for k in keywords):
            return rank
    return DESIGN_RANK_DEFAULT


def _author_component(hindex) -> float:
    """
    מעמד החוקרים — נרמול לוגריתמי של ה-h-index המקסימלי בין המחברים.
    h-index גבוה = חוקר משפיע בתחומו. None (אין נתון) = ציון ניטרלי-נמוך.
    """
    if hindex is None:
        return 0.30
    try:
        h = max(int(hindex), 0)
    except (ValueError, TypeError):
        return 0.30
    return min(math.log1p(h) / math.log1p(AUTHOR_HINDEX_TOP), 1.0)


def _impact_component(fwci, citations) -> float:
    """השפעה בפועל — FWCI (מנורמל לתחום) או ציטוטים. רצפה למאמרים טריים."""
    if fwci is not None:
        try:
            norm = min(math.log1p(max(float(fwci), 0)) / math.log1p(IMPACT_FWCI_TOP), 1.0)
        except (ValueError, TypeError):
            norm = IMPACT_FLOOR
    elif citations is not None:
        try:
            norm = min(math.log1p(max(int(citations), 0)) / math.log1p(100), 1.0)
        except (ValueError, TypeError):
            norm = IMPACT_FLOOR
    else:
        return IMPACT_FLOOR
    return max(IMPACT_FLOOR, norm)


def importance_breakdown(article: dict) -> dict:
    """מחזיר את ארבעת המרכיבים (0..100 כל אחד) + הציון הכולל — שקוף לחלוטין."""
    comp = {
        "design":  _design_component(article.get("pub_types", []), article.get("title", "")),
        "journal": _journal_component(article.get("journal_issn")),
        "author":  _author_component(article.get("author_hindex")),
        "impact":  _impact_component(article.get("fwci"), article.get("citations")),
    }
    total = sum(SCORE_WEIGHTS[k] * v for k, v in comp.items()) * 100
    return {
        "design":  round(comp["design"] * 100),
        "journal": round(comp["journal"] * 100),
        "author":  round(comp["author"] * 100),
        "impact":  round(comp["impact"] * 100),
        "hindex":  article.get("author_hindex"),
        "fwci":    article.get("fwci"),
        "total":   round(total, 1),
    }


def compute_importance(article: dict) -> float:
    return importance_breakdown(article)["total"]
