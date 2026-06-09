"""מנוע הניתוח — מריץ את 'המבקר הקליני' מול Claude ומחזיר JSON מובנה."""
import json

from . import db
from .config import ANTHROPIC_API_KEY, ANALYSIS_MODEL, ANALYSIS_MAX_TOKENS
from .prompts import CRITIC_SYSTEM_PROMPT, build_user_message


class AnalysisError(Exception):
    pass


def _extract_json(text: str) -> dict:
    """חילוץ עמיד של אובייקט JSON מטקסט (גם אם יש עטיפת ```json)."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
    # מצא את ה-{ הראשון וה-} התואם האחרון
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise AnalysisError("לא נמצא JSON בתשובת המודל")
    return json.loads(text[start:end + 1])


def analyze_article(article: dict, content: str, source_scope: str,
                    model: str | None = None) -> dict:
    """
    מריץ ניתוח על מאמר.
    article: dict מטבלת articles. content: טקסט מלא או תקציר. source_scope: FULL_TEXT/ABSTRACT_ONLY.
    מחזיר את ה-payload (dict) ושומר ל-DB.
    """
    if not ANTHROPIC_API_KEY:
        raise AnalysisError("חסר ANTHROPIC_API_KEY ב-.env")
    try:
        import anthropic
    except ImportError as e:
        raise AnalysisError("חבילת anthropic לא מותקנת — הרץ: pip install anthropic") from e

    model = model or ANALYSIS_MODEL
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    user_msg = build_user_message(article, content, source_scope)

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=ANALYSIS_MAX_TOKENS,
            system=CRITIC_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": "{"},  # prefill — מאלץ JSON
            ],
        )
    except Exception as e:
        raise AnalysisError(f"שגיאת קריאה ל-Claude: {e}") from e

    raw = "{" + resp.content[0].text
    payload = _extract_json(raw)
    db.save_analysis(article["pmid"], payload, model, source_scope)
    return payload


def get_or_create_analysis(pmid: str, force: bool = False):
    """מחזיר ניתוח קיים מה-cache, או יוצר חדש. שולף טקסט מלא אם אפשר, אחרת תקציר."""
    from .fulltext import resolve_fulltext

    article = db.get_article(pmid)
    if not article:
        raise AnalysisError(f"מאמר {pmid} לא נמצא במסד")

    if not force:
        cached = db.get_analysis(pmid)
        if cached:
            return cached["payload"], cached["source_scope"], True  # (payload, scope, from_cache)

    # נסה טקסט מלא; נפילה חיננית לתקציר
    ft = resolve_fulltext(article)
    if ft and ft.get("text"):
        content, scope = ft["text"], "FULL_TEXT"
    else:
        content = article.get("abstract") or ""
        scope = "ABSTRACT_ONLY"
        if not content.strip():
            raise AnalysisError("אין תקציר ואין טקסט מלא — לא ניתן לנתח")

    payload = analyze_article(article, content, scope)
    return payload, scope, False
