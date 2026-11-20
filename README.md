# Multilingual AI Response Review

A Python command-line project that turns rubric annotations into a CSV summary and a browser-readable report. The sample has 13 paired examples in English, Spanish, and Portuguese. Each case includes a reference answer and a note explaining the evaluation.

Open [the sample report](example_output/AI_Response_Review.html) locally in a browser to review the results and expand individual cases.

## Run it

Use Python 3.10 or later. The project uses the standard library and runs offline.

```sh
python review.py data/sample_reviews.csv --out reports
python -m unittest discover -s tests -v
```

On systems where Python 3 is installed as `python3` or `py -3`, use that command in place of `python`. The command writes `reports/summary.csv` and `reports/AI_Response_Review.html`.

## How scoring works

| Dimension | Weight | 0 | 1 | 2 |
| --- | ---: | --- | --- | --- |
| Accuracy | 50% | Materially wrong | Partially correct or missing a material detail | Matches the reference |
| Instruction following | 30% | Violates an explicit format or core constraint | Follows part of the request | Follows all explicit requirements |
| Clarity | 20% | Hard to understand | Understandable with awkward phrasing | Clear and direct |

Score each response against the prompt and reference. Enter one 0–2 score per dimension and include an annotation note. A response's overall score is the weighted sum of its three scores. Equal weighted scores count as ties. Group means include every case in the group.

For example, ES-04 asks for only the number of minutes. Response A gives “25 minutos,” which earns full accuracy but zero for instruction following. Response B gives “25,” earning full points on both dimensions. This distinction makes format failures visible even when the content is right.

## Project files

| Path | Contents |
| --- | --- |
| `review.py` | Input validation, exact weighted scoring, grouping, and report generation |
| `data/sample_reviews.csv` | Synthetic prompts, responses, rubric scores, and notes |
| `example_output/` | Reproducible HTML report and CSV summary |
| `tests/test_review.py` | Tests for ties, invalid input, escaped HTML, and reproducible CLI output |

## Sample results and scope

Across 13 cases, A wins 6, B wins 4, and 3 tie. The sample is synthetic, and the rubric scores are illustrative. No live model was called. The tool summarizes supplied annotations; it does not judge new responses automatically or measure model performance. This project was created with AI assistance, including the ES-05 example.

## Make it your own

After running the sample, add one original case to the CSV. Write a prompt and reference, draft two candidate responses, score them independently, and explain the difference in the notes. Regenerate the report and check that the case count and its language grouping update. Retain the synthetic-data description for any examples you draft yourself.
