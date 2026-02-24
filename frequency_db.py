"""
frequency_db.py – SQLite-backed frequency tracker for TextExploder.

Passively records how often words and short phrases (2-3 word n-grams)
are typed, and surfaces the most frequent ones as abbreviation candidates.
"""

import os
import sqlite3
import datetime

# DB lives alongside config.json in %APPDATA%\MyTextExploder
APPDATA_DIR = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "MyTextExploder"
)
os.makedirs(APPDATA_DIR, exist_ok=True)
DB_PATH = os.path.join(APPDATA_DIR, "frequency.db")

# ── Stop words: common English words that would be noise ──
STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "not", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "shall",
    "can", "need", "must", "to", "of", "in", "for", "on", "with", "at",
    "by", "from", "as", "into", "about", "like", "after", "before",
    "between", "through", "during", "it", "its", "this", "that", "these",
    "those", "he", "she", "they", "we", "you", "me", "him", "her", "us",
    "them", "my", "your", "his", "our", "their", "what", "which", "who",
    "when", "where", "how", "all", "each", "every", "both", "few", "more",
    "most", "some", "any", "no", "just", "than", "too", "very", "also",
    "so", "if", "then", "else", "up", "out", "get", "got", "yes", "yeah",
    "okay", "here", "there",
})

MIN_PHRASE_LENGTH = 4
MAX_NGRAM_WORDS = 3  # Track up to trigrams


def _is_substantive_word(word: str) -> bool:
    """Return True if the word is meaningful (not a stop word and long enough)."""
    return len(word) >= MIN_PHRASE_LENGTH and word not in STOP_WORDS


def is_trackable_phrase(phrase: str) -> bool:
    """Return True if a multi-word phrase should be recorded.
    
    At least one word in the phrase must be substantive (not a stop word, ≥4 chars).
    The phrase must contain at least one letter.
    """
    words = phrase.strip().lower().split()
    if len(words) < 2:
        return False  # Use is_trackable() for single words
    if not any(c.isalpha() for c in phrase):
        return False
    # At least one word must be substantive
    return any(_is_substantive_word(w) for w in words)


