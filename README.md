MagangHub Advanced Filters — scraper, merger, and search toolkit for vacancies
====================================================================

This repository provides an OOP Python client and command-line tools to
scrape the MagangHub public vacancies API, persist raw page JSON (each
file contains an ISO UTC `_scraped_at` timestamp), merge saved pages into
a single file, and run powerful local searches. Key features include a
resilient `requests`-based scraper, a merger for numeric page files,
structured filters (e.g. `--nama_kabupaten`, `--program_studi`,
`--posisi`, `--deskripsi_posisi`), a government-postings filter
(`--gov` with `0|1|2` semantics), free-text deep search, and optional
JSON export with helper fields such as `_applicants_per_slot` and
`_acceptance_prob`.

What is included
-----------------
- `maganghub_client/` — client, models, scraper and search utilities.
- `scripts/scrape_and_save.py` — paginate the API and save each page as `1.json`, `2.json`, ...
- `scripts/build_all_json.py` — merge numbered page files into one `all.json` (optional)
- `scripts/run.py` — structured and free-text search over saved pages
- `data/` — where scraped page folders live (e.g. `data/prov_33/1.json`)

Quick workflow
--------------
1. Scrape pages from MagangHub and save them locally.
2. (Optional) Merge page files into a single `all.json` for convenience.
3. Use `scripts/run.py` to search, filter, sort and export matches.

Prerequisites
-------------
- Python 3.8+
- (Recommended) Virtual environment

