"""
שליפת טקסט מלא — מודול מבודד ('שקע'). שלוש שכבות, מהזולה ללגיטימית ביותר:

  1) Open Access חינמי (Europe PMC)        — עובד עכשיו, בלי login.
  2) Resolver הפורטל המוסדי (DOI/PMID)      — ימולא אחרי בדיקת הפורטל שלך.
  3) נפילה חיננית → תקציר בלבד.

החלפת הפורטל בעתיד = שינוי הפונקציה _portal_fulltext בלבד.
"""
import re
import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from . import db
from .config import BROWSER_PROFILE_DIR

USER_AGENT = "ObGyn-LitRadar/0.1 (personal research tool)"
_TAG_RE = re.compile(r"<[^>]+>")


def _http_get(url: str, timeout=30) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=timeout) as r:
        return r.read()


# ── שכבה 1: Open Access דרך Europe PMC ──────────────────────────────────
def _europepmc_fulltext(article: dict) -> str | None:
    pmid = article.get("pmid")
    if not pmid:
        return None
    # מצא PMCID דרך ה-API
    try:
        q = urlencode({"query": f"EXT_ID:{pmid} AND SRC:MED", "format": "json",
                       "resultType": "core"})
        data = json.loads(_http_get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?{q}"))
        results = data.get("resultList", {}).get("result", [])
        if not results:
            return None
        rec = results[0]
        pmcid = rec.get("pmcid")
        is_oa = rec.get("isOpenAccess") == "Y" or rec.get("inEPMC") == "Y"
        if not (pmcid and is_oa):
            return None
        # שלוף XML של הטקסט המלא
        xml = _http_get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML").decode("utf-8", "ignore")
        text = _TAG_RE.sub(" ", xml)
        text = re.sub(r"\s+", " ", text).strip()
        return text if len(text) > 1500 else None
    except Exception:
        return None


# ── שכבה 2: Resolver הפורטל המוסדי (Playwright, פרופיל מתמשך) ───────────
# סקיצה — תופעל אחרי שנדע מה קורה כשמזינים DOI בטאב DOI/PMID של הפורטל.
PORTAL_DOI_URL_TEMPLATE = None  # למשל: "https://<portal>/openurl?doi={doi}"


def _portal_fulltext(article: dict) -> str | None:
    """
    שולף טקסט מלא דרך הפורטל המוסדי באמצעות פרופיל דפדפן מחובר (login ידני חד-פעמי).
    כרגע מושבת עד שנסגור את תבנית ה-resolver. ראה README → 'חיבור הפורטל'.
    """
    if PORTAL_DOI_URL_TEMPLATE is None:
        return None
    doi = article.get("doi")
    if not doi:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    url = PORTAL_DOI_URL_TEMPLATE.format(doi=doi)
    try:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=str(BROWSER_PROFILE_DIR), headless=False)
            page = ctx.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(3000)
            body = page.inner_text("body")
            ctx.close()
            text = re.sub(r"\s+", " ", body).strip()
            return text if len(text) > 1500 else None
    except Exception:
        return None


# ── מתאם ─────────────────────────────────────────────────────────────────
def resolve_fulltext(article: dict, use_cache: bool = True) -> dict | None:
    """
    מחזיר {'text':..., 'source':...} או None. שומר ל-cache לפי PMID.
    סדר ניסיון: cache → Europe PMC (OA) → פורטל מוסדי.
    """
    pmid = article.get("pmid")
    if use_cache and pmid:
        cached = db.get_fulltext(pmid)
        if cached and cached.get("text"):
            return {"text": cached["text"], "source": cached["source"]}

    for fn, src in ((_europepmc_fulltext, "europepmc_oa"),
                    (_portal_fulltext, "portal")):
        text = fn(article)
        if text:
            if pmid:
                db.save_fulltext(pmid, text, src)
            return {"text": text, "source": src}
    return None
