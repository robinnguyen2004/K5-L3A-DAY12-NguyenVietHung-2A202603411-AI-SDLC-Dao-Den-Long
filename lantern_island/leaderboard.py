"""Local leaderboard (Ticket-04 section 3), stdlib only.

Stored as JSON on the local disk (default ~/.dao-den-long/leaderboard.json; override with the
DDL_DATA_DIR environment variable), so it survives closing and reopening the game.
Entry: {name, score, nights_won, achieved_at (ISO 8601 with timezone), seed}.
Top 10, score descending; equal scores -> whoever achieved it first ranks higher.
"""
import datetime
import json
import os
import tempfile
import unicodedata

TOP = 10
NAME_MIN, NAME_MAX = 3, 12


def data_path():
    base = os.environ.get("DDL_DATA_DIR") or os.path.join(os.path.expanduser("~"), ".dao-den-long")
    return os.path.join(base, "leaderboard.json")


def clean_name(name):
    """Return the NFC name if valid, else None. Allowed: 3-12 of [A-Za-z0-9_]; Vietnamese letters with
    diacritics (Latin script) are accepted as the optional bonus."""
    if not isinstance(name, str):
        return None
    n = unicodedata.normalize("NFC", name.strip())
    if not NAME_MIN <= len(n) <= NAME_MAX:
        return None
    for ch in n:
        if ch == "_" or ("0" <= ch <= "9") or ("A" <= ch <= "Z") or ("a" <= ch <= "z"):
            continue
        if ch.isalpha() and unicodedata.name(ch, "").startswith("LATIN"):
            continue
        return None
    return n


def _when(entry):
    return datetime.datetime.fromisoformat(entry["achieved_at"])


def sort_entries(entries):
    """score desc, then earlier achieved_at first (timezone-aware comparison); stable."""
    return sorted(entries, key=lambda e: (-int(e["score"]), _when(e)))[:TOP]


def load(path=None):
    path = path or data_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        entries = [e for e in data.get("entries", []) if isinstance(e, dict) and clean_name(e.get("name"))]
        return sort_entries(entries)
    except (OSError, ValueError, KeyError, TypeError):
        return []


def save(entries, path=None):
    path = path or data_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"entries": entries}, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)  # atomic: a crash never leaves a half-written file


def make_entry(name, score, nights_won, seed, achieved_at=None):
    n = clean_name(name)
    if n is None:
        raise ValueError("Tên phải có 3-12 ký tự: chữ cái, chữ số hoặc _ (cho phép chữ tiếng Việt có dấu)")
    if not isinstance(score, int) or isinstance(score, bool) or score < 0:
        raise ValueError("score must be a non-negative integer")
    if not isinstance(nights_won, int) or isinstance(nights_won, bool) or not 0 <= nights_won <= 3:
        raise ValueError("nights_won must be 0-3")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    when = achieved_at or datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if datetime.datetime.fromisoformat(when).tzinfo is None:
        raise ValueError("achieved_at needs a timezone")
    return {"name": n, "score": score, "nights_won": nights_won, "achieved_at": when, "seed": seed}


def add(name, score, nights_won, seed, achieved_at=None, path=None):
    """Validate, insert, keep the top 10, persist. Returns (entries, rank or None if it did not make the top 10)."""
    e = make_entry(name, score, nights_won, seed, achieved_at)
    entries = load(path) + [e]
    top = sort_entries(entries)
    save(top, path)
    rank = next((i + 1 for i, x in enumerate(top) if x is e), None)
    return top, rank


def export(out_path, path=None):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"entries": load(path)}, f, ensure_ascii=False, indent=2)
        f.write("\n")
