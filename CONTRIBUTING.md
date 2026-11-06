# Contributing

Corrections and missing issues are welcome. Edit `quotes.csv`, not the table in the README, which is generated from it.

## What's most useful

- **Missing issues:** rows with no quote and a "Not found" note, especially #252–317. If you have the old email, fill in the row and remove the note.
- **Wrong attributions:** change the attribution and link your source in the pull request. Keep a note saying what the issue originally printed, for example `Printed as Mark Twain`.
- **Early issues:** before about #64, some rows may have the wrong number.

## Columns

| Column | Format |
| --- | --- |
| `issue` | Number without the `#`. Blank for 2010 issues, which have no number. |
| `date` | The date printed in the issue, as `YYYY-MM-DD`. Older rows use a form like `2011, week 24`. |
| `quote` | The quote, without quotation marks. |
| `attribution` | The name as printed, unless you're correcting it. |
| `notes` | Anything else, such as `Dup of #123` or `Variant of #123`. Separate notes with `; `. |

## Before opening a pull request

```bash
python3 scripts/build_readme.py
```

```bash
python3 scripts/check.py
```

New issues are added automatically each week, so there's no need to send those.

By contributing, you agree to release your contribution under [CC0 1.0](LICENSE).
