"""חישוב ציון חשיבות (0..100) — פשוט ושקוף: סוג מחקר + עיתון + טריות."""
import math
from datetime import date

from .config import (SCORE_WEIGHTS, DESIGN_RANK, DESIGN_RANK_DEFAULT, JOURNALS)

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


def _recency_component(pub_date: str | None, half_life_days: int = 120) -> float:
    """דעיכה מעריכית: מאמר טרי = ~1.0, מתחצה כל ~4 חודשים."""
    if not pub_date:
        return 0.5
    try:
        y, m, d = (int(x) for x in pub_date[:10].split("-"))
        age = (date.today() - date(y, m, d)).days
    except (ValueError, TypeError):
        return 0.5
    age = max(age, 0)
    return math.exp(-math.log(2) * age / half_life_days)


_DESIGN_LABEL = "סוג מחקר"
_JOURNAL_LABEL = "עיתון"
_RECENCY_LABEL = "טריות"


def importance_breakdown(article: dict) -> dict:
    """מחזיר את שלושת המרכיבים (0..100 כל אחד) + הציון הכולל — שקוף לחלוטין."""
    comp = {
        "design":  _design_component(article.get("pub_types", []), article.get("title", "")),
        "journal": _journal_component(article.get("journal_issn")),
        "recency": _recency_component(article.get("pub_date")),
    }
    total = sum(SCORE_WEIGHTS[k] * v for k, v in comp.items()) * 100
    return {
        "design":  round(comp["design"] * 100),
        "journal": round(comp["journal"] * 100),
        "recency": round(comp["recency"] * 100),
        "total":   round(total, 1),
    }


def compute_importance(article: dict) -> float:
    return importance_breakdown(article)["total"]
