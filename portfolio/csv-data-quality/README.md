# CSV Data Cleanup & Quality Audit — Reproducible Portfolio Demo

**An executable demonstration using fictional records. This is not a paid-client case study.**

## Deliverable for a client
- Cleaned UTF-8 CSV or Excel workbook, with duplicate/format checks
- An exception register for missing, invalid and conflicting values
- Reconciliation: input and output row totals, categories of changes
- All unverified information left unchanged and clearly flagged

## Reproduce this exact test (Python 3, standard library only)
```bash
python clean_csv.py sample_input.csv --out-dir results
```

The repository contains [the Python script](./clean_csv.py) and [fictional input CSV](./sample_input.csv). It does not send files to third-party services.

### Confirmed result
| Check | Result |
|---|---:|
| Input rows | 12 |
| Output rows | 10 |
| Exact normalized email duplicates merged | 2 |
| Review flags, including conflict flags | 6 |
| Country values standardized | 9 |
| Dates standardized | 5 |

### Important safeguards
- Email checks verify **syntax only**; they **do not verify mailbox deliverability**.
- Deduplication requires exact normalized syntactically valid email addresses, not fuzzy guesswork.
- Ambiguous dates remain unchanged and are marked for manual review.
- Conflicts between duplicate rows are noted; no fabricated fields or enrichment.
- A client project involving personal data requires agreed processing terms and safe transfer **before** any file is shared.
- CSV values are not sanitized for spreadsheet formula injection; this demo is only safe for trusted synthetic input. Production work requires a separate output-escaping policy and client approval.

## Pilot offer
**USD $25 introductory fixed-price** for up to **1,000 straightforward CSV rows**, after reviewing a redacted sample and confirming the rules. Deliverable: cleaned CSV, issue register and QA summary. Web research, real email deliverability, CRM integration, sensitive data handling, and custom rules are excluded unless separately agreed.

For a scope quote, contact the repository owner using their public profile or create an issue here. No success or past client orders are claimed.
