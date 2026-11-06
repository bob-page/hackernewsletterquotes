#!/usr/bin/env python3
"""Add any new issues to quotes.csv from the public Buttondown archive.

Starts at the issue after the highest number in the file and stops once the next
few numbers aren't published, in case a number gets skipped. Exits 1 if a published page can't be parsed, so a
format change fails visibly instead of adding a bad row.
"""
import argparse
import html
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

from build_readme import render
from quoteslib import README_PATH, read_rows, related_note, write_rows

URL = "https://buttondown.com/hacker-newsletter/archive/{}/"
USER_AGENT = "hackernewsletterquotes-bot"
STANDARD_MASTHEAD = "hackernewsletter"
LOOK_AHEAD = 3


class ParseError(Exception):
    pass


def fetch(issue):
    """Return the page HTML, or None if the issue isn't published yet."""
    request = urllib.request.Request(URL.format(issue), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def page_lines(page):
    page = re.sub(r"(?is)<(script|style|head)\b.*?</\1>", " ", page)
    page = re.sub(r"(?i)<br\s*/?>|</(p|div|td|h\d|li|tr)>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page))
    lines = (re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.split("\n"))
    return [line for line in lines if line]


def parse_date(text):
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group()
    match = re.search(r"[A-Z][a-z]+ \d{1,2}, \d{4}", text)
    if match:
        return datetime.strptime(match.group(), "%B %d, %Y").strftime("%Y-%m-%d")
    raise ParseError("no date near the issue number")


def parse_issue(page):
    """Return (quote, attribution, date, printed_issue, masthead)."""
    lines = page_lines(page)
    at = next((i for i, line in enumerate(lines) if re.search(r"Issue #\d", line)), None)
    if at is None or at < 2:
        raise ParseError("no issue line")
    printed = re.search(r"Issue #\s*([\d.]+)", lines[at]).group(1)
    date = parse_date(" ".join(lines[at : at + 8]))
    masthead = lines[at - 1]
    text = lines[at - 2]
    if text.startswith("//"):
        if at < 3:
            raise ParseError("attribution with no quote")
        text = f"{lines[at - 3]} {text}"
    if "//" not in text:
        raise ParseError(f"no quote before the masthead: {text[:80]!r}")
    quote, attribution = (part.strip() for part in text.rsplit("//", 1))
    if not quote or not attribution:
        raise ParseError(f"incomplete quote: {text[:80]!r}")
    return quote.strip('"“”').strip(), attribution, date, printed, masthead


def make_row(issue, page, earlier_rows):
    quote, attribution, date, printed, masthead = parse_issue(page)
    notes = []
    related = related_note(quote, earlier_rows)
    if related:
        notes.append(related)
    if printed != str(issue):
        notes.append(f"Page says #{printed}")
    if masthead.replace(" ", "").lower() != STANDARD_MASTHEAD:
        notes.append(f'Masthead: "{masthead}"')
    return dict(issue=str(issue), date=date, quote=quote, attribution=attribution, notes="; ".join(notes))


def highest_issue(rows):
    return max(int(float(r["issue"])) for r in rows if r["issue"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print new rows without saving")
    args = parser.parse_args()

    rows = read_rows()
    added = []
    latest = highest_issue(rows)
    misses = 0
    while misses < LOOK_AHEAD:
        issue = latest + misses + 1
        page = fetch(issue)
        time.sleep(1)
        if page is None:
            misses += 1
            continue
        try:
            row = make_row(issue, page, rows)
        except ParseError as error:
            print(f"Issue #{issue}: {error} ({URL.format(issue)})", file=sys.stderr)
            sys.exit(1)
        rows.append(row)
        added.append(row)
        print(f"#{row['issue']} {row['date']}: {row['quote']} //{row['attribution']}")
        latest = issue
        misses = 0

    if not added:
        print(f"No new issues after #{latest}")
    elif not args.dry_run:
        write_rows(rows)
        README_PATH.write_text(render(rows), encoding="utf-8")


if __name__ == "__main__":
    main()
