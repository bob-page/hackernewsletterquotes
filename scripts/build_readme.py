#!/usr/bin/env python3
"""Generate README.md from quotes.csv. Edit quotes.csv, not the README table."""
from quoteslib import README_PATH, normalize, read_rows

INTRO = """# Hacker Newsletter Quotes

Every issue of [Hacker Newsletter](https://hackernewsletter.com/) opens with a short quote. This is an attempt to collect all of them.

This is an unofficial fan project and isn't affiliated with the newsletter. Corrections and missing issues are welcome: see [CONTRIBUTING.md](CONTRIBUTING.md).

**{unique} unique quotes from {issues} issues**, newest first. {missing} issue numbers are still missing.

- Attributions are as printed in the newsletter and haven't been verified.
- Dates are the date printed in each issue.
- Before about #64 (2011), some archived pages show another issue's content, so those numbers are unreliable.
- Issues from 2010 have no number.
- This collection is released under [CC0 1.0](LICENSE). That covers the compilation only: rights in the quotes and the newsletter stay with their owners.

<!-- Generated from quotes.csv by scripts/build_readme.py. Don't edit below this line. -->

| Issue | Date | Quote | Attribution | Notes |
| --- | --- | --- | --- | --- |
"""


def cell(value):
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def render(rows):
    with_quote = [r for r in rows if r["quote"]]
    missing = sum(1 for r in rows if not r["quote"] and "Not found" in r["notes"])
    text = INTRO.format(
        unique=len({normalize(r["quote"]) for r in with_quote}),
        issues=len(with_quote),
        missing=missing,
    )
    for r in reversed(rows):
        issue = f"#{r['issue']}" if r["issue"] else ""
        text += f"| {issue} | {cell(r['date'])} | {cell(r['quote'])} | {cell(r['attribution'])} | {cell(r['notes'])} |\n"
    return text


def main():
    README_PATH.write_text(render(read_rows()), encoding="utf-8")


if __name__ == "__main__":
    main()