def _get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a new connection to the frequency database."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create the database and tables if they don't exist."""
    conn = _get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS typed_phrases (
                phrase      TEXT PRIMARY KEY,
                count       INTEGER NOT NULL DEFAULT 1,
                first_typed TEXT NOT NULL,
                last_typed  TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_count
                ON typed_phrases(count DESC);
        """)
        conn.commit()
    finally:
        conn.close()


def is_trackable(word: str) -> bool:
    """Return True if the word should be recorded (not a stop word, long enough)."""
    normalized = word.strip().lower()
    if len(normalized) < MIN_PHRASE_LENGTH:
        return False
    if normalized in STOP_WORDS:
        return False
    # Must contain at least one letter (skip pure numbers / punctuation)
    if not any(c.isalpha() for c in normalized):
        return False
    return True


def record_phrase(phrase: str, db_path: str | None = None) -> None:
    """Insert or increment count for a phrase."""
    normalized = phrase.strip().lower()
    if not is_trackable(normalized):
        return
    now = datetime.datetime.now().isoformat()
    conn = _get_connection(db_path)
    try:
        conn.execute(
            """
            INSERT INTO typed_phrases (phrase, count, first_typed, last_typed)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(phrase) DO UPDATE SET
                count = count + 1,
                last_typed = excluded.last_typed
            """,
            (normalized, now, now),
        )
        conn.commit()
    finally:
        conn.close()


def record_phrases_batch(phrases: list[str], db_path: str | None = None) -> None:
    """Batch-insert/increment a list of phrases in a single transaction.
    
    Accepts both single words and multi-word phrases. Single words are
    filtered through is_trackable(); multi-word phrases through is_trackable_phrase().
    """
    now = datetime.datetime.now().isoformat()
    conn = _get_connection(db_path)
    try:
        for phrase in phrases:
            normalized = phrase.strip().lower()
            # Determine if it's a single word or multi-word phrase
            is_multi = " " in normalized
            if is_multi:
                if not is_trackable_phrase(normalized):
                    continue
            else:
                if not is_trackable(normalized):
                    continue
            conn.execute(
                """
                INSERT INTO typed_phrases (phrase, count, first_typed, last_typed)
                VALUES (?, 1, ?, ?)
                ON CONFLICT(phrase) DO UPDATE SET
                    count = count + 1,
                    last_typed = excluded.last_typed
                """,
                (normalized, now, now),
            )
        conn.commit()
    finally:
        conn.close()


# ── Database size management ──

MAX_ROWS = 5000          # Hard cap on total tracked phrases
STALE_DAYS = 30          # Prune low-count entries older than this
STALE_MAX_COUNT = 2      # Only prune entries at or below this count


def prune_db(db_path: str | None = None) -> int:
    """Remove stale low-value entries and enforce a row cap.
    
    Returns the number of rows deleted.
    """
    conn = _get_connection(db_path)
    deleted = 0
    try:
        # 1. Remove stale entries: count ≤ STALE_MAX_COUNT and not typed in STALE_DAYS
        cutoff = (
            datetime.datetime.now() - datetime.timedelta(days=STALE_DAYS)
        ).isoformat()
        cursor = conn.execute(
            "DELETE FROM typed_phrases WHERE count <= ? AND last_typed < ?",
            (STALE_MAX_COUNT, cutoff),
        )
        deleted += cursor.rowcount

        # 2. Enforce row cap: keep top MAX_ROWS by count, delete the rest
        row = conn.execute("SELECT COUNT(*) FROM typed_phrases").fetchone()
        total = row[0]
        if total > MAX_ROWS:
            excess = total - MAX_ROWS
            conn.execute(
                """
                DELETE FROM typed_phrases WHERE phrase IN (
                    SELECT phrase FROM typed_phrases
                    ORDER BY count ASC, last_typed ASC
                    LIMIT ?
                )
                """,
                (excess,),
            )
            deleted += excess

        conn.commit()
    finally:
        conn.close()
    return deleted


def get_top_phrases(
    min_count: int = 9,
    limit: int = 20,
    exclude: set[str] | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """
    Return the most frequently typed phrases.

    Args:
        min_count: Minimum number of times a phrase must have been typed.
        limit: Maximum number of results to return.
        exclude: Set of phrases (lowercased) to exclude (e.g. existing abbreviation replacements).

    Returns:
        List of dicts with keys: phrase, count, first_typed, last_typed.
    """
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT phrase, count, first_typed, last_typed
            FROM typed_phrases
            WHERE count >= ?
            ORDER BY count DESC
            LIMIT ?
            """,
            (min_count, limit * 3),  # over-fetch to allow filtering
        )
        results = []
        exclude_set = exclude or set()
        for row in cursor:
            if row["phrase"] in exclude_set:
                continue
            results.append({
                "phrase": row["phrase"],
                "count": row["count"],
                "first_typed": row["first_typed"],
                "last_typed": row["last_typed"],
            })
            if len(results) >= limit:
                break
        return results
    finally:
        conn.close()


def get_phrase_stats(db_path: str | None = None) -> dict:
    """Return summary stats: total tracked phrases, total keystrokes counted."""
    conn = _get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total_phrases, COALESCE(SUM(count), 0) AS total_counts "
            "FROM typed_phrases"
        ).fetchone()
        return {
            "total_phrases": row["total_phrases"],
            "total_counts": row["total_counts"],
        }
    finally:
        conn.close()


def get_tracked_phrases(
    limit: int = 500,
    db_path: str | None = None,
) -> list[dict]:
    """Return tracked phrases/words ordered by most recently typed."""
    conn = _get_connection(db_path)
    try:
        cursor = conn.execute(
            """
            SELECT phrase, count, first_typed, last_typed
            FROM typed_phrases
            ORDER BY last_typed DESC, count DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "phrase": row["phrase"],
                "count": row["count"],
                "first_typed": row["first_typed"],
                "last_typed": row["last_typed"],
            }
            for row in cursor
        ]
    finally:
        conn.close()


def dismiss_phrase(phrase: str, db_path: str | None = None) -> None:
    """Remove a phrase from tracking so it won't be suggested again."""
    normalized = phrase.strip().lower()
    conn = _get_connection(db_path)
    try:
        conn.execute("DELETE FROM typed_phrases WHERE phrase = ?", (normalized,))
        conn.commit()
    finally:
        conn.close()
