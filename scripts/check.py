#!/usr/bin/env python3
"""Validate quotes.csv. Exits 1 on problems."""
import csv
import io
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone

from quoteslib import CSV_PATH, FIELDS, label, normalize

FIRST_YEAR = 2010
FIRST_CONTINUOUS_ISSUE = 22  # Every number from here on has a row, found or not.
FIRST_ORDERED_ISSUE = 64  # Earlier numbers are unreliable and can be out of order.
MAX_QUOTE_LENGTH = 600

ISSUE = re.compile(r"[1-9]\d*(\.\d+)?")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
WEEK_DATE = re.compile(r"(\d{4}), week (\d{1,2})")
UNKNOWN_DATE = "2011, date unknown"
REFERENCE = re.compile(r"\b(Dup|Variant) of (#[\d.]*\d|\d{4}, week \d{1,2})")

BAD_TEXT = [
    (re.compile(r"[\x00-\x1f\x7f ​-‍⁠﻿]"), "control or invisible character"),
    (re.compile(r"&(?:[a-zA-Z]+|#\d+);"), "HTML entity"),
    (re.compile(r"</?(?:a|b|i|p|br|em|strong|span|div)\b[^>]*>", re.I), "HTML tag"),
    (re.compile("â€|[ÃÂ][\u0080-¿]|�"), "garbled text"),
]


def read_file(path=CSV_PATH):
    """Return (rows, problems). Rows are (line, row) pairs. Problems are (line, message) pairs."""
    raw = path.read_bytes()
    problems = []
    if raw.startswith(b"\xef\xbb\xbf"):
        problems.append((1, "remove the byte order mark at the start of the file"))
    if b"\r" in raw:
        problems.append((None, "use LF line endings, not CRLF"))
    if not raw.endswith(b"\n"):
        problems.append((None, "the file must end with a newline"))
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        return [], problems + [(None, f"not valid UTF-8: {error}")]

    rows = []
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    try:
        header = next(reader, None)
        if header != FIELDS:
            return [], problems + [(1, f"expected columns {FIELDS}, got {header}")]
        for values in reader:
            if len(values) != len(FIELDS):
                problems.append((reader.line_num, f"expected {len(FIELDS)} columns, got {len(values)}"))
            else:
                rows.append((reader.line_num, dict(zip(FIELDS, values))))
    except csv.Error as error:
        problems.append((reader.line_num, f"bad CSV: {error}"))
    return rows, problems


def check_date(value, today):
    """Return (date or None, problem or None) for a date column."""
    if ISO_DATE.fullmatch(value):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            return None, f"{value!r} isn't a real date"
        if parsed.year < FIRST_YEAR or parsed > today + timedelta(days=1):
            return None, f"date {value!r} is out of range"
        return parsed, None
    week = WEEK_DATE.fullmatch(value)
    if week:
        if not FIRST_YEAR <= int(week[1]) <= today.year or not 1 <= int(week[2]) <= 53:
            return None, f"date {value!r} is out of range"
        return None, None
    if value == UNKNOWN_DATE:
        return None, None
    return None, f"bad date {value!r}: use YYYY-MM-DD"


def check_text(name, value):
    problems = []
    if value != value.strip():
        problems.append(f"stray whitespace in {name}")
    for pattern, description in BAD_TEXT:
        if pattern.search(value):
            problems.append(f"{description} in {name}")
    return problems


def check_row(row, today):
    problems = []
    for name in FIELDS:
        problems += check_text(name, row[name])

    if row["issue"] and not ISSUE.fullmatch(row["issue"]):
        problems.append(f"bad issue number {row['issue']!r}")
    if not row["issue"] and not row["date"]:
        problems.append("needs an issue number or a date")

    if row["quote"]:
        if not row["date"]:
            problems.append("a quote needs a date")
        if not row["attribution"] and not row["notes"]:
            problems.append("a quote needs an attribution, or a note explaining why it has none")
        if re.search(r'^["“”]|["“”]$', row["quote"]):
            problems.append("leave quotation marks off the quote")
        if "//" in row["quote"]:
            problems.append("the attribution belongs in its own column, not after // in the quote")
        if len(row["quote"]) > MAX_QUOTE_LENGTH:
            problems.append(f"the quote is over {MAX_QUOTE_LENGTH} characters: is it only the quote?")
        if "Not found" in row["notes"]:
            problems.append("remove the 'Not found' note now that the row has a quote")
    else:
        if not row["notes"]:
            problems.append("a row with no quote needs a note")
        if row["attribution"]:
            problems.append("attribution without a quote")

    if re.match(r"[/\-–—]", row["attribution"]):
        problems.append("leave the leading mark off the attribution")
    if any(not part.strip() for part in row["notes"].split(";")) and row["notes"]:
        problems.append("empty note: separate notes with '; '")
    return problems


def check_references(row, earlier):
    """Check Dup and Variant notes against earlier rows with quotes, keyed by label."""
    problems = []
    marked = "Same page content as" in row["notes"]
    for kind, target in REFERENCE.findall(row["notes"]):
        other = earlier.get(target)
        if other is None:
            problems.append(f"{kind} note points to {target}, which isn't an earlier row with a quote")
        elif kind == "Dup":
            marked = True
            if normalize(other["quote"]) != normalize(row["quote"]):
                problems.append(f"marked as a dup of {target}, but the quotes differ")
    if row["quote"] and not marked:
        for other in earlier.values():
            if normalize(other["quote"]) == normalize(row["quote"]):
                problems.append(f"repeats {label(other)}: add the note 'Dup of {label(other)}'")
                break
    return problems


def find_problems(rows, today=None):
    today = today or datetime.now(timezone.utc).date()
    problems = []
    seen = {}
    earlier = {}
    last_date = last_issue = None

    for line, row in rows:
        found = check_row(row, today)
        parsed, problem = check_date(row["date"], today) if row["date"] else (None, None)
        if problem:
            found.append(problem)
        if parsed:
            if last_date and parsed < last_date:
                found.append(f"date {row['date']} is earlier than the row before it ({last_date})")
            last_date = parsed

        issue = row["issue"]
        if ISSUE.fullmatch(issue):
            if issue in seen:
                found.append(f"issue #{issue} appears twice, also on line {seen[issue]}")
            seen.setdefault(issue, line)
            number = float(issue)
            if number >= FIRST_ORDERED_ISSUE:
                if last_issue and number <= last_issue:
                    found.append(f"issue #{issue} is out of order: rows go oldest first")
                last_issue = number

        found += check_references(row, earlier)
        if row["quote"]:
            earlier.setdefault(label(row), row)
        problems += [(line, message) for message in found]

    numbers = {int(float(issue)) for issue in seen}
    if numbers:
        for number in range(max(FIRST_CONTINUOUS_ISSUE, min(numbers)), max(numbers)):
            if number not in numbers:
                problems.append((None, f"issue #{number} has no row: keep it with a 'Not found' note"))
    return problems


def report(line, message):
    place = f"quotes.csv line {line}" if line else "quotes.csv"
    if os.environ.get("GITHUB_ACTIONS"):
        safe = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        print(f"::error file=quotes.csv{f',line={line}' if line else ''}::{safe}")
    else:
        print(f"{place}: {message}")


def main():
    rows, problems = read_file()
    problems += find_problems(rows)
    for line, message in problems:
        report(line, message)
    if problems:
        sys.exit(1)
    print(f"OK: {len(rows)} rows")


if __name__ == "__main__":
    main()
