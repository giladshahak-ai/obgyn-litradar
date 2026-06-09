"""שכבת מסד נתונים — SQLite. קובץ יחיד, אפס התקנה. נשדרג ל-Postgres אם נעבור למחלקה."""
import json
import sqlite3
from datetime import datetime, timezone
from contextlib import contextmanager

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    pmid        TEXT PRIMARY KEY,
    doi         TEXT,
    title       TEXT NOT NULL,
    abstract    TEXT,
    journal     TEXT,
    journal_issn TEXT,
    pub_date    TEXT,           -- ISO date (YYYY-MM-DD ככל שניתן)
    authors     TEXT,           -- JSON list
    pub_types   TEXT,           -- JSON list
    mesh        TEXT,           -- JSON list
    topics      TEXT,           -- JSON list (קטגוריות בעברית)
    citations   INTEGER DEFAULT NULL,
    author_hindex INTEGER DEFAULT NULL,  -- h-index מקסימלי בין המחברים
    author_top  TEXT DEFAULT NULL,       -- שם החוקר המשפיע ביותר
    importance  REAL DEFAULT 0,
    fetched_at  TEXT,
    UNIQUE(pmid)
);

CREATE TABLE IF NOT EXISTS analyses (
    pmid         TEXT PRIMARY KEY,
    payload      TEXT NOT NULL,  -- JSON של פלט "המבקר הקליני"
    model        TEXT,
    source_scope TEXT,           -- FULL_TEXT / ABSTRACT_ONLY
    created_at   TEXT,
    FOREIGN KEY(pmid) REFERENCES articles(pmid)
);

