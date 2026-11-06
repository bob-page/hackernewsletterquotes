"""Shared helpers for reading quotes.csv and spotting repeated quotes."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "quotes.csv"
README_PATH = ROOT / "README.md"
FIELDS = ["issue", "date", "quote", "attribution", "notes"]
VARIANT_THRESHOLD = 0.7


def read_rows(path=CSV_PATH):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError(f"{path}: expected columns {FIELDS}, got {reader.fieldnames}")
        return list(reader)


def write_rows(rows, path=CSV_PATH):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def normalize(quote):
    """Compare quotes on their words alone, ignoring case and punctuation."""
    return re.sub(r"\W", "", quote.lower())


def tokens(quote):
    return set(re.findall(r"\w+", quote.lower()))


def label(row):
    return f"#{row['issue']}" if row["issue"] else row["date"]


def related_note(quote, rows):
    """Return a 'Dup of' or 'Variant of' note against earlier rows, or ''."""
    key = normalize(quote)
    words = tokens(quote)
    variant = None
    for row in rows:
        if not row["quote"]:
            continue
        if normalize(row["quote"]) == key:
            return f"Dup of {label(row)}"
        other = tokens(row["quote"])
        union = words | other
        if variant is None and len(words) >= 4 and len(words & other) / len(union) >= VARIANT_THRESHOLD:
            variant = row
    return f"Variant of {label(variant)}" if variant else ""