Install
-------
From the project root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate   # PowerShell / cmd
python -m pip install -r requirements.txt
```

1) Scrape (save pages)
-----------------------
Use the scraper to fetch pages and write them into a folder such as `data/prov_33`.

Single-line example (PowerShell / bash):

```bash
python scripts/scrape_and_save.py --save-dir data/prov_33 --kode_provinsi 33
```

Important options
- `--save-dir` (required): directory to write pages
- `--start-page`: default 1
- `--limit`: items per page (default 100)
- `--max-pages`: optional cap
- `--delay`: politeness delay between requests

2) Merge pages (optional)
--------------------------
Combine numeric page files into `all.json`.

Single-line example:

```bash
python scripts/build_all_json.py --dir data/prov_33
```

3) Search saved pages
---------------------
`scripts/run.py` supports both free-text and structured searches.

Structured filters (examples):
- `--nama_kabupaten` — space-separated tokens (OR within field). Prefixes like `KAB.` / `KOTA` are removed for matching.
- `--program_studi` — tokens matched against program titles parsed from `program_studi`.
- `--posisi` — tokens matched against the `posisi` (title).
- `--deskripsi_posisi` — tokens matched in job description (and related fields).
- `--gov` — government filter: `1` = government postings only, `0` = non-government only, `2` = both (default).
- `--dir all` — search every province folder under `data/`.
- `--out` — write matched items to a JSON file (adds helper fields `_applicants_per_slot` and `_acceptance_prob`).

By default structured filters are combined with logical AND (an item must match every provided structured filter). Within a field tokens act as OR (match any). `--mode and|or` applies to free-text `--deep` queries.

One-line examples (single line per shell)
---------------------------------------

- Bash / PowerShell (search Hukum vacancies in Surakarta or Boyolali, government postings, sorted by acceptance desc):

```bash
python scripts/run.py --dir all --nama_kabupaten "surakarta boyolali" --program_studi "hukum" --gov 1 --accept desc
```

- Windows cmd (same command in cmd.exe):

```cmd
python scripts\run.py --dir all --nama_kabupaten "surakarta boyolali" --program_studi "hukum" --gov 1 --accept desc
```

Explanation of the example
--------------------------
- `--dir all`: search all `data/` subfolders (each province folder)
- `--nama_kabupaten "surakarta boyolali"`: match either location token (cleaned, case-insensitive)
- `--program_studi "hukum"`: match program titles containing "hukum"
- `--gov 1`: only include vacancies with government agency information
- `--accept desc`: sort results by estimated acceptance probability (descending)

Free-text search example
------------------------
Search across multiple fields in one string (tokens split by whitespace):

```bash
python scripts/run.py --dir data/prov_33 --deep "python backend yogyakarta" --mode or
```

Output columns and saved fields
-------------------------------
- Displayed columns: posisi, perusahaan, kabupaten, kuota, terdaftar, accept%
- `accept%` is computed as: min(1.0, jumlah_kuota / (jumlah_terdaftar + 1))
- Saved JSON (when using `--out`) includes `_applicants_per_slot` and `_acceptance_prob` per item.

Troubleshooting & tips
----------------------
- Run scripts from the project root and activate your virtualenv to avoid `ModuleNotFoundError` for `maganghub_client`.
- If a search returns zero results, try removing one structured filter or using fewer tokens, or run a free-text `--deep` query to inspect matches.
- If you want looser structured logic, ask to add a `--struct-mode` flag (OR vs AND across structured filters) or a `--show-matches` debug option.

Developer notes
---------------
- `maganghub_client/search.py` implements `VacancySearch` and `search_deep` (tokenized search and program_studi parsing).
- `maganghub_client/scraper.py` writes an ISO `_scraped_at` timestamp into saved page JSON files.
- The HTTP client uses `requests.Session` with retries for robustness.

Next steps / optional improvements
---------------------------------
- Add fuzzy matching (typo tolerance) using `rapidfuzz`.
- Add CSV/Excel export or an option to include the scrape timestamp in filenames.
- Add unit tests for search filters and scraper behavior.

License & attribution
---------------------
This project consumes MagangHub's public API (Kementerian Ketenagakerjaan). Use data responsibly and comply with any API terms.

If you want a shorter quickstart or a maintainer-focused README, tell me which audience and I will produce a trimmed variant.


Quick concepts

This is a structured, professional README for the MagangHub scraping and search tools.

## Overview

This repository provides a command-line toolkit to scrape the MagangHub public vacancies API, merge results, and perform searches on the saved data.

## Features

- **Scraping**: Fetch and save vacancies from the API.
- **Merging**: Combine multiple JSON files into a single file for easier access.
- **Search CLI**: A command-line interface for searching through saved vacancies with various filters.

## Usage

### Scraping

To scrape data, use the following command:

```bash
python scripts/scrape_and_save.py --save-dir data/prov_33 --kode_provinsi 33
```

### Merging

To merge JSON files, run:

```bash
python scripts/build_all_json.py --dir data/prov_33
```

### Searching

To search through saved vacancies, use:

```bash
python scripts/run.py --dir data/prov_33 --nama_kabupaten "example" --gov 1
```

## Examples

### Government Postings

To filter for government postings, use the `--gov` flag:

```bash
python scripts/run.py --dir all --gov 1
```

### Free-text Search

For a free-text search, you can use:

```bash
python scripts/run.py --dir data/prov_33 --deep "search term"
```

## Conclusion

This toolkit is designed to help users efficiently scrape, merge, and search through job vacancies from the MagangHub API. For further assistance, please refer to the documentation or contact support.
3. Run `scripts/run.py` to filter and inspect results locally.

Prerequisites

--------------

- Python 3.8+
- A virtual environment (recommended).

Install

--------------

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

If you prefer not to install `tabulate`, the search CLI will fall back to a simple text table.

1) Scrape (save pages)

--------------

Use the scraper to fetch pages and save them under a directory such as `data/prov_33` (folder is created automatically). Each page is saved as `1.json`, `2.json`, ... until the API returns an empty `data` list.

Example (province code 33):

```powershell
python .\scripts\scrape_and_save.py --save-dir data\prov_33 --kode_provinsi 33
```

Options

- `--save-dir` (required) — directory to write pages (created if missing)
- `--start-page` — default 1
- `--limit` — items per page (default 100)
- `--max-pages` — optional cap
- `--delay` — seconds between requests (politeness)

Notes

- Saved files are the raw JSON responses from the API. Keep the `data/` folder private — it may contain many files.

2) (Optional) Merge pages into a single file

--------------

If you prefer a single file, run the merger which reads numeric `*.json` files and writes `all.json`:

```powershell
python .\scripts\build_all_json.py --dir data\prov_33
```

Output structure (simple):

```json
{ "data": [ ...all items... ], "meta": { "pages": [ {"file":"1.json","count":10}, ...], "total_items": N }}
```

3) Search saved pages (recommended)

--------------

The main interactive CLI is `scripts/run.py`. It supports two modes:

- Free-text `--deep` search across many fields (posisi, deskripsi_posisi, perusahaan, program_studi, jenjang).
- Structured filters that let you specify fields explicitly (recommended for advanced queries).

Examples

Structured search (no `--deep` required):

```powershell
python .\scripts\run.py --dir data\prov_33 --nama_kabupaten "boyolali surakarta sukoharjo" --program_studi "hukum ekonomi islam" --posisi "" --deskripsi_posisi "" --accept desc
```

- `--nama_kabupaten` — space-separated tokens (OR within field). Matches cleaned `nama_kabupaten` (prefixes like `KAB.` / `KOTA` are removed) or province. Example: `boyolali`.
- `--program_studi` — tokens matched against parsed `program_studi` titles.
- `--posisi` — tokens matched against `posisi` text.
- `--deskripsi_posisi` — tokens matched against `deskripsi_posisi`.
- `--accept` — `desc` or `asc` to sort results by estimated acceptance percentage.
- `--dir all` — special value: search across every subfolder under `data/` (e.g. `data/prov_33`, `data/prov_34`, ...).
- `--out` — save matched items (with computed fields) to a JSON file.

Government postings filter
----------------------------

You can filter results by whether a vacancy is a government posting using `--gov` with numeric values:

- `1` = only government postings (either `government_agency.government_agency_name` or `sub_government_agency.sub_government_agency_name` is present)
- `0` = only non-government postings (both fields empty/null)
- `2` = both (default — include government and non-government)

One-line examples

- Bash / PowerShell (single-line):

```bash
python scripts/run.py --dir all --nama_kabupaten "surakarta boyolali" --program_studi "hukum" --gov 1 --accept desc
```

- Windows cmd (single-line):

```cmd
python scripts\run.py --dir all --nama_kabupaten "surakarta boyolali" --program_studi "hukum" --gov 1 --accept desc
```

Free-text search (simple):

```powershell
python .\scripts\run.py --dir data\prov_33 --deep "sleman yogyakarta marketing Manajemen Pemasaran"
```

- `--mode` controls token logic for `--deep` (`and` or `or`, default `or`).

What the table shows

--------------

The table displays these columns:

- `id_posisi` — the vacancy unique id
- `posisi` — position title
- `perusahaan` — company name
- `kabupaten` — district/city
- `kuota` — jumlah_kuota (slots)
- `terdaftar` — jumlah_terdaftar (registered applicants)
- `accept%` — estimated acceptance probability as a percentage, computed as:

  acceptance_prob = min(1.0, jumlah_kuota / (jumlah_terdaftar + 1))

This is a simple, naive estimate assuming uniform random selection. It is only an approximate indicator.

Saved JSON

--------------

If you use `--out results.json`, each saved item will include two helper fields:

- `_applicants_per_slot` — (jumlah_terdaftar + 1) / jumlah_kuota (raw competitiveness)
- `_acceptance_prob` — acceptance probability as a fraction (0..1)

Troubleshooting

--------------

- If you get `ModuleNotFoundError: No module named 'maganghub_client'` when running a script directly, run from the repo root and the scripts already add the project root to `sys.path` so `python scripts\run.py ...` should work. If you still see errors, ensure your working directory is the project root and your virtualenv is activated.

- If `tabulate` is not installed, the CLI falls back to a readable ASCII table.

Development notes

--------------

- `maganghub_client/` contains a small client, dataclasses and parsing helpers. The code attempts to be defensive: it preserves raw JSON under `raw` for fields we don't explicitly map.
- The scraper uses `requests.Session` with retry/backoff for robustness.

Next improvements (optional)

- Add fuzzy matching (typo tolerance) for program or posisi using `rapidfuzz`.
- Add exact-phrase search and quoted-space parsing for `--deep`.
- Export CSV/Excel with selected columns.

License & attribution

--------------

Use this code responsibly. The API belongs to Kementerian Ketenagakerjaan (Kemnaker). This tool only consumes their public API and stores local copies of responses for offline searching and analysis.

Contact / Support

--------------

If you want changes to the CLI flags, sorting, or output format, tell me which behavior you prefer and I will update the scripts accordingly.
