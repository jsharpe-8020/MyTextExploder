"""Quick smoke test for frequency_db — runs without pytest."""
import os
import sys
import datetime

# Ensure we can import from the project directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import frequency_db

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_smoke_test.db")

def cleanup():
    if os.path.exists(DB):
        os.remove(DB)

def main():
    cleanup()
    frequency_db.init_db(DB)
    print("[OK] init_db")

    # ── Single word tracking ──
    assert not frequency_db.is_trackable("the"), "stop word should be rejected"
    assert not frequency_db.is_trackable("hi"), "short word should be rejected"
    assert frequency_db.is_trackable("hello"), "valid word should be accepted"
    print("[OK] is_trackable")

    # ── Multi-word phrase tracking ──
    assert frequency_db.is_trackable_phrase("hello world"), "valid bigram accepted"
    assert frequency_db.is_trackable_phrase("the quick fox"), "trigram with stop words accepted (has substantive word)"
    assert not frequency_db.is_trackable_phrase("the and"), "all stop words rejected"
    assert not frequency_db.is_trackable_phrase("hello"), "single word rejected by phrase check"
    print("[OK] is_trackable_phrase")

    # ── Record + get ──
    frequency_db.record_phrase("hello", DB)
    frequency_db.record_phrase("Hello", DB)
    frequency_db.record_phrase("HELLO", DB)
    results = frequency_db.get_top_phrases(min_count=1, db_path=DB)
    assert len(results) == 1, f"Expected 1, got {len(results)}"
    assert results[0]["phrase"] == "hello"
    assert results[0]["count"] == 3, f"Expected 3, got {results[0]['count']}"
    print("[OK] record_phrase + case normalization")

    # ── Batch with mixed single + multi-word ──
    frequency_db.record_phrases_batch([
        "world", "world", "python", "the", "a",     # single words
        "hello world", "hello world", "the and",      # phrases
    ], DB)
    results = frequency_db.get_top_phrases(min_count=1, db_path=DB)
    phrases = {r["phrase"]: r["count"] for r in results}
    assert "world" in phrases and phrases["world"] == 2
    assert "python" in phrases and phrases["python"] == 1
    assert "the" not in phrases, "stop word should not be recorded"
    assert "hello world" in phrases and phrases["hello world"] == 2, "bigram should be recorded"
    assert "the and" not in phrases, "all-stop-word phrase rejected"
    print("[OK] record_phrases_batch (single + multi-word)")

    # ── Threshold (default=9) ──
    results_default = frequency_db.get_top_phrases(db_path=DB)  # uses default min_count=9
    assert len(results_default) == 0, "Nothing should exceed the 9-count threshold yet"
    print("[OK] default threshold = 9")

    # ── Exclude filter ──
    results = frequency_db.get_top_phrases(min_count=1, exclude={"hello"}, db_path=DB)
    assert all(r["phrase"] != "hello" for r in results)
    print("[OK] exclude filter")

    # ── Stats ──
    stats = frequency_db.get_phrase_stats(DB)
    assert stats["total_phrases"] > 0
    assert stats["total_counts"] > 0
    print("[OK] get_phrase_stats")

    # ── Dismiss ──
    frequency_db.dismiss_phrase("hello", DB)
    results = frequency_db.get_top_phrases(min_count=1, db_path=DB)
    assert all(r["phrase"] != "hello" for r in results)
    print("[OK] dismiss_phrase")

    # ── Prune (row cap enforcement) ──
    cleanup()
    frequency_db.init_db(DB)
    # Insert more than MAX_ROWS entries
    import sqlite3
    conn = sqlite3.connect(DB)
    old_date = (datetime.datetime.now() - datetime.timedelta(days=60)).isoformat()
    for i in range(100):
        conn.execute(
            "INSERT INTO typed_phrases (phrase, count, first_typed, last_typed) VALUES (?, 1, ?, ?)",
            (f"staleword{i:04d}", old_date, old_date),
        )
    conn.commit()
    conn.close()
    deleted = frequency_db.prune_db(DB)
    assert deleted > 0, f"Expected pruning to delete stale rows, got {deleted}"
    stats = frequency_db.get_phrase_stats(DB)
    assert stats["total_phrases"] < 100
    print(f"[OK] prune_db (deleted {deleted} stale rows)")

    cleanup()
    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    main()
