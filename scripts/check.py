#!/usr/bin/env python3
"""Validate quotes.csv and confirm README.md is up to date. Exits 1 on problems."""
import re
import sys

from build_readme import render
from quoteslib import README_PATH, read_rows

DATE = re.compile(r"^(\d{4}-\d{2}-\d{2}|\d{4}, week \d{1,2}|2011, date unknown)$")


def find_problems(rows):
    problems = []
    seen = set()
    for line, row in enumerate(rows, start=2):
        where = f"quotes.csv line {line}"
        issue = row["issue"]
        if issue:
            if not re.fullmatch(r"\d+(\.\d+)?", issue):
                problems.append(f"{where}: bad issue number {issue!r}")
            if issue in seen:
                problems.append(f"{where}: issue #{issue} appears twice")
            seen.add(issue)
        elif not row["date"]:
            problems.append(f"{where}: needs an issue number or a date")
        if row["date"] and not DATE.match(row["date"]):
            problems.append(f"{where}: bad date {row['date']!r}")
        if row["quote"] and not row["date"]:
            problems.append(f"{where}: a quote needs a date")
        if not row["quote"] and not row["notes"]:
            problems.append(f"{where}: a row with no quote needs a note")
        if row["attribution"] and not row["quote"]:
            problems.append(f"{where}: attribution without a quote")
        for name, value in row.items():
            if value != value.strip() or "\n" in value:
                problems.append(f"{where}: stray whitespace in {name}")
    return problems


def main():
    rows = read_rows()
    problems = find_problems(rows)
    if README_PATH.read_text(encoding="utf-8") != render(rows):
        problems.append("README.md is out of date: run python3 scripts/build_readme.py")
    for problem in problems:
        print(problem)
    if problems:
        sys.exit(1)
    print(f"OK: {len(rows)} rows")


if __name__ == "__main__":
    main()
