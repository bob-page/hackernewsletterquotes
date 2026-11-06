"""Tests for the quotes.csv validator."""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from check import find_problems, read_file

TODAY = date(2026, 11, 6)


def row(issue="100", day="2020-01-03", quote="Some quote here.", attribution="Someone", notes=""):
    return dict(issue=issue, date=day, quote=quote, attribution=attribution, notes=notes)


def messages(*rows):
    numbered = list(enumerate(rows, start=2))
    return [message for _, message in find_problems(numbered, TODAY)]


class Rows(unittest.TestCase):
    def assert_flags(self, text, *rows):
        found = messages(*rows)
        self.assertTrue(any(text in message for message in found), found)

    def test_good_rows_pass(self):
        self.assertEqual(messages(row(), row("101", "2020-01-10", "Another quote.")), [])

    def test_dates(self):
        self.assert_flags("isn't a real date", row(day="2026-13-99"))
        self.assert_flags("isn't a real date", row(day="2023-02-29"))
        self.assert_flags("out of range", row(day="2009-12-31"))
        self.assert_flags("out of range", row(day="2026-11-08"))
        self.assert_flags("out of range", row(day="2011, week 54"))
        self.assert_flags("bad date", row(day="Oct 30"))
        self.assert_flags("earlier than", row("100", "2020-02-07"), row("101", "2020-01-03", "Other."))
        self.assertEqual(messages(row(day="2026-11-07")), [])

    def test_issues(self):
        self.assert_flags("bad issue number", row("0817"))
        self.assert_flags("bad issue number", row("#817"))
        self.assert_flags("appears twice", row(), row(quote="Other."))
        self.assert_flags("out of order", row("101"), row("100", quote="Other."))
        self.assert_flags("#101 has no row", row("100"), row("102", quote="Other."))

    def test_early_issues_can_be_out_of_order(self):
        self.assertEqual(messages(row("23"), row("22", "2011, week 24", "Other.")), [])

    def test_text(self):
        self.assert_flags("stray whitespace", row(quote=" Padded."))
        self.assert_flags("HTML entity", row(quote="Fish &amp; chips"))
        self.assert_flags("HTML tag", row(quote="Bold <b>move</b>"))
        self.assert_flags("garbled", row(quote="Donâ€™t panic"))
        self.assert_flags("invisible", row(quote="Odd space"))
        self.assert_flags("quotation marks", row(quote='"Wrapped"'))
        self.assert_flags("own column", row(quote="Words //Someone"))
        self.assert_flags("over 600", row(quote="x" * 601))
        self.assert_flags("leading mark", row(attribution="//Someone"))

    def test_missing_fields(self):
        self.assert_flags("needs a note", row(quote="", attribution=""))
        self.assert_flags("attribution without", row(quote="", notes="Not found"))
        self.assert_flags("needs an attribution", row(attribution=""))
        self.assert_flags("needs a date", row(day=""))
        self.assert_flags("remove the 'Not found'", row(notes="Not found"))
        self.assertEqual(messages(row(day="", quote="", attribution="", notes="Not found")), [])

    def test_references(self):
        first = row("100")
        self.assert_flags("repeats #100", first, row("101", "2020-01-10"))
        self.assert_flags("isn't an earlier row", first, row("101", "2020-01-10", "Other.", notes="Dup of #999"))
        self.assert_flags("quotes differ", first, row("101", "2020-01-10", "Other.", notes="Dup of #100"))
        self.assertEqual(messages(first, row("101", "2020-01-10", notes="Dup of #100")), [])
        self.assertEqual(messages(first, row("101", "2020-01-10", "Some quote there.", notes="Variant of #100")), [])
        self.assertEqual(messages(first, row("101", "2020-01-10", notes="Same page content as #100")), [])


class File(unittest.TestCase):
    def problems(self, content):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "quotes.csv"
            path.write_bytes(content)
            return [message for _, message in read_file(path)[1]]

    def assert_flags(self, text, content):
        found = self.problems(content)
        self.assertTrue(any(text in message for message in found), found)

    HEADER = b"issue,date,quote,attribution,notes\n"

    def test_good_file_passes(self):
        self.assertEqual(self.problems(self.HEADER + b'1,2020-01-03,"A, quote",Someone,\n'), [])

    def test_bad_files(self):
        self.assert_flags("expected columns", b"issue,date\n")
        self.assert_flags("expected 5 columns", self.HEADER + b"1,2020-01-03\n")
        self.assert_flags("expected 5 columns", self.HEADER + b"1,2,3,4,5,6\n")
        self.assert_flags("CRLF", self.HEADER.replace(b"\n", b"\r\n"))
        self.assert_flags("end with a newline", self.HEADER.rstrip())
        self.assert_flags("byte order mark", b"\xef\xbb\xbf" + self.HEADER)
        self.assert_flags("not valid UTF-8", self.HEADER + b"1,2020-01-03,caf\xe9,x,\n")
        self.assert_flags("bad CSV", self.HEADER + b'1,2020-01-03,"unclosed,x,\n')


if __name__ == "__main__":
    unittest.main()