CREATE TABLE IF NOT EXISTS fulltext (
    pmid       TEXT PRIMARY KEY,
    text       TEXT,
    source     TEXT,            -- europepmc_oa / portal / none
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_articles_importance ON articles(importance DESC);
CREATE INDEX IF NOT EXISTS idx_articles_pubdate    ON articles(pub_date DESC);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # מיגרציה למסדים קיימים — הוספת עמודות מחברים אם חסרות
        cols = {r[1] for r in conn.execute("PRAGMA table_info(articles)").fetchall()}
        if "author_hindex" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN author_hindex INTEGER DEFAULT NULL")
        if "author_top" not in cols:
            conn.execute("ALTER TABLE articles ADD COLUMN author_top TEXT DEFAULT NULL")


# ── מאמרים ──────────────────────────────────────────────────────────────
def upsert_article(art: dict):
    """art = dict עם המפתחות של טבלת articles (authors/pub_types/mesh/topics כרשימות)."""
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO articles (pmid, doi, title, abstract, journal, journal_issn,
                pub_date, authors, pub_types, mesh, topics, citations,
                author_hindex, author_top, importance, fetched_at)
            VALUES (:pmid,:doi,:title,:abstract,:journal,:journal_issn,
                :pub_date,:authors,:pub_types,:mesh,:topics,:citations,
                :author_hindex,:author_top,:importance,:fetched_at)
            ON CONFLICT(pmid) DO UPDATE SET
                doi=excluded.doi, title=excluded.title, abstract=excluded.abstract,
                journal=excluded.journal, journal_issn=excluded.journal_issn,
                pub_date=excluded.pub_date, authors=excluded.authors,
                pub_types=excluded.pub_types, mesh=excluded.mesh, topics=excluded.topics,
                citations=COALESCE(excluded.citations, articles.citations),
                author_hindex=COALESCE(excluded.author_hindex, articles.author_hindex),
                author_top=COALESCE(excluded.author_top, articles.author_top),
                importance=excluded.importance
            """,
            {
                "pmid": art["pmid"],
                "doi": art.get("doi"),
                "title": art["title"],
                "abstract": art.get("abstract"),
                "journal": art.get("journal"),
                "journal_issn": art.get("journal_issn"),
                "pub_date": art.get("pub_date"),
                "authors": json.dumps(art.get("authors", []), ensure_ascii=False),
                "pub_types": json.dumps(art.get("pub_types", []), ensure_ascii=False),
                "mesh": json.dumps(art.get("mesh", []), ensure_ascii=False),
                "topics": json.dumps(art.get("topics", []), ensure_ascii=False),
                "citations": art.get("citations"),
                "author_hindex": art.get("author_hindex"),
                "author_top": art.get("author_top"),
                "importance": art.get("importance", 0),
                "fetched_at": art.get("fetched_at", now_iso()),
            },
        )


def article_exists(pmid: str) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT 1 FROM articles WHERE pmid=?", (pmid,)).fetchone()
        return row is not None


def _row_to_article(row: sqlite3.Row) -> dict:
    d = dict(row)
    for k in ("authors", "pub_types", "mesh", "topics"):
        try:
            d[k] = json.loads(d.get(k) or "[]")
        except (json.JSONDecodeError, TypeError):
            d[k] = []
    return d


def query_articles(topic=None, journal=None, days=None, study_type=None,
                   search=None, limit=300) -> list[dict]:
    sql = "SELECT * FROM articles WHERE 1=1"
    params = []
    if topic:
        sql += " AND topics LIKE ?"
        params.append(f"%{topic}%")
    if journal:
        sql += " AND journal = ?"
        params.append(journal)
    if study_type:
        sql += " AND pub_types LIKE ?"
        params.append(f"%{study_type}%")
    if search:
        sql += " AND (title LIKE ? OR abstract LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if days:
        sql += " AND pub_date >= date('now', ?)"
        params.append(f"-{int(days)} days")
    sql += " ORDER BY importance DESC, pub_date DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [_row_to_article(r) for r in rows]


def get_article(pmid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM articles WHERE pmid=?", (pmid,)).fetchone()
        return _row_to_article(row) if row else None


def clear_articles(keep_analyzed: bool = True):
    """מנקה מאמרים. keep_analyzed=True שומר מאמרים שכבר נותחו (לא מאבד עבודה)."""
    with get_conn() as conn:
        if keep_analyzed:
            conn.execute(
                "DELETE FROM articles WHERE pmid NOT IN (SELECT pmid FROM analyses)")
        else:
            conn.execute("DELETE FROM articles")


def all_journals_in_db() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT journal FROM articles ORDER BY journal").fetchall()
        return [r["journal"] for r in rows if r["journal"]]


# ── ניתוחים ─────────────────────────────────────────────────────────────
def save_analysis(pmid: str, payload: dict, model: str, source_scope: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO analyses (pmid, payload, model, source_scope, created_at)
               VALUES (?,?,?,?,?)
               ON CONFLICT(pmid) DO UPDATE SET
                 payload=excluded.payload, model=excluded.model,
                 source_scope=excluded.source_scope, created_at=excluded.created_at""",
            (pmid, json.dumps(payload, ensure_ascii=False), model, source_scope, now_iso()),
        )


def get_analysis(pmid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM analyses WHERE pmid=?", (pmid,)).fetchone()
        if not row:
            return None
        d = dict(row)
        d["payload"] = json.loads(d["payload"])
        return d


# ── טקסט מלא ─────────────────────────────────────────────────────────────
def save_fulltext(pmid: str, text: str, source: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO fulltext (pmid, text, source, fetched_at) VALUES (?,?,?,?)
               ON CONFLICT(pmid) DO UPDATE SET
                 text=excluded.text, source=excluded.source, fetched_at=excluded.fetched_at""",
            (pmid, text, source, now_iso()),
        )


def get_fulltext(pmid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fulltext WHERE pmid=?", (pmid,)).fetchone()
        return dict(row) if row else None


# ── meta ────────────────────────────────────────────────────────────────
def set_meta(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO meta (key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))


def get_meta(key: str, default=None):
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default
