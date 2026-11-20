import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace

from review import load_reviews, preference, render_report, summarize

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "sample_reviews.csv"


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.reviews = load_reviews(SAMPLE)

    def test_equal_weighted_scores_with_different_rubric_scores(self):
        review = replace(self.reviews[0], a=(2, 0, 0), b=(0, 2, 2))
        self.assertEqual(preference(review), "Tie")

    def test_summary_counts(self):
        overall, english, spanish, portuguese = summarize(self.reviews)
        self.assertEqual((overall["a_wins"], overall["b_wins"], overall["ties"]), (5, 4, 3))
        self.assertEqual([row["cases"] for row in (english, spanish, portuguese)], [4, 4, 4])

    def test_invalid_score_identifies_line_and_field(self):
        with SAMPLE.open(encoding="utf-8", newline="") as file:
            rows = list(csv.reader(file))
        rows[1][rows[0].index("a_accuracy")] = "3"
        with tempfile.TemporaryDirectory() as temp:
            invalid = Path(temp) / "invalid.csv"
            with invalid.open("w", encoding="utf-8", newline="") as file:
                csv.writer(file).writerows(rows)
            with self.assertRaisesRegex(ValueError, r"Line 2: a_accuracy"):
                load_reviews(invalid)

    def test_report_escapes_csv_text(self):
        reviews = [replace(self.reviews[0], response_a="<script>test</script>")]
        report = render_report(reviews, summarize(reviews))
        self.assertIn("&lt;script&gt;", report)
        self.assertNotIn("<script>", report)

    def test_cli_reproduces_sample_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(
                [sys.executable, str(ROOT / "review.py"), str(SAMPLE), "--out", temp],
                check=True, capture_output=True, text=True,
            )
            for expected in (ROOT / "example_output").iterdir():
                self.assertEqual((Path(temp) / expected.name).read_bytes(), expected.read_bytes())


if __name__ == "__main__":
    unittest.main()
