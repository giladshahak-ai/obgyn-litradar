"""חישוב ציון חשיבות (0..100) — שקוף וניתן לכוונון ב-config.SCORE_WEIGHTS."""
import math
import re
from datetime import date

from .config import (SCORE_WEIGHTS, DESIGN_RANK, DESIGN_RANK_DEFAULT, JOURNALS)

_JOURNAL_WEIGHT = {j["issn"]: j["weight"] for j in JOURNALS}
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


def _citation_component(citations: int | None, pub_date: str | None) -> float:
    """מהירות ציטוט מנורמלת לוגריתמית. None → ניטרלי (0.4)."""
    if citations is None:
        return 0.4
    return min(math.log1p(citations) / math.log1p(100), 1.0)


def _sample_component(abstract: str | None) -> float:
    """ניסיון לחלץ גודל מדגם מהתקציר (n=..., N participants...). גס בכוונה."""
    if not abstract:
        return 0.4
    nums = re.findall(r"\b[nN]\s*=\s*([\d,]{2,7})", abstract)
    nums += re.findall(r"([\d,]{3,7})\s+(?:patients|participants|women|cases|pregnan)", abstract)
    vals = []
    for s in nums:
        try:
            vals.append(int(s.replace(",", "")))
        except ValueError:
            pass
    if not vals:
        return 0.4
    return min(math.log1p(max(vals)) / math.log1p(10000), 1.0)


def compute_importance(article: dict) -> float:
    parts = {
        "journal":   _journal_component(article.get("journal_issn")),
        "design":    _design_component(article.get("pub_types", []), article.get("title", "")),
        "recency":   _recency_component(article.get("pub_date")),
        "citations": _citation_component(article.get("citations"), article.get("pub_date")),
        "sample":    _sample_component(article.get("abstract")),
    }
    score = sum(SCORE_WEIGHTS[k] * v for k, v in parts.items())
    return round(score * 100, 1)
