"""Summarize human rubric scores for paired AI responses."""
import argparse
from collections import defaultdict
import csv
from dataclasses import dataclass
from fractions import Fraction
from html import escape
from pathlib import Path
from statistics import mean

DIMENSIONS = ("accuracy", "instruction_following", "clarity")
FIELDS = ("case_id", "language", "prompt", "reference", "response_a", "response_b",
          *(f"{side}_{dimension}" for side in "ab" for dimension in DIMENSIONS), "notes")
LANGUAGES = {"en": "English", "es": "Spanish", "pt": "Portuguese"}


@dataclass(frozen=True)
class Review:
    case_id: str
    language: str
    prompt: str
    reference: str
    response_a: str
    response_b: str
    a: tuple[int, ...]
    b: tuple[int, ...]
    notes: str


def load_reviews(path: Path) -> list[Review]:
    """Read UTF-8 annotations and report invalid rows with their line number."""
    reviews = []
    seen = set()
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file, strict=True)
        if reader.fieldnames is None or sorted(reader.fieldnames) != sorted(FIELDS):
            raise ValueError("CSV headers must match the sample schema.")
        for raw in reader:
            line = reader.line_num
            if None in raw or any(value is None or not value.strip() for value in raw.values()):
                raise ValueError(f"Line {line}: every column must contain a value.")
            row = {key: value.strip() for key, value in raw.items()}
            if row["case_id"] in seen:
                raise ValueError(f"Line {line}: duplicate case ID {row['case_id']!r}.")
            if row["language"] not in LANGUAGES:
                raise ValueError(f"Line {line}: language must be en, es, or pt.")
            scores = []
            for side in "ab":
                values = []
                for dimension in DIMENSIONS:
                    field = f"{side}_{dimension}"
                    if row[field] not in {"0", "1", "2"}:
                        raise ValueError(f"Line {line}: {field} must be 0, 1, or 2.")
                    values.append(int(row[field]))
                scores.append(tuple(values))
            reviews.append(Review(
                row["case_id"], row["language"], row["prompt"], row["reference"],
                row["response_a"], row["response_b"], *scores, row["notes"]
            ))
            seen.add(row["case_id"])
    if not reviews:
        raise ValueError("CSV must contain at least one review.")
    return reviews


def weighted_score(scores: tuple[int, ...]) -> Fraction:
    accuracy, instructions, clarity = scores
    return Fraction(5 * accuracy + 3 * instructions + 2 * clarity, 10)


def preference(review: Review) -> str:
    difference = weighted_score(review.a) - weighted_score(review.b)
    if difference == 0:
        return "Tie"
    return "A" if difference > 0 else "B"


def summary_row(label: str, reviews: list[Review]) -> dict:
    results = [preference(review) for review in reviews]
    return {
        "group": label, "cases": len(reviews),
        "a_wins": results.count("A"), "b_wins": results.count("B"),
        "ties": results.count("Tie"),
        "a_mean": f"{float(mean(weighted_score(review.a) for review in reviews)):.2f}",
        "b_mean": f"{float(mean(weighted_score(review.b) for review in reviews)):.2f}",
    }


def summarize(reviews: list[Review]) -> list[dict]:
    groups = defaultdict(list)
    for review in reviews:
        groups[review.language].append(review)
    return [summary_row("Overall", reviews)] + [
        summary_row(label, groups[code]) for code, label in LANGUAGES.items() if code in groups
    ]


def render_report(reviews: list[Review], summary: list[dict]) -> str:
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row.values()) + "</tr>"
        for row in summary
    )
    cases = []
    for review in reviews:
        cases.append(f"""
        <details><summary>{escape(review.case_id)} · {LANGUAGES[review.language]} · {preference(review)}</summary>
        <p><strong>Prompt</strong> {escape(review.prompt)}</p>
        <p><strong>Reference</strong> {escape(review.reference)}</p>
        <p><strong>Response A</strong> {escape(review.response_a)} <small>Rubric {review.a}</small></p>
        <p><strong>Response B</strong> {escape(review.response_b)} <small>Rubric {review.b}</small></p>
        <p><strong>Annotation note</strong> {escape(review.notes)}</p></details>
        """)
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Multilingual AI Response Review</title>
<style>
* {{box-sizing:border-box}} body {{margin:0;background:#edf2f4;color:#172b37;font:16px/1.55 system-ui,sans-serif}}
main {{max-width:960px;margin:auto;padding:clamp(16px,5vw,48px)}} header {{background:#163340;color:#fff;padding:clamp(20px,5vw,40px);border-radius:18px}}
h1 {{font-size:clamp(32px,6vw,52px);line-height:1.05;letter-spacing:-.04em;margin:0 0 16px}}
h2 {{margin-top:32px}} p {{margin:12px 0}} .table {{overflow:auto;border-radius:12px}}
table {{width:100%;border-collapse:collapse;background:white;white-space:nowrap}}
th,td {{text-align:left;padding:12px;border-bottom:1px solid #dae4e8}} th {{background:#dcebe8}}
details {{background:#fff;border-radius:10px;margin:8px 0;padding:12px 16px;overflow-wrap:anywhere}}
summary {{cursor:pointer;font-weight:650}} small {{color:#49616d}}
</style>
<main><header><h1>Multilingual AI Response Review</h1>
<p>{len(reviews)} paired cases with synthetic prompts, responses, and illustrative annotations.</p></header>
<h2>Rubric results</h2>
<p>Weighted scores range from 0 to 2. Accuracy counts for 50%, instruction following for 30%, and clarity for 20%. These sample results describe the supplied examples only.</p>
<div class="table"><table aria-label="Response preference by language">
<thead><tr><th scope="col">Group</th><th scope="col">Cases</th><th scope="col">A wins</th>
<th scope="col">B wins</th><th scope="col">Ties</th><th scope="col">A mean</th><th scope="col">B mean</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<h2>Case review</h2><p>Select a case to see the prompt, reference, and annotation. Rubric values appear in the order accuracy, instruction following, and clarity.</p>
{''.join(cases)}</main></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="CSV of annotated response pairs")
    parser.add_argument("--out", type=Path, required=True, help="Output directory")
    args = parser.parse_args()
    try:
        reviews = load_reviews(args.input)
        summary = summarize(reviews)
        args.out.mkdir(parents=True, exist_ok=True)
        paths = [args.out / "summary.csv", args.out / "AI_Response_Review.html"]
        if args.input.resolve() in [path.resolve() for path in paths] or any(
            path.exists() and path.samefile(args.input) for path in paths
        ):
            raise ValueError("Output files must be separate from the input CSV.")
        with paths[0].open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=list(summary[0]))
            writer.writeheader()
            writer.writerows(summary)
        paths[1].write_text(render_report(reviews, summary), encoding="utf-8")
    except (OSError, ValueError, csv.Error) as error:
        parser.exit(2, f"Error: {error}\n")
    print(f"Reviewed {len(reviews)} pairs. Reports written to {args.out}")


if __name__ == "__main__":
    main()
