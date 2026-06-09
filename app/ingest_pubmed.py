"""איסוף מ-PubMed דרך E-utilities (esearch + efetch). חינמי, רשמי, יציב."""
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode
from urllib.request import urlopen, Request

from . import db
from .config import (JOURNALS, OBGYN_FILTER, HIGH_VALUE_FILTER, HIGH_VALUE_ONLY,
                     NCBI_EMAIL, NCBI_API_KEY,
                     TOPIC_MAP, DEFAULT_TOPIC, DEFAULT_LOOKBACK_DAYS)
from .scoring import compute_importance

EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
USER_AGENT = "ObGyn-LitRadar/0.1 (personal research tool)"


def _http_get(url: str, retries: int = 4) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:
            code = getattr(e, "code", None)
            if attempt == retries - 1 or code not in (429, 500, 502, 503):
                raise
            time.sleep(1.5 * (attempt + 1))  # backoff על rate-limit / שגיאת שרת
    raise RuntimeError("unreachable")


def _common_params() -> dict:
    p = {"tool": "ObGyn-LitRadar"}
    if NCBI_EMAIL:
        p["email"] = NCBI_EMAIL
    if NCBI_API_KEY:
        p["api_key"] = NCBI_API_KEY
    return p


def _esearch(query: str, lookback_days: int) -> list[str]:
    params = _common_params() | {
        "db": "pubmed",
        "term": query,
        "datetype": "edat",          # תאריך כניסה ל-PubMed = "מעכשיו קדימה"
        "reldate": lookback_days,
        "retmax": 200,
        "retmode": "json",
    }
    import json as _json
    data = _json.loads(_http_get(f"{EUTILS}/esearch.fcgi?{urlencode(params)}"))
    return data.get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str]) -> bytes:
    params = _common_params() | {
        "db": "pubmed", "id": ",".join(pmids), "retmode": "xml",
    }
    return _http_get(f"{EUTILS}/efetch.fcgi?{urlencode(params)}")


def _text(el, path, default=None):
    found = el.find(path)
    return found.text if found is not None and found.text else default


def _parse_date(art_el) -> str | None:
    """מחזיר ISO date מ-ArticleDate או PubDate."""
    for path in (".//ArticleDate", ".//Journal/JournalIssue/PubDate"):
        d = art_el.find(path)
        if d is None:
            continue
        y = _text(d, "Year")
        if not y:
            continue
        m = _text(d, "Month", "01")
        day = _text(d, "Day", "01")
        months = {"jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
                  "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"}
        m = months.get(m[:3].lower(), m if m.isdigit() else "01")
        try:
            return f"{int(y):04d}-{int(m):02d}-{int(day):02d}"
        except ValueError:
            return f"{int(y):04d}-01-01"
    return None


def _classify_topics(mesh: list[str], title: str = "", abstract: str = "") -> list[str]:
    # שלב 1 — אותות חזקים: MeSH + כותרת (מדויק, מאמרים טריים מסתמכים על הכותרת).
    strong = " | ".join(mesh).lower() + " || " + (title or "").lower()
    topics = [name for name, keys in TOPIC_MAP
              if any(k.lower() in strong for k in keys)]
    if topics:
        return topics
    # שלב 2 — רשת ביטחון: אם דבר לא נמצא, סרוק גם את התקציר (recall על חשבון דיוק).
    blob = strong + " " + (abstract or "").lower()
    topics = [name for name, keys in TOPIC_MAP
              if any(k.lower() in blob for k in keys)]
    return topics or [DEFAULT_TOPIC]


def _parse_articles(xml_bytes: bytes, issn_to_weight: dict) -> list[dict]:
    root = ET.fromstring(xml_bytes)
    out = []
    for pa in root.findall(".//PubmedArticle"):
        art = pa.find(".//Article")
        if art is None:
            continue
        pmid = _text(pa, ".//PMID")
        title = _text(art, "ArticleTitle", "")
        # תקציר (יכול להיות מחולק לכמה חלקים)
        abstract_parts = []
        for ab in art.findall(".//Abstract/AbstractText"):
            label = ab.get("Label")
            txt = "".join(ab.itertext())
            abstract_parts.append(f"{label}: {txt}" if label else txt)
        abstract = "\n".join(abstract_parts) or None

        journal = _text(art, ".//Journal/Title")
        issn = _text(art, ".//Journal/ISSN")
        authors = []
        for au in art.findall(".//AuthorList/Author"):
            ln, fn = _text(au, "LastName"), _text(au, "ForeName")
            if ln:
                authors.append(f"{ln} {fn or ''}".strip())
        pub_types = [pt.text for pt in art.findall(".//PublicationTypeList/PublicationType") if pt.text]
        mesh = [mh.text for mh in pa.findall(".//MeshHeadingList/MeshHeading/DescriptorName") if mh.text]

        doi = None
        for aid in pa.findall(".//ArticleIdList/ArticleId"):
            if aid.get("IdType") == "doi":
                doi = aid.text
        pub_date = _parse_date(art)

        rec = {
            "pmid": pmid, "doi": doi, "title": title, "abstract": abstract,
            "journal": journal, "journal_issn": issn,
            "pub_date": pub_date, "authors": authors,
            "pub_types": pub_types, "mesh": mesh,
            "topics": _classify_topics(mesh, title, abstract or ""), "citations": None,
        }
        rec["importance"] = compute_importance(rec)
        out.append(rec)
    return out


def fetch_new(lookback_days: int = DEFAULT_LOOKBACK_DAYS, progress=None,
              high_value_only: bool = HIGH_VALUE_ONLY) -> dict:
    """
    מושך מאמרים חדשים מכל העיתונים. progress: callable(msg) אופציונלי.
    high_value_only: אם True — רק RCT/מטא/סקירה/הנחיה (מצמצם נפח לאיכות).
    מחזיר סיכום {fetched, new, skipped}.
    """
    db.init_db()
    issn_to_weight = {j["issn"]: j["weight"] for j in JOURNALS}
    seen, new_count = 0, 0

    for j in JOURNALS:
        q = f'{j["issn"]}[IS]'
        if j["filter_obgyn"]:
            q = f'({q}) AND {OBGYN_FILTER}'
        if high_value_only:
            q = f'({q}) AND {HIGH_VALUE_FILTER}'
        if progress:
            progress(f'מחפש: {j["name"]} …')
        try:
            pmids = _esearch(q, lookback_days)
        except Exception as e:
            if progress:
                progress(f'  ⚠ שגיאה ב-{j["name"]}: {e}')
            continue
        time.sleep(0.4)  # נימוס מול NCBI
        if not pmids:
            continue
        # סנן PMIDs שכבר קיימים
        fresh = [p for p in pmids if not db.article_exists(p)]
        seen += len(pmids)
        if not fresh:
            continue
        try:
            xml = _efetch(fresh)
            articles = _parse_articles(xml, issn_to_weight)
        except Exception as e:
            if progress:
                progress(f'  ⚠ שגיאת efetch ב-{j["name"]}: {e}')
            continue
        for art in articles:
            db.upsert_article(art)
            new_count += 1
        if progress:
            progress(f'  ✓ {j["name"]}: {len(articles)} מאמרים חדשים')
        time.sleep(0.4)

    db.set_meta("last_run", db.now_iso())
    summary = {"fetched": seen, "new": new_count}
    if progress:
        progress(f'סיום: {new_count} מאמרים חדשים נוספו.')
    return summary


if __name__ == "__main__":
    print(fetch_new(progress=print))
