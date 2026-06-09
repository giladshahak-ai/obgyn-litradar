"""חישוב ציון חשיבות (0..100) — משקלים מסתגלים לגיל: ראיות עד שהציטוטים מתבגרים."""
import math
from datetime import date

from .config import (SCORE_WEIGHTS, DESIGN_RANK, DESIGN_RANK_DEFAULT, JOURNALS,
                     AUTHOR_HINDEX_TOP, IMPACT_FWCI_TOP,
                     CITATION_MIN_MONTHS, CITATION_MATURE_MONTHS)

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
    """השפעה בפועל — FWCI (מנורמל לתחום) או ציטוטים. ללא רצפה (הגיל מטופל במשקל)."""
    if fwci is not None:
        try:
            return min(math.log1p(max(float(fwci), 0)) / math.log1p(IMPACT_FWCI_TOP), 1.0)
        except (ValueError, TypeError):
            return 0.0
    if citations is not None:
        try:
            return min(math.log1p(max(int(citations), 0)) / math.log1p(100), 1.0)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


def _maturity(pub_date) -> float:
    """0..1 — בשלות הציטוטים. <6 ח'=0 (ציטוטים חסרי משמעות), מלא ב-24 ח'."""
    if not pub_date:
        return 0.0
    try:
        y, m, d = (int(x) for x in str(pub_date)[:10].split("-"))
        months = (date.today() - date(y, m, d)).days / 30.44
    except (ValueError, TypeError):
        return 0.0
    span = max(CITATION_MATURE_MONTHS - CITATION_MIN_MONTHS, 1)
    return max(0.0, min((months - CITATION_MIN_MONTHS) / span, 1.0))


def _eff_weights(maturity: float) -> dict:
    """משקלים אפקטיביים: משקל ההשפעה גדל עם הגיל; ה'משוחרר' עובר לרמת הראיות."""
    W = SCORE_WEIGHTS
    wi = W["impact"] * maturity
    return {"design": W["design"] + W["impact"] * (1 - maturity),
            "journal": W["journal"], "author": W["author"], "impact": wi}


def importance_breakdown(article: dict) -> dict:
    """ערכי המרכיבים (0..100) + משקלים אפקטיביים לפי גיל + הציון הכולל — שקוף."""
    comp = {
        "design":  _design_component(article.get("pub_types", []), article.get("title", "")),
        "journal": _journal_component(article.get("journal_issn")),
        "author":  _author_component(article.get("author_hindex")),
        "impact":  _impact_component(article.get("fwci"), article.get("citations")),
    }
    mat = _maturity(article.get("pub_date"))
    ew = _eff_weights(mat)
    total = sum(ew[k] * comp[k] for k in comp) * 100
    return {
        "design":  round(comp["design"] * 100),
        "journal": round(comp["journal"] * 100),
        "author":  round(comp["author"] * 100),
        "impact":  round(comp["impact"] * 100),
        "impact_weight": round(ew["impact"] * 100),
        "maturity": round(mat * 100),
        "hindex":  article.get("author_hindex"),
        "fwci":    article.get("fwci"),
        "total":   round(total, 1),
    }


def compute_importance(article: dict) -> float:
    return importance_breakdown(article)["total"]
